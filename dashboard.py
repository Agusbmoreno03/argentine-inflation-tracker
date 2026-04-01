import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import glob

# ── CONFIG ────────────────────────────────────────────────────────────────────
FOLDER = r"C:\Users\agusm\Downloads\Pythonclass"

# ── LOAD ALL CSVS AUTOMATICALLY ──────────────────────────────────────────────
@st.cache_data
def load_all_weeks():
    files = sorted(glob.glob(os.path.join(FOLDER, "precios_almacen_*.csv")))
    weeks = []
    for f in files:
        df = pd.read_csv(f)
        # Normalize column names (older CSVs have Spanish names)
        df = df.rename(columns={
            'Producto': 'Product', 'Marca': 'Brand',
            'Precio_Actual': 'Price', 'Precio_Lista': 'List_Price',
            'Precio_S2': 'Price', 'Precio_S3': 'Price'
        })
        df['Product'] = df['Product'].str.strip().str.lower()
        df['Brand']   = df['Brand'].str.strip().str.lower()
        date = os.path.basename(f).replace("precios_almacen_", "").replace(".csv", "")
        df['Week'] = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        weeks.append(df)
    return weeks

weeks = load_all_weeks()
dates = [df['Week'].iloc[0] for df in weeks]

# ── MERGE ALL WEEKS ───────────────────────────────────────────────────────────
def merge_weeks(weeks):
    base = weeks[0][['Product', 'Brand', 'Price', 'List_Price']].copy()
    base = base.rename(columns={'Price': 'Price_W1', 'List_Price': 'List_Price_W1'})
    for i, df in enumerate(weeks[1:], 2):
        cols = ['Product', 'Brand', 'Price']
        if 'List_Price' in df.columns:
            cols.append('List_Price')
        base = base.merge(df[cols], on=['Product', 'Brand'])
        base = base.rename(columns={'Price': f'Price_W{i}'})
        if 'List_Price' in df.columns:
            base = base.rename(columns={'List_Price': f'List_Price_W{i}'})
    return base

df = merge_weeks(weeks)
n  = len(weeks)

# ── CUMULATIVE VARIATION PER WEEK ────────────────────────────────────────────
cumul = [0]
for i in range(2, n + 1):
    var = ((df[f'Price_W{i}'] / df['Price_W1']) - 1) * 100
    cumul.append(var.mean())

# ── LIST PRICE INFLATION (first vs last) ─────────────────────────────────────
last_lp = f'List_Price_W{n}'
if last_lp in df.columns and 'List_Price_W1' in df.columns:
    df['Var_ListPrice_%'] = ((df[last_lp] / df['List_Price_W1']) - 1) * 100
    list_inflation = df['Var_ListPrice_%'].mean()
else:
    df['Var_ListPrice_%'] = df['Var_Monthly_%'] if 'Var_Monthly_%' in df.columns else 0
    list_inflation = 0

promo_inflation = cumul[-1]

# ── UI ────────────────────────────────────────────────────────────────────────
st.title("🇦🇷 Argentine Grocery Inflation Tracker")
st.caption(f"Carrefour Argentina — Almacén category — {dates[0]} to {dates[-1]}")

# Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Weeks tracked", f"{n}")
col2.metric("Monthly inflation (List Price)", f"{list_inflation:.2f}%")
col3.metric("Monthly inflation (Promo Price)", f"{promo_inflation:.2f}%")

st.divider()

# Trend chart
st.subheader("📈 Cumulative Inflation by Week")
fig1, ax1 = plt.subplots(figsize=(10, 4))
ax1.plot(dates, cumul, marker='o', color='#e67e22', linewidth=2.5)
ax1.axhline(0, color='black', linewidth=0.8, linestyle='--')
ax1.set_ylabel("Cumulative Change vs Week 1 (%)")
ax1.grid(True, linestyle='--', alpha=0.5)
for i, v in enumerate(cumul):
    ax1.annotate(f"{v:.2f}%", (dates[i], v), textcoords="offset points", xytext=(0, 10), ha='center')
st.pyplot(fig1)

st.divider()

# Biggest movers
st.subheader("📊 Biggest Movers (List Price)")
col_a, col_b = st.columns(2)

top_up   = df.nlargest(5, 'Var_ListPrice_%')[['Product', 'Var_ListPrice_%']]
top_down = df.nsmallest(5, 'Var_ListPrice_%')[['Product', 'Var_ListPrice_%']]

with col_a:
    st.markdown("**🔴 Top 5 Increases**")
    for _, row in top_up.iterrows():
        st.markdown(f"- {row['Product'][:40]} → **+{row['Var_ListPrice_%']:.1f}%**")

with col_b:
    st.markdown("**🔵 Top 5 Decreases**")
    for _, row in top_down.iterrows():
        st.markdown(f"- {row['Product'][:40]} → **{row['Var_ListPrice_%']:.1f}%**")

st.divider()

# Dispersion
st.subheader("📋 Price Dispersion (List Price)")
col_x, col_y, col_z = st.columns(3)
col_x.metric("Went UP",   f"{(df['Var_ListPrice_%'] > 0).sum()} products")
col_y.metric("Went DOWN", f"{(df['Var_ListPrice_%'] < 0).sum()} products")
col_z.metric("No change", f"{(df['Var_ListPrice_%'] == 0).sum()} products")

st.divider()
st.caption("Data updates automatically every Sunday when the scraper runs.")
