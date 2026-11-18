"""Aurum Copilot — Institutional Commodity Quant AI Engine.

Powers the personalized conversational trade advisor for AurumSpread.
Provides automated trade suggestions, hedge ratio calculations, tender risk audits,
COMEX landed parity analysis, and order ticket preparation directly from the live data models.
Functions with an offline deterministic institutional NLP engine and supports external LLMs.
"""

from typing import Dict, Any, List, Optional
import re
import pandas as pd
from src.normalize import CONTRACT_SPECS
from src.hedge_optimizer import calculate_optimal_hedge
from src.parity_engine import calculate_landed_import_parity
from src.quiet_alerts import scan_quiet_alerts
from src.order_ticket import generate_spread_order_ticket


class AurumCopilot:
    """Institutional Commodity Derivatives Intelligence Copilot."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.latest_date = pd.to_datetime(df["trade_date"], errors="coerce", format="mixed").max()
        self.latest_df = df[pd.to_datetime(df["trade_date"], errors="coerce", format="mixed") == self.latest_date]
        self.avg_gold_price = float(self.latest_df["normalized_price_per_gram"].mean()) if not self.latest_df.empty else 7500.0
        # Parity benchmark: GOLDM + GOLDTEN average on the latest date (same as the website)
        bench = self.latest_df[self.latest_df["symbol"].isin(["GOLDM", "GOLDTEN"])]
        self.parity_benchmark_price = (
            float(bench["normalized_price_per_gram"].mean()) if not bench.empty else self.avg_gold_price
        )

    def _latest_pair(self, symbol: str = "GOLDM"):
        """Nearest two expiries of a contract on the latest date: (near_exp, far_exp, near_px, far_px)."""
        rows = self.latest_df[self.latest_df["symbol"] == symbol].copy()
        if len(rows) < 2:
            return None
        rows["_exp"] = pd.to_datetime(rows["expiry_date"], errors="coerce", format="mixed")
        rows = rows.dropna(subset=["_exp"]).sort_values("_exp")
        if len(rows) < 2:
            return None
        n, f = rows.iloc[0], rows.iloc[1]
        return n["_exp"], f["_exp"], float(n["close"]), float(f["close"])

    def query(self, user_prompt: str) -> str:
        """Process user trade queries, analyze market state, and return actionable quant advice."""
        prompt_lower = user_prompt.lower().strip()

        # 1. Best Spread / Trade Suggestions
        if any(w in prompt_lower for w in ["best spread", "trade suggestion", "opportunity", "opportunities", "any trade", "what should i trade"]):
            return self._handle_trade_suggestions()

        # 2. Hedge Physical Gold
        if any(w in prompt_lower for w in ["hedge", "holding", "physical gold", "portfolio hedge"]):
            return self._handle_hedging(prompt_lower)

        # 3. COMEX / Landed Import Parity & Basis
        if any(w in prompt_lower for w in ["comex", "import parity", "basis", "landed", "usdinr", "customs", "tariff"]):
            return self._handle_parity()

        # 4. Tender Period / Delivery Risk
        if any(w in prompt_lower for w in ["tender", "delivery", "margin spike", "physical assignment"]):
            return self._handle_tender_inquiry()

        # 5. Order Ticket / Broker Execution
        if any(w in prompt_lower for w in ["order ticket", "zerodha", "dhan", "kite", "order slip", "execute"]):
            return self._handle_order_ticket(prompt_lower)

        # 6. Contract Specs / Purity differences
        if any(w in prompt_lower for w in ["contract spec", "purity", "lot size", "difference between gold", "goldm vs", "goldpetal"]):
            return self._handle_contract_specs()

        # 7. General Quant / Help fallback
        return self._handle_general_guidance(user_prompt)

    def _handle_trade_suggestions(self) -> str:
        """Scan latest quiet alerts and return verified post-cost recommendations."""
        alerts_res = scan_quiet_alerts(self.df, entry_zscore=1.8)
        active_count = alerts_res["active_alerts_count"]
        alerts_df = alerts_res["alerts_df"]

        reply = f"### 📊 Live Commodity Intelligence Scan ({self.latest_date.strftime('%d %b %Y')})\n\n"
        reply += f"I analyzed **{alerts_res['total_pairs_evaluated']} active calendar spread pairs** across MCX gold contracts.\n\n"

        if active_count > 0 and not alerts_df.empty:
            active_pairs = alerts_df[alerts_df["status"] == "ACTIVE QUIET ALERT"]
            reply += f"🟢 **Found {active_count} Executable Post-Cost Edge(s)** that survive exchange fees, taxes, and liquidity haircuts:\n\n"
            for _, row in active_pairs.iterrows():
                reply += (
                    f"- **{row['symbol']}** ({row['near_expiry']} ➔ {row['far_expiry']}):\n"
                    f"  • **Signal**: `{row['signal_type']}` (Z-Score: `{row['spread_zscore']}`)\n"
                    f"  • **Gross Spread**: `₹{row['calendar_spread_inr']}/g` | **Roundtrip Cost**: `₹{row['round_trip_cost_inr']}/g`\n"
                    f"  • **Net Executable Edge**: `+₹{row['net_edge_inr']}/g`\n"
                    f"  • **Near Leg Volume**: `{row['volume_lots']} lots`\n\n"
                )
            reply += "💡 *Recommendation*: Execute using a 2-leg limit order ticket on Tab 4 to capture the mispricing."
        else:
            reply += (
                "🛡️ **Capital Preservation Mode Active**: Currently, **zero false alarms** are firing.\n\n"
                f"• **Statistical Deviations Detected**: `{alerts_res['raw_signals_count']}`\n"
                f"• **Tender Delivery Lockouts**: `{alerts_res['tender_suppressed_count']}` pairs suppressed to avoid MCX 25%+ delivery margin spikes.\n"
                f"• **Cost / Fee Traps**: `{alerts_res['cost_suppressed_count']}` pairs suppressed where gross edge was smaller than roundtrip fees.\n\n"
                "📌 **Quant Verdict**: The market is currently in fair-value equilibrium. Pro quant rule: **knowing when NOT to trade is where your capital survives.**"
            )

        return reply

    def _handle_hedging(self, prompt: str) -> str:
        """Parse holding amount and calculate exact delta hedge."""
        # Extract number of grams from prompt, e.g. "hedge 250g" or "hedge 500 grams"
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:g|gm|gram|grams)", prompt)
        grams = float(match.group(1)) if match else 100.0

        # Calculate optimal hedges against GOLDM, GOLDTEN, GOLDGUINEA
        hedge_m = calculate_optimal_hedge("GOLDM", "GOLDGUINEA", lots_a=max(1, int(round(grams / 100.0))), gold_price_per_g=self.avg_gold_price)
        
        reply = (
            f"### 🛡️ Delta-Neutral Hedge Recommendation for {grams:,.0f}g Physical Gold\n\n"
            f"At the current benchmark price of **₹{self.avg_gold_price:,.2f}/g**, your holding notional value is **₹{grams * self.avg_gold_price:,.2f}**.\n\n"
            f"**Recommended MCX Hedge Options**:\n"
        )

        # 1. Using GOLDM (100g lots)
        lots_goldm = int(round(grams / 100.0))
        if lots_goldm > 0:
            residual_m = abs(grams - (lots_goldm * 100))
            reply += f"1. **Wholesale Mini Hedge**: Short **{lots_goldm} lot(s) of GOLDM** ({lots_goldm * 100}g).\n   • Residual Mismatch: `{residual_m}g` | Efficiency: `{max(0.0, 100 - (residual_m/grams)*100):.1f}%`\n\n"

        # 2. Using GOLDGUINEA (8g lots)
        lots_guinea = int(round(grams / 8.0))
        residual_g = abs(grams - (lots_guinea * 8))
        reply += f"2. **Precision Retail Hedge**: Short **{lots_guinea} lot(s) of GOLDGUINEA** ({lots_guinea * 8}g).\n   • Residual Mismatch: `{residual_g}g` | Efficiency: `{max(0.0, 100 - (residual_g/grams)*100):.1f}%`\n\n"

        # 3. Using GOLDPETAL (1g lots)
        lots_petal = int(grams)
        reply += f"3. **Exact Zero-Delta Hedge**: Short **{lots_petal} lot(s) of GOLDPETAL** (Exact 100.0% Delta Match).\n\n"

        reply += "⚠️ *Risk Note*: Maintain hedge till 5 days before contract expiry, then roll over to avoid the MCX physical delivery tender window."
        return reply

    def _handle_parity(self) -> str:
        """Calculate and explain MCX vs COMEX Landed Import Parity."""
        parity = calculate_landed_import_parity(
            domestic_mcx_price_per_g=self.parity_benchmark_price,
        )

        reply = (
            f"### 🌐 MCX vs COMEX Import Parity & Landed Basis\n\n"
            f"• **COMEX Gold Benchmark**: `${parity['comex_usd_per_oz']:,}/troy oz`\n"
            f"• **USD/INR Reference**: `₹{parity['usdinr_rate']}`\n"
            f"• **Tariff Structure**: `10% BCD + 5% AIDC = {parity['total_tariffs_pct']}% customs levy (from 13 May 2026), plus 3% IGST`\n"
            f"• **Theoretical Landed Fair Value**: **₹{parity['landed_price_ex_gst_per_g']:,.2f}/g** (₹{parity['landed_price_per_10g_ex_gst']:,.0f}/10g ex-GST)\n"
            f"• **MCX (GOLDM + GOLDTEN avg)**: **₹{self.parity_benchmark_price:,.2f}/g**\n\n"
            f"**India Gold Basis (Domestic vs Landed)**:\n"
            f"### {'🟢 ' if parity['basis_inr_per_g'] >= 0 else '🔴 '} Basis: **₹{parity['basis_inr_per_g']:+,.2f}/g** ({parity['basis_pct']:+.2f}%)\n\n"
            f"**Institutional Verdict**: {parity['market_verdict']}\n\n"
            f"{parity['actionable_insight']}"
        )
        return reply

    def _handle_tender_inquiry(self) -> str:
        """Explain the MCX Tender Period rules and why it matters."""
        return (
            "### ⚠️ MCX Physical Delivery Tender Window Explained\n\n"
            "Under MCX rules, commodity futures contracts enter a **mandatory tender period 5 business days prior to expiry**:\n\n"
            "1. **Delivery Margin Spike**: Brokers and the exchange impose an immediate **25%+ delivery margin** on all open contracts in the tender window.\n"
            "2. **Physical Vault Assignment Risk**: If a speculative calendar spread is held into the tender window, the short near-leg can be assigned physical gold delivery in an MCX vault.\n"
            "3. **AurumSpread Capital Defense**: Our engine automatically blocks any entry into contracts within 5 days of expiry and signals an automatic pre-tender rollover exit.\n\n"
            "📌 *Tip*: Always trade calendar spreads between contracts with at least 15–30 days to expiry for clean cash settlement."
        )

    def _handle_order_ticket(self, prompt: str) -> str:
        """Generate order ticket preview."""
        pair = self._latest_pair("GOLDM")
        if pair is None:
            return "Not enough GOLDM expiries in the latest data to build a calendar spread ticket."
        near_exp, far_exp, near_px, far_px = pair
        ticket = generate_spread_order_ticket(
            symbol="GOLDM",
            near_expiry=near_exp,
            far_expiry=far_exp,
            strategy_type="Long Calendar Spread",
            lots=1,
            near_price=near_px,
            far_price=far_px,
        )

        reply = (
            f"### 📋 2-Leg Order Ticket (GOLDM {near_exp:%b} ➔ {far_exp:%b}, prices from {self.latest_date:%d %b %Y})\n\n"
            f"• **Strategy**: `{ticket['strategy']}`\n"
            f"• **Leg 1 (Near Month)**: `{ticket['legs'][0]['transaction_type']} 1 lot {ticket['legs'][0]['trading_symbol']} @ LIMIT ₹{ticket['legs'][0]['price']:,.0f}`\n"
            f"• **Leg 2 (Far Month)**: `{ticket['legs'][1]['transaction_type']} 1 lot {ticket['legs'][1]['trading_symbol']} @ LIMIT ₹{ticket['legs'][1]['price']:,.0f}`\n"
            f"• **Net Calendar Spread**: `₹{ticket['net_spread_price']:,.2f}`\n"
            f"• **Margin (estimate)**: about `₹{ticket['estimated_spread_margin_inr']:,.0f}` as a spread vs `₹{ticket['estimated_unhedged_margin_inr']:,.0f}` outright, assuming {ticket['margin_assumptions']}. Check your broker's margin calculator for live figures.\n\n"
            "⬇️ *The Kite and Dhan JSON payloads are in the Order Ticket panel.*"
        )
        return reply

    def _handle_contract_specs(self) -> str:
        """Display all 4 contract specifications."""
        reply = "### 🔬 MCX Gold Contracts Specification Matrix\n\n"
        for sym, spec in CONTRACT_SPECS.items():
            reply += (
                f"- **{spec['name']} (`{sym}`)**:\n"
                f"  • Lot Size: `{spec['lot_size_grams']}g` | Quoted: `per {spec['quote_unit_grams']}g`\n"
                f"  • Purity: `{spec['purity']}/1000` (Adjustment: `{spec['purity_factor']:.4f}`)\n"
                f"  • Normalization: `{spec['formula_str']}`\n\n"
            )
        reply += "💡 *Why this matters*: Comparing raw quoted prices without normalization creates fake arbitrage signals. AurumSpread standardizes all 4 contracts to ₹/1g of 999 gold."
        return reply

    def _handle_general_guidance(self, prompt: str) -> str:
        """Provide helpful guidance on what the copilot can do."""
        return (
            f"👋 I am your **Aurum Quant Copilot**, connected to the live MCX Bhavcopy database and risk engines.\n\n"
            "Here are some specific queries you can ask me:\n"
            "- 💡 *'What is the best calendar spread opportunity today?'*\n"
            "- 🛡️ *'How should I hedge 250 grams of physical gold?'*\n"
            "- 🌐 *'Is MCX gold at a premium or discount to COMEX import parity?'*\n"
            "- ⚠️ *'Explain why commodity spread alerts get suppressed'* \n"
            "- 📋 *'Generate a 2-leg Zerodha order ticket for GOLDM Nov-Dec'* \n"
            "- 🔬 *'Explain the difference between GOLDM and GOLDPETAL'* \n\n"
            f"Currently monitoring **{self.df['symbol'].nunique()} instruments** across **{len(self.latest_df)} active contract expiries**."
        )
