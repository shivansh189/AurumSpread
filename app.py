from src.backtest_engine import run_calendar_spread_backtest
from src.spread_intelligence import calculate_spread_intelligence
from src.spread_engine import calculate_calendar_spreads
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.ingest import adapt_mcx_bhavcopy
from src.normalize import normalize_gold_prices

DATA_PATH = Path(
    "data/processed/historical_gold_futures.csv"
)

st.set_page_config(
    page_title="AurumSpread",
    page_icon="🟡",
    layout="wide",
)
st.markdown("""
<style>
/* Main background */
.stApp {
    background-color: #0B1120;
    color: #E5E7EB;
}

/* Main content spacing */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* Headings */
h1, h2, h3 {
    color: #F5C542 !important;
    font-weight: 700;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #111827;
    border-right: 1px solid #263247;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background-color: #151F32;
    border: 1px solid #263247;
    padding: 18px;
    border-radius: 12px;
}

/* Metric labels */
div[data-testid="stMetricLabel"] {
    color: #9CA3AF;
}

/* Metric values */
div[data-testid="stMetricValue"] {
    color: #F5C542;
}

/* Tabs */
button[data-baseweb="tab"] {
    color: #D1D5DB;
}

/* Data tables */
div[data-testid="stDataFrame"] {
    border: 1px solid #263247;
    border-radius: 10px;
}

/* Buttons */
.stButton button {
    background-color: #F5C542;
    color: #111827;
    border-radius: 8px;
    border: none;
    font-weight: 600;
}

/* Select boxes and input fields */
div[data-baseweb="select"] > div {
    background-color: #151F32;
    border-color: #263247;
}
</style>
""", unsafe_allow_html=True)

st.title("🟡 AurumSpread")
st.caption(
    "MCX Gold Contract Intelligence | Historical analysis only"
)

if not DATA_PATH.exists():
    st.error(f"Dataset not found: {DATA_PATH}")
    st.stop()


raw = pd.read_csv(DATA_PATH)

# The historical dataset is already standardized and normalized.
df = raw.copy()

df["trade_date"] = pd.to_datetime(
    df["trade_date"], errors="coerce"
)
df["expiry_date"] = pd.to_datetime(
    df["expiry_date"], errors="coerce"
)
df["normalized_price_per_gram"] = pd.to_numeric(
    df["normalized_price_per_gram"], errors="coerce"
)

df["trade_date"] = pd.to_datetime(
    df["trade_date"], errors="coerce"
)
df["expiry_date"] = pd.to_datetime(
    df["expiry_date"], errors="coerce"
)

tabs = st.tabs([
    "Market Overview",
    "Spread Explorer",
    "Backtesting",
    "Data Quality",
])

with tabs[0]:
    st.subheader("Market Overview")

    st.caption(
    "MCX gold futures | Historical market statistics "
    "and normalized price overview"
)

    
    # Summary metrics for the latest trading date.
    
    # Summary metrics for the latest trading date.
    latest_date = df["trade_date"].max()
    latest_data = df[df["trade_date"] == latest_date]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Latest Trading Date",
        latest_date.strftime("%d %b %Y"),
    )

    col2.metric(
        "Contract Expiry Rows",
        len(latest_data),
    )

    col3.metric(
        "Average Normalized Price",
        f"₹{latest_data['normalized_price_per_gram'].mean():,.2f}/g",
    )

    # Compare each symbol and expiry across trading dates.
    price_changes = df.sort_values("trade_date").groupby(
        ["symbol", "expiry_date"]
    )["normalized_price_per_gram"].agg(
        lambda prices: prices.iloc[-1] - prices.iloc[0]
    )

    largest_change = (
        price_changes.abs().max()
        if not price_changes.empty
        else 0
    )

    col4.metric(
        "Largest Absolute Change",
        f"₹{largest_change:,.2f}/g",
    )



    c1, c2, c3 = st.columns(3)
    c1.metric("Futures contracts", len(df))
    c2.metric("Gold instruments", df["symbol"].nunique())
    c3.metric(
        "Trading dates",
        df["trade_date"].nunique(),
    )

    trading_days = df["trade_date"].nunique()

if trading_days < 2:
    st.info(
        f"The current sample contains {trading_days} trading day. "
        "Historical performance cannot yet be evaluated."
    )
