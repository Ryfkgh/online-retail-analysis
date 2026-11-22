"""Interactive sales dashboard for the Online Retail II dataset.

Run from the project root:
    streamlit run app.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import metrics as m  # noqa: E402

# One hue carries the data; neutrals carry everything else.
INK = "#16212c"
MUTED = "#5b6875"
ACCENT = "#1f6f8b"
ACCENT_SOFT = "#a9cfdf"
PARTIAL = "#c7d0d8"
GRID = "#e8edf1"
FONT = '"Source Sans", "Source Sans 3", "Source Sans Pro", sans-serif'

st.set_page_config(page_title="Online Retail Sales", page_icon=":material/monitoring:", layout="wide")

st.html(f"""
<style>
  ::selection {{ background: rgba(31, 111, 139, 0.18); }}
  .block-container {{ padding-top: 2.25rem; max-width: 1280px; }}
  h1 {{ font-size: 2rem !important; letter-spacing: -0.01em; padding-bottom: 0.25rem !important; }}
  h3 {{ font-size: 1.15rem !important; }}
  [data-testid="stMetricLabel"] p {{ color: {MUTED}; font-weight: 500; }}
  [data-testid="stMetricValue"] {{ font-size: 1.75rem; font-weight: 600;
                                   font-variant-numeric: tabular-nums; }}
  .st-key-kpis {{ border-top: 1px solid {GRID}; border-bottom: 1px solid {GRID};
                  padding: 0.9rem 0 0.6rem; margin: 0.5rem 0 0.75rem; }}
  .st-key-intro p {{ color: {MUTED}; margin-bottom: 0.15rem; }}
  .note {{ color: {MUTED}; font-size: 0.9rem; }}
  @media (max-width: 640px) {{
    h1 {{ font-size: 1.6rem !important; }}
    .st-key-kpis [data-testid="stHorizontalBlock"] {{ flex-flow: row wrap; gap: 0.75rem 1rem; }}
    .st-key-kpis [data-testid="stColumn"] {{ flex: 1 1 calc(50% - 1rem) !important;
                                             min-width: calc(50% - 1rem) !important; }}
    [data-testid="stMetricValue"] {{ font-size: 1.4rem; }}
  }}
