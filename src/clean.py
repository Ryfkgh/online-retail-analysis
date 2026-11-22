"""Clean the UCI Online Retail II dataset.

Reads the raw Excel file (two sheets, Dec 2009 - Dec 2011), applies each
cleaning rule in order, and records how many rows every rule touched.

Outputs:
    data/processed/transactions.parquet   one row per valid line item
    data/processed/cleaning_log.csv       rows affected by each step

Run from the project root:
    python src/clean.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_XLSX = ROOT / "data" / "raw" / "online_retail_II.xlsx"
RAW_CACHE = ROOT / "data" / "raw" / "online_retail_II.parquet"
OUT_DIR = ROOT / "data" / "processed"

# Stock codes that are fees, postage or manual adjustments, not products.
NON_PRODUCT_CODES = {
    "POST", "DOT", "C2", "M", "m", "D", "S", "B", "CRUK", "PADS",
    "BANK CHARGES", "AMAZONFEE", "ADJUST", "ADJUST2", "TEST001", "TEST002",
}


def load_raw() -> pd.DataFrame:
    """Read both Excel sheets once, then reuse a parquet cache."""
    if RAW_CACHE.exists():
        return pd.read_parquet(RAW_CACHE)
    sheets = pd.read_excel(RAW_XLSX, sheet_name=None,
                           dtype={"Invoice": str, "StockCode": str, "Description": str})
    df = pd.concat([s.assign(Sheet=name) for name, s in sheets.items()], ignore_index=True)
    df.to_parquet(RAW_CACHE, index=False)
    return df


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    log = []

    def step(name: str, before: int, after: int, note: str) -> None:
        log.append({"step": name, "rows_before": before, "rows_removed": before - after,
                    "rows_after": after, "note": note})

    df = df.rename(columns={"Customer ID": "CustomerID"}).copy()
    df["Invoice"] = df["Invoice"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip().str.upper()
    df["Description"] = df["Description"].astype("string").str.strip()
    step("load", len(df), len(df), "Both sheets combined (Dec 2009 - Dec 2011)")

    # The two sheets overlap for a few days in December 2010.
    sheet_names = df["Sheet"].unique()
    first_end = df.loc[df["Sheet"] == sheet_names[0], "InvoiceDate"].max()
    n = len(df)
    in_overlap = (df["Sheet"] != sheet_names[0]) & (df["InvoiceDate"] <= first_end)
    df = df[~in_overlap]
    step("sheet_overlap", n, len(df),
         f"Second sheet repeats invoices up to {first_end:%d %b %Y}; kept the first copy")
    df = df.drop(columns="Sheet")

    n = len(df)
    df = df.drop_duplicates()
    step("exact_duplicates", n, len(df), "Identical rows, usually double-scanned items")

    n = len(df)
    df = df[~df["Invoice"].str.startswith("A")]
    step("bad_debt_adjustments", n, len(df), "Invoices starting with 'A' are accounting entries")

    n = len(df)
    is_fee = df["StockCode"].isin(NON_PRODUCT_CODES) | df["StockCode"].str.startswith("GIFT_")
    df = df[~is_fee]
    step("non_product_codes", n, len(df), "Postage, fees, discounts, manual entries, gift vouchers")

    n = len(df)
    df = df[df["Price"] > 0]
    step("zero_or_negative_price", n, len(df), "Free samples, damaged-stock notes and write-offs")

    df["IsReturn"] = df["Invoice"].str.startswith("C")
    n = len(df)
    df = df[~((df["Quantity"] < 0) & ~df["IsReturn"])]
    step("negative_qty_not_return", n, len(df), "Stock corrections that are not customer returns")

    # Order-entry errors: a line cancelled in full by the same customer within a day
    # (e.g. 80,995 paper crafts ordered and cancelled minutes later). Drop both lines.
    n = len(df)
    df = df.reset_index(drop=True)
    key = ["CustomerID", "StockCode", "Price", "AbsQty"]
    lines = df.assign(AbsQty=df["Quantity"].abs(), Row=df.index)
    pairs = lines[~lines["IsReturn"]].merge(lines[lines["IsReturn"]], on=key, suffixes=("", "_c"))
    lag = pairs["InvoiceDate_c"] - pairs["InvoiceDate"]
    pairs = pairs[(lag >= pd.Timedelta(0)) & (lag <= pd.Timedelta(days=1))]
    pairs = pairs.drop_duplicates("Row_c").drop_duplicates("Row")
    df = df.drop(index=pd.Index(pairs["Row"]).union(pd.Index(pairs["Row_c"])))
    step("cancelled_within_a_day", n, len(df),
         f"{len(pairs)} sales fully cancelled by the same customer within 24 hours; "
         "both lines removed (net revenue unchanged)")

    # Customer ID arrives as a float (12346.0); keep it as a clean string.
    df["CustomerID"] = df["CustomerID"].astype("Int64").astype("string")
    df["Country"] = df["Country"].replace({"EIRE": "Ireland", "RSA": "South Africa",
                                           "Unspecified": pd.NA})

    # One description per product: use the most common spelling for each code.
    canonical = (df.dropna(subset=["Description"])
                   .groupby("StockCode")["Description"]
                   .agg(lambda s: s.value_counts().index[0]))
    df["Description"] = df["StockCode"].map(canonical)

    df["Revenue"] = (df["Quantity"] * df["Price"]).round(2)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Month"] = df["InvoiceDate"].dt.to_period("M").dt.to_timestamp()

    missing = int(df["CustomerID"].isna().sum())
    log.append({"step": "missing_customer_id_kept", "rows_before": len(df), "rows_removed": 0,
                "rows_after": len(df),
                "note": f"{missing} rows have no Customer ID; kept for revenue, excluded from customer metrics"})

    cols = ["Invoice", "StockCode", "Description", "Quantity", "Price", "Revenue",
            "InvoiceDate", "Month", "CustomerID", "Country", "IsReturn"]
    return df[cols].reset_index(drop=True), pd.DataFrame(log)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw = load_raw()
    clean_df, log = clean(raw)
    clean_df.to_parquet(OUT_DIR / "transactions.parquet", index=False)
    log.to_csv(OUT_DIR / "cleaning_log.csv", index=False)
    print(log.to_string(index=False))
    print(f"\nSaved {len(clean_df):,} rows to {OUT_DIR / 'transactions.parquet'}")


if __name__ == "__main__":
    main()