else:
    st.success(
        f"Historical dataset contains {trading_days} trading days. "
        "Historical price movement can now be evaluated."
    )
    with st.expander("📊 View Historical Dataset", expanded=False):
      st.dataframe(
        df[
            [
                "trade_date",
                "symbol",
                "expiry_date",
                "close",
                "normalized_price_per_gram",
            ]
        ].sort_values(["symbol", "expiry_date"]),
        use_container_width=True,
        hide_index=True,
    )
    
    # Show price movement across trading dates.
    
    st.subheader("Historical Price Movement")

    # Let the user choose one expiry date.
    expiry_dates = sorted(
        df["expiry_date"].dropna().unique()
    )

    selected_expiry = st.selectbox(
        "Select expiry date",
        expiry_dates,
        format_func=lambda date: pd.Timestamp(date).strftime(
            "%d %b %Y"
        ),
    )

    chart_data = df[
        df["expiry_date"] == selected_expiry
    ].sort_values("trade_date")

    fig = px.line(
    chart_data,
    x="trade_date",
    y="normalized_price_per_gram",
    color="symbol",
    markers=True,
    title="Historical Gold Price Movement",
    hover_data=["expiry_date", "close"],
)

    fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0B1120",
    plot_bgcolor="#0B1120",
    font=dict(
        color="#E5E7EB",
        family="Arial",
    ),
    title=dict(
        font=dict(
            color="#F5C542",
            size=20,
        ),
    ),
    xaxis=dict(
        title="Trading Date",
        showgrid=True,
        gridcolor="#263247",
    ),
    yaxis=dict(
        title="Normalized Price (₹/gram)",
        showgrid=True,
        gridcolor="#263247",
    ),
    legend=dict(
        title="Gold Instrument",
        bgcolor="#151F32",
    ),
    margin=dict(l=20, r=20, t=60, b=20),
)

    fig.update_traces(
    line=dict(width=3),
    marker=dict(size=6),
)

    st.plotly_chart(fig, use_container_width=True) 

    st.subheader("Daily Price Change")

    daily_prices = chart_data.pivot_table(
        index="symbol",
        columns="trade_date",
        values="normalized_price_per_gram",
        aggfunc="first",
    )

    daily_prices = daily_prices.sort_index(axis=1)

    if daily_prices.shape[1] >= 2:
        first_day = daily_prices.columns[-2]
        latest_day = daily_prices.columns[-1]

        daily_prices["Change (₹/gram)"] = (
            daily_prices[latest_day] - daily_prices[first_day]
        )

        daily_prices["Change (%)"] = (
            daily_prices["Change (₹/gram)"]
            / daily_prices[first_day]
            * 100
        )

        st.dataframe(
            daily_prices.round(2),
            use_container_width=True,
        )
    else:
        st.info("At least two trading dates are needed.")

with tabs[1]:
    st.subheader("Calendar Spread Explorer")

    st.caption(
        "Compare near-expiry and far-expiry contracts "
        "of the same gold instrument."
    )

    symbols = sorted(df["symbol"].dropna().unique())

    selected_symbol = st.selectbox(
        "Select gold instrument",
        symbols,
        key="spread_symbol",
    )

    # Calculate calendar spreads for the selected instrument.
    spread_data = calculate_calendar_spreads(
        df,
        symbol=selected_symbol,
    )

    if spread_data.empty:
        st.warning(
            "No calendar spread data is available "
            "for this instrument."
        )
    else:
        # Select the near expiry.
        near_expiries = sorted(
            spread_data["near_expiry"].dropna().unique()
        )

        selected_near = st.selectbox(
            "Select near expiry",
            near_expiries,
            format_func=lambda date: pd.Timestamp(date).strftime(
                "%d %b %Y"
            ),
            key="spread_near_expiry",
        )

        # Only show far expiries that are later than the selected near expiry.
        far_expiries = sorted(
            spread_data[
                spread_data["near_expiry"] == selected_near
            ]["far_expiry"]
            .dropna()
            .unique()
        )

        if not far_expiries:
            st.warning(
                "No later expiry is available for "
                "the selected near expiry."
            )
        else:
            selected_far = st.selectbox(
                "Select far expiry",
                far_expiries,
                format_func=lambda date: pd.Timestamp(date).strftime(
                    "%d %b %Y"
                ),
                key="spread_far_expiry",
            )

            # Filter to the selected expiry pair.
            selected_spread = spread_data[
                (spread_data["near_expiry"] == selected_near)
                & (spread_data["far_expiry"] == selected_far)
            ].sort_values("trade_date")

if selected_spread.empty:
    st.warning(
        "No observations found for this expiry pair."
    )

else:
    latest = selected_spread.iloc[-1]

    # Calculate spread intelligence.
    intelligence = calculate_spread_intelligence(
        selected_spread
    )

    latest_intelligence = intelligence.iloc[-1]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Latest Calendar Spread",
        f"₹{latest['calendar_spread']:,.2f}/g",
    )

    col2.metric(
        "Latest Spread %",
        f"{latest['spread_percent']:.2f}%",
    )

    col3.metric(
        "Latest Trading Date",
        pd.Timestamp(
            latest["trade_date"]
        ).strftime("%d %b %Y"),
    )

                # Calendar spread chart.
    fig = px.line(
                    selected_spread,
                    x="trade_date",
                    y="calendar_spread",
                    markers=True,
                    title=(
                        f"{selected_symbol}: "
                        f"{pd.Timestamp(selected_near).strftime('%d %b %Y')} "
                        f"vs "
                        f"{pd.Timestamp(selected_far).strftime('%d %b %Y')}"
                    ),
                    labels={
                        "trade_date": "Trading Date",
                        "calendar_spread": "Calendar Spread (₹/gram)",
                    },
                    hover_data=[
                        "near_price",
                        "far_price",
                        "spread_percent",
                    ],
                )

    st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

                # Spread percentage chart.
    fig_percent = px.line(
                    selected_spread,
                    x="trade_date",
                    y="spread_percent",
                    markers=True,
                    title="Calendar Spread (%)",
                    labels={
                        "trade_date": "Trading Date",
                        "spread_percent": "Spread (%)",
                    },
                )

    st.plotly_chart(
                    fig_percent,
                    use_container_width=True,
                )

    # Spread Intelligence Metrics
