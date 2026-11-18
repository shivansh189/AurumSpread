import pandas as pd

from src.backtest_engine import run_calendar_spread_backtest


def test_end_of_data_exit():

    test_data = pd.DataFrame({
        "trade_date": [
            "2026-09-10",
            "2026-09-11",
            "2026-09-12",
        ],
        "near_expiry": [
            "2026-09-30",
            "2026-09-30",
            "2026-09-30",
        ],
        "far_expiry": [
            "2026-10-30",
            "2026-10-30",
            "2026-10-30",
        ],
        "near_price": [100, 101, 102],
        "far_price": [110, 109, 108],
        "calendar_spread": [10, 8, 6],
        "spread_zscore": [-2.5, -1.5, -1.0],
    })

    results = run_calendar_spread_backtest(
        test_data,
        entry_zscore=2.0,
        exit_zscore=0.0,
        transaction_cost_per_leg=5.0,
        slippage_per_leg=2.0,
    )

    print("\nEND OF DATA EXIT TEST")
    print(results[[
        "trade_date",
        "spread_zscore",
        "position",
        "action",
        "daily_pnl",
        "trade_id",
    ]])

    # Trade enters on first observation.
    assert results.iloc[0]["action"] == "Enter Long Spread"

    # Position remains open until the final observation.
    assert results.iloc[1]["action"] == "Hold"

    # Final observation closes the position.
    assert (
        results.iloc[2]["action"]
        == "End of Data Exit Long Spread"
    )

    # Position is flat after exit.
    assert results.iloc[2]["position"] == 0

    # Entry costs = 2 legs * (5 + 2) = 14.
    assert results.iloc[0]["daily_pnl"] == -14

    # Final spread change = 6 - 8 = -2.
    # Exit costs = 14.
    # Total final day P&L = -2 - 14 = -16.
    assert results.iloc[2]["daily_pnl"] == -16

    # Trade ID remains recorded on the exit row.
    assert results.iloc[2]["trade_id"] == 1

    print("\nPASS: End-of-data exit test.")


if __name__ == "__main__":
    test_end_of_data_exit()
    print("All tests passed.")