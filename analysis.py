"""
analysis.py — Análisis de inflación con gráficos locales (matplotlib)

Lee todos los precios_almacen_*.csv de la carpeta del proyecto, arma una
canasta fija comparable entre fechas, calcula variación ajustada por días
reales transcurridos (no asume semanas parejas), y genera:

  - indice_canasta.png       -> evolución del precio promedio en el tiempo
  - top_variaciones.png      -> productos con mayor suba / mayor baja
  - variacion_por_producto.csv -> tabla completa, para explorar en Excel
  - variacion_por_intervalo.csv -> variación % ajustada por día, por intervalo

Uso:
    python analysis.py
"""
import glob
import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ── CONFIG ────────────────────────────────────────────────────────────────
FOLDER = r"C:\Users\agusm\Downloads\Pythonclass\inflation-tracker"
TOP_N = 12  # cuántos productos mostrar en el ranking de subas/bajas
# ─────────────────────────────────────────────────────────────────────────


def load_all_data(folder):
    pattern = os.path.join(folder, "precios_almacen_*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No se encontraron CSVs en {folder}")

    dfs = []
    skipped = []
    required_cols = {"Date", "Product", "Brand", "Price"}
    for path in files:
        name = os.path.basename(path)
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
            # normalizar nombres de columna por si vienen con espacios o distinta capitalización
            df.columns = [c.strip() for c in df.columns]

            missing = required_cols - set(df.columns)
            if missing:
                print(f"  [SALTEADO] {name}: faltan columnas {missing}. Columnas encontradas: {list(df.columns)}")
                skipped.append(name)
                continue

            df["Date"] = pd.to_datetime(df["Date"])
            df["Product"] = df["Product"].astype(str).str.strip().str.lower()
            df["Brand"] = df["Brand"].astype(str).str.strip().str.lower()
            df["key"] = df["Product"] + "|" + df["Brand"]
            dfs.append(df)
        except Exception as e:
            print(f"  [SALTEADO] {name}: error al leer ({e})")
            skipped.append(name)

    if not dfs:
        raise RuntimeError("Ningun archivo se pudo cargar correctamente. Revisa los [SALTEADO] de arriba.")

    print(f"\nCargados correctamente: {len(dfs)}/{len(files)} archivos")
    if skipped:
        print(f"Salteados por formato distinto: {skipped}")
    return pd.concat(dfs, ignore_index=True)


def build_fixed_basket(full):
    """Solo productos presentes en TODAS las fechas, para comparar manzanas con manzanas."""
    dates = sorted(full["Date"].unique())
    products_per_date = [set(full[full["Date"] == d]["key"]) for d in dates]
    common = set.intersection(*products_per_date)
    print(f"Productos presentes en las {len(dates)} fechas: {len(common)}")
    return full[full["key"].isin(common)], dates, common


def variation_by_interval(avg_by_date):
    """Variación % ajustada por días reales entre cada medición consecutiva."""
    rows = []
    prev_date, prev_price = None, None
    for d, price in avg_by_date.items():
        if prev_date is not None:
            days = (d - prev_date).days
            pct = (price / prev_price - 1) * 100
            daily = ((price / prev_price) ** (1 / days) - 1) * 100
            monthly_equiv = ((1 + daily / 100) ** 30 - 1) * 100
            rows.append({
                "desde": prev_date.date(), "hasta": d.date(), "dias": days,
                "var_%_periodo": round(pct, 2),
                "var_%_diaria": round(daily, 3),
                "var_%_mensual_equivalente": round(monthly_equiv, 2),
            })
        prev_date, prev_price = d, price
    return pd.DataFrame(rows)


def variation_by_product(basket, dates):
    """Variación % de primera a última fecha, por producto (canasta fija)."""
    first_date, last_date = dates[0], dates[-1]
    first = basket[basket["Date"] == first_date].set_index("key")["Price"]
    last = basket[basket["Date"] == last_date].set_index("key")["Price"]
    names = basket[["key", "Product", "Brand"]].drop_duplicates("key").set_index("key")

    var = ((last / first - 1) * 100).sort_values(ascending=False)
    result = var.to_frame("var_pct").join(names)
    result.index.name = "key"
    return result.reset_index(drop=True)[["Product", "Brand", "var_pct"]]


def plot_index(avg_by_date, out_path):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(avg_by_date.index, avg_by_date.values, marker="o", linewidth=2, color="#2a78d6")
    for d, p in avg_by_date.items():
        ax.annotate(f"${p:,.0f}", (d, p), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    ax.set_title(f"Precio promedio canasta fija ({len(avg_by_date)} mediciones) - Carrefour Almacén")
    ax.set_ylabel("Precio promedio ($)")
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Guardado: {out_path}")


def plot_top_variations(var_df, top_n, out_path):
    top_up = var_df.head(top_n)
    top_down = var_df.tail(top_n).sort_values("var_pct")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    axes[0].barh(top_up["Product"].str[:35][::-1], top_up["var_pct"][::-1], color="#e34948")
    axes[0].set_title(f"Top {top_n} mayores aumentos")
    axes[0].set_xlabel("% variación")
    axes[0].tick_params(axis="y", labelsize=8)

    axes[1].barh(top_down["Product"].str[:35][::-1], top_down["var_pct"][::-1], color="#1baf7a")
    axes[1].set_title(f"Top {top_n} mayores bajas")
    axes[1].set_xlabel("% variación")
    axes[1].tick_params(axis="y", labelsize=8)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Guardado: {out_path}")


if __name__ == "__main__":
    os.chdir(FOLDER)

    full = load_all_data(FOLDER)
    basket, dates, common = build_fixed_basket(full)
    avg_by_date = basket.groupby("Date")["Price"].mean().sort_index()

    interval_df = variation_by_interval(avg_by_date)
    print("\nVariación por intervalo (ajustada por días):")
    print(interval_df.to_string(index=False))

    product_var = variation_by_product(basket, dates)
    print(f"\nTop {TOP_N} aumentos:")
    print(product_var.head(TOP_N).to_string(index=False))
    print(f"\nTop {TOP_N} bajas:")
    print(product_var.tail(TOP_N).sort_values("var_pct").to_string(index=False))

    interval_df.to_csv("variacion_por_intervalo.csv", index=False)
    product_var.to_csv("variacion_por_producto.csv", index=False)

    plot_index(avg_by_date, "indice_canasta.png")
    plot_top_variations(product_var, TOP_N, "top_variaciones.png")

    print("\nListo. Archivos generados en:", FOLDER)