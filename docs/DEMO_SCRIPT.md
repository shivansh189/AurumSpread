# AurumSpread — Finale Demo Script & Q&A

**Hack in Hills '26 · Track 03 · Team AurumSpread**
Live site: **https://aurumspread.vercel.app**

---

## Before you present

- [ ] Open the site **before** you go on stage; let the 3D intro finish once so it is cached.
- [ ] Have the backup demo video ready offline on your laptop.
- [ ] Have the repo open in a second tab: `github.com/shivansh189/AurumSpread`.
- [ ] Know these four numbers cold: **99 sessions**, **4 contracts**, **−58% edge decay**, **beta 0.0379**.
- [ ] Phone hotspot ready in case the venue Wi-Fi fails.

---

## The one-sentence pitch

> AurumSpread turns MCX's public Bhavcopy into a comparable ₹-per-gram series across
> the four gold contracts, measures the relative pricing differences between them,
> and then tests honestly whether any of it is tradable after costs — and shows that
> mostly it is not.

Say the last clause with confidence. It is the point, not an apology. The brief
states that a rigorous demonstration that no persistent edge survives costs is a
valid analytical outcome.

---

## 4-minute walkthrough

### 0:00 — The problem (30s, no screen)

> "MCX lists gold in four contracts: GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL.
> Same metal. But different lot sizes, different quotation bases, 995 versus 999
> purity, and two different expiry windows. So their screen prices are not
> comparable. The question we were given was: can you measure the real pricing
> differences between them, and are those differences tradable?"

### 0:30 — Normalization and data (45s) · *Tab 1*

Scroll to the dashboard. Point at the four contract cards.

> "Everything is converted to rupees per gram of 999 gold. GOLDM divided by ten,
> times 999 over 995 for purity. GOLDGUINEA divided by eight. After normalization
> the four contracts sit within about seventy rupees a gram of each other — that
> residual spread is what we analyse."

Point at the data badge.

> "Ninety-nine MCX sessions, first of July to seventeenth of November. Twenty-three
> hundred and seventy-six rows. Including the Diwali Muhurat session on Sunday the
> eighth of November — without it, the ninth of November's previous-closes don't
> reconcile."

### 1:15 — The quiet alert scanner (30s) · *Tab 1, scroll down*

> "Fifty-five expiry pairs scanned on the latest session. Raw triggers: zero.
> Active alerts: zero. The scanner is built to stay quiet. It only fires when a
> post-cost edge actually survives fees, slippage, the tender lockout and a
> liquidity floor."

### 1:45 — **Out-of-sample validation — the centrepiece** (75s) · *Tab 4*

This is the section to spend time on. Switch the split dropdown to **15 Oct 2026**.

> "This is the part that matters. We tune the entry and exit thresholds on data up
> to the fourteenth of October only. Then we apply those exact thresholds,
> unchanged, to the window after it — data the tuning never saw.
>
> In-sample: a hundred and fourteen trades, a hundred and sixty-seven rupees net
> per trade. Out-of-sample: thirty-eight trades, seventy rupees. **Fifty-eight
> percent of the apparent edge disappears the moment you stop fitting.**"

Change the dropdown to **1 Oct 2026**.

> "And it's not one unlucky split. At this split the tuned thresholds trigger
> twice in six weeks and lose money. The in-sample result was selection bias."

Point at the attribution box.

> "We also separate strategy from gold. Daily spread P&L regressed on the near
> leg's move gives a beta of 0.038 and an R-squared of 0.045. The legs hedge the
> gold move, which is exactly what a calendar spread should do — so we report the
> relative-value part and the directional part separately instead of calling it
> all alpha."

### 3:00 — Execution and parity (40s) · *Tab 4 bottom, then Tab 3*

> "When a spread does survive, it exports as a two-leg Kite Connect or Dhan order
> payload — correct sides, lot counts and limit prices, with a tender-window
> warning. We never place an order; a human reviews the payload."

Switch to Tab 3, scroll to parity.

> "And a cross-check on the whole market: COMEX converted to Indian landed cost
> using the duty structure in force since May this year — ten percent customs plus
> five percent AIDC. MCX is trading about four percent above import parity."

### 3:40 — Close (20s)

> "Clean data, verified by an autonomous agent. Four contracts normalized. Every
> signal tested on data it never saw. P&L separated from the gold price. And an
> honest answer: at these costs, on this sample, there is no persistent edge —
> which is a finding, not a failure."

