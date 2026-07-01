import requests
import pandas as pd
from datetime import datetime
import time
import os
import subprocess
import logging

# ── CONFIG ────────────────────────────────────────────────────────────────────
SAVE_FOLDER = r"C:\Users\agusm\Downloads\Pythonclass\inflation-tracker"
PAGES = 20
INITIAL_WAIT_SECONDS = 30      # esperar a que el WiFi se reconecte si la PC se despertó
MAX_RETRIES_PER_PAGE = 3       # reintentos por página antes de saltearla
RETRY_BACKOFF_SECONDS = 5      # espera entre reintentos (se multiplica cada intento)
GIT_PUSH_RETRIES = 2           # reintentos para el push a GitHub
# ─────────────────────────────────────────────────────────────────────────────

LOG_FILE = os.path.join(SAVE_FOLDER, "scraper.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


def scrape_carrefour():
    all_products = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    log.info("Starting weekly scrape...")

    consecutive_empty_pages = 0

    for p in range(PAGES):
        start, end = p * 50, p * 50 + 49
        url = f"https://www.carrefour.com.ar/api/catalog_system/pub/products/search/almacen?_from={start}&_to={end}&O=OrderByTopSaleDESC"

        page_data = None
        for attempt in range(1, MAX_RETRIES_PER_PAGE + 1):
            try:
                res = requests.get(url, headers=headers, timeout=15)
                res.raise_for_status()
                page_data = res.json()
                break  # success, no need to retry
            except Exception as e:
                wait = RETRY_BACKOFF_SECONDS * attempt
                log.warning(f"Page {p+1}, attempt {attempt}/{MAX_RETRIES_PER_PAGE} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)

        if page_data is None:
            log.error(f"Page {p+1} failed after {MAX_RETRIES_PER_PAGE} attempts. Skipping this page.")
            consecutive_empty_pages += 1
            if consecutive_empty_pages >= 3:
                log.error("3 consecutive pages failed. Aborting scrape (likely connection issue).")
                break
            continue

        if not page_data:
            # empty page = reached the end of the catalog, this is normal
            break

        consecutive_empty_pages = 0

        for item in page_data:
            try:
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
            except (KeyError, IndexError, TypeError, AttributeError) as e:
                log.warning(f"Skipping malformed product on page {p+1}: {e}")
                continue

        log.info(f"Page {p+1} processed ({len(all_products)} products accumulated)")
        time.sleep(1.5)

    return pd.DataFrame(all_products)


def git_commit_and_push(filename):
    """Best-effort commit and push. Never raises; only logs success or failure."""
    try:
        subprocess.run(["git", "add", filename], cwd=SAVE_FOLDER, check=True,
                        capture_output=True, text=True)
        commit_msg = f"Auto: add {os.path.basename(filename)} - {datetime.now().strftime('%Y-%m-%d')}"
        commit = subprocess.run(["git", "commit", "-m", commit_msg], cwd=SAVE_FOLDER,
                                 capture_output=True, text=True)
        if commit.returncode != 0 and "nothing to commit" not in commit.stdout.lower():
            log.error(f"git commit failed: {commit.stdout} {commit.stderr}")
            return

        for attempt in range(1, GIT_PUSH_RETRIES + 1):
            push = subprocess.run(["git", "push"], cwd=SAVE_FOLDER,
                                   capture_output=True, text=True, timeout=30)
            if push.returncode == 0:
                log.info("Pushed to GitHub successfully.")
                return
            log.warning(f"git push attempt {attempt}/{GIT_PUSH_RETRIES} failed: {push.stderr.strip()}")
            time.sleep(5)

        log.error("git push failed after all retries. CSV was saved locally, will need manual push.")

    except FileNotFoundError:
        log.error("git command not found. Is Git installed and in PATH? CSV saved locally only.")
    except subprocess.CalledProcessError as e:
        log.error(f"git command failed: {e.stdout} {e.stderr}")
    except Exception as e:
        log.error(f"Unexpected error during git push: {e}")


if __name__ == "__main__":
    os.chdir(SAVE_FOLDER)

    log.info(f"Waiting {INITIAL_WAIT_SECONDS}s for network to be ready (in case PC just woke up)...")
    time.sleep(INITIAL_WAIT_SECONDS)

    df = scrape_carrefour()

    if not df.empty:
        filename = f"precios_almacen_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        log.info(f"Done! {len(df)} products saved to '{filename}'")

        git_commit_and_push(filename)
    else:
        log.error("No data retrieved. Check your connection or if Carrefour changed their API.")

    log.info("Run finished.\n")



      