st.subheader("Spread Intelligence")

col4, col5, col6, col7 = st.columns(4)

col4.metric(
    "Spread Change",
    f"₹{latest_intelligence['spread_change']:,.2f}/g"
    if pd.notna(latest_intelligence["spread_change"])
    else "N/A",
)

col5.metric(
    "Spread Direction",
    latest_intelligence["spread_direction"]
    if pd.notna(latest_intelligence["spread_direction"])
    else "N/A",
)

col6.metric(
    "Historical Percentile",
    f"{latest_intelligence['spread_percentile']:.2f}%",
)

col7.metric(
    "Spread Z-Score",
    f"{latest_intelligence['spread_zscore']:.2f}"
    if pd.notna(latest_intelligence["spread_zscore"])
    else "N/A",
)

# Spread Intelligence Interpretation
st.subheader("Spread Interpretation")

current_percentile = latest_intelligence["spread_percentile"]
current_zscore = latest_intelligence["spread_zscore"]
current_direction = latest_intelligence["spread_direction"]

if current_percentile <= 20:
    percentile_text = "The spread is near the lower end of its observed history."
elif current_percentile >= 80:
    percentile_text = "The spread is near the upper end of its observed history."
else:
    percentile_text = "The spread is within the middle range of its observed history."

if current_zscore <= -1:
    zscore_text = "The spread is below its expanding historical mean."
elif current_zscore >= 1:
    zscore_text = "The spread is above its expanding historical mean."
else:
    zscore_text = "The spread is close to its expanding historical mean."

st.info(
    f"{current_direction}. "
    f"{percentile_text} "
    f"{zscore_text}"
)

# Historical percentile chart
st.subheader("Historical Spread Percentile")

fig_percentile = px.line(
    intelligence,
    x="trade_date",
    y="spread_percentile",
    markers=True,
    title="Spread Percentile Over Time",
    labels={
        "trade_date": "Trading Date",
        "spread_percentile": "Historical Percentile (%)",
    },
)

fig_percentile.add_hline(
    y=50,
    line_dash="dash",
    annotation_text="50th Percentile",
)

st.plotly_chart(
    fig_percentile,
    use_container_width=True,
)


# Spread z-score chart
st.subheader("Spread Z-Score")

fig_zscore = px.line(
    intelligence,
    x="trade_date",
    y="spread_zscore",
    markers=True,
    title="Spread Z-Score Over Time",
    labels={
        "trade_date": "Trading Date",
        "spread_zscore": "Z-Score",
    },
)

fig_zscore.add_hline(
    y=0,
    line_dash="dash",
    annotation_text="Historical Mean",
)

st.plotly_chart(
    fig_zscore,
    use_container_width=True,
)

st.subheader("Spread Observations")

st.dataframe(
                    selected_spread[
                        [
                            "trade_date",
                            "near_expiry",
                            "far_expiry",
                            "near_price",
                            "far_price",
                            "calendar_spread",
                            "spread_percent",
                        ]
                    ].sort_values("trade_date", ascending=False),
                    use_container_width=True,
                )

