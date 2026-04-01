# Argentine Grocery Inflation Tracker 🇦🇷

## What is this project?

I built this to track real food inflation in Argentina by scraping price data directly from Carrefour's website every week. The idea is pretty simple — instead of waiting for the government's monthly CPI report, I collect prices myself and see how they move week over week.

Argentina has a well-known inflation problem so tracking prices at a high frequency makes a lot of sense here. Things can move fast and monthly reports tend to smooth over what's actually happening on the ground.

## How it works

- **Data source:** Carrefour Argentina (`carrefour.com.ar`) — Almacén (Grocery) category
- **Method:** Direct API calls to Carrefour's product search endpoint — no browser needed, their API is public
- **Frequency:** Weekly snapshots, automated every Sunday

---

## Project log

###  Week 1 — March 8, 2026 (Baseline)

First scrape ever. Built the initial script, hit Carrefour's API, and saved 250 grocery products to a CSV. This is the baseline everything else gets compared against.

At this point the script was fully manual — just running cells in a Jupyter notebook one by one.

---

### Week 2 — March 15, 2026

Ran the same scraper one week later and did the first Week-over-Week comparison.

**Results (W1 → W2):**
- Products matched: 50
- Weekly inflation rate: **+2.07%**
- Some items spiked over 30% — turned out to be promotions expiring, not real price hikes

![Weekly Price Increases](top_aumentos_semanal.png)

---

###  Week 3 — March 22, 2026

Third scrape. Now with 3 data points I could calculate cumulative inflation for the first 15 days of March.

**Results (W1 → W3, using promotional price):**
- Products matched: 49
- Cumulative inflation: **-0.16%**

That negative number looked weird so I dug into the distribution:
- 35 out of 49 products had **zero price change**
- 8 went down, 6 went up
- The "decreases" were huge swings (-28%, -25%) from big brands like Maggi and Savora — clearly promotions, not deflation

**Key fix discovered here:** the original code was calculating inflation by dividing the *average price of W3 by the average price of W1*, which is statistically wrong. The correct way is to calculate the % change per product first and then average those. Fixed this in `InflationProject_v2.ipynb`.

---

###  Key improvement: switching to List Price

This is where things got interesting. Carrefour's API returns two price fields:

- `Price` — what you pay at checkout (includes active discounts)
- `List Price` — the official shelf price before any promotion

When I redid the W1 → W3 comparison using `List Price` instead of `Price`, the results changed significantly:

| Metric | Promo Price | List Price |
|---|---|---|
| Cumulative inflation (15 days) | -0.16% | **+0.35%** |
| Products that went down | 8 | 2 |
| No change | 35 | 42 |

The fake "deflation" completely disappeared. Those Maggi and Savora drops were 100% promotional noise. The real inflation signal using List Price was **+0.35% over 15 days** — small but positive, which makes way more sense for Argentina right now.

The conclusion: **Carrefour is keeping list prices stable and using promotions as the main pricing lever.** From here on the scraper saves both columns from the start.

---

###  Week 4 — March 29, 2026 (First automated scrape)

Two big upgrades happened before this scrape:

**1. Automated scraping** — created a standalone `scraper.py` file and set it up with Windows Task Scheduler to run every Sunday automatically. No more running the notebook manually.

**2. Bigger sample** — increased from 5 pages (250 products) to 20 pages (1000 products) so the basket is more statistically robust and more products survive the week-over-week merge.

**Final March 2026 results (W1 → W4):**
- Products with full 4-week history: 48
- Monthly inflation (List Price): **-0.81%**
- Monthly inflation (Promo Price): **+1.57%**

That gap between the two numbers is actually the most interesting finding of the whole month. Carrefour lowered official shelf prices but pulled back on discounts — so on paper prices went down, but if you actually went to the supermarket you paid more. Pretty sneaky move.

The weekly trend also told an interesting story — prices spiked in week 2, dropped in week 3 because of promos, then jumped again in week 4 when those promos ended. If you only looked at the monthly number you'd completely miss that volatility.

Biggest increases were **national brands** (flour +10%, mayonnaise +7.9%). Biggest decreases were all **Carrefour's own private label** products (tomato, corn, lentils) — they clearly cut prices on their own brand to compete.

---

### Dashboard — March 30, 2026

Built a Streamlit dashboard (`dashboard.py`) that reads all the weekly CSVs automatically and displays:

- Key metrics (weeks tracked, monthly inflation List Price vs Promo Price)
- Cumulative inflation trend line across all weeks
- Top 5 biggest increases and decreases
- Price dispersion breakdown (how many products went up, down, or stayed flat)

The dashboard updates automatically whenever a new weekly CSV gets added — no code changes needed.

To run it:
```
C:\Users\agusm\AppData\Local\Python\pythoncore-3.14-64\python.exe -m streamlit run dashboard.py
```

---

## Files in this repo

| File | Description |
|---|---|
| `InflationProyect.ipynb` | Original notebook — shows the full learning process, bugs and all |
| `InflationProject_v2.ipynb` | Improved version — English outputs, fixed calculation, List Price tracking |
| `scraper.py` | Standalone scraper that runs automatically every Sunday via Task Scheduler |
| `dashboard.py` | Streamlit dashboard — reads all CSVs and displays the full analysis |
| `precios_almacen_20260308.csv` | Week 1 data (baseline) |
| `precios_almacen_20260315.csv` | Week 2 data |
| `precios_almacen_20260322.csv` | Week 3 data |
| `precios_almacen_20260329.csv` | Week 4 data (first automated scrape, 1000 products) |

> The original notebook is kept on purpose — it documents the whole learning process including the bugs, the methodology fixes, and why switching to List Price matters. The v2 is the clean version going forward.

---

## Next steps
- Keep collecting weekly data through April and beyond
- Add more product categories beyond Grocery (dairy, meat, cleaning products)
- Correlate price changes with USD/ARS exchange rate using `yfinance`
