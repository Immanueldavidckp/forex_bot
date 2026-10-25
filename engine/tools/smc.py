"""
tools/smc.py — Smart Money Concepts zones: fair value gaps, order blocks, breakers.

  fair_value_gaps  3-bar imbalance, with how much of it has been filled since
  order_blocks     the last opposite candle before the leg that broke structure,
                   with its state: fresh (untouched), tested (traded into) or broken
                   (closed through: it becomes a breaker block, acting the other way)
  displacement     bars whose body is large against the ATR: the moves that leave FVGs and OBs

Zones are {kind: bull|bear, top, bottom, idx, t, ...}; a bull zone is support below price,
a bear zone resistance above it.
"""
from __future__ import annotations

from typing import Dict, List

from .bars import Bar, body, is_down, is_up


def fair_value_gaps(bars: List[Bar], min_size: float = 0.0) -> List[Dict]:
    """Bull FVG: bar i+1's low above bar i−1's high (the gap between them was never traded).
    Bear FVG: bar i+1's high below bar i−1's low. min_size drops small gaps (a price distance).
    fill: 0 = untouched … 1 = traded through. state: open | partial | filled, or inverted
    once a bar closes beyond the far side (the gap then works the other way)."""
    out: List[Dict] = []
    for i in range(1, len(bars) - 1):
        a, c = bars[i - 1], bars[i + 1]
        if c["l"] > a["h"]:
            kind, top, bottom = "bull", c["l"], a["h"]
        elif c["h"] < a["l"]:
            kind, top, bottom = "bear", a["l"], c["h"]
        else:
            continue
        if top - bottom < min_size or top <= bottom:
            continue
        fill, state = 0.0, "open"
        for b in bars[i + 2:]:
            if kind == "bull":
                fill = max(fill, min(1.0, (top - b["l"]) / (top - bottom)))
                if b["c"] < bottom:
                    state = "inverted"
                    break
            else:
                fill = max(fill, min(1.0, (b["h"] - bottom) / (top - bottom)))
                if b["c"] > top:
                    state = "inverted"
                    break
        if state != "inverted":
            state = "filled" if fill >= 1.0 else "partial" if fill > 0 else "open"
        out.append({"kind": kind, "top": top, "bottom": bottom, "idx": i, "t": bars[i]["t"],
                    "fill": round(max(fill, 0.0), 3), "state": state})
    return out


def order_blocks(bars: List[Bar], events: List[Dict], max_back: int = 30) -> List[Dict]:
    """For every structure break (structure.market_structure()["events"]): the leg that broke it
    starts at the lowest low (bullish) / highest high (bearish) between the broken swing and
    the break; the order block is the last opposite-colour candle at or before that point
    (within max_back bars). Zone = that candle's high..low.
    state after the break: fresh, tested (a later bar traded into it), broken (a later close
    beyond the far side; breaker=True, and it now works the other way)."""
    out: List[Dict] = []
    seen = set()
    for ev in events:
        bi, si = ev["idx"], ev.get("swing_idx", max(0, ev["idx"] - max_back))
        lo_i = max(0, min(si, bi - 1))
        seg = range(lo_i, bi)
        if not seg:
            continue
        if ev["dir"] == "up":
            k = min(seg, key=lambda j: bars[j]["l"])
            pick = next((j for j in range(k, max(-1, k - max_back), -1) if is_down(bars[j])), None)
            kind = "bull"
        else:
            k = max(seg, key=lambda j: bars[j]["h"])
            pick = next((j for j in range(k, max(-1, k - max_back), -1) if is_up(bars[j])), None)
            kind = "bear"
        if pick is None or (kind, pick) in seen:
            continue
        seen.add((kind, pick))
        top, bottom = bars[pick]["h"], bars[pick]["l"]
        state = "fresh"
        for b in bars[bi + 1:]:
            if kind == "bull":
                if b["c"] < bottom:
                    state = "broken"
                    break
                if b["l"] <= top:
                    state = "tested"
            else:
                if b["c"] > top:
                    state = "broken"
                    break
                if b["h"] >= bottom:
                    state = "tested"
        out.append({"kind": kind, "top": top, "bottom": bottom, "idx": pick, "t": bars[pick]["t"],
                    "event": ev["kind"], "event_t": ev["t"], "state": state, "breaker": state == "broken"})
    return out


def displacement(bars: List[Bar], atr: float, mult: float = 1.5) -> List[int]:
    """Indexes of bars whose body is at least mult × ATR."""
    if not atr:
        return []
    return [i for i, b in enumerate(bars) if body(b) >= mult * atr]
