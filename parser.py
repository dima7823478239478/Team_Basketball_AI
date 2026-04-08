from playwright.sync_api import sync_playwright
import pandas as pd

url = "https://ablforpeople.com/game/149593/timeline"

data = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(url)
    page.wait_for_timeout(5000)

    # Пытаемся найти все элементы (потом уточним селектор)
    elements = page.query_selector_all("div")

    for el in elements:
        text = el.inner_text().strip()

        # фильтруем мусор
        if len(text) < 5:
            continue

        # простая эвристика: события обычно содержат время
        if ":" in text:
            data.append(text)

    browser.close()

# превращаем в DataFrame
df = pd.DataFrame(data, columns=["raw_event"])

# сохраняем
df.to_csv("game_149593_raw.csv", index=False)

print("Сохранено:", len(df), "событий")