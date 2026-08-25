import datetime
import os
import re
import asyncio
import pandas as pd
from playwright.async_api import async_playwright

URL = "https://panoramicams.com/porto-pollo-kite-zone/"
CSV_FILE = "porto_pollo_wind_history.csv"
COLUMNS = ["timestamp", "velocita_knots", "raffica_knots", "direzione_cardinal", "direzione_deg"]

def deg_to_cardinal(deg):
    if deg is None:
        return "N/A"
    cardinals = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return cardinals[round((deg % 360) / 22.5) % 16]

async def scrape_once():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)
        
        content = await page.inner_text("body")
        speed_match = re.search(r"Velocit(?:a|à|&agrave;)[^0-9\n\r]*([\d]+[.,]?[\d]*)\s*nodi", content, re.IGNORECASE)
        gust_match = re.search(r"Raffica[^0-9\n\r]*([\d]+[.,]?[\d]*)\s*nodi", content, re.IGNORECASE)
        
        speed = float(speed_match.group(1).replace(",", ".")) if speed_match else None
        gust = float(gust_match.group(1).replace(",", ".")) if gust_match else None

        direction_deg = None
        try:
            style_attr = await page.locator(".winddir").get_attribute("style")
            if style_attr:
                deg_match = re.search(r"(\d+(?:\.\d+)?)\s*deg", style_attr)
                if deg_match:
                    direction_deg = round(float(deg_match.group(1)), 1)
        except Exception:
            pass

        await browser.close()

        if speed is not None:
            reading = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "velocita_knots": speed,
                "raffica_knots": gust,
                "direzione_cardinal": deg_to_cardinal(direction_deg),
                "direzione_deg": direction_deg
            }
            df_new = pd.DataFrame([reading], columns=COLUMNS)
            file_exists = os.path.exists(CSV_FILE)
            df_new.to_csv(CSV_FILE, mode="a", header=not file_exists, index=False)
            print(f"Logged: {reading}")

asyncio.run(scrape_once())