"""MCX Gold Contract Normalization Engine.

Converts all supported MCX gold futures quotes to INR per 1 gram of 999 purity.
Formulas:
  - GOLDM:      Close / 10 * (999 / 995)   (quoted per 10g, 995 purity, 100g lot)
  - GOLDTEN:    Close / 10                 (quoted per 10g, 999 purity, 10g lot)
  - GOLDGUINEA: Close / 8                  (quoted per 8g, 999 purity, 8g lot)
  - GOLDPETAL:  Close / 1                  (quoted per 1g, 999 purity, 1g lot)
"""

from typing import Dict, Any
import pandas as pd

CONTRACT_SPECS: Dict[str, Dict[str, Any]] = {
    "GOLDM": {
        "name": "Gold Mini",
        "lot_size_grams": 100,
        "quote_unit_grams": 10,
        "purity": 995,
        "purity_factor": 999 / 995,
        "expiry_cycle": "3rd–5th of expiry month",
        "tender_period_days": 5,
        "formula_str": "Close ÷ 10 × (999 / 995)",
    },
    "GOLDTEN": {
        "name": "Gold 10 Grams",
        "lot_size_grams": 10,
        "quote_unit_grams": 10,
        "purity": 999,
        "purity_factor": 1.0,
        "expiry_cycle": "27th–31st of expiry month",
        "tender_period_days": 5,
        "formula_str": "Close ÷ 10",
    },
    "GOLDGUINEA": {
        "name": "Gold Guinea",
        "lot_size_grams": 8,
        "quote_unit_grams": 8,
        "purity": 999,
        "purity_factor": 1.0,
        "expiry_cycle": "27th–31st of expiry month",
        "tender_period_days": 5,
        "formula_str": "Close ÷ 8",
    },
    "GOLDPETAL": {
        "name": "Gold Petal",
        "lot_size_grams": 1,
        "quote_unit_grams": 1,
        "purity": 999,
        "purity_factor": 1.0,
        "expiry_cycle": "27th–31st of expiry month",
        "tender_period_days": 5,
        "formula_str": "Close ÷ 1",
    },
}


def normalize_gold_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Convert supported MCX gold futures quotes to ₹/gram, adjusted to 999 purity.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing at least 'symbol' and 'close' columns.

    Returns
    -------
    pd.DataFrame
        Copy of input DataFrame with added 'normalized_price_per_gram' column.
    """
    required = {"symbol", "close"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    result = df.copy()
    result["close"] = pd.to_numeric(
        result["close"], errors="coerce"
    )

    formulas = {
        "GOLDM": lambda price: price / 10.0 * (999.0 / 995.0),
        "GOLDTEN": lambda price: price / 10.0,
        "GOLDGUINEA": lambda price: price / 8.0,
        "GOLDPETAL": lambda price: price / 1.0,
    }

    result["normalized_price_per_gram"] = pd.NA

    for symbol, formula in formulas.items():
        mask = result["symbol"].astype(str).str.strip().str.upper().eq(symbol)
        if mask.any():
            result.loc[mask, "normalized_price_per_gram"] = (
                formula(result.loc[mask, "close"])
            )

    result["normalized_price_per_gram"] = pd.to_numeric(
        result["normalized_price_per_gram"],
        errors="coerce",
    )

    return result
