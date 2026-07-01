import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import glob
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────
FOLDER = os.path.dirname(os.path.abspath(__file__))
REQUIRED_COLS = {"Date", "Product", "Brand", "Price"}

# ── LOAD ALL CSVS AUTOMATICALLY (skip files with a different schema) ─────────
@st.cache_data
def load_all_weeks():
    files = sorted(glob.glob(os.path.join(FOLDER, "precios_almacen_*.csv")))
    weeks, skipped = [], []
    for f in files:
        df = pd.read_csv(f, encoding="utf-8-sig")
        df.columns = [c.strip() for c in df.columns]
        missing = REQUIRED_COLS - set(df.columns)
        if missing:
            skipped.append((os.path.basename(f), missing))
            continue

        df["Product"] = df["Product"].str.strip().str.lower()
        df["Brand"] = df["Brand"].str.strip().str.lower()
        # Evitar que productos duplicados (mismo Product+Brand en el mismo CSV)
        # multipliquen filas al mergear las 11 semanas entre si
        df = df.drop_duplicates(subset=["Product", "Brand"], keep="first")
        date_str = os.path.basename(f).replace("precios_almacen_", "").replace(".csv", "")
        df["WeekDate"] = datetime.strptime(date_str, "%Y%m%d")
        weeks.append(df)
    return weeks, skipped

weeks, skipped_files = load_all_weeks()

if not weeks:
    st.error("No se encontró ningún precios_almacen_*.csv con el formato esperado.")
    st.stop()

dates = [df["WeekDate"].iloc[0] for df in weeks]

# ── MERGE ALL WEEKS (canasta fija: solo productos presentes en TODAS las fechas) ──
def merge_weeks(weeks):
    base = weeks[0][["Product", "Brand", "Price", "List_Price"]].copy()
    base = base.rename(columns={"Price": "Price_W1", "List_Price": "List_Price_W1"})
    for i, df in enumerate(weeks[1:], 2):
        cols = ["Product", "Brand", "Price"]
        if "List_Price" in df.columns:
            cols.append("List_Price")
        base = base.merge(df[cols], on=["Product", "Brand"])
        base = base.rename(columns={"Price": f"Price_W{i}"})
        if "List_Price" in df.columns:
            base = base.rename(columns={"List_Price": f"List_Price_W{i}"})
    return base

df = merge_weeks(weeks)
n = len(weeks)

# ── VARIACION ACUMULADA POR FECHA, MAS EQUIVALENTE MENSUAL AJUSTADO POR DIAS ──
# Se usa el indice de Jevons (promedio GEOMETRICO de las variaciones relativas
# de cada producto), el mismo tipo de calculo que usan institutos de estadistica
# oficiales (incl. INDEC) para agregados elementales de precios. A diferencia de:
#   - promedio ARITMETICO de % individuales -> muy sensible a outliers grandes
#   - ratio de precios promedio (Dutot)      -> sesgado hacia productos caros
# el promedio geometrico de razones de precio (Price_t / Price_0) es robusto a
# ambos problemas.
relatives_w1 = df["Price_W1"]
cumul = [0.0]
monthly_equiv = [0.0]
for i in range(2, n + 1):
    relatives = df[f"Price_W{i}"] / relatives_w1
    jevons_ratio = relatives.prod() ** (1 / len(relatives))
    pct = (jevons_ratio - 1) * 100
    cumul.append(pct)
    days_elapsed = (dates[i - 1] - dates[0]).days
    if days_elapsed > 0:
        daily_rate = jevons_ratio ** (1 / days_elapsed) - 1
        monthly_equiv.append(((1 + daily_rate) ** 30 - 1) * 100)
    else:
        monthly_equiv.append(0.0)

