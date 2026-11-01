"""
engine/pnl.py — what the desk actually made (David 2026-10-30: "run this in the 24/7 will check how much
profit it can make").

    python3 -m engine.pnl [--days 7] [--since 2026-10-30T15:09] [--magic 5050505]

Every closed deal's NET is profit + commission + swap, so the spread, the broker's cut and the financing are
all in the number. Trades are grouped by magic, because three different things trade this account:

    5050505   the V5 engine          24102099  Claude's own MT5 trades
    5050600   Kronos

WHY THE CONFIDENCE INTERVAL IS PRINTED AND NOT JUST THE TOTAL
-------------------------------------------------------------
A run of 0.01-lot trades is mostly noise. Measured on our own history, a trade's dollar outcome has a
standard deviation several times its mean, so a few dozen trades can show any total at all. The report
therefore prints the 95 % interval for the TRUE mean and, when the mean is positive, how many trades it
would take to tell that mean from zero (Bailey & Lopez de Prado's minimum track record length, which comes
to the same thing as n >= (1.645 x sd / mean)^2 one-sided).

Reading a positive total with an interval that spans zero as "it works" is the mistake this report exists
to stop.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import sys
from collections import defaultdict
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mt5_client as mt5c                                        # noqa: E402

from .config import DATA_DIR                                     # noqa: E402

NAMES = {5050505: "V5 engine", 5050600: "Kronos", 24102099: "Claude's own"}
RUN_FILE = os.path.join(DATA_DIR, "profit_run.json")


def run_start() -> Optional[Dict]:
    """when the 24/7 run on the profit profile began (engine_data/profit_run.json)."""
    try:
        with open(RUN_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def closed(days: float = 7.0, since_ms: Optional[int] = None) -> List[Dict]:
    """closing deals only (entry == 1): one per finished position, carrying its whole net."""
    out = []
    for d in mt5c.deals(days=days) or []:
        if int(d.get("entry", 0)) != 1:
            continue
        t_ms = int(d.get("time_msc") or int(d.get("time", 0)) * 1000)
        if since_ms and t_ms < since_ms:
            continue
        net = float(d.get("profit", 0)) + float(d.get("commission", 0)) + float(d.get("swap", 0))
        out.append({"t": t_ms, "magic": int(d.get("magic", 0)), "symbol": d.get("symbol"),
                    "volume": float(d.get("volume", 0)), "net": net,
                    "profit": float(d.get("profit", 0)), "commission": float(d.get("commission", 0)),
                    "swap": float(d.get("swap", 0)), "comment": d.get("comment", "")})
    return sorted(out, key=lambda r: r["t"])


def stats(rows: List[Dict]) -> Dict:
    n = len(rows)
    if n == 0:
        return {"n": 0}
    xs = [r["net"] for r in rows]
    total = sum(xs)
    mean = total / n
    sd = (sum((x - mean) ** 2 for x in xs) / (n - 1)) ** 0.5 if n > 1 else float("nan")
    se = sd / math.sqrt(n) if n > 1 and sd == sd else float("nan")
    t = mean / se if se and se == se and se > 0 else 0.0
    lo = mean - 1.96 * se if se == se else float("nan")
    hi = mean + 1.96 * se if se == se else float("nan")
    need = None
    if mean > 0 and sd == sd and sd > 0:
        need = int(math.ceil((1.645 * sd / mean) ** 2))
    return {"n": n, "total": total, "mean": mean, "sd": sd, "se": se, "t": t, "lo": lo, "hi": hi,
            "win": sum(1 for x in xs if x > 0) / n, "need_n": need,
            "costs": sum(r["commission"] + r["swap"] for r in rows),
            "first": rows[0]["t"], "last": rows[-1]["t"]}


def verdict(s: Dict) -> str:
    if not s.get("n"):
        return "no closed trades yet"
    if s["n"] < 30:
        return f"{s['n']} trades is far too few to mean anything either way"
    if s["lo"] > 0:
        return "profitable, and the interval clears zero"
    if s["hi"] < 0:
        return "LOSING, and the interval clears zero"
    side = "positive" if s["mean"] > 0 else "negative"
    extra = f"; ~{s['need_n']:,} trades would be needed to call it" if s.get("need_n") else ""
    return f"{side} so far but indistinguishable from zero{extra}"


def _fmt_t(ms: int) -> str:
    return _dt.datetime.fromtimestamp(ms / 1000, _dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def report(days: float = 7.0, since_ms: Optional[int] = None, magic: Optional[int] = None) -> Dict:
    rows = closed(days, since_ms)
    if magic is not None:
        rows = [r for r in rows if r["magic"] == magic]
    by = defaultdict(list)
    for r in rows:
        by[r["magic"]].append(r)
    out = {"window_days": days, "since": since_ms, "by_magic": {}, "all": stats(rows)}
    for m, rs in by.items():
        out["by_magic"][m] = {"name": NAMES.get(m, f"magic {m}"), **stats(rs)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=7.0)
    ap.add_argument("--since", default="", help="ISO time, e.g. 2026-10-30T15:09 (UTC)")
    ap.add_argument("--magic", type=int, default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--run", action="store_true", help="only the 24/7 run on the profit profile")
    a = ap.parse_args()
    since = None
    if a.run:
        r0 = run_start()
        if r0:
            since = r0["started_ms"]
            a.days = max(a.days, (_dt.datetime.now(_dt.timezone.utc).timestamp() * 1000 - since) / 86400000 + 0.5)
    if a.since:
        since = int(_dt.datetime.fromisoformat(a.since).replace(tzinfo=_dt.timezone.utc).timestamp() * 1000)
    r = report(a.days, since, a.magic)
    if a.json:
        print(json.dumps(r, indent=1))
        return 0
    print(f"closed trades in the last {a.days:g} days" + (f" since {_fmt_t(since)}" if since else ""))
    for m, s in sorted(r["by_magic"].items(), key=lambda kv: -abs(kv[1].get("total", 0))):
        if not s.get("n"):
            continue
        print(f"\n  {s['name']} (magic {m})")
        print(f"    {s['n']} trades, {s['win']*100:.0f} % won, {_fmt_t(s['first'])} -> {_fmt_t(s['last'])}")
        print(f"    net ${s['total']:+.2f}   per trade ${s['mean']:+.4f}  (95 % CI ${s['lo']:+.4f} .. ${s['hi']:+.4f}, t={s['t']:+.2f})")
        print(f"    of which commission + swap: ${s['costs']:+.2f}")
        print(f"    -> {verdict(s)}")
    s = r["all"]
    if s.get("n"):
        print(f"\n  EVERYTHING: {s['n']} trades, net ${s['total']:+.2f}, per trade ${s['mean']:+.4f} "
              f"(95 % CI ${s['lo']:+.4f} .. ${s['hi']:+.4f})")
        print(f"  -> {verdict(s)}")
    else:
        print("\n  no closed trades in this window")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
