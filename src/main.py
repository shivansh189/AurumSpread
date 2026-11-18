
from pathlib import Path
import sys
import pandas as pd

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.spread_engine import calculate_calendar_spreads
from src.spread_intelligence import calculate_spread_intelligence
from src.backtest_engine import run_calendar_spread_backtest


# ==========================================
# CONFIGURATION
# ==========================================

DATA_PATH = PROJECT_ROOT / "data" / "processed" / "historical_gold_futures.csv"

# Choose the instrument to backtest
SYMBOL = "GOLDGUINEA"

# Strategy settings
ENTRY_ZSCORE = 2.0
EXIT_ZSCORE = 0.0
LOTS = 1

# Select the expiry pair to backtest.
# Set these to expiry dates available in your historical data.
NEAR_EXPIRY = "2026-10-30"
FAR_EXPIRY = "2026-11-30"

# Transaction costs and slippage per leg, per lot.
# Keep at 0 until you confirm the correct values.
TRANSACTION_COST_PER_LEG = 0.0
SLIPPAGE_PER_LEG = 0.0


# ==========================================
# LOAD HISTORICAL DATA
# ==========================================

def load_data():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Historical dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    required_columns = [
        "symbol",
        "trade_date",
        "expiry_date",
        "close",
        "normalized_price_per_gram",
    ]

    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Dataset missing required columns: {missing}"
        )

    df["trade_date"] = pd.to_datetime(
        df["trade_date"], errors="coerce"
    )

    df["expiry_date"] = pd.to_datetime(
        df["expiry_date"], errors="coerce"
    )

    df = df.dropna(
        subset=["trade_date", "expiry_date"]
    )

    print("\n========== DATASET ==========")
    print(f"Rows loaded: {len(df)}")
    print(f"Symbol: {SYMBOL}")
    print(
        f"Date range: {df['trade_date'].min().date()} "
        f"to {df['trade_date'].max().date()}"
    )

    return df


# ==========================================
# BUILD SPREAD DATA
# ==========================================

def build_spreads(df):
    print("\n========== CALCULATING SPREADS ==========")

    spread_df = calculate_calendar_spreads(
        df=df,
        symbol=SYMBOL
    )

    if spread_df.empty:
        raise ValueError(
            f"No calendar spreads generated for {SYMBOL}"
        )

    print(f"Spread rows generated: {len(spread_df)}")

    return spread_df


# ==========================================
# CALCULATE SPREAD INTELLIGENCE
# ==========================================

def build_intelligence(spread_df):
    print("\n========== SPREAD INTELLIGENCE ==========")

    intelligence_df = calculate_spread_intelligence(
        spread_df
    )

    if intelligence_df.empty:
        raise ValueError(
            "Spread intelligence returned no data."
        )

    print(
        "Intelligence rows generated:",
        len(intelligence_df)
    )

    return intelligence_df


# ==========================================
# SELECT EXPIRY PAIR
# ==========================================

def select_expiry_pair(df):
    global NEAR_EXPIRY, FAR_EXPIRY

    available_pairs = (
        df[["near_expiry", "far_expiry"]]
        .drop_duplicates()
        .sort_values(["near_expiry", "far_expiry"])
    )

    print("\n========== AVAILABLE EXPIRY PAIRS ==========")

    print(
        available_pairs.to_string(index=False)
    )

    if NEAR_EXPIRY is None or FAR_EXPIRY is None:
        print(
            "\nExpiry pair has not been configured yet."
        )
        print(
            "Review the available pairs above, then set "
            "NEAR_EXPIRY and FAR_EXPIRY at the top of main.py."
        )
        return None

    near_date = pd.to_datetime(NEAR_EXPIRY)
    far_date = pd.to_datetime(FAR_EXPIRY)

    selected = df[
        (df["near_expiry"] == near_date)
        & (df["far_expiry"] == far_date)
    ].copy()

    if selected.empty:
        raise ValueError(
            "Selected expiry pair was not found in the data."
        )

    print(
        f"\nSelected pair: {near_date.date()} "
        f"-> {far_date.date()}"
    )

    return selected


# ==========================================
# RUN BACKTEST
# ==========================================

def run_backtest(selected_df):
    print("\n========== RUNNING BACKTEST ==========")

    results = run_calendar_spread_backtest(
        data=selected_df,
        entry_zscore=ENTRY_ZSCORE,
        exit_zscore=EXIT_ZSCORE,
        transaction_cost_per_leg=TRANSACTION_COST_PER_LEG,
        slippage_per_leg=SLIPPAGE_PER_LEG,
        lots=LOTS,
    )

    if results.empty:
        raise ValueError(
            "Backtest returned no results."
        )

    return results


# ==========================================
# SAVE RESULTS
# ==========================================

def save_results(spread_df, intelligence_df, backtest_df):
    output_dir = PROJECT_ROOT / "data" / "processed"
    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    spread_path = (
        output_dir / "calendar_spreads.csv"
    )

    intelligence_path = (
        output_dir / "spread_intelligence.csv"
    )

    backtest_path = (
        output_dir / "backtest_results.csv"
    )

    spread_df.to_csv(
        spread_path,
        index=False
    )

    intelligence_df.to_csv(
        intelligence_path,
        index=False
    )

    backtest_df.to_csv(
        backtest_path,
        index=False
    )

    print("\n========== FILES SAVED ==========")
    print(spread_path)
    print(intelligence_path)
    print(backtest_path)


# ==========================================
# MAIN
# ==========================================

def main():
    df = load_data()

    spread_df = build_spreads(df)

    intelligence_df = build_intelligence(
        spread_df
    )

    selected_df = select_expiry_pair(
        intelligence_df
    )

    if selected_df is None:
        print(
            "\nSetup complete. Configure the expiry pair "
            "and run main.py again."
        )
        return

    backtest_df = run_backtest(
        selected_df
    )

    save_results(
        spread_df,
        intelligence_df,
        backtest_df
    )

    print("\n========== BACKTEST COMPLETE ==========")
    print(
        backtest_df[
            ["trade_date", "calendar_spread",
             "spread_zscore", "position",
             "action", "daily_pnl"]
        ].tail(20).to_string(index=False)
    )

    print(
        "\nTotal P&L:",
        backtest_df["daily_pnl"].sum()
    )


if __name__ == "__main__":
    main()
