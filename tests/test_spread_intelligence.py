"""Test spread intelligence (Z-score, percentiles, directional statistics)."""

from pathlib import Path
import pandas as pd
import pytest
from src.spread_engine import calculate_calendar_spreads
from src.spread_intelligence import calculate_spread_intelligence


def test_spread_intelligence():
    data_path = Path("data/processed/historical_gold_futures.csv")
    if not data_path.exists():
        pytest.skip("Historical dataset not found")

    df = pd.read_csv(data_path)
    symbol = "GOLDGUINEA"

    spreads = calculate_calendar_spreads(df=df, symbol=symbol)
    assert not spreads.empty

    pairs = spreads[["near_expiry", "far_expiry"]].drop_duplicates()
    first_pair = pairs.iloc[0]

    selected_spread = spreads[
        (spreads["near_expiry"] == first_pair["near_expiry"])
        & (spreads["far_expiry"] == first_pair["far_expiry"])
    ].copy()

    intelligence = calculate_spread_intelligence(selected_spread)

    assert not intelligence.empty
    expected_cols = [
        "trade_date",
        "calendar_spread",
        "spread_direction",
        "spread_percentile",
        "historical_mean",
        "historical_std",
        "spread_zscore",
    ]
    for col in expected_cols:
        assert col in intelligence.columns

    # Verify that Z-scores are NaN for < 10 prior observations
    if len(intelligence) > 10:
        first_few_nan = intelligence["spread_zscore"].iloc[:9].isna().all()
        assert first_few_nan