with tabs[2]:

    st.subheader("Calendar Spread Backtesting")

    st.caption(
        "Historical calendar-spread strategy simulation "
        "using MCX gold futures."
    )

    # --------------------------------------------------
    # 1. Select instrument
    # --------------------------------------------------

    backtest_symbols = sorted(
        df["symbol"].dropna().unique()
    )

    selected_bt_symbol = st.selectbox(
        "Select gold instrument",
        backtest_symbols,
        key="calendar_bt_symbol",
    )

    # --------------------------------------------------
    # 2. Generate calendar spreads
    # --------------------------------------------------

    bt_spread_data = calculate_calendar_spreads(
        df,
        symbol=selected_bt_symbol,
    )

    if bt_spread_data.empty:

        st.warning(
            "No calendar spread data is available "
            "for this instrument."
        )

    else:

        # --------------------------------------------------
        # 3. Select near expiry
        # --------------------------------------------------

        bt_near_expiries = sorted(
            bt_spread_data["near_expiry"]
            .dropna()
            .unique()
        )

        selected_bt_near = st.selectbox(
            "Select near expiry",
            bt_near_expiries,
            format_func=lambda date: pd.Timestamp(
                date
            ).strftime("%d %b %Y"),
            key="calendar_bt_near",
        )

        # --------------------------------------------------
        # 4. Select far expiry
        # --------------------------------------------------

        bt_far_expiries = sorted(
            bt_spread_data[
                bt_spread_data["near_expiry"]
                == selected_bt_near
            ]["far_expiry"]
            .dropna()
            .unique()
        )

        if not bt_far_expiries:

            st.warning(
                "No later expiry is available "
                "for the selected near expiry."
            )

        else:

            selected_bt_far = st.selectbox(
                "Select far expiry",
                bt_far_expiries,
                format_func=lambda date: pd.Timestamp(
                    date
                ).strftime("%d %b %Y"),
                key="calendar_bt_far",
            )

            # --------------------------------------------------
            # 5. Select strategy settings
            # --------------------------------------------------

            st.subheader("Strategy Settings")

            col1, col2 = st.columns(2)

            entry_zscore = col1.number_input(
                "Entry z-score threshold",
                min_value=0.5,
                max_value=5.0,
                value=2.0,
                step=0.5,
                key="calendar_bt_entry",
            )

            exit_zscore = col2.number_input(
                "Exit z-score threshold",
                min_value=0.0,
                max_value=1.5,
                value=0.0,
                step=0.25,
                key="calendar_bt_exit",
            )

            if exit_zscore >= entry_zscore:

                st.warning(
                    "The exit z-score must be smaller "
                    "than the entry z-score."
                )

            else:

                # --------------------------------------------------
                # 6. Cost settings
                # --------------------------------------------------

                st.subheader("Transaction Costs & Slippage")

                col3, col4 = st.columns(2)

                transaction_cost = col3.number_input(
                    "Transaction cost per leg (₹)",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key="calendar_bt_cost",
                )

                slippage = col4.number_input(
                    "Slippage per leg (₹)",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key="calendar_bt_slippage",
                )

                # --------------------------------------------------
                # 7. Filter selected expiry pair
                # --------------------------------------------------

                selected_bt_spread = bt_spread_data[
                    (
                        bt_spread_data["near_expiry"]
                        == selected_bt_near
                    )
                    &
                    (
                        bt_spread_data["far_expiry"]
                        == selected_bt_far
                    )
                ].sort_values(
                    "trade_date"
                ).reset_index(drop=True)

                if selected_bt_spread.empty:

                    st.warning(
                        "No observations found "
                        "for this expiry pair."
                    )

                else:

                    # --------------------------------------------------
                    # 8. Calculate spread intelligence
                    # --------------------------------------------------

                    bt_intelligence = (
                        calculate_spread_intelligence(
                            selected_bt_spread
                        )
                    )

                    # --------------------------------------------------
                    # 9. Run gross backtest
                    # --------------------------------------------------

                    gross_results = (
                        run_calendar_spread_backtest(
                            bt_intelligence,
                            entry_zscore=entry_zscore,
                            exit_zscore=exit_zscore,
                            transaction_cost_per_leg=0.0,
                            slippage_per_leg=0.0,
                        )
                    )
                    
                st.dataframe(gross_results)

                    
                    
                    # Stop only if the backtest has no usable observations
                # Stop only if the backtest has no usable observations
                if gross_results.empty:
                 st.warning(
        "Not enough valid spread z-score data to run "
        "the backtest for this expiry pair. "
        "Please select another expiry pair."
    )
                 st.stop()

