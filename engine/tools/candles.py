"""
tools/candles.py — candlestick patterns on the last bar (or any bar i).

patterns(bars) → e.g. ["bull_engulfing", "hammer"]. Names: doji, hammer, shooting_star,
bull_engulfing, bear_engulfing, inside_bar, outside_bar, bull_marubozu, bear_marubozu,
morning_star, evening_star.
"""
from __future__ import annotations

from typing import List

from .bars import Bar, body, is_down, is_up, lower_wick, span, upper_wick


def patterns(bars: List[Bar], i: int = -1) -> List[str]:
    if not bars:
        return []
    i = i % len(bars)
    b = bars[i]
    r = span(b)
    out: List[str] = []
    if r <= 0:
        return out
    if body(b) <= 0.1 * r:
        out.append("doji")
    if lower_wick(b) >= 2 * body(b) and lower_wick(b) >= 0.6 * r and upper_wick(b) <= 0.25 * r:
        out.append("hammer")
    if upper_wick(b) >= 2 * body(b) and upper_wick(b) >= 0.6 * r and lower_wick(b) <= 0.25 * r:
        out.append("shooting_star")
    if body(b) >= 0.9 * r:
        out.append("bull_marubozu" if is_up(b) else "bear_marubozu")
    if i >= 1:
        p = bars[i - 1]
        if is_down(p) and is_up(b) and b["o"] <= p["c"] and b["c"] >= p["o"] and body(b) > body(p):
            out.append("bull_engulfing")
        if is_up(p) and is_down(b) and b["o"] >= p["c"] and b["c"] <= p["o"] and body(b) > body(p):
            out.append("bear_engulfing")
        if b["h"] < p["h"] and b["l"] > p["l"]:
            out.append("inside_bar")
        if b["h"] > p["h"] and b["l"] < p["l"]:
            out.append("outside_bar")
    if i >= 2:
        a, m = bars[i - 2], bars[i - 1]
        small = body(m) <= 0.3 * body(a) if body(a) else False
        if is_down(a) and small and is_up(b) and b["c"] > (a["o"] + a["c"]) / 2:
            out.append("morning_star")
        if is_up(a) and small and is_down(b) and b["c"] < (a["o"] + a["c"]) / 2:
            out.append("evening_star")
    return out
