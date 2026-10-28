"""Test calendar spread calculation engine."""

from pathlib import Path
import pandas as pd
import pytest
from src.spread_engine import calculate_calendar_spreads


def test_calculate_calendar_spreads():
    data_path = Path("data/processed/historical_gold_futures.csv")
    if not data_path.exists():
        pytest.skip("Historical dataset not found")

    df = pd.read_csv(data_path)
    symbol = "GOLDGUINEA"

    spreads = calculate_calendar_spreads(df=df, symbol=symbol)

    assert not spreads.empty
    expected_cols = [
        "trade_date",
        "symbol",
        "near_expiry",
        "far_expiry",
        "near_price",
        "far_price",
        "calendar_spread",
        "spread_percent",
    ]
    for col in expected_cols:
        assert col in spreads.columns

    # Verify that far_expiry > near_expiry
    assert (pd.to_datetime(spreads["far_expiry"]) > pd.to_datetime(spreads["near_expiry"])).all()

    # Verify that spread = far_price - near_price
    diff = spreads["far_price"] - spreads["near_price"]
    assert (abs(spreads["calendar_spread"] - diff) < 1e-4).all()