# Verify that expected P&L column exists
                if "daily_pnl" not in gross_results.columns:
                   st.error(
        "Backtest output does not contain the daily_pnl column."
    )
                   st.write("Available columns:", gross_results.columns.tolist())
                   st.stop()
                    # --------------------------------------------------
                    # 10. Run net backtest with costs
                    # --------------------------------------------------

                net_results = (
                        run_calendar_spread_backtest(
                            bt_intelligence,
                            entry_zscore=entry_zscore,
                            exit_zscore=exit_zscore,
                            transaction_cost_per_leg=(
                                transaction_cost
                            ),
                            slippage_per_leg=slippage,
                        )
                    )

                    # --------------------------------------------------
                    # 11. Calculate performance metrics
                    # --------------------------------------------------

                gross_pnl = (
                        gross_results["daily_pnl"].sum()
                    )

                net_pnl = (
                        net_results["daily_pnl"].sum()
                    )

                total_costs = (
                        gross_pnl - net_pnl
                    )

                cumulative_pnl = (
                        net_results["daily_pnl"].cumsum()
                    )

                running_peak = (
                        cumulative_pnl.cummax()
                    )

                drawdown = (
                        cumulative_pnl - running_peak
                    )

                max_drawdown = drawdown.min()

                    # --------------------------------------------------
                    # 12. Identify completed trades
                    # --------------------------------------------------

                completed_trade_ids = (
                        net_results[
                            net_results["action"].str.contains(
                                "Exit",
                                case=False,
                                na=False,
                            )
                        ]["trade_id"]
                        .dropna()
                        .unique()
                    )

                trade_data = net_results.dropna(
                        subset=["trade_id"]
                    ).copy()

                trade_pnl = (
                        trade_data.groupby(
                            "trade_id"
                        )["daily_pnl"].sum()
                    )

                completed_trades = (
                        trade_pnl[
                            trade_pnl.index.isin(
                                completed_trade_ids
                            )
                        ]
                    )

                total_trades = len(
                        completed_trades
                    )

                winning_trades = (
                        completed_trades > 0
                    ).sum()

                losing_trades = (
                        completed_trades < 0
                    ).sum()

                win_rate = (
                        winning_trades / total_trades * 100
                        if total_trades > 0
                        else 0.0
                    )

                average_trade_pnl = (
                        completed_trades.mean()
                        if total_trades > 0
                        else 0.0
                    )

                    # --------------------------------------------------
                    # 13. Display metrics
                    # --------------------------------------------------

                st.subheader("Backtest Results")

                c1, c2, c3, c4 = st.columns(4)

                c1.metric(
                        "Gross P&L",
                        f"₹{gross_pnl:,.2f}",
                    )

                c2.metric(
                        "Net P&L",
                        f"₹{net_pnl:,.2f}",
                    )

                c3.metric(
                        "Total Costs",
                        f"₹{total_costs:,.2f}",
                    )

                c4.metric(
                        "Maximum Drawdown",
                        f"₹{max_drawdown:,.2f}",
                    )

                c5, c6, c7, c8 = st.columns(4)

                c5.metric(
                        "Completed Trades",
                        total_trades,
                    )

                c6.metric(
                        "Win Rate",
                        f"{win_rate:.2f}%",
                    )

                c7.metric(
                        "Winning Trades",
                        winning_trades,
                    )

                c8.metric(
                        "Losing Trades",
                        losing_trades,
                    )

                st.metric(
                        "Average P&L per Trade",
                        f"₹{average_trade_pnl:,.2f}",
                    )

                    # --------------------------------------------------
                    # 14. P&L chart
                    # --------------------------------------------------

                st.subheader("Cumulative P&L")

                pnl_chart = pd.DataFrame({
                        "trade_date": net_results[
                            "trade_date"
                        ],
                        "Gross P&L": (
                            gross_results[
                                "daily_pnl"
                            ].cumsum()
                        ),
                        "Net P&L": (
                            net_results[
                                "daily_pnl"
                            ].cumsum()
                        ),
                    })

                fig_pnl = px.line(
                        pnl_chart,
                        x="trade_date",
                        y=[
                            "Gross P&L",
                            "Net P&L",
                        ],
                        markers=True,
                        title=(
                            "Gross vs Net "
                            "Cumulative P&L"
                        ),
                        labels={
                            "trade_date": "Trading Date",
                            "value": "P&L (₹)",
                            "variable": "P&L Type",
                        },
                    )

                fig_pnl.add_hline(
                        y=0,
                        line_dash="dash",
                    )

                st.plotly_chart(
                        fig_pnl,
                        use_container_width=True,
                    )

                    # --------------------------------------------------
                    # 15. Spread and z-score chart
                    # --------------------------------------------------

                st.subheader(
                        "Spread and Strategy Signals"
                    )

                fig_signal = px.line(
                        bt_intelligence,
                        x="trade_date",
                        y="spread_zscore",
                        markers=True,
                        title="Spread Z-Score",
                    )

                fig_signal.add_hline(
                        y=entry_zscore,
                        line_dash="dash",
                        annotation_text="Short Entry",
                    )

                fig_signal.add_hline(
                        y=-entry_zscore,
                        line_dash="dash",
                        annotation_text="Long Entry",
                    )

                fig_signal.add_hline(
                        y=exit_zscore,
                        line_dash="dot",
                        annotation_text="Long Exit",
                    )

                fig_signal.add_hline(
                        y=-exit_zscore,
                        line_dash="dot",
                        annotation_text="Short Exit",
                    )

                st.plotly_chart(
                        fig_signal,
                        use_container_width=True,
                    )

                    # --------------------------------------------------
                    # 16. Trade history
                    # --------------------------------------------------

                st.subheader("Backtest Trade History")

                st.dataframe(
                        net_results[
                            [
                                "trade_date",
                                "calendar_spread",
                                "spread_zscore",
                                "position",
                                "action",
                                "daily_pnl",
                                "cumulative_pnl",
                            ]
                        ].sort_values(
                            "trade_date",
                            ascending=False,
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )

                    # --------------------------------------------------
                    # 17. Strategy explanation
                    # --------------------------------------------------

                st.info(
                        "Long spread: enter when the z-score "
                        "falls below the negative entry threshold. "
                        "Short spread: enter when the z-score "
                        "exceeds the positive entry threshold. "
                        "Positions exit when the z-score returns "
                        "to the configured exit threshold or "
                        "when the near contract approaches expiry."
                    )

                st.caption(
                        "Historical research simulation only. "
                        "Results are based on normalized spread "
                        "changes and do not represent live "
                        "trading performance. Cost assumptions "
                        "are configurable and may not capture "
                        "all actual brokerage, exchange fees, "
                        "taxes, market impact, or margin costs."
                    )

                # --------------------------------------------------
                # 18. Exit Z-Score Strategy Comparison
                # --------------------------------------------------

                st.subheader("Exit Z-Score Strategy Comparison")
                st.success("Exit Z-Score comparison section is running!")
                st.caption(
                    "Compare exit thresholds while keeping "
                    "the entry z-score fixed at 2.0."
                )

                exit_threshold_values = [
                    0.0,
                    0.5,
                    1.0,
                    1.5,
                ]

                exit_comparison_results = []

                for exit_threshold in exit_threshold_values:

                    comparison_backtest = (
                        run_calendar_spread_backtest(
                            bt_intelligence,
                            entry_zscore=2.0,
                            exit_zscore=exit_threshold,
                            transaction_cost_per_leg=transaction_cost,
                            slippage_per_leg=slippage,
                        )
                    )

                    completed_trades = (
                        comparison_backtest[
                            comparison_backtest["action"].str.contains(
                                "Exit",
                                case=False,
                                na=False,
                            )
                            &
                            comparison_backtest["trade_id"].notna()
                        ]
                    )

                    total_trades = len(completed_trades)

                    total_net_pnl = (
                        comparison_backtest["daily_pnl"].sum()
                    )

                    exit_comparison_results.append(
                        {
                            "Exit Z-Score": exit_threshold,
                            "Completed Trades": total_trades,
                            "Net P&L (₹)": round(
                                total_net_pnl,
                                2,
                            ),
                        }
                    )

                exit_comparison_df = pd.DataFrame(
                    exit_comparison_results
                )

                st.dataframe(
                    exit_comparison_df,
                    use_container_width=True,
                    hide_index=True,
                )

                fig_exit_comparison = px.bar(
                    exit_comparison_df,
                    x="Exit Z-Score",
                    y="Net P&L (₹)",
                    title="Net P&L by Exit Z-Score",
                    text="Net P&L (₹)",
                )

                st.plotly_chart(
                    fig_exit_comparison,
                    use_container_width=True,
                )
# --------------------------------------------------
# Expiry Pair Performance Comparison
# --------------------------------------------------

st.divider()


st.subheader("Expiry Pair Performance")

st.caption(
    "Compare the calendar-spread strategy across all "
    "available expiry pairs using consistent settings."
)

# Default research settings
comparison_entry_zscore = 2.0
comparison_exit_zscore = 0.0
comparison_transaction_cost = 5.0
comparison_slippage = 2.0

# Generate all calendar spreads for selected instrument
comparison_spreads = calculate_calendar_spreads(
    df,
    symbol=selected_bt_symbol
)

if comparison_spreads.empty:

    st.warning(
        "No calendar spread data is available "
        "for comparison."
    )

else:

    comparison_results = []

    # Get all available expiry pairs
    expiry_pairs = (
        comparison_spreads[
            ["near_expiry", "far_expiry"]
        ]
        .drop_duplicates()
        .sort_values(
            ["near_expiry", "far_expiry"]
        )
    )

    # Run backtest for each expiry pair
    for _, pair in expiry_pairs.iterrows():

        near_expiry = pair["near_expiry"]
        far_expiry = pair["far_expiry"]

        pair_data = comparison_spreads[
            (
                comparison_spreads["near_expiry"]
                == near_expiry
            )
            &
            (
                comparison_spreads["far_expiry"]
                == far_expiry
            )
        ].sort_values(
            "trade_date"
        ).reset_index(drop=True)

        # Calculate spread intelligence
        pair_intelligence = (
            calculate_spread_intelligence(
                pair_data
            )
        )

        # Run backtest with costs
        pair_backtest = (
            run_calendar_spread_backtest(
                pair_intelligence,
                entry_zscore=(
                    comparison_entry_zscore
                ),
                exit_zscore=(
                    comparison_exit_zscore
                ),
                transaction_cost_per_leg=(
                    comparison_transaction_cost
                ),
                slippage_per_leg=(
                    comparison_slippage
                ),
            )
        )

        # Identify completed trades
        completed_trade_ids = (
            pair_backtest[
                pair_backtest["action"].str.contains(
                    "Exit",
                    case=False,
                    na=False
                )
            ]["trade_id"]
            .dropna()
            .unique()
        )

        trade_data = pair_backtest.dropna(
            subset=["trade_id"]
        ).copy()

        trade_pnl = (
            trade_data.groupby(
                "trade_id"
            )["daily_pnl"].sum()
        )

        completed_trades = trade_pnl[
            trade_pnl.index.isin(
                completed_trade_ids
            )
        ]

        total_trades = len(completed_trades)

        winning_trades = (
            completed_trades > 0
        ).sum()

        # Calculate profit factor
        gross_profit = completed_trades[
            completed_trades > 0
        ].sum()

        gross_loss = abs(
            completed_trades[
                completed_trades < 0
            ].sum()
        )

        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else None
        )

        # Calculate holding period
        holding_periods = []

        for trade_id in completed_trade_ids:

            trade_rows = pair_backtest[
                pair_backtest["trade_id"]
                == trade_id
            ]

            entry_rows = trade_rows[
                trade_rows["action"].str.contains(
                    "Enter",
                    case=False,
                    na=False
                )
            ]

            exit_rows = trade_rows[
                trade_rows["action"].str.contains(
                    "Exit",
                    case=False,
                    na=False
                )
            ]

            if (
                not entry_rows.empty
                and not exit_rows.empty
            ):

                entry_date = pd.to_datetime(
                    entry_rows.iloc[0]["trade_date"]
                )

                exit_date = pd.to_datetime(
                    exit_rows.iloc[-1]["trade_date"]
                )

                holding_days = (
                    exit_date - entry_date
                ).days

                holding_periods.append(
                    holding_days
                )

        average_holding_days = (
            sum(holding_periods)
            / len(holding_periods)
            if holding_periods
            else None
        )

        # Calculate remaining metrics
        win_rate = (
            winning_trades / total_trades * 100
            if total_trades > 0
            else 0.0
        )

        net_pnl = pair_backtest[
            "daily_pnl"
        ].sum()

        # Reliability label
        reliability = (
            "Insufficient Data"
            if len(pair_data) < 30
            else (
                "No Completed Trades"
                if total_trades == 0
                else "Evaluated"
            )
        )

        # IMPORTANT: Append each expiry pair
        comparison_results.append({
            "Near Expiry": near_expiry,
            "Far Expiry": far_expiry,
            "Observations": len(pair_data),
            "Completed Trades": total_trades,
            "Winning Trades": winning_trades,
            "Win Rate (%)": win_rate,
            "Net P&L (₹)": net_pnl,
            "Profit Factor": profit_factor,
            "Average Holding Days": average_holding_days,
            "Reliability": reliability,
        })

    # Create comparison DataFrame
    comparison_df = pd.DataFrame(
        comparison_results
    )

    # Convert metric columns to numeric
    comparison_df["Profit Factor"] = pd.to_numeric(
        comparison_df["Profit Factor"],
        errors="coerce"
    )

    comparison_df["Average Holding Days"] = pd.to_numeric(
        comparison_df["Average Holding Days"],
        errors="coerce"
    )

    # Round metrics
    comparison_df["Profit Factor"] = (
        comparison_df["Profit Factor"].round(2)
    )

    comparison_df["Average Holding Days"] = (
        comparison_df["Average Holding Days"].round(1)
    )

    comparison_df["Win Rate (%)"] = (
        comparison_df["Win Rate (%)"].round(2)
    )

    comparison_df["Net P&L (₹)"] = (
        comparison_df["Net P&L (₹)"].round(2)
    )

    # Format expiry dates
    comparison_df["Near Expiry"] = (
        pd.to_datetime(
            comparison_df["Near Expiry"]
        ).dt.strftime("%d %b %Y")
    )

    comparison_df["Far Expiry"] = (
        pd.to_datetime(
            comparison_df["Far Expiry"]
        ).dt.strftime("%d %b %Y")
    )

    # Prepare display table
    display_df = comparison_df.copy()

    display_df["Profit Factor"] = (
        display_df["Profit Factor"].apply(
            lambda value: (
                "N/A" if pd.isna(value)
                else f"{value:.2f}"
            )
        )
    )

    display_df["Average Holding Days"] = (
        display_df["Average Holding Days"].apply(
            lambda value: (
                "N/A" if pd.isna(value)
                else f"{value:.1f} days"
            )
        )
    )

    # Display comparison table
    st.dataframe(
        display_df.sort_values(
            "Net P&L (₹)",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )

    # Comparison summary
    st.subheader("Comparison Summary")

    total_pairs = len(comparison_df)

    profitable_pairs = (
        comparison_df["Net P&L (₹)"] > 0
    ).sum()

    losing_pairs = (
        comparison_df["Net P&L (₹)"] < 0
    ).sum()

    no_trade_pairs = (
        comparison_df["Completed Trades"] == 0
    ).sum()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Expiry Pairs",
        total_pairs
    )

    c2.metric(
        "Profitable Pairs",
        profitable_pairs
    )

    c3.metric(
        "Losing Pairs",
        losing_pairs
    )

    c4.metric(
        "No Completed Trades",
        no_trade_pairs
    )

    # P&L comparison chart
    st.subheader("Net P&L by Expiry Pair")

    comparison_df["Expiry Pair"] = (
        comparison_df["Near Expiry"]
        + " → "
        + comparison_df["Far Expiry"]
    )

    fig_comparison = px.bar(
        comparison_df,
        x="Expiry Pair",
        y="Net P&L (₹)",
        title="Calendar Spread Expiry Pair Comparison",
        labels={
            "Expiry Pair": "Expiry Pair",
            "Net P&L (₹)": "Net P&L (₹)"
        }
    )

    fig_comparison.add_hline(
        y=0,
        line_dash="dash"
    )

    fig_comparison.update_layout(
        xaxis_tickangle=-45
    )

    st.plotly_chart(
        fig_comparison,
        use_container_width=True
    )

    st.caption(
        "Research comparison only. Expiry pairs may "
        "have overlapping trading dates, so their "
        "combined P&L is not portfolio performance."
    )



