# 🟡 AurumSpread

### Cross-Contract Relative Value Intelligence for MCX Gold Futures

**Hack in Hills '26** · **Track 03: Commodity Derivatives Intelligence** · **Final Round**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/pytest-31%20passed-brightgreen.svg)]()
[![Data](https://img.shields.io/badge/MCX%20Bhavcopy-99%20sessions-yellow.svg)]()
[![Scope](https://img.shields.io/badge/universe-4%20MCX%20gold%20contracts-gold.svg)]()

**Live site:** https://aurumspread.vercel.app

---

## What this is

MCX lists the same underlying metal — gold — in four different futures contracts.
They differ in lot size, quotation base, purity and expiry window, so their quoted
prices are not directly comparable:

| Contract | Trading unit | Quoted per | Purity | Expiry window |
|---|---|---|---|---|
| GOLDM | 100 g | 10 g | 995 | 3rd–5th |
| GOLDTEN | 10 g | 10 g | 999 | 27th–31st |
| GOLDGUINEA | 8 g | 8 g | 999 | 27th–31st |
| GOLDPETAL | 1 g | 1 g | 999 | 27th–31st |

AurumSpread turns the public MCX Bhavcopy into a comparable ₹ per 1 gram of 999
gold series, measures the relative pricing differences between these contracts,
and then tests honestly whether any of those differences are tradable after real
costs. **The headline finding is that they are mostly not** — and the project is
built to show that rather than hide it.

---

## The finding

The brief states that a rigorous demonstration that no persistent edge survives
costs is a valid analytical outcome. That is what the data shows.

Thresholds are tuned on an earlier window only, then applied **unchanged** to a
later window the tuning never saw:

| Split | In-sample net / trade | Out-of-sample net / trade | Trades out-of-sample |
|---|---|---|---|
| 15 Sep 2026 | ₹256.93 | ₹141.59 | 17 |
| 01 Oct 2026 | ₹261.56 | −₹2.50 | 2 |
| **15 Oct 2026** | **₹167.48** | **₹70.82 (−58%)** | 38 |
| 01 Nov 2026 | ₹240.83 | −₹2.50 | 2 |

At every split the apparent edge shrinks substantially out-of-sample, and at two
splits the tuned thresholds barely trigger at all. On the latest session the
quiet-alert scanner reports **zero** actionable spreads after costs.

**Attribution.** Regressing daily spread P&L on the daily move of the near leg
gives beta 0.0379 and R² 0.045 across 1,232 held days: the two legs hedge most
of the gold move, as a calendar spread should. Of the gross P&L, roughly half is
relative-value and half is explained by the move in the underlying — reported
separately rather than claimed as strategy alpha.

Both are reproducible: `src/validation_engine.py`, shown live in the
**Out-of-Sample Validation** panel on the site.

---

## Core capabilities

1. **Contract-by-contract lifecycle.** Every contract is tracked as an
   independent `(symbol, expiry)` pair, so there is no continuous-series
   stitching and no artificial jump at rollover. Entries are blocked inside the
   MCX 5-day physical tender window.
2. **Unit + purity normalization.** `GOLDM: close ÷ 10 × 999/995`,
   `GOLDTEN: close ÷ 10`, `GOLDGUINEA: close ÷ 8`, `GOLDPETAL: close ÷ 1`.
3. **Cost-aware walk-forward backtest.** Day-by-day replay with no look-ahead:
   z-scores use an expanding window of prior observations only, and a position is
   never opened on information from the day it is evaluated.
4. **Liquidity-penalised fills.** Settlement price is not an executable price, so
   a slippage haircut derived from volume and open interest is applied before any
   trade counts.
5. **Out-of-sample validation and P&L attribution** (above).
6. **MCX vs COMEX landed import parity.** COMEX $/oz → ₹/g landed cost using the
   duty structure in force since 13 May 2026 (10% BCD + 5% AIDC, gold exempt from
   SWC, 3% IGST), giving the India gold basis.
7. **Broker-ready 2-leg order tickets.** A viable spread exports as Zerodha Kite
   Connect and DhanHQ order payloads, or CSV.
8. **Agent-verified data integrity.** A TinyFish web agent opens mcxindia.com in a
   real browser and re-reads the exchange data independently of our downloaded
   files. Three recorded checks, all passing:
   - a valid date (17/11/2026) is served correctly;
   - a **market holiday (02/10/2026, Gandhi Jayanti) is silently substituted** —
     MCX returned 17 Nov 2026 data while the date input still read 02/10/2026,
     with no message. This is exactly the failure the brief warns about, and a
     downloaded file cannot detect it;
   - a GOLDM row re-read live matches our stored close, volume and open interest.

   Recorded in `data/verification/agent_runs.json` and replayed by
   `src/agent_verification.py`, so the comparison is reproducible without
   re-running the agent.

---

## Honest limitations

- **The dataset is a 99-session snapshot** (1 Jul – 17 Nov 2026). Conclusions are
  bounded by that sample; a few months of gold spreads is a small sample for a
  claim about persistent edge.
- **Margin figures are estimates**, not live MCX SPAN margins. The outright and
  calendar-offset percentages are inputs, labelled as assumptions.
- **No live intraday feed.** MCX publishes Bhavcopy after the session closes, so
  the dashboard is end-of-day by construction.
- **The parity panel's COMEX and USD/INR inputs are a dated reference** for the
  last session, editable by the user, not a streaming quote.
- **No order is ever placed.** The ticket generator produces a payload for a human
  to review and submit.

---

## Architecture

```text
AurumSpread/
├── landing_page/index.html         # The product: single-page analytics site (Vercel)
├── app.py                          # Streamlit dashboard over the same engines
│
├── src/                            # Analytical engines (pure functions over DataFrames)
│   ├── ingest.py                   # Bhavcopy loading, symbol trimming, date validation
│   ├── normalize.py                # Contract specs + unit/purity normalization
│   ├── spread_engine.py            # Calendar spread pair construction
│   ├── spread_intelligence.py      # Expanding-window mean, std, percentile, z-score
│   ├── backtest_engine.py          # Walk-forward replay, costs, breakeven search
│   ├── validation_engine.py        # Out-of-sample validation + P&L attribution
│   ├── carry_engine.py             # Term structure, implied carry, micro-premium
│   ├── liquidity_engine.py         # Depth, tender lockout, slippage estimation
│   ├── quiet_alerts.py             # Post-cost alert scanner with suppression audit
│   ├── parity_engine.py            # COMEX landed import parity and India basis
│   ├── order_ticket.py             # Kite / Dhan 2-leg order payloads
│   ├── hedge_optimizer.py          # Integer lot delta-neutral hedge ratios
│   ├── data_doctor.py              # Dataset health audit
│   ├── agent_verification.py       # Compares TinyFish agent readings vs the dataset
│   └── copilot_engine.py           # Rule-based query responder (see note below)
│
├── scripts/
│   ├── build_expanded_dataset.py   # Raw Bhavcopy CSVs → historical_gold_futures.csv
│   ├── build_site_data.py          # Rebuilds the site's embedded DATA from the dataset
│   └── download_mcx.py             # Playwright Bhavcopy downloader
│
├── data/
│   ├── verification/               # Recorded TinyFish agent observations
│   ├── raw/                        # Raw daily Bhavcopy CSVs (gitignored)
│   └── processed/
│       └── historical_gold_futures.csv   # 2,376 rows · 4 contracts · 99 sessions
│
└── tests/                          # 31 pytest tests (1 skipped: live MCX scrape)
```

**On `copilot_engine.py`:** this is a deterministic keyword-routed responder over
the same engines, not a language model. It is described that way deliberately.
The project's AI component is the TinyFish web agent used for data verification.

---

## Data pipeline

```text
MCX Bhavcopy CSV  →  ingest/normalize  →  historical_gold_futures.csv
                                               │
                        ┌──────────────────────┼──────────────────────┐
                        ▼                      ▼                      ▼
                 spread_engine         carry/liquidity          data_doctor
                        │                      │                      │
                 spread_intelligence           │                      │
                        │                      │                      │
            backtest + validation ─────────────┴──────────────────────┘
                        │
            scripts/build_site_data.py  →  landing_page/index.html
```

The site is static: `build_site_data.py` recomputes every figure from the CSV with
the same Python engines and writes them into the page, so the website and the
backend can never disagree. The site's in-browser backtest was verified against
the Python engine across 4,320 parameter combinations with zero mismatches.

### Data considerations handled

- **Requested-date validation.** MCX returns the most recent available trading day
  for an unrecognised, holiday, malformed or future date. The TinyFish agent
  checks the displayed date against the requested one.
- **Symbol padding and mixed date formats** (`04DEC2026` vs `04 Dec 2026`) are
  normalised on ingest.
- **Special sessions.** The dataset includes the Diwali Muhurat session of Sunday
  8 Nov 2026; without it, 9 Nov previous-closes do not reconcile.
- **Expiry-keyed tracking,** never a continuous near-month series.

---

## Quickstart

```bash
git clone https://github.com/shivansh189/AurumSpread.git
cd AurumSpread
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest                                              # 31 passed, 1 skipped
```

Open the site locally:

```bash
open landing_page/index.html        # or just visit https://aurumspread.vercel.app
```

Rebuild the site's data after adding Bhavcopy files:

```bash
python scripts/build_expanded_dataset.py   # raw CSVs → dataset
python scripts/build_site_data.py          # dataset → site
```

Run the Streamlit dashboard over the same engines:

```bash
streamlit run app.py
```

---

## Team

| Member | Role |
|---|---|
| **Shivansh Sahni** | Data & Python backend — Bhavcopy ingestion, normalization, COMEX parity model |
| **Krishna Sharma** | Quant logic & backtesting — walk-forward simulator, cost model, tender lifecycle, out-of-sample validation |
| **Dhruv Gupta** | Frontend & outreach — analytics site, visualisations, demo |

---

*Built for **Hack in Hills '26**, Track 03.*
