
import pandas as pd



def run_calendar_spread_backtest(
    intelligence_data: pd.DataFrame,
    entry_zscore: float = 2.0,
    exit_zscore: float = 0.0,
    transaction_cost_per_leg: float = 0.0,
    slippage_per_leg: float = 0.0,
) -> pd.DataFrame:

    required_columns = [
        "trade_date",
        "near_expiry",
        "far_expiry",
        "calendar_spread",
        "spread_zscore",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in intelligence_data.columns
    ]

    if missing_columns:
        raise ValueError(f"Missing columns: {missing_columns}")

    if entry_zscore <= 0:
        raise ValueError("entry_zscore must be greater than zero.")

    if exit_zscore < 0 or exit_zscore >= entry_zscore:
        raise ValueError(
            "exit_zscore must be >= 0 and < entry_zscore."
        )

    if transaction_cost_per_leg < 0 or slippage_per_leg < 0:
        raise ValueError("Costs and slippage cannot be negative.")

    data = intelligence_data.copy()

    for col in ["trade_date", "near_expiry", "far_expiry"]:
        data[col] = pd.to_datetime(data[col], errors="coerce")

    for col in ["calendar_spread", "spread_zscore"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = (
        data.dropna(subset=required_columns)
        .sort_values("trade_date")
        .drop_duplicates(
            subset=["trade_date", "near_expiry", "far_expiry"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    result_columns = [
        "trade_date",
        "near_expiry",
        "far_expiry",
        "calendar_spread",
        "spread_zscore",
        "position",
        "trade_id",
        "action",
        "daily_pnl",
        "entry_date",
        "entry_spread",
        "cumulative_pnl",
    ]

    if data.empty:
        return pd.DataFrame(columns=result_columns)

    results = []

    position = 0
    trade_id = 0
    entry_date = None
    entry_spread = None

    cost_per_entry_exit = 2 * (
        transaction_cost_per_leg + slippage_per_leg
    )

    for i, row in data.iterrows():

        current_date = row["trade_date"]
        current_spread = row["calendar_spread"]
        current_zscore = row["spread_zscore"]
        near_expiry = row["near_expiry"]

        daily_pnl = 0.0
        action = "Hold"

        expiry_exit = False
        end_of_data_exit = False

        if i + 1 < len(data):

            next_date = data.loc[i + 1, "trade_date"]
            next_near_expiry = data.loc[i + 1, "near_expiry"]

            expiry_exit = (
    current_date >= near_expiry
    or next_near_expiry != near_expiry
)

        else:

            days_until_expiry = (
                near_expiry - current_date
            ).days

            expiry_exit = (
                current_date < near_expiry
                and days_until_expiry <= 3
            )

            end_of_data_exit = not expiry_exit

        # Update P&L for an open position.
        if position != 0:

            previous_spread = data.loc[
                i - 1, "calendar_spread"
            ]

            spread_change = current_spread - previous_spread

            daily_pnl = spread_change * position

            if position == 1:
                exit_signal = current_zscore >= exit_zscore
            else:
                exit_signal = current_zscore <= -exit_zscore

            if exit_signal or expiry_exit or end_of_data_exit:

                if exit_signal:
                    action = (
                        "Exit Long Spread"
                        if position == 1
                        else "Exit Short Spread"
                    )

                elif expiry_exit:
                    action = (
                        "Expiry Exit Long Spread"
                        if position == 1
                        else "Expiry Exit Short Spread"
                    )

                else:
                    action = (
                        "End of Data Exit Long Spread"
                        if position == 1
                        else "End of Data Exit Short Spread"
                    )

                daily_pnl -= cost_per_entry_exit

                position = 0
                entry_date = None
                entry_spread = None

        # Enter only when no position is open.
        if (
            position == 0
            and not expiry_exit
            and not end_of_data_exit
            and "Exit" not in action
        ):

            if current_zscore <= -entry_zscore:

                position = 1
                trade_id += 1

                entry_date = current_date
                entry_spread = current_spread

                action = "Enter Long Spread"

                daily_pnl -= cost_per_entry_exit

            elif current_zscore >= entry_zscore:

                position = -1
                trade_id += 1

                entry_date = current_date
                entry_spread = current_spread

                action = "Enter Short Spread"

                daily_pnl -= cost_per_entry_exit

        current_trade_id = (
            trade_id
            if position != 0 or "Exit" in action
            else None
        )

        results.append({
            "trade_date": current_date,
            "near_expiry": row["near_expiry"],
            "far_expiry": row["far_expiry"],
            "calendar_spread": current_spread,
            "spread_zscore": current_zscore,
            "position": position,
            "trade_id": current_trade_id,
            "action": action,
            "daily_pnl": daily_pnl,
            "entry_date": entry_date,
            "entry_spread": entry_spread,
        })

    results_df = pd.DataFrame(results)

    if not results_df.empty:
        results_df["cumulative_pnl"] = (
            results_df["daily_pnl"].cumsum()
        )

    return results_df
