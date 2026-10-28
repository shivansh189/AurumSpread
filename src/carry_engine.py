"""Futures Term Structure, Implied Carry, and Roll-down Decomposition Engine.

Separates predictable time-value (carry / roll-down) from true mispricing (alpha)
across MCX gold contracts, and computes retail micro-premiums.
"""

from typing import Optional, Dict, Any
import numpy as np
import pandas as pd


def calculate_term_structure(
    df: pd.DataFrame,
    trade_date: Optional[Any] = None,
    symbol: Optional[str] = None,
) -> pd.DataFrame:
    """Compute the term structure and annualized implied carry for a given trading date.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned and normalized dataset.
    trade_date : optional
        Specific date to inspect. Defaults to the latest available trading date.
    symbol : str, optional
        Filter by instrument (e.g. 'GOLDM', 'GOLDTEN'). If None, all contracts are included.

    Returns
    -------
    pd.DataFrame
        Table sorted by expiry with days to expiry, implied carry % p.a., and curve slope.
    """
    data = df.copy()
    data["trade_date"] = pd.to_datetime(data["trade_date"], errors="coerce", format="mixed")
    data["expiry_date"] = pd.to_datetime(data["expiry_date"], errors="coerce", format="mixed")

    if trade_date is None:
        target_date = data["trade_date"].max()
    else:
        target_date = pd.to_datetime(trade_date)

    curve = data[data["trade_date"] == target_date].copy()
    if symbol:
        curve = curve[curve["symbol"].str.upper() == symbol.upper()]

    if curve.empty:
        return pd.DataFrame()

    curve = curve.sort_values(["symbol", "expiry_date"]).reset_index(drop=True)
    curve["days_to_expiry"] = (curve["expiry_date"] - target_date).dt.days

    # Calculate carry relative to the front contract within each symbol
    results = []
    for sym, group in curve.groupby("symbol"):
        group = group.sort_values("expiry_date").reset_index(drop=True)
        if group.empty:
            continue
        front_row = group.iloc[0]
        front_price = float(front_row["normalized_price_per_gram"])
        front_days = int(front_row["days_to_expiry"])

        for idx, row in group.iterrows():
            row_dict = row.to_dict()
            curr_price = float(row["normalized_price_per_gram"])
            curr_days = int(row["days_to_expiry"])
            days_diff = curr_days - front_days

            if idx == 0 or days_diff <= 0:
                annualized_carry = 0.0
                regime = "Front Month (Anchor)"
            else:
                price_diff = curr_price - front_price
                pct_diff = price_diff / front_price
                annualized_carry = (pct_diff * (365.0 / days_diff)) * 100.0
                if annualized_carry > 0.2:
                    regime = "Contango"
                elif annualized_carry < -0.2:
                    regime = "Backwardation"
                else:
                    regime = "Flat"

            row_dict["spread_vs_front_inr"] = curr_price - front_price if idx > 0 else 0.0
            row_dict["annualized_carry_pct"] = annualized_carry
            row_dict["market_regime"] = regime
            results.append(row_dict)

    res_df = pd.DataFrame(results)
    return res_df


def decompose_carry_and_mispricing(
    spread_data: pd.DataFrame,
    risk_free_rate_pct: float = 6.5,
) -> pd.DataFrame:
    """Decompose raw calendar spread into expected carrying cost and true mispricing.

    Expected Carry = Spot * (r + storage) * (t2 - t1) / 365
    True Mispricing = Observed Calendar Spread - Expected Theoretical Carry

    Parameters
    ----------
    spread_data : pd.DataFrame
        DataFrame with calendar spread data containing 'trade_date', 'near_expiry',
        'far_expiry', 'calendar_spread', 'near_price', 'far_price'.
    risk_free_rate_pct : float
        Annualized cost-of-carry / financing rate in percentage (default 6.5% for INR).

    Returns
    -------
    pd.DataFrame
        DataFrame with added 'expected_carry_inr', 'true_mispricing_inr',
        and 'annualized_spread_carry_pct'.
    """
    df = spread_data.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["near_expiry"] = pd.to_datetime(df["near_expiry"])
    df["far_expiry"] = pd.to_datetime(df["far_expiry"])

    days_diff = (df["far_expiry"] - df["near_expiry"]).dt.days
    days_diff = days_diff.replace(0, np.nan)

    # Theoretical cost of carry per gram based on near contract price
    near_px = pd.to_numeric(df["near_price"], errors="coerce")
    far_px = pd.to_numeric(df["far_price"], errors="coerce")
    spread = pd.to_numeric(df["calendar_spread"], errors="coerce")

    # Annualized implied carry % from actual market spread
    df["annualized_spread_carry_pct"] = (
        (spread / near_px) * (365.0 / days_diff) * 100.0
    )

    # Theoretical carry in ₹/g at given benchmark financing rate
    df["expected_carry_inr"] = near_px * (risk_free_rate_pct / 100.0) * (days_diff / 365.0)

    # Mispricing = actual spread minus theoretical carry
    df["true_mispricing_inr"] = spread - df["expected_carry_inr"]

    # Roll-down yield per day = spread / days_diff
    df["daily_roll_down_inr"] = spread / days_diff

    return df


def calculate_retail_micro_premium(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate the retail micro-premium: premium of small contracts (GOLDPETAL,
    GOLDGUINEA, GOLDTEN) relative to wholesale mini (GOLDM) on a normalized ₹/g basis.

    Parameters
    ----------
    df : pd.DataFrame
        Historical dataset with all 4 contracts.

    Returns
    -------
    pd.DataFrame
        Table of daily micro-premiums in ₹/g and % over GOLDM.
    """
    data = df.copy()
    data["trade_date"] = pd.to_datetime(data["trade_date"])

    # Aggregate average normalized price per trade_date and symbol
    pivot_px = data.pivot_table(
        index="trade_date",
        columns="symbol",
        values="normalized_price_per_gram",
        aggfunc="mean",
    )

    if "GOLDM" not in pivot_px.columns:
        return pd.DataFrame()

    benchmark = pivot_px["GOLDM"]
    results = []

    for sym in ["GOLDPETAL", "GOLDGUINEA", "GOLDTEN"]:
        if sym in pivot_px.columns:
            diff_inr = pivot_px[sym] - benchmark
            pct_diff = (diff_inr / benchmark) * 100.0
            temp_df = pd.DataFrame({
                "trade_date": pivot_px.index,
                "symbol": sym,
                "benchmark_symbol": "GOLDM",
                "symbol_price_per_g": pivot_px[sym].values,
                "goldm_price_per_g": benchmark.values,
                "premium_inr_per_g": diff_inr.values,
                "premium_pct": pct_diff.values,
            })
            results.append(temp_df)

    if not results:
        return pd.DataFrame()

    res = pd.concat(results, ignore_index=True).dropna(subset=["symbol_price_per_g", "goldm_price_per_g"])
    return res.sort_values(["trade_date", "symbol"]).reset_index(drop=True)