---

## Q&A — hard questions and honest answers

### "Your backtest makes money in-sample. Isn't that just overfitting?"
> "Yes, and we show it. That's what the validation panel is for. In-sample is a
> hundred and sixty-seven rupees per trade, out-of-sample is seventy — a
> fifty-eight percent decay. At two of the four splits it goes negative. We'd
> rather show the decay than quote the in-sample number."

### "How do I know there's no look-ahead bias?"
> "Three things. Z-scores use an expanding window of strictly prior observations
> — the mean and standard deviation are shifted by one day, and we require ten
> prior observations before any signal. Entry uses that day's z-score and the P&L
> is marked from the next day's price change. And there's a dedicated test,
> `test_no_future_leakage`, that fails if that ordering breaks."

### "Are those margin numbers real MCX SPAN margins?"
> "No, and the panel says so. They're an estimate from two inputs you can change:
> ten percent of notional outright and a seventy-five percent calendar-spread
> offset. Real SPAN margins change daily. We'd use the broker's margin API in
> production."

### "Why is MCX four percent above import parity? That looks wrong."
> "After the May 2026 duty hike — customs went from five to ten percent and AIDC
> from one to five — domestic prices sit structurally above landed cost. There's
> also a timing effect: the COMEX reference is a US close and MCX is an Indian
> close. The panel's inputs are editable so you can test either."

### "Is the Copilot actually AI?"
> "No. `copilot_engine.py` routes keywords to deterministic functions. We call it
> a rule-based responder in the README because calling it AI would be misleading.
> Our genuine AI component is the TinyFish web agent that independently verifies
> our data against mcxindia.com."

### "How do you know your data is correct?"
> "Two layers. Data Doctor audits symbol padding, date parsing, price sanity,
> lifecycle ordering, zero volumes and holiday continuity — a hundred out of a
> hundred. And a TinyFish agent re-reads rows straight from the MCX site in a
> real browser and compares them to our stored values. It also checks the
> requested-date trap your brief warns about: MCX silently returns the most
> recent available trading day for a holiday or malformed date, and a downloaded
> file can't detect that on its own."

### "Ninety-nine sessions is a small sample."
> "Agreed, and it's in our limitations section. Four and a half months of gold
> spreads can't settle whether an edge persists across regimes. What it can do —
> and does — is show that an edge fitted on one window doesn't carry to the next.
> More history would make the negative result stronger, not weaker."

### "What's genuinely novel here versus a Bloomberg terminal?"
> "Three things. Purity and unit normalization is automated rather than a manual
> formula. Entries are blocked inside the MCX five-day physical tender window,
> which is MCX-specific and not in generic tools. And the honest pre-cost versus
> post-cost survival proof with an out-of-sample split — most retail tools show
> you the pre-cost number."

### "What would you build next?"
> "Three things, in order. Intraday data instead of end-of-day settlement, since
> settlement prices aren't executable. Live broker margin APIs to replace our
> margin estimate. And a longer history — two or three years — so the
> out-of-sample test spans more than one gold regime."

### "Did you use AI to build this?"
> "Yes, as a tool, and we can walk you through any line. The analytical decisions
> — the expanding-window z-score, the tender lockout rule, the out-of-sample
> split design, the attribution regression — are ours, and the tests encode them."

---

## If something breaks on stage

| Problem | What to do |
|---|---|
| Site won't load | Switch to the backup video. Keep talking; do not debug on stage. |
| 3D intro stutters | Scroll straight past it to the dashboard — the analytics are the point. |
| A chart renders empty | Switch tabs and back; Plotly re-renders on resize. |
| Asked for something not built | "Not in this build — here's what we'd need to add it." Never bluff. |

---

## Numbers to have memorised

| | |
|---|---|
| Sessions / rows / contracts | 99 · 2,376 · 4 |
| Date range | 1 Jul – 17 Nov 2026 |
| Data Doctor | 100/100 |
| Tests | 29 passed, 1 skipped |
| Out-of-sample decay (15 Oct split) | ₹167.48 → ₹70.82 per trade (−58%) |
| Attribution | beta 0.0379, R² 0.045, ~48% directional share |
| Active alerts on latest session | 0 of 55 pairs |
| India gold basis | +₹552/g (+4.15%) over landed parity |
| Implied carry (GOLDM front) | ~13.4% p.a., contango |