</style>
""")


@st.cache_data
def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    data = ROOT / "data" / "processed"
    return pd.read_parquet(data / "transactions.parquet"), pd.read_csv(data / "cleaning_log.csv")


def money(x: float) -> str:
    if abs(x) >= 1e6:
        return f"£{x / 1e6:.1f}M"
    if abs(x) >= 1e3:
        return f"£{x / 1e3:.0f}K"
    return f"£{x:,.0f}"


def count(x: int) -> str:
    return f"{x / 1e3:.1f}K" if x >= 10_000 else f"{x:,}"


def show(fig: go.Figure, height: int) -> None:
    """Apply the dashboard's chart style and render without Plotly's toolbar."""
    fig.update_layout(
        height=height, font=dict(family=FONT, size=13, color=INK),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=16, t=28, b=8), bargap=0.25,
        hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(family=FONT, color=INK)),
        legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", title=None),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, ticks="", automargin=True,
                     tickfont_color=MUTED, title_font_color=MUTED)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, ticks="", automargin=True,
                     tickfont_color=MUTED, title_font_color=MUTED)
    st.plotly_chart(fig, use_container_width=True, theme=None, config={"displayModeBar": False})


ACRONYMS = ["3D", "TV", "CD", "PC", "VW", "WC"]


def product_name(s: pd.Series) -> pd.Series:
    """The source data shouts in capitals; show names in title case, keeping acronyms and units."""
    out = (s.str.title()
            .str.replace(r"'S\b", "'s", regex=True)                       # 50'S -> 50's
            .str.replace(r"(\d)(Cm|Pcs)\b", lambda x: x[1] + x[2].lower(), regex=True))  # 60Cm -> 60cm
    for word in ACRONYMS:
        out = out.str.replace(rf"\b{word.title()}\b", word, regex=True)    # Wc -> WC
    return out


def short(s: pd.Series, limit: int = 28) -> pd.Series:
    return s.where(s.str.len() <= limit, s.str[: limit - 1].str.rstrip() + "…")


def ranked_bars(labels: pd.Series, values: pd.Series, height: int) -> None:
    """Horizontal bars, largest on top, labelled with their value."""
    labels, values = labels.reset_index(drop=True), values.reset_index(drop=True)
    fig = go.Figure(go.Bar(
        x=values[::-1], y=short(labels)[::-1], customdata=labels[::-1], orientation="h",
        marker_color=ACCENT, text=[money(v) for v in values[::-1]], textposition="outside",
        cliponaxis=False, textfont=dict(color=INK),
        hovertemplate="%{customdata}<br>£%{x:,.0f}<extra></extra>"))
    fig.update_xaxes(visible=False, range=[0, values.max() * 1.3])
    fig.update_yaxes(showgrid=False)
    show(fig, height)


df_all, cleaning_log = load()

# ---------- Filters ----------
with st.sidebar:
    st.header("Filters")
    months = sorted(df_all["Month"].unique())
    start, end = st.select_slider(
        "Months", options=months, value=(months[0], months[-1]),
        format_func=lambda d: pd.Timestamp(d).strftime("%b %Y"))
    countries = df_all["Country"].dropna().value_counts().index.tolist()
    picked = st.multiselect("Countries", countries, placeholder="All countries")
    st.caption("The data stops on 9 December 2011, so that month is incomplete.")
    st.caption("Source: [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii), "
               "CC BY 4.0.")

df = df_all[(df_all["Month"] >= start) & (df_all["Month"] <= end)]
if picked:
    df = df[df["Country"].isin(picked)]

# ---------- Header and KPIs ----------
st.title("Online Retail sales")
with st.container(key="intro"):
    st.markdown("A UK online gift retailer selling mostly to wholesalers. All amounts in pounds sterling.")
    scope = ", ".join(picked) if picked else "all countries"
    st.markdown(f"Showing **{pd.Timestamp(start):%b %Y} to {pd.Timestamp(end):%b %Y}**, {scope}.")

if df.empty:
    st.warning("No sales match these filters. Widen the month range or clear the country filter.")
    st.stop()

k = m.kpis(df)
with st.container(key="kpis"):
    c = st.columns(5)
    c[0].metric("Net revenue", money(k["net_revenue"]), help=f"£{k['net_revenue']:,.0f} after returns")
    c[1].metric("Orders", count(k["orders"]), help=f"{k['orders']:,} orders")
    c[2].metric("Customers", count(k["customers"]), help="Customers with a recorded ID")
    c[3].metric("Average order", money(k["avg_order_value"]))
    c[4].metric("Returns", f"{k['return_rate']:.1%}", help="Returned value as a share of gross sales")

tab_trend, tab_products, tab_customers, tab_countries, tab_data = st.tabs(
    ["Trend", "Products", "Customers", "Countries", "Data quality"])

# ---------- Trend ----------
with tab_trend:
    mo = m.monthly(df)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3],
                        vertical_spacing=0.13, subplot_titles=("Net revenue", "Orders"))
    fig.add_bar(x=mo["Month"], y=mo["net_revenue"], name="Net revenue", showlegend=False,
                marker_color=[PARTIAL if p else ACCENT for p in mo["partial_month"]],
                hovertemplate="%{x|%b %Y}<br>£%{y:,.0f}<extra></extra>", row=1, col=1)
    fig.add_scatter(x=mo["Month"], y=mo["orders"], name="Orders", showlegend=False,
                    mode="lines+markers", line=dict(color=MUTED, width=2), marker=dict(size=5),
                    hovertemplate="%{x|%b %Y}<br>%{y:,} orders<extra></extra>", row=2, col=1)
    fig.update_yaxes(tickprefix="£", tickformat="~s", rangemode="tozero", row=1, col=1)
    fig.update_yaxes(tickformat=",.0f", rangemode="tozero", nticks=3, row=2, col=1)
    fig.update_annotations(font=dict(size=13, color=MUTED), x=0, xanchor="left", yshift=8)
    show(fig, 460)

    full = mo[~mo["partial_month"]]
    notes = []
    if len(full) >= 2:
        best = full.loc[full["net_revenue"].idxmax()]
        notes.append(f"Best month: <b>{best['Month']:%B %Y}</b> ({money(best['net_revenue'])}). "
                     f"Monthly average: {money(full['net_revenue'].mean())}.")
    if mo["partial_month"].any():
        notes.append("The pale bar is December 2011, which covers only 1 to 9 December.")
    if notes:
        st.html(f'<p class="note">{" ".join(notes)}</p>')

# ---------- Products ----------
with tab_products:
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("Top products by revenue")
        n = st.slider("Products shown", 5, 30, 12)
        top = m.top_products(df, n)
        ranked_bars(product_name(top["Description"]), top["revenue"], max(320, 26 * n))
    with right:
        st.subheader("Highest return rates")
        st.caption("Among products with at least £5,000 of sales in the selected period")
        ret = m.most_returned(df, 15)
        ret[["sold", "returned"]] = ret[["sold", "returned"]].round().astype(int)
        ret["Description"] = product_name(ret["Description"])
        st.dataframe(ret, hide_index=True, use_container_width=True, column_config={
            "Description": st.column_config.TextColumn("Product", width="medium"),
            "sold": st.column_config.NumberColumn("Sold (£)", format="localized"),
            "returned": st.column_config.NumberColumn("Returned (£)", format="localized"),
            "return_share": st.column_config.ProgressColumn("Returned", format="percent",
                                                            min_value=0, max_value=1),
        })

# ---------- Customers ----------
with tab_customers:
    known = df.dropna(subset=["CustomerID"])
    if known["CustomerID"].nunique() < 50:
        st.info("This selection has fewer than 50 identified customers, too few to segment. "
                "Widen the month range or add countries.")
    else:
        rfm = m.rfm(df)
        seg = m.segment_summary(rfm)
        left, right = st.columns([3, 2], gap="large")
        with left:
            st.subheader("Customer segments")
            names = seg["segment"].str.replace(" ", "<br>", n=1)
            fig = go.Figure()
            fig.add_bar(x=names, y=seg["customer_share"], name="Share of customers",
                        marker_color=ACCENT_SOFT, customdata=seg["segment"],
                        hovertemplate="%{customdata}: %{y:.0%} of customers<extra></extra>")
            fig.add_bar(x=names, y=seg["revenue_share"], name="Share of revenue",
                        marker_color=ACCENT, customdata=seg["segment"],
                        hovertemplate="%{customdata}: %{y:.0%} of revenue<extra></extra>")
            fig.update_layout(barmode="group", bargroupgap=0.08)
            fig.update_xaxes(tickangle=0)
            fig.update_yaxes(tickformat=".0%")
            show(fig, 360)
        with right:
            st.subheader("What the segments mean")
            st.markdown(
                "- **Champions**: ordered recently and often\n"
                "- **Loyal**: order often, slightly less recently\n"
                "- **Potential loyalists**: recent, a few orders so far\n"
                "- **New**: one recent order\n"
                "- **Needs attention**: average on both\n"
                "- **At risk**: used to order often, not seen for a long time\n"
                "- **Hibernating**: few orders, long ago")

        table = seg.assign(revenue=seg["revenue"].round().astype(int),
                           avg_recency_days=seg["avg_recency_days"].round().astype(int))
        st.dataframe(table, hide_index=True, use_container_width=True, column_config={
            "segment": "Segment",
            "customers": st.column_config.NumberColumn("Customers", format="localized"),
            "revenue": st.column_config.NumberColumn("Revenue (£)", format="localized"),
            "avg_recency_days": st.column_config.NumberColumn("Days since last order", format="localized"),
            "avg_orders": st.column_config.NumberColumn("Orders per customer", format="%.1f"),
            "customer_share": st.column_config.NumberColumn("Share of customers", format="percent"),
            "revenue_share": st.column_config.NumberColumn("Share of revenue", format="percent"),
        })
        st.download_button("Download customer list with segments (CSV)", rfm.to_csv(index=False).encode(),
                            "customer_segments.csv", "text/csv", icon=":material/download:")

        st.subheader("Do new customers come back?")
        st.caption("Share of each first-order month that ordered again 1 to 12 months later. "
                   "The first row includes customers who were already buying before the data starts.")
        ret = m.cohort_retention(df).drop(columns=0, errors="ignore")
        ret.index = ret.index.strftime("%b %Y")
        fig = go.Figure(go.Heatmap(
            z=ret.values, x=ret.columns, y=ret.index, zmin=0, zmax=0.45, xgap=2, ygap=2,
            colorscale=[[0, "#f3f7fa"], [1, ACCENT]],
            colorbar=dict(tickformat=".0%", thickness=10, outlinewidth=0, title=None),
            hovertemplate="%{y} customers, month %{x}: %{z:.0%} ordered again<extra></extra>"))
        fig.update_yaxes(autorange="reversed", showgrid=False)
        fig.update_xaxes(title="Months since first order", dtick=1)
        show(fig, max(320, 22 * len(ret)))

# ---------- Countries ----------
with tab_countries:
    st.subheader("Revenue by country")
    cr = m.country_revenue(df)
    hide_uk = st.toggle("Hide the United Kingdom", value=len(picked) == 0,
                        help="The UK is 85% of all revenue and flattens every other bar")
    if hide_uk:
        cr = cr[cr["Country"] != "United Kingdom"]
    if cr.empty:
        st.info("No other countries in this selection.")
    else:
        cr = cr.head(20)
        ranked_bars(cr["Country"], cr["net_revenue"], max(300, 28 * len(cr)))

# ---------- Data quality ----------
with tab_data:
    st.subheader("Cleaning log")
    st.markdown("Every rule applied to the raw file, in order, and how many rows it removed. "
                "The code is in `src/clean.py`.")
    st.dataframe(cleaning_log, hide_index=True, use_container_width=True, column_config={
        "step": "Step",
        "rows_before": st.column_config.NumberColumn("Rows before", format="localized"),
        "rows_removed": st.column_config.NumberColumn("Removed", format="localized"),
        "rows_after": st.column_config.NumberColumn("Rows after", format="localized"),
        "note": st.column_config.TextColumn("What and why", width="large"),
    })
