"""Liquidity-Penalised Fill Estimator & MCX Contract Lifecycle Engine.

Tracks contract lifecycle, enforces MCX tender-delivery exclusion periods,
computes liquidity depth scores, and estimates liquidity-penalized slippage haircuts.
"""

from typing import Tuple, Dict, Any
import numpy as np
import pandas as pd
from src.normalize import CONTRACT_SPECS


def is_tender_period(
    trade_date: Any,
    expiry_date: Any,
    tender_days: int = 5,
) -> bool:
    """Check if the given trading date falls inside the MCX physical tender window.

    MCX contracts enter mandatory tender delivery 5 business days before expiry.
    Retail/speculative spread traders must exit before tender to avoid delivery penalty.
    """
    t_date = pd.to_datetime(trade_date)
    e_date = pd.to_datetime(expiry_date)
    days_to_expiry = (e_date - t_date).days
    return 0 <= days_to_expiry <= tender_days


def calculate_liquidity_depth(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate volume depth, open interest, estimated turnover, and liquidity tiers.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned MCX dataset with volume_lots, open_interest_lots, symbol, normalized_price_per_gram.

    Returns
    -------
    pd.DataFrame
        Dataset enriched with turnover_crores, days_to_expiry, is_in_tender, and liquidity_tier.
    """
    data = df.copy()
    data["trade_date"] = pd.to_datetime(data["trade_date"], errors="coerce", format="mixed")
    data["expiry_date"] = pd.to_datetime(data["expiry_date"], errors="coerce", format="mixed")

    data["days_to_expiry"] = (data["expiry_date"] - data["trade_date"]).dt.days
    data["is_in_tender"] = data.apply(
        lambda r: is_tender_period(r["trade_date"], r["expiry_date"], tender_days=5),
        axis=1,
    )

    # Estimate turnover in Crores:
    # Lots * lot_size_in_grams * price_per_gram / 10,000,000
    def compute_turnover(row):
        sym = str(row.get("symbol", "")).strip().upper()
        lot_g = CONTRACT_SPECS.get(sym, {}).get("lot_size_grams", 10)
        vol = float(row.get("volume_lots", 0) or 0)
        px = float(row.get("normalized_price_per_gram", 0) or 0)
        return (vol * lot_g * px) / 1e7

    data["turnover_crores"] = data.apply(compute_turnover, axis=1)

    # Determine liquidity tier
    def assign_tier(row):
        vol = float(row.get("volume_lots", 0) or 0)
        oi = float(row.get("open_interest_lots", 0) or 0)
        if row.get("is_in_tender", False):
            return "Tender Lockout (High Risk)"
        if vol >= 200 and oi >= 400:
            return "Liquid (Tier 1)"
        elif vol >= 30 and oi >= 80:
            return "Moderate (Tier 2)"
        else:
            return "Illiquid / Thin (Tier 3)"

    data["liquidity_tier"] = data.apply(assign_tier, axis=1)
    return data


def estimate_fill_slippage(
    base_slippage_inr: float,
    volume_lots: float,
    oi_lots: float,
    min_volume_threshold: float = 30.0,
    penalty_multiplier: float = 2.0,
) -> Tuple[float, bool]:
    """Estimate liquidity-penalized fill price haircut and fill viability.

    Settlement prices reported in Bhavcopy are theoretical. A thin contract
    incurs severe execution slippage when attempting to cross the spread.

    Parameters
    ----------
    base_slippage_inr : float
        Standard baseline slippage in ₹/g under normal liquid conditions.
    volume_lots : float
        Volume traded in lots on that date.
    oi_lots : float
        Open interest in lots.
    min_volume_threshold : float
        Minimum volume required for normal execution.
    penalty_multiplier : float
        Penalty scaling factor for illiquid books.

    Returns
    -------
    Tuple[float, bool]
        (executable_slippage_inr, is_fillable)
    """
    if volume_lots <= 2 or oi_lots <= 5:
        # Cannot execute with zero/trace liquidity
        return base_slippage_inr * (1.0 + penalty_multiplier * 5.0), False

    if volume_lots >= min_volume_threshold:
        return float(base_slippage_inr), True

    # Liquidity haircut expands non-linearly as volume dries up
    shortfall_ratio = (min_volume_threshold - volume_lots) / min_volume_threshold
    penalized_slippage = base_slippage_inr * (1.0 + penalty_multiplier * shortfall_ratio)
    return float(penalized_slippage), True
