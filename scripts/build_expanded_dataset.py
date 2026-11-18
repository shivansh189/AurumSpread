"""Gold Futures Dataset Builder for MCX Bhavcopy.

Ingests all 82 raw MCX Bhavcopy CSV files and builds:
data/processed/historical_gold_futures.csv (GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL)
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.normalize import normalize_commodity_prices

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

GOLD_SYMBOLS = {"GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"}


def build_datasets():
    csv_files = sorted(RAW_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {RAW_DIR}")

    print(f"Reading {len(csv_files)} raw Bhavcopy files...")
    dfs = []
    for f in csv_files:
        df = pd.read_csv(f, low_memory=False)
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)

    # Standardize column names
    for col in ["Symbol", "Instrument Name", "Option Type"]:
        if col in combined.columns:
            combined[col] = combined[col].astype(str).str.strip().str.upper()

    combined["Strike Price"] = pd.to_numeric(combined["Strike Price"], errors="coerce")

    # Filter gold futures
    bullion = combined[
        combined["Symbol"].isin(GOLD_SYMBOLS)
        & combined["Instrument Name"].eq("FUTCOM")
        & combined["Option Type"].eq("-")
        & combined["Strike Price"].eq(0)
    ].copy()

    # Parse dates
    bullion["trade_date"] = pd.to_datetime(bullion["Date"], format="%d %b %Y", errors="coerce")
    
    expiry_text = bullion["Expiry Date"].astype(str).str.strip().str.upper()
    exp_dt = pd.to_datetime(expiry_text, format="%d%b%Y", errors="coerce")
    fallback = exp_dt.isna()
    exp_dt.loc[fallback] = pd.to_datetime(expiry_text.loc[fallback], format="%d %b %Y", errors="coerce")
    bullion["expiry_date"] = exp_dt

    bullion = bullion[[
        "Symbol", "trade_date", "expiry_date", "Close", "Volume(Lots)", "Open Interest(Lots)"
    ]].copy()

    bullion.columns = [
        "symbol", "trade_date", "expiry_date", "close", "volume_lots", "open_interest_lots"
    ]

    for c in ["close", "volume_lots", "open_interest_lots"]:
        bullion[c] = pd.to_numeric(bullion[c], errors="coerce")

    # Drop invalid rows
    bullion = bullion.dropna(subset=["symbol", "trade_date", "expiry_date", "close"]).reset_index(drop=True)

    # Normalize to ₹/1g of 999 purity
    bullion = normalize_commodity_prices(bullion)
    bullion = bullion.sort_values(["symbol", "trade_date", "expiry_date"]).reset_index(drop=True)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Gold Dataset
    gold_df = bullion[bullion["symbol"].isin(GOLD_SYMBOLS)].copy()
    gold_out = PROCESSED_DIR / "historical_gold_futures.csv"
    gold_df.to_csv(gold_out, index=False)
    print(f"Saved Gold dataset to {gold_out} ({len(gold_df)} rows, symbols: {gold_df['symbol'].unique()})")


if __name__ == "__main__":
    build_datasets()
