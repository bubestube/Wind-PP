import datetime
import os
import re
import asyncio
import pandas as pd
from playwright.async_api import async_playwright

URL = "https://panoramicams.com/porto-pollo-kite-zone/"
CSV_FILE = "porto_pollo_wind_history.csv"
COLUMNS = [
    "timestamp",
    "velocita_knots",
    "raffica_knots",
    "temperatura_c",
    "direzione_cardinal",
    "direzione_deg",
]

def deg_to_cardinal(deg):
    if deg is None:
        return "N/A"
    cardinals = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]
    return cardinals[round((deg % 360) / 22.5) % 16]

async def scrape_once():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)

        # Expand accordion for temperature
        try:
            temp_button = page.locator("button:has-text('Temperatura')")
            if await temp_button.count() > 0:
                await temp_button.first.click()
                await page.wait_for_timeout(2000)
        except Exception:
            pass

        extracted = await page.evaluate(r"""() => {
            const meteo = document.querySelector('.wp-block-panoramicamsweather-meteostation');
            if (!meteo) return null;
            
            const text = meteo.innerText || '';
            const windDirEl = meteo.querySelector('.winddir');
            let windDir = null;
            if (windDirEl) {
                const style = windDirEl.getAttribute('style') || '';
                const match = style.match(/(\d+(?:\.\d+)?)\s*deg/);
                if (match) windDir = parseFloat(match[1]);
            }
            
            return {
                rawText: text,
                windDir: windDir
            };
        }""")

        await browser.close()

        if not extracted or not extracted.get("rawText"):
            print("Failed to find meteo element.")
            return

        raw_text = extracted["rawText"]

        speed_match = re.search(r"Velocit(?:a|à|&agrave;)[^\d]*([\d]+[.,]?[\d]*)", raw_text, re.IGNORECASE)
        gust_match = re.search(r"Raffica[^\d]*([\d]+[.,]?[\d]*)", raw_text, re.IGNORECASE)
        temp_match = re.search(r"Temperatura[\s\S]*?([\-]?\d+[.,]?\d*)\s*(?:°|C|gradi)?", raw_text, re.IGNORECASE)

        speed = float(speed_match.group(1).replace(",", ".")) if speed_match else None
        gust = float(gust_match.group(1).replace(",", ".")) if gust_match else speed
        
        temperature = None
        if temp_match:
            try:
                temperature = float(temp_match.group(1).replace(",", "."))
            except ValueError:
                pass

        direction_deg = extracted.get("windDir")

        if speed is not None:
            reading = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "velocita_knots": speed,
                "raffica_knots": gust,
                "temperatura_c": temperature,
                "direzione_cardinal": deg_to_cardinal(direction_deg),
                "direzione_deg": direction_deg,
            }
            df_new = pd.DataFrame([reading], columns=COLUMNS)
            file_exists = os.path.exists(CSV_FILE)
            df_new.to_csv(CSV_FILE, mode="a", header=not file_exists, index=False)
            print(f"Logged reading: {reading}")

if __name__ == "__main__":
    asyncio.run(scrape_once())
