import pandas as pd
import re

# =========================
# LOAD
# =========================
df = pd.read_csv("game_149593_raw.csv")

lines = []

for row in df["raw_event"]:
    parts = str(row).split("\n")
    for p in parts:
        p = p.strip()
        if p:
            lines.append(p)

# =========================
# CLEAN
# =========================
cleaned = lines.copy()

index_end = cleaned.index('Игра завершена')
cleaned = cleaned[index_end:]
cleaned = cleaned[::-1]

index_start = cleaned.index('1 период')
cleaned = cleaned[index_start:]

# =========================
# PARSE EVENTS
# =========================
events = []
current_period = None

i = 0
while i < len(cleaned):
    line = cleaned[i]

    if "период" in line.lower():
        current_period = line
        i += 1
        continue

    if re.match(r"\d{2}:\d{2}", line):
        time = line

        action_idx = i + 1
        while action_idx < len(cleaned) and re.match(r"\d+:\d+", cleaned[action_idx]):
            action_idx += 1

        if action_idx < len(cleaned):
            action = cleaned[action_idx]

            player_idx = action_idx + 1
            if player_idx < len(cleaned):
                player = cleaned[player_idx]

                if not re.match(r"\d{2}:\d{2}", player) and "период" not in player.lower():
                    events.append({
                        "period": current_period,
                        "time": time,
                        "player": player,
                        "action": action
                    })
                    i = player_idx + 1
                    continue

    i += 1

events_df = pd.DataFrame(events)


# =========================
# CLASSIFY EVENTS
# =========================
def classify(action):
    a = action.lower().strip()
    if a == "2 очка":
        return "2pt_made"
    if a == "3 очка":
        return "3pt_made"
    if a == "1 очко" or "1 очко" in a or "штрафной бросок" in a:
        return "ft_made"
    return "other"


events_df["event_type"] = events_df["action"].apply(classify)

# =========================
# LOAD TEAMS
# =========================
teams = pd.read_csv("teams_roster_full.csv")
teams["surname"] = teams["name"].apply(lambda x: x.split()[0].lower())
surname_to_team = dict(zip(teams["surname"], teams["team"]))


def get_team(player_str):
    if not isinstance(player_str, str):
        return None
    parts = player_str.split()
    if len(parts) < 2:
        return None
    surname = parts[1].lower()
    return surname_to_team.get(surname, None)


events_df["team"] = events_df["player"].apply(get_team)

# =========================
# ПРАВИЛЬНЫЙ ПОДСЧЕТ СЧЕТА
# =========================
print("=" * 60)
print("ПРАВИЛЬНЫЙ ПОДСЧЕТ СЧЕТА (уникальные события):")
print("=" * 60)

# Берем только попадания
made_shots = events_df[events_df["event_type"].isin(["2pt_made", "3pt_made", "ft_made"])].copy()

# Удаляем дубликаты (одинаковое время, действие, игрок)
made_shots_unique = made_shots.drop_duplicates(subset=['time', 'action', 'player'])

print(f"Всего событий с попаданиями: {len(made_shots)}")
print(f"Уникальных попаданий: {len(made_shots_unique)}")

# Подсчитываем очки по уникальным событиям
score_correct = {"Крылья": 0, "Los Lobos Locos": 0}

# Для отладки - считаем отдельно по типам
two_pts = made_shots_unique[made_shots_unique['event_type'] == '2pt_made']
three_pts = made_shots_unique[made_shots_unique['event_type'] == '3pt_made']
ft = made_shots_unique[made_shots_unique['event_type'] == 'ft_made']

print(f"\nУникальных 2-очковых: {len(two_pts)}")
print(f"Уникальных 3-очковых: {len(three_pts)}")
print(f"Уникальных штрафных: {len(ft)}")

# Считаем очки по командам
for _, row in two_pts.iterrows():
    if row['team'] in score_correct:
        score_correct[row['team']] += 2

for _, row in three_pts.iterrows():
    if row['team'] in score_correct:
        score_correct[row['team']] += 3

for _, row in ft.iterrows():
    if row['team'] in score_correct:
        score_correct[row['team']] += 1

print("\n" + "=" * 60)
print("ФИНАЛЬНЫЙ СЧЕТ (уникальные события):")
print(f"Крылья: {score_correct['Крылья']}")
print(f"Los Lobos Locos: {score_correct['Los Lobos Locos']}")
print("=" * 60)

# Проверяем
if score_correct['Крылья'] == 50 and score_correct['Los Lobos Locos'] == 54:
    print("\n✅ СЧЕТ СОВПАДАЕТ! 50:54")
elif score_correct['Крылья'] == 54 and score_correct['Los Lobos Locos'] == 50:
    print("\n✅ СЧЕТ СОВПАДАЕТ! 54:50")
else:
    print(f"\n❌ Счет не совпадает. Должно быть 50:54 или 54:50")
    diff_krylya = score_correct['Крылья'] - 50
    diff_lobos = score_correct['Los Lobos Locos'] - 54
    print(f"Разница: Крылья {diff_krylya}, Lobos {diff_lobos}")

# Детальный подсчет по игрокам
print("\n" + "=" * 60)
print("ДЕТАЛЬНЫЙ ПОДСЧЕТ ПО ИГРОКАМ:")
print("=" * 60)

player_scores = {}
for _, row in made_shots_unique.iterrows():
    player = row['player']
    team = row['team']
    event = row['event_type']

    if player not in player_scores:
        player_scores[player] = {'team': team, '2pt': 0, '3pt': 0, 'ft': 0}

    if event == '2pt_made':
        player_scores[player]['2pt'] += 1
    elif event == '3pt_made':
        player_scores[player]['3pt'] += 1
    elif event == 'ft_made':
        player_scores[player]['ft'] += 1

for player, stats in sorted(player_scores.items()):
    total = stats['2pt'] * 2 + stats['3pt'] * 3 + stats['ft']
    print(f"\n{player} ({stats['team']}):")
    print(f"  2pt: {stats['2pt']} = {stats['2pt'] * 2} очков")
    print(f"  3pt: {stats['3pt']} = {stats['3pt'] * 3} очков")
    print(f"  FT: {stats['ft']} = {stats['ft']} очков")
    print(f"  ВСЕГО: {total} очков")

# Сохраняем результат
made_shots_unique.to_csv("correct_made_shots.csv", index=False)
print("\nРезультат сохранен в 'correct_made_shots.csv'")

# Проверяем дублирование по времени для конкретных игроков
print("\n" + "=" * 60)
print("ПРОВЕРКА ДУБЛИРОВАНИЯ ПО ВРЕМЕНИ:")
print("=" * 60)

# Смотрим, какие события дублируются чаще всего
duplicates = made_shots.groupby(['time', 'action', 'player']).size().reset_index(name='count')
duplicates = duplicates[duplicates['count'] > 1].sort_values('count', ascending=False)
print("\nСобытия с дубликатами (более 1 раза):")
print(duplicates.head(20))
