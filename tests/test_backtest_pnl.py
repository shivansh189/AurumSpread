import pandas as pd

from src.backtest_engine import run_calendar_spread_backtest


def create_test_data():
    return pd.DataFrame({
        "trade_date": pd.date_range(
            start="2026-01-01",
            periods=4,
            freq="D",
        ),
        "near_expiry": pd.to_datetime(
            ["2026-02-27"] * 4
        ),
        "far_expiry": pd.to_datetime(
            ["2026-03-27"] * 4
        ),
        "near_price": [100, 100, 100, 100],
        "far_price": [110, 108, 107, 110],
        "calendar_spread": [10, 8, 7, 10],
        "spread_zscore": [-2.5, -1.5, -0.5, 0.5],
    })


def test_long_spread_pnl():
    data = create_test_data()

    result = run_calendar_spread_backtest(
        data,
        entry_zscore=2.0,
        exit_zscore=0.0,
    )

    print(result[
        ["trade_date", "calendar_spread",
         "position", "action", "daily_pnl"]
    ])

    # Enter long when z-score <= -2.
    assert result.loc[0, "action"] == "Enter Long Spread"

    # Spread moves from 10 to 8: long spread loses 2.
    assert result.loc[1, "daily_pnl"] == -2

    # Spread moves from 8 to 7: long spread loses 1.
    assert result.loc[2, "daily_pnl"] == -1

    # Exit when z-score reaches/crosses 0.
    assert result.loc[3, "action"] == "Exit Long Spread"

    # Spread moves from 7 to 10: long spread gains 3.
    assert result.loc[3, "daily_pnl"] == 3

    print("PASS: Long spread P&L calculation.")


def test_transaction_costs():
    data = create_test_data()

    result = run_calendar_spread_backtest(
        data,
        entry_zscore=2.0,
        exit_zscore=0.0,
        transaction_cost_per_leg=5.0,
        slippage_per_leg=2.0,
    )

    # Two legs at entry: 2 * (5 + 2) = 14.
    assert result.loc[0, "daily_pnl"] == -14

    # Exit day: spread gain of 3 minus exit costs of 14.
    assert result.loc[3, "daily_pnl"] == -11

    # Total: -14 - 2 - 1 - 11 = -28.
    assert result["daily_pnl"].sum() == -28

    print("PASS: Transaction costs and slippage.")


if __name__ == "__main__":
    test_long_spread_pnl()
    test_transaction_costs()

    print("All tests passed.")