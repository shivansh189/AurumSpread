"""Test calendar spread calculation and backtesting across all expiry pairs."""

from pathlib import Path
import pandas as pd
import pytest

from src.spread_engine import calculate_calendar_spreads
from src.spread_intelligence import calculate_spread_intelligence
from src.backtest_engine import run_calendar_spread_backtest, calculate_backtest_summary


def test_all_expiry_pairs():
    data_path = Path("data/processed/historical_gold_futures.csv")
    if not data_path.exists():
        pytest.skip("Historical dataset not found")

    df = pd.read_csv(data_path)
    symbol = "GOLDGUINEA"

    spread_data = calculate_calendar_spreads(df=df, symbol=symbol)
    assert not spread_data.empty

    expiry_pairs = (
        spread_data[["near_expiry", "far_expiry"]]
        .drop_duplicates()
        .sort_values(["near_expiry", "far_expiry"])
    )
    assert len(expiry_pairs) > 0

    tested_pairs = 0
    for _, pair in expiry_pairs.iterrows():
        near_expiry = pair["near_expiry"]
        far_expiry = pair["far_expiry"]

        selected_spread = spread_data[
            (spread_data["near_expiry"] == near_expiry)
            & (spread_data["far_expiry"] == far_expiry)
        ].sort_values("trade_date")

        intelligence = calculate_spread_intelligence(selected_spread)

        backtest = run_calendar_spread_backtest(
            intelligence_data=intelligence,
            entry_zscore=2.0,
            exit_zscore=0.0,
            transaction_cost_per_leg=5.0,
            slippage_per_leg=2.0,
        )

        assert not backtest.empty
        assert "cumulative_pnl" in backtest.columns
        tested_pairs += 1

    assert tested_pairs == len(expiry_pairs)
