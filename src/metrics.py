"""Business metrics shared by the notebook and the dashboard.

Every function takes the cleaned transactions table produced by clean.py.
Revenue is net of returns unless a column name says otherwise.
"""

import pandas as pd

SEGMENT_ORDER = ["Champions", "Loyal", "Potential loyalists", "New",
                 "Needs attention", "At risk", "Hibernating"]


def kpis(df: pd.DataFrame) -> dict:
    sales = df[~df["IsReturn"]]
    gross = sales["Revenue"].sum()
    returned = -df.loc[df["IsReturn"], "Revenue"].sum()
    orders = sales["Invoice"].nunique()
    return {
        "net_revenue": gross - returned,
        "gross_revenue": gross,
        "orders": orders,
        "customers": sales["CustomerID"].nunique(),
        "avg_order_value": gross / orders if orders else 0.0,
        "return_rate": returned / gross if gross else 0.0,
    }


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly revenue, with a flag on months the data does not fully cover."""
    sales = df[~df["IsReturn"]]
    out = pd.DataFrame({
        "gross_revenue": sales.groupby("Month")["Revenue"].sum(),
        "returns": -df[df["IsReturn"]].groupby("Month")["Revenue"].sum(),
        "orders": sales.groupby("Month")["Invoice"].nunique(),
        "customers": sales.groupby("Month")["CustomerID"].nunique(),
    }).fillna(0)
    out["net_revenue"] = out["gross_revenue"] - out["returns"]
    # The data stops on 9 Dec 2011, so the final month is incomplete.
    # (Earlier Decembers end around the 23rd because of the Christmas closure.)
    last = df["InvoiceDate"].max()
    out["partial_month"] = (out.index == last.to_period("M").to_timestamp()) & (last.day < 20)
    return out.reset_index()


def top_products(df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    sales = df[~df["IsReturn"]]
    return (sales.groupby("Description")
                 .agg(revenue=("Revenue", "sum"), units=("Quantity", "sum"),
                      orders=("Invoice", "nunique"))
                 .nlargest(n, "revenue")
                 .reset_index())


def most_returned(df: pd.DataFrame, n: int = 15, min_sales: float = 5000) -> pd.DataFrame:
    """Products with the highest share of revenue returned (ignores small sellers)."""
    sold = df[~df["IsReturn"]].groupby("Description")["Revenue"].sum()
    back = -df[df["IsReturn"]].groupby("Description")["Revenue"].sum()
    t = pd.DataFrame({"sold": sold, "returned": back}).fillna(0)
    t = t[t["sold"] >= min_sales]
    t["return_share"] = t["returned"] / t["sold"]
    return t.nlargest(n, "return_share").reset_index()


def country_revenue(df: pd.DataFrame) -> pd.DataFrame:
    t = df.dropna(subset=["Country"]).groupby("Country").agg(
        net_revenue=("Revenue", "sum"),
        customers=("CustomerID", "nunique"),
    )
    t["share"] = t["net_revenue"] / t["net_revenue"].sum()
    return t.sort_values("net_revenue", ascending=False).reset_index()


def rfm(df: pd.DataFrame) -> pd.DataFrame:
    """Recency / frequency / monetary scores and a named segment per customer."""
    known = df.dropna(subset=["CustomerID"])
    ref = known["InvoiceDate"].max() + pd.Timedelta(days=1)
    sales = known[~known["IsReturn"]]
    t = pd.DataFrame({
        "recency_days": (ref - sales.groupby("CustomerID")["InvoiceDate"].max()).dt.days,
        "frequency": sales.groupby("CustomerID")["Invoice"].nunique(),
        "monetary": known.groupby("CustomerID")["Revenue"].sum(),
    }).dropna()
    t = t[t["monetary"] > 0]

    t["R"] = pd.qcut(t["recency_days"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    t["F"] = pd.qcut(t["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    t["M"] = pd.qcut(t["monetary"], 5, labels=[1, 2, 3, 4, 5]).astype(int)

    def name(row) -> str:
        r, f = row["R"], row["F"]
        if r >= 4 and f >= 4:
            return "Champions"
        if r >= 3 and f >= 4:
            return "Loyal"
        if r >= 4 and f >= 2:
            return "Potential loyalists"
        if r >= 4:
            return "New"
        if r <= 2 and f >= 3:
            return "At risk"
        if r <= 2:
            return "Hibernating"
        return "Needs attention"

    t["segment"] = t.apply(name, axis=1)
    return t.reset_index()


def segment_summary(rfm_table: pd.DataFrame) -> pd.DataFrame:
    s = rfm_table.groupby("segment").agg(
        customers=("CustomerID", "count"),
        revenue=("monetary", "sum"),
        avg_recency_days=("recency_days", "mean"),
        avg_orders=("frequency", "mean"),
    )
    s["customer_share"] = s["customers"] / s["customers"].sum()
    s["revenue_share"] = s["revenue"] / s["revenue"].sum()
    return s.reindex([x for x in SEGMENT_ORDER if x in s.index]).reset_index()


def cohort_retention(df: pd.DataFrame, max_months: int = 12) -> pd.DataFrame:
    """Share of each first-purchase cohort that bought again N months later."""
    sales = df[~df["IsReturn"]].dropna(subset=["CustomerID"])
    last = df["InvoiceDate"].max()
    if last.day < 20:  # leave out the incomplete final month
        sales = sales[sales["Month"] < last.to_period("M").to_timestamp()]
    first = sales.groupby("CustomerID")["Month"].min().rename("Cohort")
    s = sales[["CustomerID", "Month"]].drop_duplicates().join(first, on="CustomerID")
    s["MonthsSince"] = ((s["Month"].dt.year - s["Cohort"].dt.year) * 12
                        + (s["Month"].dt.month - s["Cohort"].dt.month))
    counts = s.pivot_table(index="Cohort", columns="MonthsSince", values="CustomerID",
                           aggfunc="nunique")
    retention = counts.div(counts[0], axis=0)
    return retention.loc[:, :max_months]
