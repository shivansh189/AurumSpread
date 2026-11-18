"""Test backtest engine execution and trade lifecycle."""

from pathlib import Path
import pandas as pd
import pytest

from src.spread_engine import calculate_calendar_spreads
from src.spread_intelligence import calculate_spread_intelligence
from src.backtest_engine import (
    run_calendar_spread_backtest,
    calculate_backtest_summary,
    find_breakeven_cost,
)


def test_calendar_spread_backtest_execution():
    data_path = Path("data/processed/historical_gold_futures.csv")
    if not data_path.exists():
        pytest.skip("Historical dataset not found")

    df = pd.read_csv(data_path)
    symbol = "GOLDGUINEA"

    spread_data = calculate_calendar_spreads(df=df, symbol=symbol)
    assert not spread_data.empty

    pairs = spread_data[["near_expiry", "far_expiry"]].drop_duplicates()
    first_pair = pairs.iloc[0]

    selected_spread = spread_data[
        (spread_data["near_expiry"] == first_pair["near_expiry"])
        & (spread_data["far_expiry"] == first_pair["far_expiry"])
    ].sort_values("trade_date")

    intelligence = calculate_spread_intelligence(selected_spread)

    # Test execution with intelligence_data parameter
    backtest = run_calendar_spread_backtest(
        intelligence_data=intelligence,
        entry_zscore=2.0,
        exit_zscore=0.0,
        transaction_cost_per_leg=0.0,
        slippage_per_leg=0.0,
    )

    assert not backtest.empty
    assert "daily_pnl" in backtest.columns
    assert "cumulative_pnl" in backtest.columns
    assert "cumulative_gross_pnl" in backtest.columns

    # Test summary function
    summary = calculate_backtest_summary(backtest)
    assert "total_trades" in summary
    assert "win_rate" in summary
    assert "total_net_pnl" in summary

    # Test breakeven cost calculation
    be_cost = find_breakeven_cost(intelligence, entry_zscore=2.0, exit_zscore=0.0)
    assert be_cost >= 0.0