# ── LIST PRICE INFLATION (primera vs ultima fecha, ajustada por dias, mismo metodo) ──
last_lp = f"List_Price_W{n}"
total_days = (dates[-1] - dates[0]).days
if last_lp in df.columns and "List_Price_W1" in df.columns:
    df["Var_ListPrice_%"] = ((df[last_lp] / df["List_Price_W1"]) - 1) * 100  # se mantiene por producto para el ranking
    lp_relatives = df[last_lp] / df["List_Price_W1"]
    jevons_lp = lp_relatives.prod() ** (1 / len(lp_relatives))
    list_inflation_total = (jevons_lp - 1) * 100
    daily_rate_lp = jevons_lp ** (1 / total_days) - 1 if total_days > 0 else 0
    list_inflation_monthly = ((1 + daily_rate_lp) ** 30 - 1) * 100
else:
    df["Var_ListPrice_%"] = 0
    list_inflation_total = 0
    list_inflation_monthly = 0

promo_inflation_total = cumul[-1]
promo_inflation_monthly = monthly_equiv[-1]

# ── UI ────────────────────────────────────────────────────────────────────────
st.title("🇦🇷 Argentine Grocery Inflation Tracker")
st.caption(
    f"Carrefour Argentina — Almacén category — "
    f"{dates[0].strftime('%d %b %Y')} to {dates[-1].strftime('%d %b %Y')} "
    f"({total_days} días, {n} mediciones, {len(df)} productos comparables)"
)

if skipped_files:
    with st.expander(f"⚠️ {len(skipped_files)} archivo(s) con formato distinto, salteados"):
        for name, missing in skipped_files:
            st.write(f"- `{name}`: faltan columnas {missing}")

# Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Mediciones", f"{n}")
col2.metric("Inflación mensual equiv. (List Price)", f"{list_inflation_monthly:.2f}%",
            help=f"Variación total del período: {list_inflation_total:.2f}% en {total_days} días, ajustada a equivalente mensual")
col3.metric("Inflación mensual equiv. (Promo Price)", f"{promo_inflation_monthly:.2f}%",
            help=f"Variación total del período: {promo_inflation_total:.2f}% en {total_days} días, ajustada a equivalente mensual")

st.divider()

# Trend chart — eje X con fechas reales, no "Week 1, Week 2..."
st.subheader("📈 Variación acumulada en el tiempo")
fig1, ax1 = plt.subplots(figsize=(10, 4))
ax1.plot(dates, cumul, marker="o", color="#e67e22", linewidth=2.5)
ax1.axhline(0, color="black", linewidth=0.8, linestyle="--")
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
ax1.set_ylabel("Variación acumulada vs primera medición (%)")
ax1.grid(True, linestyle="--", alpha=0.5)
for d, v in zip(dates, cumul):
    ax1.annotate(f"{v:.2f}%", (d, v), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8)
fig1.autofmt_xdate()
st.pyplot(fig1)
st.caption("Nota: el eje X usa fechas reales — los intervalos entre mediciones no son siempre parejos, por eso las métricas de arriba usan variación diaria compuesta en vez de asumir semanas parejas.")

st.divider()

# Biggest movers
st.subheader("📊 Mayor variación por producto (List Price, primera vs última medición)")
col_a, col_b = st.columns(2)

top_up = df.nlargest(5, "Var_ListPrice_%")[["Product", "Var_ListPrice_%"]]
top_down = df.nsmallest(5, "Var_ListPrice_%")[["Product", "Var_ListPrice_%"]]

with col_a:
    st.markdown("**🔴 Top 5 aumentos**")
    for _, row in top_up.iterrows():
        st.markdown(f"- {row['Product'][:40]} → **+{row['Var_ListPrice_%']:.1f}%**")

with col_b:
    st.markdown("**🔵 Top 5 bajas**")
    for _, row in top_down.iterrows():
        st.markdown(f"- {row['Product'][:40]} → **{row['Var_ListPrice_%']:.1f}%**")

st.divider()

# Dispersion
st.subheader("📋 Dispersión de precios (List Price)")
col_x, col_y, col_z = st.columns(3)
col_x.metric("Subieron", f"{(df['Var_ListPrice_%'] > 0).sum()} productos")
col_y.metric("Bajaron", f"{(df['Var_ListPrice_%'] < 0).sum()} productos")
col_z.metric("Sin cambio", f"{(df['Var_ListPrice_%'] == 0).sum()} productos")

st.divider()
st.caption("Los datos se actualizan automáticamente cada sábado cuando corre el scraper.")