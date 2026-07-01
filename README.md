# Argentine Inflation Tracker

[**🔗 Live dashboard on Streamlit Cloud**](https://argentine-inflation-tracker-7ccbexajsjfk2zi2wlvjsv.streamlit.app/)

A weekly scraper of grocery prices from the "almacén" (pantry) category of Carrefour Argentina, used to track real inflation of a mass-consumption basket and compare it against Argentina's official CPI (INDEC).

## How it works

`scraper.py` runs automatically every Saturday via Windows Task Scheduler. It scrapes Carrefour's public API (`/api/catalog_system/pub/products/search/almacen`), saves a CSV with ~1000 products (`precios_almacen_YYYYMMDD.csv`), and pushes it to this repo with an automatic commit and push.

## Available data

| File | Date | Products |
|---|---|---|
| `precios_almacen_20260308.csv` to `20260405.csv` | Mar-Apr 2026 | ~1000 each |
| `precios_almacen_20260412.csv` to `20260426.csv` | Apr 2026 | ~1000 each |
| `precios_almacen_20260510.csv`, `20260518.csv`, `20260531.csv` | May 2026 | ~1000 each |
| `precios_almacen_20260621.csv`, `20260701.csv` | Jun-Jul 2026 | ~1000 each |
| `canasta_carrefour_20260322.csv` | Mar 2026 | reduced basket |

**Note on gaps:** between April and June 2026 the scraper ran irregularly (Task Scheduler required the laptop to be on, plugged in, and logged in at the exact scheduled time), so dates aren't always spaced 7 days apart. See the "Methodology" section below for how this is handled in the analysis. This was fixed in July 2026 (see Changelog).

## Inflation analysis methodology

Since measurements aren't always spaced exactly one week apart, the analysis **does not assume even intervals**. In addition, to average price changes across a whole basket of products, the project uses the **Jevons index** (the same type of calculation used by official statistics offices, including Argentina's INDEC, for elementary price aggregates) instead of a simple average. This was arrived at after testing three methods and finding two of them gave unreliable results:

| Method | Problem |
|---|---|
| Arithmetic mean of each product's % change | Highly sensitive to outliers: 2-3 products with large jumps (e.g. +80%) distort the average even though they're a small minority of the basket |
| Ratio of average prices (Dutot index) | Biased toward expensive products: a $19,000 olive oil carries the same weight in the average as a $500 pack of noodles, when it should be weighted by relative change, not absolute price |
| **Geometric mean of price relatives (Jevons index)** ✅ | Robust to both problems — the one used in this project |

**Calculation steps:**

1. Build a **fixed basket**: only products present in *every* compared date (to avoid mixing catalog additions/removals with actual price changes). Product and brand names are normalized to lowercase before comparison, to avoid excluding products due to a capitalization mismatch between weeks.
2. For each interval between measurements, compute each product's price ratio (`final_price / initial_price`) and average those ratios **geometrically** (Jevons), not arithmetically.
3. Adjust that ratio for the **actual number of days elapsed** between measurements:

   ```
   daily_change = jevons_ratio ^ (1 / days_elapsed) - 1
   ```

4. Express it as a monthly equivalent (`(1 + daily_change)^30 - 1`) to compare directly against INDEC's CPI, which is published monthly.

### Results (March 22 – July 1, 2026, basket of 109 products present across all 11 measurements)

| Metric | Value |
|---|---|
| Monthly equivalent inflation (List Price) | 1.89% |
| Monthly equivalent inflation (Promo Price) | 3.69% |
| Cumulative change for the period (101 days) | 12.96% |

**Interesting finding:** the "list" price rose noticeably less than the effective promotional price — almost half as much. This suggests **promotions shrank over time**: the "official" shelf price barely moved, but what people actually end up paying (with active discounts) rose faster. Worth tracking over time to confirm whether the trend holds.

Both figures are in line with INDEC's official CPI for the same period (~2.8%-3.7% monthly in April-May 2026), which validates that the Jevons index with a fixed basket is a better proxy than the methods tried earlier.

## Changelog

### July 2026 (part 2) — fixing the calculation method
- Found that the arithmetic mean of individual % changes gave unrealistic results (e.g. 11% monthly) due to outlier sensitivity — a few products with large price jumps distorted the aggregate.
- Tried replacing it with a ratio of average prices (Dutot), which fixed the outlier problem but introduced a bias toward expensive products.
- Adopted the **Jevons index** (geometric mean of price ratios), consistent with official statistics methodology, in both `dashboard.py` and `analysis.py`.
- Unified the text normalization rule (lowercase + trimmed) between `dashboard.py` and `analysis.py` — they previously gave different basket sizes (621 vs 109 products) for the same dataset because one of the two wasn't lowercasing product names before comparing.
- Fixed a bug in `dashboard.py` where duplicate products within a single CSV (same name+brand repeated) multiplied rows when merging the 11 weeks together, eventually hanging the app.
- Added `analysis.py`: a standalone matplotlib script to run locally, with robust handling of CSVs in a different format (skips them with a warning instead of breaking the whole analysis).

### July 2026 (part 1) — scraper robustness and automation
- **Retries with backoff** per page instead of aborting the whole scrape on the first error.
- **30s initial wait** on startup, to give WiFi time to reconnect if the PC just woke from sleep.
- **Persistent logging** to `scraper.log` with a timestamp for every run (previously only visible in the console, lost when running without a logged-in session).
- **Automatic commit and push to GitHub** at the end of each run (best-effort: if it fails, the CSV is still saved locally and the error is logged).
- Reconfigured the Windows Task Scheduler task:
  - `Run whether user is logged on or not`
  - `Wake the computer to run this task`
  - `If the scheduled start is missed, run the task as soon as possible`
  - Task history enabled to audit future runs.

These changes followed the discovery that the scraper had stopped pushing data to GitHub since April 5th, even though it kept running locally on and off due to the previous Task Scheduler setup (which required the laptop plugged in and logged in at the exact scheduled time, with no retry if a run was missed).

## Repo files

- `scraper.py` — scraping script + automatic push to GitHub
- `analysis.py` — local analysis with matplotlib charts (basket index + top product-level price changes)
- `dashboard.py` — Streamlit dashboard
- `precios_almacen_*.csv` — weekly data
- `precios_almacen_20260308.csv`, `20260315.csv` — old format (Spanish column names), excluded from analysis due to schema incompatibility
- `reporte_comparativo_final.csv` — comparative report
- `top_aumentos_semanal.png` — visualization of the biggest weekly increases
- `requirements.txt` — dependencies
