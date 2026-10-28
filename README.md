# 🟡 AurumSpread
### Commodity Derivatives Intelligence Platform for MCX Gold Futures
**Hack in Hills '26** | **Track 03: Commodity Derivatives Intelligence**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/pytest-23%20passed-brightgreen.svg)]()
[![Platform](https://img.shields.io/badge/dashboard-Streamlit-orange.svg)]()
[![MCX Data](https://img.shields.io/badge/data-MCX%20Bhavcopy-yellow.svg)]()

---

## 👥 Team AurumSpread

| Team Member | Role | Core Deliverables |
|---|---|---|
| **Shivansh Sahni** | Data & Python Backend | MCX Bhavcopy ingestion, symbol trimming, date validation, and ₹/1g 999 gold normalization. |
| **Krishna Sharma** | Quant Logic & Backtesting | Day-by-day walk-forward simulator, cost-of-carry decomposition, liquidity penalty, and tender lifecycle rules. |
| **Dhruv Gupta** | Frontend UI & Outreach | 4-tab institutional Streamlit dashboard, Plotly interactive analytics, and demo presentation. |

---

## 🎯 Problem Statement & Theme Alignment

In the Indian commodities market on the **Multi Commodity Exchange (MCX)**:
- **Same Gold, 4 Different Contracts**: Lot sizes (100g, 10g, 8g, 1g), quotation bases (per 10g, 8g, 1g), purities (995 vs 999), and expiry cycles (3rd–5th vs 27th–31st) all diverge.
- **Messy MCX Bhavcopy**: Space-padded symbols, mixed date formats (`%d %b %Y` vs `%d%b%Y`), and silent holiday fallbacks create false signals.
- **The Arbitrage Mirage**: Apparent calendar spread arbitrage profits vanish once realistic exchange turnover fees, STT/CTT taxes, delivery margins, and thin liquidity haircuts are accounted for.
- **Continuous Series Rollover Distortion**: Retail terminals (e.g. TradingView continuous contracts) stitch together contracts, introducing artificial price jumps at expiry that corrupt econometric spreads.

### Theme Alignment: Track 03 (Commodity Derivatives Intelligence)
AurumSpread delivers **analytical rigor over daily signals**: proving that an apparent paper edge does **not** survive realistic transaction costs is itself an essential, actionable institutional quant finding.

---

## 🚀 The 4 Core USPs (Novelty)

1. **Contract-by-Contract Lifecycle Engine**  
   Every contract is tracked as an independent `(Symbol, Expiry)` pair. Eliminates artificial rollover jumps and blocks new entries during illiquid and **MCX physical tender windows** (5 days pre-expiry).
2. **Unit + Purity + Carry Normalization**  
   Converts all four contracts to a uniform **₹ per 1 gram of 999 purity gold**:
   - `GOLDM`: $\text{Close} \div 10 \times \frac{999}{995}$ *(adjusted from 995 purity)*
   - `GOLDTEN`: $\text{Close} \div 10$
   - `GOLDGUINEA`: $\text{Close} \div 8$
   - `GOLDPETAL`: $\text{Close} \div 1$  
   Separates predictable time-value roll-down from true pricing discrepancies.
3. **Liquidity-Penalised Fill Estimator**  
   MCX settlement price is **not** an executable price. A dynamic slippage haircut derived from Volume and Open Interest depth is applied before any trade is counted.
4. **Honest Pre-Cost vs Post-Cost Survival Proof**  
   Directly charts pre-cost theoretical equity against post-cost net equity, proving whether an apparent edge survives real-world fees and slippage.

---

## 🖥️ The 4-Tab Trader Dashboard

```text
AurumSpread/
├── Tab 1: Fair Price & Quiet Alert      → Normalized ₹/g for all 4 contracts; alerts only post-cost
├── Tab 2: Expiry Calendar & Liquidity   → Lifecycle timeline, volume & OI depth, tender zones
├── Tab 3: Futures Curve & Carry         → Curve by expiry; roll-down vs real mispricing
└── Tab 4: Profit vs Fees Simulator      → Walk-forward replay, "What kills the edge?" sensitivity
```

### 1. Tab 1: Fair Price & Quiet Alert
- **4-Contract Normalized Snapshot**: Real-time comparison of all 4 contracts on a ₹/1g of 999 gold benchmark.
- **Quiet Alert System**: Scans 60 active spread pairs on the latest market date. Alerts fire **only** when a post-cost executable edge ($> 0$) survives all statutory charges, slippage, and liquidity filters. Suppresses noise and false arbitrage traps.

### 2. Tab 2: Expiry Calendar & Liquidity
- **Lifecycle Timeline**: Tracks contract roll-off across calendar months.
- **Volume & Open Interest Depth**: Visualizes liquidity concentration across near vs far expiries.
- **Tender Delivery Exclusion Zones**: Highlights the MCX 5-day pre-expiry tender window where physical delivery allocation and margin spikes occur.

### 3. Tab 3: Futures Curve & Carry
- **Term Structure Curve**: Interactive forward curve (₹/g vs Expiry) displaying Contango / Backwardation regimes.
- **Annualized Implied Carry Rate**: Quantifies financing cost (% p.a.) between front and deferred contracts.
- **Retail Micro-Premium Analysis**: Tracks the structural premium that retail-sized contracts (`GOLDPETAL`, `GOLDGUINEA`) command over mini (`GOLDM`).

### 4. Tab 4: Profit vs Fees Simulator ("What Kills the Edge?")
- **Walk-Forward Simulator**: Replays calendar spread strategies without future data leakage.
- **Overlaid Pre-Cost vs Post-Cost Equity Curves**: Shows paper profit vs realized net equity.
- **"What Kills the Edge?" Breakeven Slider**: Automatically computes the exact cost per leg at which the strategy's net P&L drops to zero.
- **Signal Suppression Funnel**: Visualizes how raw statistical anomalies are filtered out by tender windows, liquidity minimums, and fee barriers.

---

## 🌟 Stretch Features Highlighted in Presentation

- **📐 Lot-Size Hedge Ratio Optimizer**: Calculates exact delta-neutral integer lot ratios between mismatched contracts (e.g. 1 GOLDM 100g vs 12 GOLDGUINEA 8g, or exact zero-delta 2 GOLDM : 25 GOLDGUINEA).
- **🩺 MCX Data Doctor**: Automated Bhavcopy integrity audit checking symbol padding, ISO date formatting, holiday continuity, zero volumes, and contract lifecycle ordering (100/100 score).
- **🏷️ Retail Micro-Premium Heatmap**: Quantifies retail convenience markups over wholesale mini contracts.

---

## 🥊 What Exists Today vs AurumSpread

| Capability | Retail Terminals (Zerodha, Groww) | Charting (TradingView) | Derivatives Portals (Sensibull) | Institutional (Bloomberg) | **AurumSpread** |
|---|---|---|---|---|---|
| **Purity & Unit Normalization** | ❌ Raw quote only | ❌ None | ❌ None | ⚠️ Manual formula | ✅ **Automated (995 to 999 ₹/g)** |
| **No Rollover Discontinuity** | ❌ Rollover jumps | ❌ Continuous jumps | ❌ None | ⚠️ Manual roll rules | ✅ **Contract-by-contract lifecycle** |
| **MCX Tender Period Lockout** | ❌ None | ❌ None | ❌ None | ❌ Custom setup | ✅ **Automated 5-day tender lockout** |
| **Dynamic Liquidity Haircut** | ❌ Uses settlement px | ❌ None | ❌ None | ⚠️ Static bid-ask | ✅ **Dynamic Volume/OI haircut** |
| **Quiet Alert Noise Suppression** | ❌ Raw price alerts | ❌ Indicator noise | ❌ None | ❌ High false-alarm rate | ✅ **Post-cost survival alerts only** |
| **Cost** | Free (Brokered) | \$15–\$60/mo | \$10–\$25/mo | \$24,000+/year | ✅ **Open-Source Quant Prototype** |

---

## 🛠️ Technology Stack & Architecture

- **Language & Runtime**: Python 3.10+
- **Analytics & Quants**: Pandas, NumPy
- **Interactive UI**: Streamlit
- **Visualizations**: Plotly Express & Plotly Graph Objects
- **Test Automation**: Pytest (23 unit & integration tests)
- **Data Source**: Official MCX Bhavcopy (public daily exchange data)

```text
AurumSpread/
├── app.py                     # 4-Tab Institutional Streamlit Dashboard
├── build_historical_dataset.py # Pipeline cleaning raw Bhavcopy CSVs
├── requirements.txt           # Project dependencies
├── pytest.ini                 # Pytest configuration
│
├── src/                       # Core Analytical Engines
│   ├── normalize.py           # Unit & 999 purity normalization
│   ├── spread_engine.py       # Calendar spread pair generator
│   ├── spread_intelligence.py # Expanding-window Z-score & percentiles
│   ├── carry_engine.py        # Forward curve, annualized carry & micro-premium
│   ├── liquidity_engine.py    # Volume/OI depth, tender lockout, dynamic slippage
│   ├── backtest_engine.py     # Walk-forward backtester & survival proof
│   ├── quiet_alerts.py        # Quiet alert scanner & noise suppression
│   ├── hedge_optimizer.py     # Lot-size integer delta hedge optimizer
│   └── data_doctor.py         # Automated Bhavcopy health auditor
│
├── data/
│   ├── raw/                   # Raw daily MCX Bhavcopy CSV files
│   └── processed/             # Cleaned historical_gold_futures.csv
│
└── tests/                     # 23 automated pytest test cases
```

---

## ⚡ Quickstart & Installation

### 1. Clone the repository & create virtual environment
```bash
git clone https://github.com/<your-username>/AurumSpread.git
cd AurumSpread
python -m venv .venv
```

Activate environment:
- **Windows**: `.venv\Scripts\activate`
- **Linux / macOS**: `source .venv/bin/activate`

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the automated test suite
```bash
pytest
```
*Expected result: 23 passed, 0 failures.*

### 4. Launch the Streamlit dashboard
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🏆 Hackathon Submission Checklist (Final Round)

- [x] **Track 03 Alignment**: Rigorous commodity derivatives intelligence with cost-of-carry and walk-forward backtesting.
- [x] **4 Core USPs Implemented**: Contract lifecycle, unit+purity normalization, liquidity-penalised fill, honest pre vs post-cost survival proof.
- [x] **4-Tab Trader Dashboard**: Exactly matches PPT Slide 6 structure and features.
- [x] **Stretch Features**: Lot-size hedge optimizer, MCX Data Doctor audit, "What kills the edge?" sensitivity, retail micro-premium analysis.
- [x] **100% Passing Test Suite**: 23 clean pytest tests verifying data integrity, quant models, and zero future data leakage.
- [x] **Production Ready**: Beautiful institutional dark-gold theme, responsive interactive charts, zero runtime errors.

---
*Built with ❤️ for **Hack in Hills '26** by Team AurumSpread.*
