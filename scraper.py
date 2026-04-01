import requests
import pandas as pd
from datetime import datetime
import time
import os

# ── CONFIG ────────────────────────────────────────────────────────────────────
SAVE_FOLDER = r"C:\Users\agusm\Downloads\Pythonclass\inflation-tracker" 
PAGES = 20  
# ─────────────────────────────────────────────────────────────────────────────

def scrape_carrefour():
    all_products = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting weekly scrape...")

    for p in range(PAGES):
        start, end = p * 50, p * 50 + 49
        url = f"https://www.carrefour.com.ar/api/catalog_system/pub/products/search/almacen?_from={start}&_to={end}&O=OrderByTopSaleDESC"

        try:
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()
            data = res.json()

            if not data:
                break

            for item in data:
                item_data = item['items'][0]
                commertial_offer = item_data['sellers'][0]['commertialOffer']
                unit = item_data.get('measurementUnit', 'un')
                unit = unit.replace('GRM', 'g').replace('MLT', 'ml').replace('KGM', 'kg')

                all_products.append({
                    "Date": datetime.now().strftime('%Y-%m-%d'),
                    "Product": item.get('productName').strip().lower(),
                    "Brand": item.get('brand').strip().lower(),
                    "Price": commertial_offer.get('Price'),
                    "List_Price": commertial_offer.get('ListPrice'),
                    "Unit": f"{item_data.get('unitMultiplier', 1)} {unit}"
                })

            print(f" > Page {p+1} processed ({len(all_products)} products accumulated)")
            time.sleep(1.5)

        except Exception as e:
            print(f" Error on page {p+1}: {e}")
            break

    return pd.DataFrame(all_products)


if __name__ == "__main__":
    os.chdir(SAVE_FOLDER)

    df = scrape_carrefour()

    if not df.empty:
        filename = f"precios_almacen_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\nDone! {len(df)} products saved to '{filename}'")
    else:
        print("No data retrieved. Check your connection.")



      

