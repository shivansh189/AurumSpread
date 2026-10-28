"""MCX Gold Lot-Size Hedge Ratio Optimizer.

Calculates optimal integer contract ratios between differing MCX gold contracts
(GOLDM 100g, GOLDTEN 10g, GOLDGUINEA 8g, GOLDPETAL 1g) to achieve delta neutrality.
"""

import math
from typing import Dict, Any, List
from src.normalize import CONTRACT_SPECS


def calculate_optimal_hedge(
    symbol_a: str,
    symbol_b: str,
    lots_a: int = 1,
    gold_price_per_g: float = 7500.0,
) -> Dict[str, Any]:
    """Find the optimal integer lot ratio between two MCX gold contracts.

    Minimizes residual delta exposure (|grams_a - grams_b|).

    Parameters
    ----------
    symbol_a : str
        First contract symbol (e.g. 'GOLDM').
    symbol_b : str
        Second contract symbol (e.g. 'GOLDGUINEA').
    lots_a : int
        Number of lots traded in contract A (default 1).
    gold_price_per_g : float
        Current gold price in ₹/g to compute notional values and margins.

    Returns
    -------
    Dict[str, Any]
        Dictionary with optimal lots_b, exact grams for each leg,
        residual mismatch in grams, hedge efficiency %, notional values,
        and smallest exact zero-mismatch ratio.
    """
    sym_a = symbol_a.strip().upper()
    sym_b = symbol_b.strip().upper()

    lot_g_a = CONTRACT_SPECS.get(sym_a, {}).get("lot_size_grams", 10)
    lot_g_b = CONTRACT_SPECS.get(sym_b, {}).get("lot_size_grams", 10)

    total_g_a = lots_a * lot_g_a

    # Ideal float lots for leg B
    ideal_lots_b = total_g_a / lot_g_b

    # Test floor and ceil integer lots
    candidate_b_low = max(1, math.floor(ideal_lots_b))
    candidate_b_high = max(1, math.ceil(ideal_lots_b))

    mismatch_low = abs(total_g_a - candidate_b_low * lot_g_b)
    mismatch_high = abs(total_g_a - candidate_b_high * lot_g_b)

    if mismatch_low <= mismatch_high:
        best_lots_b = candidate_b_low
        mismatch_g = mismatch_low
    else:
        best_lots_b = candidate_b_high
        mismatch_g = mismatch_high

    total_g_b = best_lots_b * lot_g_b
    hedge_efficiency_pct = max(0.0, 100.0 * (1.0 - (mismatch_g / max(total_g_a, total_g_b))))

    # Exact smallest zero-delta ratio using Greatest Common Divisor
    gcd = math.gcd(lot_g_a, lot_g_b)
    exact_ratio_a = lot_g_b // gcd
    exact_ratio_b = lot_g_a // gcd
    exact_matched_grams = exact_ratio_a * lot_g_a

    notional_a = total_g_a * gold_price_per_g
    notional_b = total_g_b * gold_price_per_g
    delta_exposure_inr = (total_g_a - total_g_b) * gold_price_per_g

    return {
        "symbol_a": sym_a,
        "symbol_b": sym_b,
        "lots_a": lots_a,
        "lots_b": best_lots_b,
        "lot_size_a_grams": lot_g_a,
        "lot_size_b_grams": lot_g_b,
        "total_grams_a": total_g_a,
        "total_grams_b": total_g_b,
        "residual_mismatch_grams": mismatch_g,
        "delta_exposure_inr": delta_exposure_inr,
        "hedge_efficiency_pct": round(hedge_efficiency_pct, 2),
        "notional_a_inr": notional_a,
        "notional_b_inr": notional_b,
        "exact_zero_delta_ratio": f"{exact_ratio_a} {sym_a} : {exact_ratio_b} {sym_b}",
        "exact_matched_grams": exact_matched_grams,
    }
