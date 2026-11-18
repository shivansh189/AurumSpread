"""Independent verification of the dataset by a TinyFish web agent.

The MCX Bhavcopy is the project's only data source, and the problem statement
warns that MCX "may return the most recent available trading day for an
unrecognized, holiday, malformed, or future date". A dataset built from
downloaded files cannot detect that on its own: the file is simply whatever the
exchange served.

So a TinyFish web agent re-reads selected rows straight from mcxindia.com in a
real browser and the results are compared against the stored dataset. Two things
are checked:

1. **Date integrity** - the trading date the page displays must equal the date
   that was requested, which is exactly the silent-substitution failure above.
2. **Value integrity** - close, volume and open interest read from the live page
   must equal the stored values for that (symbol, trade date, expiry).

Agent runs take minutes and cost credits, so results are recorded to
data/verification/agent_runs.json and replayed. This module does no network I/O;
it only compares recorded agent output with the dataset.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

RUNS_PATH = Path(__file__).resolve().parent.parent / "data" / "verification" / "agent_runs.json"

_MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], start=1)}


def parse_mcx_expiry(text: str) -> Optional[pd.Timestamp]:
    """Parse the compact MCX expiry form (04DEC2026) or a spaced one (04 Dec 2026)."""
    s = str(text).strip().upper().replace(" ", "")
    if len(s) < 9:
        return None
    try:
        return pd.Timestamp(year=int(s[5:9]), month=_MONTHS[s[2:5]], day=int(s[:2]))
    except (KeyError, ValueError):
        return None


def load_agent_runs(path: Path | str = RUNS_PATH) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("runs", [])


def verify_against_dataset(
    df: pd.DataFrame,
    runs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compare recorded agent observations with the stored dataset.

    Each check is reported individually so a failure is visible rather than
    averaged away.
    """
    runs = load_agent_runs() if runs is None else runs
    data = df.copy()
    data["trade_date"] = pd.to_datetime(data["trade_date"], errors="coerce", format="mixed")
    data["expiry_date"] = pd.to_datetime(data["expiry_date"], errors="coerce", format="mixed")

    checks: List[Dict[str, Any]] = []

    for run in runs:
        kind = run.get("kind")
        requested = run.get("requested_date")

        if kind == "date_integrity":
            matched = bool(run.get("date_matches"))
            expected = bool(run.get("expect_match", True))
            checks.append({
                "kind": "date_integrity",
                "label": run.get("label", f"Requested {requested}"),
                "requested": requested,
                "observed": run.get("displayed_date"),
                "passed": matched == expected,
                "detail": run.get("note", ""),
                "steps": run.get("steps"),
            })
            continue

        if kind == "row_integrity":
            trade_date = pd.to_datetime(run.get("trade_date"), errors="coerce", format="mixed")
            for row in run.get("rows", []):
                sym = str(row.get("symbol", "")).strip().upper()
                exp = parse_mcx_expiry(row.get("expiry_date", ""))
                stored = data[(data["symbol"] == sym)
                              & (data["trade_date"] == trade_date)
                              & (data["expiry_date"] == exp)]
                if stored.empty:
                    checks.append({
                        "kind": "row_integrity",
                        "label": f"{sym} {exp:%d %b %Y}" if exp is not None else sym,
                        "requested": run.get("trade_date"),
                        "observed": "not present in dataset",
                        "passed": False,
                        "detail": "The agent read this row from MCX but the dataset has no matching row.",
                        "steps": run.get("steps"),
                    })
                    continue
                s = stored.iloc[0]
                fields = {
                    "close": (float(row["close"]), float(s["close"])),
                    "volume_lots": (float(row["volume_lots"]), float(s["volume_lots"])),
                    "open_interest_lots": (float(row["open_interest_lots"]), float(s["open_interest_lots"])),
                }
                mismatched = [k for k, (a, b) in fields.items() if abs(a - b) > 0.005]
                checks.append({
                    "kind": "row_integrity",
                    "label": f"{sym} · {exp:%d %b %Y} expiry",
                    "requested": f"{trade_date:%d %b %Y}",
                    "observed": "close ₹{:,.0f} · vol {:,.0f} · OI {:,.0f}".format(
                        fields["close"][0], fields["volume_lots"][0], fields["open_interest_lots"][0]),
                    "passed": not mismatched,
                    "detail": ("Live page matches the stored row on close, volume and open interest."
                               if not mismatched else
                               "Mismatch on: " + ", ".join(mismatched)),
                    "steps": run.get("steps"),
                })

    passed = sum(1 for c in checks if c["passed"])
    return {
        "checks": checks,
        "total": len(checks),
        "passed": passed,
        "failed": len(checks) - passed,
        "all_passed": len(checks) > 0 and passed == len(checks),
        "agent_runs": len(runs),
        "total_steps": sum(r.get("steps") or 0 for r in runs),
    }
