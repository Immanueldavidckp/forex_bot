"""
tools/bars.py — the one data shape every tool takes, and the helpers around it.

A bar is a dict {"t": epoch milliseconds of the bar's start, "o", "h", "l", "c", "v"};
a series is a list of bars, oldest first. Nothing here knows which market the bars
came from: where sessions matter (days, resampling, VWAP) the caller passes the
market's timezone and session start.
"""
from __future__ import annotations

import datetime as _dt
from typing import Dict, List, Optional

Bar = Dict[str, float]


# ── time ────────────────────────────────────────────────────────────────────

def to_dt(ms: int, tz: _dt.tzinfo) -> _dt.datetime:
    return _dt.datetime.fromtimestamp(ms / 1000, tz)


def session_key(ms: int, tz: _dt.tzinfo) -> str:
    """The session (local calendar day) a bar belongs to, as YYYY-MM-DD."""
    return to_dt(ms, tz).strftime("%Y-%m-%d")


def split_sessions(bars: List[Bar], tz: _dt.tzinfo) -> Dict[str, List[Bar]]:
    out: Dict[str, List[Bar]] = {}
    for b in bars:
        out.setdefault(session_key(b["t"], tz), []).append(b)
    return out


def _fixed_offset(tz: _dt.tzinfo) -> Optional[int]:
    """Seconds east of UTC for a fixed-offset zone, None for one with DST (zoneinfo)."""
    off = tz.utcoffset(None)
    return int(off.total_seconds()) if off is not None else None


def resample(bars: List[Bar], minutes: int, tz: _dt.tzinfo, anchor: _dt.time = _dt.time(0, 0)) -> List[Bar]:
    """N-minute bars from finer ones. Buckets count from `anchor` (local time) each day,
    so a session that opens at 09:15 gets 09:15, 09:20, ... rather than clock-aligned
    bars. Highs/lows extend, the close is the last close, volume adds up."""
    a, step = anchor.hour * 3600 + anchor.minute * 60, minutes * 60
    fixed = _fixed_offset(tz)
    out: List[Bar] = []
    cur: Optional[Bar] = None
    cur_key = None
    for b in bars:
        off = fixed if fixed is not None else int(to_dt(b["t"], tz).utcoffset().total_seconds())
        loc = b["t"] // 1000 + off
        day = loc // 86400
        key = (day, (loc % 86400 - a) // step)
        if key != cur_key:
            if cur:
                out.append(cur)
            start = day * 86400 + a + key[1] * step - off
            cur = {"t": start * 1000, "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]}
            cur_key = key
        else:
            cur["h"] = max(cur["h"], b["h"])
            cur["l"] = min(cur["l"], b["l"])
            cur["c"] = b["c"]
            cur["v"] += b["v"]
    if cur:
        out.append(cur)
    return out


# ── one candle ──────────────────────────────────────────────────────────────

def body(b: Bar) -> float:
    return abs(b["c"] - b["o"])


def span(b: Bar) -> float:
    return b["h"] - b["l"]


def upper_wick(b: Bar) -> float:
    return b["h"] - max(b["o"], b["c"])


def lower_wick(b: Bar) -> float:
    return min(b["o"], b["c"]) - b["l"]


def is_up(b: Bar) -> bool:
    return b["c"] > b["o"]


def is_down(b: Bar) -> bool:
    return b["c"] < b["o"]


def close_position(b: Bar) -> float:
    """Where the close sits in the bar's range: 0 = at the low, 1 = at the high."""
    r = span(b)
    return (b["c"] - b["l"]) / r if r > 0 else 0.5
