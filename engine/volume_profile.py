"""
engine/volume_profile.py — row 7 of the /smc concept table: volume profile, POC, value area, HVN / LVN, naked POCs.
Researched 2026-10-29 by a Fable 5.1 agent (TradingView Volume Profile / Visible Range help, CQG's value area
note, LuxAlgo value-area / naked-POC / volume-node concept pages, Steidlmayer's CBOT two-row method).

  rows       fixed in PRICE, so a price always lands in the same row: ≈ 1 / 10,000 of the price rounded to
             1-2-5 (GOLD 0.5 $, EURUSD 1 pip, USDJPY 0.01) on M5 / M15, twice that on M30+; doubled / halved until
             the profile has 24–200 rows.
  volume     each bar's MT5 tick volume spread evenly over the rows its high–low covers (LuxAlgo; TradingView
             does the same with lower-timeframe bars). Bars without volume (files saved before 2026-10-29) count
             1 each: then it is a TIME-at-price profile (TPO-like), and says so.
  POC        the row with the most volume (tie: the one nearest the range's middle, then the lower).
  value area 70 % of the volume, grown from the POC by the CBOT two-row step: compare the two rows above with the
             two below, add the bigger pair (tie: the upper), until ≥ 70 %. VAH / VAL = its top / bottom.
  HVN / LVN  a row above (below) the 3 rows on each side; HVN ≥ 1.5 × the mean row, LVN ≤ 0.5 × the mean row and
             ≥ 10 % of the POC (the empty tails are no nodes).
  naked POC  a finished day's POC no later bar has traded through (tested = a later bar's low ≤ POC ≤ high;
             accepted = a close on the far side of it from where that day closed).
  profiles   each FxPro server day (the last 5 finished + today developing — a developing POC moves, only the
             finished days' are levels) and the major leg (protected swing → now).

    profiles(bars, m, tf) -> {"volume": bool, "row": float, "days": [...], "leg": {...} | None}
"""
from __future__ import annotations

import datetime as _dt
import math
from typing import Dict, List, Optional

from .smc_marks import SERVER_TZ

VALUE_AREA, NODE_N, HVN_X, LVN_X, LVN_MIN_POC = 0.70, 3, 1.5, 0.5, 0.10
ROWS_MIN, ROWS_MAX, DAYS = 24, 200, 5


def row_size(bars: List[Dict], tf: str) -> float:
    closes = sorted(b["c"] for b in bars)
    raw = closes[len(closes) // 2] * 1e-4
    e = math.floor(math.log10(raw))
    unit = min((k * 10 ** e for k in (1, 2, 5, 10)), key=lambda u: abs(math.log(u / raw)))
    return unit * (1 if tf in ("M5", "M15") else 2)


def _profile(bars: List[Dict], a: int, b: int, row: float, use_vol: bool) -> Optional[Dict]:
    lo, hi = min(bars[i]["l"] for i in range(a, b + 1)), max(bars[i]["h"] for i in range(a, b + 1))
    while (hi - lo) / row > ROWS_MAX:
        row *= 2
    while (hi - lo) / row < ROWS_MIN and row > 1e-9:
        row /= 2
    base = math.floor(lo / row + 1e-9)
    n = math.floor(hi / row + 1e-9) - base + 1
    V = [0.0] * n
    for i in range(a, b + 1):
        x = bars[i]
        v = (x.get("v") or 0.0) if use_vol else 1.0
        if v <= 0:
            continue
        r0, r1 = math.floor(x["l"] / row + 1e-9) - base, math.floor(x["h"] / row + 1e-9) - base
        if r0 == r1 or x["h"] == x["l"]:
            V[r0] += v
            continue
        span = x["h"] - x["l"]
        for r in range(r0, r1 + 1):                             # the overlap of the bar with row r
            top, bot = (base + r + 1) * row, (base + r) * row
            V[r] += v * (min(top, x["h"]) - max(bot, x["l"])) / span
    total = sum(V)
    if total <= 0:
        return None
    mid = (n - 1) / 2
    poc = max(range(n), key=lambda r: (V[r], -abs(r - mid), -r))
    top = bot = poc
    va = V[poc]
    while va < VALUE_AREA * total and (top < n - 1 or bot > 0):
        up = sum(V[r] for r in (top + 1, top + 2) if r < n)
        dn = sum(V[r] for r in (bot - 1, bot - 2) if r >= 0)
        if up >= dn and top < n - 1:
            k = min(2, n - 1 - top)
            va, top = va + up, top + k
        else:
            k = min(2, bot)
            va, bot = va + dn, bot - k
    mean = total / n
    peak = lambda r, f: all(f(V[r], V[j]) for j in range(r - NODE_N, r + NODE_N + 1) if j != r and 0 <= j < n)
    price = lambda r: (base + r + 0.5) * row
    hvn = [price(r) for r in range(n) if V[r] >= HVN_X * mean and r != poc and peak(r, lambda u, w: u > w)]
    lvn = [price(r) for r in range(n) if LVN_MIN_POC * V[poc] <= V[r] <= LVN_X * mean and peak(r, lambda u, w: u < w)]
    return {"from_idx": a, "to_idx": b, "row": row, "low": base * row, "rows": [round(v, 2) for v in V], "total": total,
            "poc": price(poc), "vah": (base + top + 1) * row, "val": (base + bot) * row, "hvn": hvn, "lvn": lvn}


def profiles(bars: List[Dict], m: Dict, tf: str) -> Dict:
    use_vol = any(b.get("v") for b in bars)
    out = {"volume": use_vol, "row": None, "days": [], "leg": None}
    if not bars:
        return out
    row = out["row"] = row_size(bars, tf)
    day = [_dt.datetime.fromtimestamp(b["t"] / 1000, SERVER_TZ).date() for b in bars]
    cuts = [0] + [i for i in range(1, len(bars)) if day[i] != day[i - 1]]
    spans = [(cuts[k], (cuts[k + 1] - 1) if k + 1 < len(cuts) else len(bars) - 1) for k in range(len(cuts))]
    for a, b in spans[1:][-(DAYS + 1):]:                        # the first day may be cut off by the bar window
        p = _profile(bars, a, b, row, use_vol)
        if not p:
            continue
        p["day"], p["developing"] = day[a].isoformat(), b == len(bars) - 1
        if not p["developing"]:
            poc, side = p["poc"], bars[b]["c"] >= p["poc"]
            p["tested_idx"] = next((i for i in range(b + 1, len(bars)) if bars[i]["l"] <= poc <= bars[i]["h"]), None)
            p["accepted_idx"] = next((i for i in range(b + 1, len(bars)) if (bars[i]["c"] < poc if side else bars[i]["c"] > poc)), None)
            p["naked"] = p["tested_idx"] is None
        out["days"].append(p)
    prot = m.get("protected")
    if prot and len(bars) - prot["idx"] >= 10:
        out["leg"] = _profile(bars, prot["idx"], len(bars) - 1, row, use_vol)
    return out
