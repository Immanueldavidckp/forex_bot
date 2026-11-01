"""
engine/profit.py — the cost layer (David 2026-10-30: "create the trading logic which will make more profit
... take all the valid trade, no limit for trade and position, lot 0.01").

WHY THIS MODULE IS ABOUT COST AND NOT ABOUT DIRECTION
-----------------------------------------------------
Measured on our own 16 months of FxPro history (engine/research/profit/, 0.01 lot, one full spread per
round trip), random entries decompose as:

    GROSS (before cost)  -$0.024 per trade   t = -1.91   -> a coin flip, as expected
    COST  (one spread)   +$0.081 per trade
    NET                  -$0.106 per trade

Direction is free; the spread is the entire profit and loss. About 360 rule x geometry combinations were
scanned (breakout, fade, RSI, EMA cross, displacement, every hour of the day, time-series momentum) on
M15 / H1 / H4: not one reached t > 1.0, where chance alone would have thrown up several above 2. The one
effect with strong published evidence, the Krohn-Mueller-Whelan dollar drift around the daily fixes
(J. Finance 79(1) 2024), is not present in our 2025-26 sample either (pooled t = -0.39), which matches the
paper's own finding that it decayed after 2013.

So the lever that moves money here is not a better entry. It is paying less to get in. Every rule in this
file exists to cut the cost of a trade the engine was going to take anyway; none of them tries to predict
where price goes, and none of them refuses a setup for being "low quality".

David's constraints are kept exactly: every valid setup is taken, there is no cap on trades or on open
positions, and every order is the minimum lot.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Dict, Optional, Tuple

from .config import DATA_DIR

COST_FILE = os.path.join(DATA_DIR, "symbol_cost.json")

P = {
    # a symbol is worth trading at all only if its spread is a small part of the move it is trying to catch.
    # Measured median spread / ATR(14, M15) over the whole history: gold and the 8 cheap majors sit at
    # 0.02-0.05, the dear crosses at 0.09-0.14, and EVERY crypto CFD at 0.31 or worse (TRUMP: 284).
    "MAX_SPREAD_ATR": 0.10,
    # the live spread must also be near that symbol's own normal. This is what keeps the engine out of the
    # 21:00-23:00 rollover, where the recorded spread runs 5-27x the median on the crosses.
    "MAX_SPREAD_X_MEDIAN": 1.5,
    # the target has to be worth the toll: cost is one spread, so a target under 10 spreads means the
    # spread is over 10% of everything the trade can win.
    "MIN_TARGET_SPREAD_X": 10.0,
    # no entry inside the rollover window (UTC), where spreads blow out and the swap is charged
    "ROLLOVER_UTC": ("20:45", "22:15"),
    # a 0.01-lot overnight hold costs more than the trade can make on the dear side: gold long -$0.58..0.96
    # a night, USDJPY short -$0.28, every crypto 20%/yr. Flatten before the swap instead of paying it.
    "FLAT_BEFORE_SWAP_UTC": "20:45",
    "NO_OVERNIGHT": True,
    # the one guard that is NOT a trade cap (David: no limit): keep the account clear of the 50% stop-out
    # even if every open stop is hit at once. Free margin floor, not a position count.
    "MIN_FREE_MARGIN_PCT": 30.0,
    # a long and a short on one symbol pay the spread twice for zero net exposure
    "NO_OPPOSING_SAME_SYMBOL": True,
}


def _hhmm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def load_costs() -> Dict[str, Dict]:
    try:
        with open(COST_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def in_rollover(now_ms: int) -> bool:
    t = _dt.datetime.fromtimestamp(now_ms / 1000, _dt.timezone.utc)
    mins = t.hour * 60 + t.minute
    a, b = (_hhmm(x) for x in P["ROLLOVER_UTC"])
    return a <= mins < b if a < b else (mins >= a or mins < b)


def minutes_to_swap(now_ms: int) -> int:
    """minutes until the swap cut-off (used to refuse a trade that cannot finish before it)."""
    t = _dt.datetime.fromtimestamp(now_ms / 1000, _dt.timezone.utc)
    mins = t.hour * 60 + t.minute
    cut = _hhmm(P["FLAT_BEFORE_SWAP_UTC"])
    return (cut - mins) if mins <= cut else (cut + 24 * 60 - mins)


def cost_gate(symbol: str, market: str, spread: float, atr: Optional[float],
              target_dist: Optional[float], now_ms: int, hold_minutes: Optional[int] = None,
              costs: Optional[Dict] = None) -> Tuple[bool, str, Dict]:
    """G9. True = the trade is cheap enough to be worth taking. Never judges direction."""
    costs = load_costs() if costs is None else costs
    c = costs.get(symbol) or {}
    med = c.get("median_spread")
    ratio = c.get("spread_atr")
    val = {"spread": spread, "median_spread": med, "spread_atr_hist": ratio}
    fails = []

    if ratio is not None and ratio > P["MAX_SPREAD_ATR"]:
        fails.append(f"{symbol} costs {ratio:.0%} of an ATR to trade (limit {P['MAX_SPREAD_ATR']:.0%})")
    if atr and atr > 0:
        live = spread / atr
        val["spread_atr_live"] = round(live, 4)
        if live > P["MAX_SPREAD_ATR"]:
            fails.append(f"spread is {live:.0%} of ATR now (limit {P['MAX_SPREAD_ATR']:.0%})")
    if med and med > 0 and spread > P["MAX_SPREAD_X_MEDIAN"] * med:
        fails.append(f"spread {spread:g} is {spread / med:.1f}x its usual {med:g}")
    if target_dist and spread > 0:
        x = abs(target_dist) / spread          # a distance, never a direction
        val["target_spread_x"] = round(x, 1)
        if x < P["MIN_TARGET_SPREAD_X"]:
            fails.append(f"target is only {x:.1f} spreads away (need {P['MIN_TARGET_SPREAD_X']:g})")
    if in_rollover(now_ms):
        fails.append("inside the rollover window")
    if P["NO_OVERNIGHT"] and hold_minutes:
        left = minutes_to_swap(now_ms)
        val["minutes_to_swap"] = left
        if hold_minutes > left:
            fails.append(f"a {hold_minutes} min hold runs past the {P['FLAT_BEFORE_SWAP_UTC']} UTC swap cut-off ({left} min left)")
    return (not fails), "; ".join(fails), val


def build_costs(tf: str = "M15") -> Dict[str, Dict]:
    """median spread, and spread as a share of ATR(14), per symbol from engine_data/history -> symbol_cost.json."""
    import numpy as np
    from .history import HIST_DIR
    out = {}
    for fn in sorted(os.listdir(HIST_DIR)):
        if not fn.endswith(".json"):
            continue
        sym = fn[:-5]
        try:
            with open(os.path.join(HIST_DIR, fn)) as f:
                d = json.load(f)
            rows = d["bars"].get(tf) or []
            if len(rows) < 500:
                continue
            a = np.array([r[:6] for r in rows], dtype=float)
            h, l, c, sp = a[:, 2], a[:, 3], a[:, 4], a[:, 5]
            pc = np.concatenate(([c[0]], c[:-1]))
            tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
            atr = np.convolve(tr, np.ones(14) / 14, mode="valid")
            med_sp = float(np.nanmedian(sp))
            med_atr = float(np.nanmedian(atr))
            if not med_atr:
                continue
            out[sym] = {"market": d.get("market"), "median_spread": med_sp,
                        "median_atr": med_atr, "spread_atr": round(med_sp / med_atr, 4),
                        "tradeable": bool(med_sp / med_atr <= P["MAX_SPREAD_ATR"])}
        except Exception:
            continue
    tmp = COST_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    os.replace(tmp, COST_FILE)
    return out


if __name__ == "__main__":
    t = build_costs()
    ok = sorted(s for s, v in t.items() if v["tradeable"])
    no = sorted(s for s, v in t.items() if not v["tradeable"])
    print(f"{len(t)} symbols -> {COST_FILE}")
    print(f"tradeable ({len(ok)}): {', '.join(ok)}")
    print(f"too dear  ({len(no)}): {', '.join(no)}")
