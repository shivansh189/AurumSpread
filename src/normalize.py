
import pandas as pd


def normalize_gold_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Convert supported MCX gold futures quotes to ₹/gram,
    adjusted to 999 purity.
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
        "GOLDM": lambda price: price / 10 * 999 / 995,
        "GOLDTEN": lambda price: price / 10,
        "GOLDGUINEA": lambda price: price / 8,
        "GOLDPETAL": lambda price: price,
    }

    result["normalized_price_per_gram"] = pd.NA

    for symbol, formula in formulas.items():
        mask = result["symbol"].eq(symbol)
        result.loc[mask, "normalized_price_per_gram"] = (
            formula(result.loc[mask, "close"])
        )

    result["normalized_price_per_gram"] = pd.to_numeric(
        result["normalized_price_per_gram"],
        errors="coerce",
    )

    return result
