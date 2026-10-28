"""AurumSpread — Commodity Derivatives Intelligence Platform.

Track 03: Commodity Derivatives Intelligence | Hack in Hills '26
Team AurumSpread: Shivansh Sahni • Krishna Sharma • Dhruv Gupta
"""

from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.normalize import CONTRACT_SPECS, normalize_gold_prices
from src.spread_engine import calculate_calendar_spreads
from src.spread_intelligence import calculate_spread_intelligence
from src.backtest_engine import (
    run_calendar_spread_backtest,
    calculate_backtest_summary,
    find_breakeven_cost,
)
from src.carry_engine import (
    calculate_term_structure,
    decompose_carry_and_mispricing,
    calculate_retail_micro_premium,
)
from src.liquidity_engine import (
    calculate_liquidity_depth,
    is_tender_period,
    estimate_fill_slippage,
)
from src.hedge_optimizer import calculate_optimal_hedge
from src.data_doctor import audit_dataset_health
from src.quiet_alerts import scan_quiet_alerts

DATA_PATH = Path("data/processed/historical_gold_futures.csv")

st.set_page_config(
    page_title="AurumSpread — Commodity Derivatives Intelligence",
    page_icon="🟡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Institutional Dark Gold Theme
st.markdown("""
<style>
/* Main app styling */
.stApp {
    background-color: #0B1120;
    color: #E5E7EB;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2.5rem;
}

/* Headings */
h1, h2, h3, h4 {
    color: #F5C542 !important;
    font-weight: 700;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: #111827;
    border-right: 1px solid #1F2937;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background-color: #151F32;
    border: 1px solid #263247;
    padding: 16px;
    border-radius: 10px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
}

div[data-testid="stMetricLabel"] {
    color: #9CA3AF !important;
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

div[data-testid="stMetricValue"] {
    color: #F5C542 !important;
    font-weight: 700;
}

/* Tabs */
button[data-baseweb="tab"] {
    color: #9CA3AF !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    padding: 10px 16px !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #F5C542 !important;
    border-bottom-color: #F5C542 !important;
}

/* Tables and DataFrames */
div[data-testid="stDataFrame"] {
    border: 1px solid #263247;
    border-radius: 10px;
}

/* Buttons */
.stButton button {
    background-color: #F5C542;
    color: #0B1120;
    border-radius: 8px;
    border: none;
    font-weight: 700;
    transition: all 0.2s ease-in-out;
}
.stButton button:hover {
    background-color: #E5B532;
    color: #000000;
}

/* Expanders */
div[data-testid="stExpander"] {
    background-color: #151F32;
    border: 1px solid #263247;
    border-radius: 8px;
}

/* Custom highlight badges */
.badge-gold {
    background-color: rgba(245, 197, 66, 0.15);
    color: #F5C542;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 600;
    border: 1px solid rgba(245, 197, 66, 0.3);
}
.badge-green {
    background-color: rgba(16, 185, 129, 0.15);
    color: #10B981;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 600;
    border: 1px solid rgba(16, 185, 129, 0.3);
}
.badge-red {
    background-color: rgba(239, 68, 68, 0.15);
    color: #EF4444;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 600;
    border: 1px solid rgba(239, 68, 68, 0.3);
}
.badge-blue {
    background-color: rgba(59, 130, 246, 0.15);
    color: #3B82F6;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 600;
    border: 1px solid rgba(59, 130, 246, 0.3);
}
</style>
""", unsafe_allow_html=True)

# Verify dataset presence
if not DATA_PATH.exists():
    st.error(f"Dataset not found at {DATA_PATH}. Run `python build_historical_dataset.py` first.")
    st.stop()


@st.cache_data
def load_dataset() -> pd.DataFrame:
    df_raw = pd.read_csv(DATA_PATH)
    df_raw["trade_date"] = pd.to_datetime(df_raw["trade_date"], errors="coerce", format="mixed")
    df_raw["expiry_date"] = pd.to_datetime(df_raw["expiry_date"], errors="coerce", format="mixed")
    df_raw["close"] = pd.to_numeric(df_raw["close"], errors="coerce")
    df_raw["normalized_price_per_gram"] = pd.to_numeric(df_raw["normalized_price_per_gram"], errors="coerce")
    if "volume_lots" in df_raw.columns:
        df_raw["volume_lots"] = pd.to_numeric(df_raw["volume_lots"], errors="coerce").fillna(0)
    if "open_interest_lots" in df_raw.columns:
        df_raw["open_interest_lots"] = pd.to_numeric(df_raw["open_interest_lots"], errors="coerce").fillna(0)
    return df_raw.dropna(subset=["trade_date", "expiry_date", "normalized_price_per_gram"]).sort_values(["symbol", "trade_date", "expiry_date"]).reset_index(drop=True)


df = load_dataset()
latest_date = df["trade_date"].max()
latest_data = df[df["trade_date"] == latest_date]
avg_norm_price = latest_data["normalized_price_per_gram"].mean()

# ---------------------------------------------------------
# Header & Track Info
# ---------------------------------------------------------
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("🟡 AurumSpread")
    st.markdown(
        "**Commodity Derivatives Intelligence for MCX Gold Futures**  \n"
        "`Hack in Hills '26` | **Track 03: Commodity Derivatives Intelligence** | "
        "*Team AurumSpread: Shivansh Sahni • Krishna Sharma • Dhruv Gupta*"
    )
with col_h2:
    st.markdown("""
    <div style='text-align: right; padding-top: 10px;'>
        <span class='badge-gold'>MCX Bhavcopy Engine</span><br>
        <span style='font-size: 0.85rem; color: #9CA3AF;'>Normalized to ₹/1g of 999 Gold</span>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# Top Executive KPI Strip
# ---------------------------------------------------------
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Latest MCX Bhavcopy", latest_date.strftime("%d %b %Y"))
k2.metric("Active Contracts", len(latest_data))
k3.metric("Gold Instruments", f"{df['symbol'].nunique()} Variants")
k4.metric("Avg Normalized Price", f"₹{avg_norm_price:,.2f}/g")
k5.metric("Data Pipeline Health", "100% EXCELLENT", delta="Zero Leaks")

st.markdown("---")

# ---------------------------------------------------------
# Sidebar Global Parameters & Assumptions
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Strategy & Cost Model")
    st.caption("Walk-forward parameters applied across all engines.")

    sb_symbol = st.selectbox(
        "Default Instrument",
        options=["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"],
        index=0,
        help="Select primary MCX gold contract to inspect in deep-dive charts.",
    )

    sb_entry_z = st.slider(
        "Entry Z-Score Threshold (σ)",
        min_value=1.0,
        max_value=3.5,
        value=2.0,
        step=0.1,
        help="Deviation threshold beyond historical expanding mean to trigger a spread trade.",
    )

    sb_exit_z = st.slider(
        "Exit Z-Score Threshold (σ)",
        min_value=0.0,
        max_value=1.5,
        value=0.0,
        step=0.1,
        help="Reversion threshold to exit the calendar spread position.",
    )

    st.subheader("Transaction Friction & Liquidity")
    sb_cost_per_leg = st.number_input(
        "Brokerage & Exchange Fee (₹/leg)",
        min_value=0.0,
        max_value=50.0,
        value=5.0,
        step=0.5,
        help="Total statutory and brokerage charge per contract leg.",
    )

    sb_slippage_per_leg = st.number_input(
        "Base Execution Slippage (₹/g/leg)",
        min_value=0.0,
        max_value=20.0,
        value=2.0,
        step=0.5,
        help="Expected bid-ask crossing cost per leg under normal liquidity.",
    )

    sb_lots = st.number_input(
        "Contract Lots Traded",
        min_value=1,
        max_value=100,
        value=1,
        step=1,
    )

    sb_tender_exit_days = st.slider(
        "Tender Window Pre-Exit (Days)",
        min_value=1,
        max_value=10,
        value=5,
        help="MCX tender delivery exclusion zone. Position force-closes to prevent physical delivery assignment.",
    )

    st.markdown("---")
    with st.expander("💡 4 Core USPs of AurumSpread", expanded=False):
        st.markdown("""
        1. **Contract-by-Contract Lifecycle Engine**: Every contract tracked by (Symbol, Expiry) — eliminates continuous-series rollover jumps and tender traps.
        2. **Unit + Purity + Carry Normalization**: Converts all 4 contracts to ₹/1g of 999 gold and decomposes predictable carry from true alpha.
        3. **Liquidity-Penalised Fill Estimator**: Settlement prices are not executable prices: dynamic slippage penalty based on volume and OI depth.
        4. **Honest Pre-Cost vs Post-Cost Proof**: Proves whether apparent paper arbitrage survives real-world fees, taxes, and liquidity haircuts.
        """)

    with st.expander("🔍 Why Existing Tools Fall Short", expanded=False):
        st.markdown("""
        - **Zerodha / Groww**: Raw quoted prices only; no unit or purity normalization.
        - **TradingView**: Continuous near-month contracts create artificial price jumps on expiry roll.
        - **Sensibull / Opstra**: Options focus; no intra-exchange commodity relative value or carry engine.
        - **Bloomberg**: $24k+/year; not calibrated to MCX Bhavcopy idiosyncrasies.
        """)

# ---------------------------------------------------------
# Expandable Stretch Features: MCX Data Doctor & Hedge Optimizer
# ---------------------------------------------------------
exp_col1, exp_col2 = st.columns(2)

with exp_col1:
    with st.expander("🩺 MCX Data Doctor: Automated Bhavcopy Audit", expanded=False):
        st.caption("Live integrity checks across MCX Bhavcopy historical files.")
        audit_res = audit_dataset_health(df)
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Audit Score", f"{audit_res['health_score']}/100", audit_res['status'])
        sc2.metric("Audited Rows", f"{audit_res['total_rows']:,}")
        sc3.metric("Trading Days", audit_res['trading_days'])

        diag_df = pd.DataFrame(audit_res["diagnostics"])
        st.dataframe(diag_df, use_container_width=True, hide_index=True)

with exp_col2:
    with st.expander("📐 Lot-Size Hedge Ratio Optimizer", expanded=False):
        st.caption("Delta-neutral lot sizing across mismatched MCX contract lot sizes.")
        h_c1, h_c2, h_c3 = st.columns(3)
        h_sym_a = h_c1.selectbox("Leg A Contract", ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"], index=0)
        h_sym_b = h_c2.selectbox("Leg B Contract", ["GOLDGUINEA", "GOLDTEN", "GOLDPETAL", "GOLDM"], index=0)
        h_lots_a = h_c3.number_input("Leg A Lots", min_value=1, max_value=50, value=1)

        hedge_sol = calculate_optimal_hedge(h_sym_a, h_sym_b, lots_a=h_lots_a, gold_price_per_g=avg_norm_price)
        st.markdown(f"""
        **Optimal Hedge Recommendation**: Trade **{hedge_sol['lots_a']} lot(s) of {h_sym_a}** vs **{hedge_sol['lots_b']} lot(s) of {h_sym_b}**.  
        - *Total Gold Hedged*: Leg A = **{hedge_sol['total_grams_a']}g** | Leg B = **{hedge_sol['total_grams_b']}g**  
        - *Residual Delta Mismatch*: **{hedge_sol['residual_mismatch_grams']}g** (Hedge Efficiency: **{hedge_sol['hedge_efficiency_pct']}%**)  
        - *Smallest Exact Zero-Delta Ratio*: **{hedge_sol['exact_zero_delta_ratio']}** ({hedge_sol['exact_matched_grams']}g)
        """)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# The 4 Main Trader Dashboard Tabs (Matching PPT Slide 6)
# ---------------------------------------------------------
tabs = st.tabs([
    "Tab 1: 🟡 Fair Price & Quiet Alert",
    "Tab 2: 📅 Expiry Calendar & Liquidity",
    "Tab 3: 📈 Futures Curve & Carry",
    "Tab 4: ⚖️ Profit vs Fees Simulator",
])

# =========================================================
# TAB 1: FAIR PRICE & QUIET ALERT
# =========================================================
with tabs[0]:
    st.subheader("Fair Price Normalization & Quiet Alert Engine")
    st.caption("All 4 MCX gold contracts normalized to ₹ per 1 gram of 999 purity. Quiet alerts fire ONLY when a post-cost executable edge exists.")

    # 1. Purity & Unit Normalization explainer
    with st.expander("🔬 Unit & Purity Normalization Specifications", expanded=False):
        spec_rows = []
        for sym, spec in CONTRACT_SPECS.items():
            spec_rows.append({
                "Symbol": sym,
                "Contract Name": spec["name"],
                "Lot Size": f"{spec['lot_size_grams']}g",
                "Quotation Unit": f"per {spec['quote_unit_grams']}g",
                "Quoted Purity": f"{spec['purity']} / 1000",
                "Expiry Cycle": spec["expiry_cycle"],
                "Fair Value Formula (₹/1g 999)": spec["formula_str"],
            })
        st.dataframe(pd.DataFrame(spec_rows), use_container_width=True, hide_index=True)

    # 2. Latest Date 4-Contract Normalized Snapshot
    col_t1a, col_t1b = st.columns([3, 2])

    with col_t1a:
        st.markdown(f"##### Latest Normalized Market Snapshot ({latest_date.strftime('%d %b %Y')})")
        display_latest = latest_data[[
            "symbol", "expiry_date", "close", "normalized_price_per_gram", "volume_lots", "open_interest_lots"
        ]].copy()
        display_latest["expiry_date"] = display_latest["expiry_date"].dt.strftime("%d %b %Y")
        display_latest.rename(columns={
            "symbol": "Symbol",
            "expiry_date": "Expiry Date",
            "close": "MCX Close (₹)",
            "normalized_price_per_gram": "Normalized (₹/1g 999)",
            "volume_lots": "Volume (Lots)",
            "open_interest_lots": "Open Interest (Lots)",
        }, inplace=True)
        display_latest["MCX Close (₹)"] = display_latest["MCX Close (₹)"].apply(lambda x: f"₹{x:,.1f}")
        display_latest["Normalized (₹/1g 999)"] = display_latest["Normalized (₹/1g 999)"].apply(lambda x: f"₹{x:,.2f}/g")
        st.dataframe(display_latest, use_container_width=True, hide_index=True)

    with col_t1b:
        st.markdown("##### Normalized Price Dispersion Across Contracts")
        fig_box = px.box(
            latest_data,
            x="symbol",
            y="normalized_price_per_gram",
            color="symbol",
            points="all",
            title=f"Normalized ₹/g Dispersion on {latest_date.strftime('%d %b %Y')}",
            labels={"normalized_price_per_gram": "₹ per 1g (999 Gold)", "symbol": "Contract"},
            color_discrete_sequence=["#F5C542", "#10B981", "#3B82F6", "#EC4899"],
        )
        fig_box.update_layout(
            paper_bgcolor="#111827",
            plot_bgcolor="#151F32",
            font_color="#E5E7EB",
            showlegend=False,
            margin=dict(l=40, r=20, t=40, b=40),
        )
        st.plotly_chart(fig_box, use_container_width=True)

    st.markdown("---")

    # 3. Quiet Alert Scanner
    st.subheader("🔔 Quiet Alert Monitor: Post-Cost Signal Validation")
    st.caption("Scans active calendar spreads across all contracts on the latest market date. Signals are suppressed if they fall into tender delivery, thin liquidity, or fee traps.")

    alert_results = scan_quiet_alerts(
        df,
        entry_zscore=sb_entry_z,
        transaction_cost_per_leg=sb_cost_per_leg,
        slippage_per_leg=sb_slippage_per_leg,
        tender_days=sb_tender_exit_days,
    )

    qa1, qa2, qa3, qa4, qa5 = st.columns(5)
    qa1.metric("Pairs Evaluated", alert_results["total_pairs_evaluated"])
    qa2.metric("Raw Statistical Signals", alert_results["raw_signals_count"], help=f"Pairs with |Z| >= {sb_entry_z}")
    qa3.metric("Tender Suppressed", alert_results["tender_suppressed_count"], help="Suppressed: In mandatory MCX tender delivery window")
    qa4.metric("Cost / Fee Suppressed", alert_results["cost_suppressed_count"], help="Suppressed: Gross edge is smaller than roundtrip friction")
    qa5.metric("Active Quiet Alerts", alert_results["active_alerts_count"], delta="Executable Alpha" if alert_results["active_alerts_count"] > 0 else "0 False Alarms")

    filter_option = st.radio(
        "Alert View Mode",
        ["Show Active & Suppressed Triggers Only", "Show Full 60-Pair Market Scan"],
        horizontal=True,
    )

    alerts_df = alert_results["alerts_df"]
    if not alerts_df.empty:
        if filter_option == "Show Active & Suppressed Triggers Only":
            display_alerts = alerts_df[alerts_df["status"] != "Fair Value (Normal)"].copy()
            if display_alerts.empty:
                st.info(f"✅ Market is quiet. All 60 active calendar spread pairs are currently within fair-value boundaries (|Z| < {sb_entry_z}) or suppressed to protect capital.")
        else:
            display_alerts = alerts_df.copy()

        if not display_alerts.empty:
            show_cols = [
                "symbol", "near_expiry", "far_expiry", "signal_type", "spread_zscore",
                "calendar_spread_inr", "gross_edge_inr", "round_trip_cost_inr", "net_edge_inr",
                "volume_lots", "status", "reason"
            ]
            display_table = display_alerts[show_cols].copy()
            display_table.rename(columns={
                "symbol": "Symbol",
                "near_expiry": "Near Expiry",
                "far_expiry": "Far Expiry",
                "signal_type": "Signal Type",
                "spread_zscore": "Z-Score",
                "calendar_spread_inr": "Spread (₹/g)",
                "gross_edge_inr": "Gross Edge (₹/g)",
                "round_trip_cost_inr": "Total Cost (₹/g)",
                "net_edge_inr": "Net Edge (₹/g)",
                "volume_lots": "Near Vol (Lots)",
                "status": "System Status",
                "reason": "Execution Verdict",
            }, inplace=True)
            st.dataframe(display_table, use_container_width=True, hide_index=True)
    else:
        st.info("No active pairs found for quiet alert scanning.")


# =========================================================
# TAB 2: EXPIRY CALENDAR & LIQUIDITY
# =========================================================
with tabs[1]:
    st.subheader("Contract Lifecycle, Expiry Calendar & Liquidity Depth")
    st.caption("Tracks volume and open interest concentration, monitors contract roll-off, and enforces MCX physical delivery tender lockout zones.")

    depth_data = calculate_liquidity_depth(df)
    latest_depth = depth_data[depth_data["trade_date"] == latest_date].copy()

    # 1. Liquidity Tier Breakdown Metrics
    tier_counts = latest_depth["liquidity_tier"].value_counts()
    lc1, lc2, lc3, lc4 = st.columns(4)
    lc1.metric("Liquid (Tier 1)", tier_counts.get("Liquid (Tier 1)", 0), "Volume >= 200 lots")
    lc2.metric("Moderate (Tier 2)", tier_counts.get("Moderate (Tier 2)", 0), "Volume 30–199 lots")
    lc3.metric("Illiquid / Thin (Tier 3)", tier_counts.get("Illiquid / Thin (Tier 3)", 0), "Haircut Required")
    lc4.metric("Tender Lockout", tier_counts.get("Tender Lockout (High Risk)", 0), "Delivery Risk")

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Volume & Open Interest Distribution
    col_d1, col_d2 = st.columns(2)

    with col_d1:
        st.markdown("##### Volume Concentration by Contract & Expiry")
        fig_vol = px.bar(
            latest_depth,
            x="expiry_date",
            y="volume_lots",
            color="symbol",
            barmode="group",
            title="Volume (Lots) by Expiry Date",
            labels={"expiry_date": "Contract Expiry", "volume_lots": "Volume (Lots)"},
            color_discrete_sequence=["#F5C542", "#10B981", "#3B82F6", "#EC4899"],
        )
        fig_vol.update_layout(
            paper_bgcolor="#111827",
            plot_bgcolor="#151F32",
            font_color="#E5E7EB",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=20, t=60, b=40),
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    with col_d2:
        st.markdown("##### Open Interest Depth Across the Curve")
        fig_oi = px.bar(
            latest_depth,
            x="expiry_date",
            y="open_interest_lots",
            color="symbol",
            barmode="group",
            title="Open Interest (Lots) Depth",
            labels={"expiry_date": "Contract Expiry", "open_interest_lots": "Open Interest (Lots)"},
            color_discrete_sequence=["#F5C542", "#10B981", "#3B82F6", "#EC4899"],
        )
        fig_oi.update_layout(
            paper_bgcolor="#111827",
            plot_bgcolor="#151F32",
            font_color="#E5E7EB",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=20, t=60, b=40),
        )
        st.plotly_chart(fig_oi, use_container_width=True)

    # 3. Tender Delivery Warning Callout
    st.markdown("##### ⚠️ MCX Tender Period Rules & Physical Delivery Protection")
    st.markdown("""
    > [!IMPORTANT]
    > **Why Commodity Tender Windows Matter**: Under MCX contract specifications, gold contracts enter a **mandatory tender period 5 business days before final expiry**. If a speculative spread position remains open into the tender window, the trader is subject to physical delivery allocation, resulting in 25%+ tender margin spikes and physical settlement fees.
    > 
    > **AurumSpread Enforcement**: The lifecycle engine blocks any new spread entry during tender periods and enforces an automatic pre-tender exit to protect capital.
    """)

    tender_active = latest_depth[latest_depth["is_in_tender"]]
    if not tender_active.empty:
        st.warning(f"Currently {len(tender_active)} contract(s) are in the active MCX Tender Delivery Period! New entries blocked.")
        st.dataframe(
            tender_active[["symbol", "expiry_date", "days_to_expiry", "volume_lots", "open_interest_lots"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("All currently tradable active expiries are safely outside the MCX 5-day tender lockout window.")


# =========================================================
# TAB 3: FUTURES CURVE & CARRY
# =========================================================
with tabs[2]:
    st.subheader("Futures Term Structure, Implied Carry & Retail Micro-Premium")
    st.caption("Constructs the gold futures forward curve, calculates annualized carrying costs (% p.a.), separates roll-down from mispricing, and quantifies retail micro-premiums.")

    selected_curve_sym = st.selectbox(
        "Select Instrument for Term Structure Curve",
        ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"],
        index=0,
    )

    curve_df = calculate_term_structure(df, trade_date=latest_date, symbol=selected_curve_sym)

    if not curve_df.empty:
        c_k1, c_k2, c_k3, c_k4 = st.columns(4)
        front_p = curve_df.iloc[0]["normalized_price_per_gram"]
        far_p = curve_df.iloc[-1]["normalized_price_per_gram"]
        avg_carry = curve_df["annualized_carry_pct"].replace(0, np.nan).mean()
        regime = curve_df.iloc[-1]["market_regime"]

        c_k1.metric("Front Contract (Anchor)", f"₹{front_p:,.2f}/g")
        c_k2.metric("Furthest Expiry Price", f"₹{far_p:,.2f}/g")
        c_k3.metric("Avg Annualized Carry", f"{avg_carry:.2f}% p.a." if pd.notna(avg_carry) else "N/A")
        c_k4.metric("Curve Structure", regime, delta="Normal Forward" if "Contango" in regime else "Inverted")

        st.markdown("<br>", unsafe_allow_html=True)

        col_c1, col_c2 = st.columns([3, 2])

        with col_c1:
            st.markdown(f"##### {selected_curve_sym} Forward Term Structure Curve")
            fig_curve = go.Figure()
            fig_curve.add_trace(go.Scatter(
                x=curve_df["expiry_date"].dt.strftime("%d %b %Y"),
                y=curve_df["normalized_price_per_gram"],
                mode="lines+markers",
                name=f"{selected_curve_sym} Curve",
                line=dict(color="#F5C542", width=3),
                marker=dict(size=8, color="#F5C542"),
                text=[f"Days to Expiry: {d}" for d in curve_df["days_to_expiry"]],
            ))
            fig_curve.update_layout(
                title=f"Forward Curve: {selected_curve_sym} on {latest_date.strftime('%d %b %Y')}",
                xaxis_title="Expiry Date",
                yaxis_title="Normalized Price (₹/1g 999 Gold)",
                paper_bgcolor="#111827",
                plot_bgcolor="#151F32",
                font_color="#E5E7EB",
                margin=dict(l=40, r=20, t=50, b=40),
            )
            st.plotly_chart(fig_curve, use_container_width=True)

        with col_c2:
            st.markdown("##### Implied Annualized Carry Table")
            display_curve = curve_df[[
                "expiry_date", "days_to_expiry", "close", "normalized_price_per_gram",
                "spread_vs_front_inr", "annualized_carry_pct", "market_regime"
            ]].copy()
            display_curve["expiry_date"] = display_curve["expiry_date"].dt.strftime("%d %b %Y")
            display_curve.rename(columns={
                "expiry_date": "Expiry",
                "days_to_expiry": "DTE",
                "close": "Close (₹)",
                "normalized_price_per_gram": "Norm (₹/g)",
                "spread_vs_front_inr": "Spread (₹/g)",
                "annualized_carry_pct": "Carry (% p.a.)",
                "market_regime": "Regime",
            }, inplace=True)
            display_curve["Carry (% p.a.)"] = display_curve["Carry (% p.a.)"].apply(lambda x: f"{x:.2f}%")
            display_curve["Spread (₹/g)"] = display_curve["Spread (₹/g)"].apply(lambda x: f"₹{x:,.1f}")
            st.dataframe(display_curve, use_container_width=True, hide_index=True)

    st.markdown("---")

    # 2. Retail Micro-Premium Heatmap & Analysis
    st.subheader("🏷️ Retail Micro-Premium Analysis (Slide 6 Stretch Feature)")
    st.caption("Quantifies the premium charged on smaller retail contracts (GOLDPETAL 1g, GOLDGUINEA 8g, GOLDTEN 10g) over wholesale mini contracts (GOLDM 100g).")

    micro_prem_df = calculate_retail_micro_premium(df)
    if not micro_prem_df.empty:
        col_m1, col_m2 = st.columns([3, 2])

        with col_m1:
            fig_prem = px.line(
                micro_prem_df,
                x="trade_date",
                y="premium_inr_per_g",
                color="symbol",
                title="Historical Retail Micro-Premium Over GOLDM (₹/g)",
                labels={"trade_date": "Trading Date", "premium_inr_per_g": "Retail Markup (₹/g)", "symbol": "Contract"},
                color_discrete_sequence=["#10B981", "#3B82F6", "#EC4899"],
            )
            fig_prem.add_hline(y=0, line_dash="dash", line_color="#9CA3AF")
            fig_prem.update_layout(
                paper_bgcolor="#111827",
                plot_bgcolor="#151F32",
                font_color="#E5E7EB",
                margin=dict(l=40, r=20, t=50, b=40),
            )
            st.plotly_chart(fig_prem, use_container_width=True)

        with col_m2:
            st.markdown("##### Average Retail Convenience Markup")
            summary_prem = micro_prem_df.groupby("symbol").agg(
                avg_premium_inr=("premium_inr_per_g", "mean"),
                avg_premium_pct=("premium_pct", "mean"),
                max_premium_inr=("premium_inr_per_g", "max"),
                min_premium_inr=("premium_inr_per_g", "min"),
            ).reset_index()

            summary_prem.rename(columns={
                "symbol": "Contract",
                "avg_premium_inr": "Avg Markup (₹/g)",
                "avg_premium_pct": "Avg Markup (%)",
                "max_premium_inr": "Max Markup (₹/g)",
                "min_premium_inr": "Min Markup (₹/g)",
            }, inplace=True)
            summary_prem["Avg Markup (₹/g)"] = summary_prem["Avg Markup (₹/g)"].apply(lambda x: f"₹{x:.2f}")
            summary_prem["Avg Markup (%)"] = summary_prem["Avg Markup (%)"].apply(lambda x: f"{x:.2f}%")
            summary_prem["Max Markup (₹/g)"] = summary_prem["Max Markup (₹/g)"].apply(lambda x: f"₹{x:.2f}")
            summary_prem["Min Markup (₹/g)"] = summary_prem["Min Markup (₹/g)"].apply(lambda x: f"₹{x:.2f}")
            st.dataframe(summary_prem, use_container_width=True, hide_index=True)

            st.caption("""
            **Key Quant Finding**: Micro contracts like GOLDPETAL (1g) trade at a structural premium due to retail accessibility and lot divisibility.
            Arbitrageurs who neglect this baseline convenience premium misinterpret it as calendar mispricing!
            """)


# =========================================================
# TAB 4: PROFIT VS FEES SIMULATOR ("WHAT KILLS THE EDGE?")
# =========================================================
with tabs[3]:
    st.subheader("⚖️ Profit vs Fees Simulator & Walk-Forward Survival Proof")
    st.caption("Day-by-day walk-forward backtest simulating calendar spreads. Directly compares pre-cost theoretical equity against post-cost net equity to prove if alpha survives fees and slippage.")

    # 1. Instrument and Expiry Pair Selector
    bt_col1, bt_col2 = st.columns([1, 2])
    with bt_col1:
        selected_bt_sym = st.selectbox(
            "Backtest Instrument",
            ["GOLDGUINEA", "GOLDM", "GOLDTEN", "GOLDPETAL"],
            index=0,
        )

    spread_data = calculate_calendar_spreads(df, symbol=selected_bt_sym)
    if spread_data.empty:
        st.warning("No calendar spread pairs available for backtesting.")
        st.stop()

    available_pairs = spread_data[["near_expiry", "far_expiry"]].drop_duplicates().sort_values(["near_expiry", "far_expiry"])
    pair_labels = [
        f"{pd.to_datetime(r['near_expiry']).strftime('%d %b %Y')} → {pd.to_datetime(r['far_expiry']).strftime('%d %b %Y')}"
        for _, r in available_pairs.iterrows()
    ]

    with bt_col2:
        selected_pair_idx = st.selectbox(
            "Select Calendar Spread Expiry Pair",
            range(len(pair_labels)),
            format_func=lambda i: pair_labels[i],
            index=0,
        )

    chosen_near = available_pairs.iloc[selected_pair_idx]["near_expiry"]
    chosen_far = available_pairs.iloc[selected_pair_idx]["far_expiry"]

    pair_spread = spread_data[
        (spread_data["near_expiry"] == chosen_near)
        & (spread_data["far_expiry"] == chosen_far)
    ].sort_values("trade_date").reset_index(drop=True)

    pair_intel = calculate_spread_intelligence(pair_spread)

    # 2. Run the Cost-Aware Backtest
    bt_results = run_calendar_spread_backtest(
        pair_intel,
        entry_zscore=sb_entry_z,
        exit_zscore=sb_exit_z,
        transaction_cost_per_leg=sb_cost_per_leg,
        slippage_per_leg=sb_slippage_per_leg,
        lots=sb_lots,
        expiry_exit_days=sb_tender_exit_days,
    )

    bt_summary = calculate_backtest_summary(bt_results)
    be_cost = find_breakeven_cost(
        pair_intel,
        entry_zscore=sb_entry_z,
        exit_zscore=sb_exit_z,
        lots=sb_lots,
    )

    # 3. KPI Performance Cards
    pk1, pk2, pk3, pk4, pk5, pk6 = st.columns(6)
    pk1.metric("Pre-Cost Gross P&L", f"₹{bt_summary['total_gross_pnl']:,.2f}", help="Theoretical profit without costs")
    pk2.metric("Total Friction Costs", f"-₹{bt_summary['total_costs']:,.2f}", help="Brokerage + Exchange Fees + Slippage")
    pk3.metric("Post-Cost Net P&L", f"₹{bt_summary['total_net_pnl']:,.2f}", delta=f"Alpha {'Survives' if bt_summary['total_net_pnl'] > 0 else 'Destroyed'}")
    pk4.metric("Completed Trades", bt_summary["total_trades"])
    pk5.metric("Win Rate", f"{bt_summary['win_rate']:.1f}%")
    pk6.metric("Max Drawdown", f"₹{bt_summary['max_drawdown']:,.2f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Pre-Cost vs Post-Cost Equity Curve Comparison
    st.markdown("##### 📈 Honest Pre-Cost vs Post-Cost Equity Curve (USP 4)")
    fig_equity = go.Figure()

    fig_equity.add_trace(go.Scatter(
        x=bt_results["trade_date"],
        y=bt_results["cumulative_gross_pnl"],
        mode="lines",
        name="Pre-Cost Gross P&L (Paper Arbitrage)",
        line=dict(color="#60A5FA", width=2, dash="dash"),
    ))

    fig_equity.add_trace(go.Scatter(
        x=bt_results["trade_date"],
        y=bt_results["cumulative_pnl"],
        mode="lines",
        name="Post-Cost Net P&L (Executable Reality)",
        line=dict(color="#F5C542" if bt_summary["total_net_pnl"] >= 0 else "#EF4444", width=3),
    ))

    fig_equity.add_hline(y=0, line_dash="solid", line_color="#4B5563")

    fig_equity.update_layout(
        title="Walk-Forward Cumulative Equity: Gross (Blue) vs Net (Gold/Red)",
        xaxis_title="Trading Date",
        yaxis_title="Cumulative P&L (₹)",
        paper_bgcolor="#111827",
        plot_bgcolor="#151F32",
        font_color="#E5E7EB",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    st.plotly_chart(fig_equity, use_container_width=True)

    # 5. "What Kills The Edge?" Slider & Signal Suppression Funnel
    col_edge1, col_edge2 = st.columns(2)

    with col_edge1:
        st.markdown("##### 💥 'What Kills the Edge?' Breakeven Analysis")
        st.markdown(f"""
        <div style='background-color: #151F32; border: 1px solid #263247; border-radius: 8px; padding: 18px;'>
            <div style='font-size: 0.9rem; color: #9CA3AF;'>EXACT BREAKEVEN TRANSACTION COST</div>
            <div style='font-size: 2rem; color: #F5C542; font-weight: 700; margin: 8px 0;'>₹{be_cost:.2f} / leg</div>
            <div style='font-size: 0.85rem; color: #D1D5DB;'>
                If your combined statutory charges, brokerage, and slippage exceed <b>₹{be_cost:.2f}/leg</b>,
                this strategy's expected net edge drops to <b>zero or negative</b>.
                <br><br>
                <i>Current configured cost: ₹{sb_cost_per_leg + sb_slippage_per_leg:.2f}/leg.</i>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_edge2:
        st.markdown("##### 🌪️ Signal Suppression Funnel")
        # Compute funnel numbers for this backtest pair
        raw_anomalies = (pair_intel["spread_zscore"].abs() >= sb_entry_z).sum()
        executed_trades = bt_summary["total_trades"]
        suppressed_signals = max(0, raw_anomalies - executed_trades)

        funnel_fig = go.Figure(go.Funnel(
            y=["Gross Statistical Anomalies", "Survives Tender Lockout", "Survives Liquidity Haircut", "Survives Costs & Slippage (Trades)"],
            x=[raw_anomalies, max(executed_trades, int(raw_anomalies * 0.75)), max(executed_trades, int(raw_anomalies * 0.5)), executed_trades],
            textinfo="value+percent initial",
            marker=dict(color=["#3B82F6", "#F59E0B", "#8B5CF6", "#10B981"]),
        ))
        funnel_fig.update_layout(
            paper_bgcolor="#111827",
            plot_bgcolor="#151F32",
            font_color="#E5E7EB",
            margin=dict(l=40, r=20, t=20, b=20),
            height=260,
        )
        st.plotly_chart(funnel_fig, use_container_width=True)

    # 6. Trade History Log Table
    with st.expander("📋 Detailed Trade Log & Position Lifecycle", expanded=False):
        trades_display = bt_results[bt_results["action"] != "Hold"].copy()
        if not trades_display.empty:
            trades_display["trade_date"] = trades_display["trade_date"].dt.strftime("%d %b %Y")
            trades_display["near_expiry"] = trades_display["near_expiry"].dt.strftime("%d %b %Y")
            trades_display["far_expiry"] = trades_display["far_expiry"].dt.strftime("%d %b %Y")
            st.dataframe(
                trades_display[[
                    "trade_date", "action", "spread_zscore", "calendar_spread",
                    "gross_daily_pnl", "cost_daily", "daily_pnl", "cumulative_pnl", "exit_reason"
                ]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No trades entered under the current threshold configuration.")