# ------------------------------------------
# Exit Z-Score Strategy Comparison
# ------------------------------------------

st.subheader("Exit Z-Score Strategy Comparison")

st.caption(
    "Compare different exit thresholds while keeping "
    "the entry threshold, strategy, and costs fixed."
)

# Fixed comparison settings
zscore_entry_value = 2.0

zscore_exit_values = [
    0.0,
    0.5,
    1.0,
    1.5,
]

zscore_transaction_cost = 5.0
zscore_slippage = 2.0

# Generate calendar spreads for selected instrument
zscore_spreads = calculate_calendar_spreads(
    df,
    symbol=selected_bt_symbol
)

if zscore_spreads.empty:

    st.warning(
        "No calendar spread data is available "
        "for Z-score comparison."
    )

else:

    zscore_results = []

    # Test every available expiry pair
    zscore_expiry_pairs = (
        zscore_spreads[
            ["near_expiry", "far_expiry"]
        ]
        .drop_duplicates()
        .sort_values(
            ["near_expiry", "far_expiry"]
        )
    )

    for _, pair in zscore_expiry_pairs.iterrows():

        near_expiry = pair["near_expiry"]
        far_expiry = pair["far_expiry"]

        pair_data = zscore_spreads[
            (
                zscore_spreads["near_expiry"]
                == near_expiry
            )
            &
            (
                zscore_spreads["far_expiry"]
                == far_expiry
            )
        ].sort_values(
            "trade_date"
        ).reset_index(drop=True)

        # Calculate spread intelligence once per pair
        pair_intelligence = (
            calculate_spread_intelligence(
                pair_data
            )
        )

        # Test each exit threshold
        for exit_threshold in zscore_exit_values:

            pair_backtest = (
                run_calendar_spread_backtest(
                    pair_intelligence,
                    entry_zscore=zscore_entry_value,
                    exit_zscore=exit_threshold,
                    transaction_cost_per_leg=(
                        zscore_transaction_cost
                    ),
                    slippage_per_leg=(
                        zscore_slippage
                    ),
                )
            )

            # Identify completed trades
            completed_trade_ids = (
                pair_backtest[
                    pair_backtest["action"].str.contains(
                        "Exit",
                        case=False,
                        na=False
                    )
                ]["trade_id"]
                .dropna()
                .unique()
            )

            trade_data = pair_backtest.dropna(
                subset=["trade_id"]
            ).copy()

            trade_pnl = (
                trade_data.groupby(
                    "trade_id"
                )["daily_pnl"].sum()
            )

            completed_trades = trade_pnl[
                trade_pnl.index.isin(
                    completed_trade_ids
                )
            ]

            total_trades = len(completed_trades)

            winning_trades = (
                completed_trades > 0
            ).sum()

            losing_trades = (
                completed_trades < 0
            ).sum()

            win_rate = (
                winning_trades / total_trades * 100
                if total_trades > 0
                else 0.0
            )

            # Total net P&L
            net_pnl = pair_backtest[
                "daily_pnl"
            ].sum()

            # Append one result per expiry pair
            # and exit threshold
            zscore_results.append({
                "Entry Z-Score": zscore_entry_value,
                "Exit Z-Score": exit_threshold,
                "Near Expiry": near_expiry,
                "Far Expiry": far_expiry,
                "Completed Trades": total_trades,
                "Winning Trades": winning_trades,
                "Losing Trades": losing_trades,
                "Win Rate (%)": win_rate,
                "Net P&L (₹)": net_pnl,
            })

    # Convert results to DataFrame
    zscore_comparison_df = pd.DataFrame(
        zscore_results
    )

    # Aggregate results by exit threshold
    zscore_summary = (
        zscore_comparison_df
        .groupby("Exit Z-Score")
        .agg(
            Expiry_Pairs=("Near Expiry", "count"),
            Completed_Trades=("Completed Trades", "sum"),
            Winning_Trades=("Winning Trades", "sum"),
            Losing_Trades=("Losing Trades", "sum"),
            Net_PnL=("Net P&L (₹)", "sum"),
        )
        .reset_index()
    )

    # Calculate overall win rate per threshold
    zscore_summary["Win Rate (%)"] = (
        zscore_summary["Winning_Trades"]
        / zscore_summary["Completed_Trades"].replace(
            0, float("nan")
        )
        * 100
    )

    # Display N/A as 0 when there are no completed trades
    zscore_summary["Win Rate (%)"] = (
        zscore_summary["Win Rate (%)"].fillna(0)
    )

    # Round display values
    zscore_summary["Net_PnL"] = (
        zscore_summary["Net_PnL"].round(2)
    )

    zscore_summary["Win Rate (%)"] = (
        zscore_summary["Win Rate (%)"].round(2)
    )

    # Display summary table
    st.dataframe(
        zscore_summary,
        use_container_width=True,
        hide_index=True
    )

    # Plot net P&L by exit threshold
    fig_zscore = px.bar(
        zscore_summary,
        x="Exit Z-Score",
        y="Net_PnL",
        title="Net P&L by Exit Z-Score",
        labels={
            "Exit Z-Score": "Exit Z-Score",
            "Net_PnL": "Net P&L (₹)",
        },
    )

    fig_zscore.add_hline(
        y=0,
        line_dash="dash"
    )

    st.plotly_chart(
        fig_zscore,
        use_container_width=True
    )

    st.caption(
        "Research comparison only. Expiry pairs may "
        "have overlapping trading dates, so their "
        "combined P&L is not portfolio performance."
    )
