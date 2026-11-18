import pandas as pd

from test_backtest_engine import calculate_backtest_summary


def test_backtest_summary():

    # Simulate 4 completed trades:
    # Trade 1: Win +20
    # Trade 2: Loss -10
    # Trade 3: Win +30 (expiry exit)
    # Trade 4: Loss -5 (end-of-data exit)

    backtest_results = pd.DataFrame({
        "trade_id": [
            1, 1,
            2, 2,
            3, 3,
            4, 4,
        ],
        "action": [
            "Enter Long Spread",
            "Exit Long Spread",

            "Enter Short Spread",
            "Exit Short Spread",

            "Enter Long Spread",
            "Expiry Exit Long Spread",

            "Enter Short Spread",
            "End of Data Exit Short Spread",
        ],
        "daily_pnl": [
            -2, 22,
            -2, -8,
            -2, 32,
            -2, -3,
        ],
    })

    print("\nTESTING BACKTEST SUMMARY")
    print("-----------------------")

    calculate_backtest_summary(
        backtest_results
    )

    # Expected trade P&L:
    # Trade 1 = 20
    # Trade 2 = -10
    # Trade 3 = 30
    # Trade 4 = -5

    expected_total_pnl = 35
    expected_completed_trades = 4
    expected_winning_trades = 2
    expected_losing_trades = 2
    expected_win_rate = 50.0

    trade_pnl = (
        backtest_results
        .groupby("trade_id")["daily_pnl"]
        .sum()
    )

    assert len(trade_pnl) == expected_completed_trades
    assert trade_pnl.sum() == expected_total_pnl

    assert (
        (trade_pnl > 0).sum()
        == expected_winning_trades
    )

    assert (
        (trade_pnl < 0).sum()
        == expected_losing_trades
    )

    assert (
        expected_winning_trades
        / expected_completed_trades
        * 100
        == expected_win_rate
    )

    print("\nPASS: Backtest summary calculations.")


if __name__ == "__main__":
    test_backtest_summary()
    print("All tests passed.")