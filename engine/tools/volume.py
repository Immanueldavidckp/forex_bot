"""
tools/volume.py — where the volume traded.

  volume_profile   POC (the price with the most volume) and the value area (VAH / VAL)
  volume_curve     the average cumulative volume by time of day over past sessions
  relative_volume  today's volume so far against that curve
"""
from __future__ import annotations

import datetime as _dt
import math
from typing import Dict, List, Optional

from .bars import Bar, split_sessions, to_dt


def volume_profile(bars: List[Bar], bins: int = 24, value_area: float = 0.70) -> Optional[Dict]:
    """Each bar's volume spread evenly over its range, in `bins` price buckets.
    → {poc, vah, val, low, high}; the value area holds `value_area` of the volume around the POC."""
    if not bars:
        return None
    lo, hi = min(b["l"] for b in bars), max(b["h"] for b in bars)
    if hi <= lo:
        return {"poc": lo, "vah": hi, "val": lo, "low": lo, "high": hi}
    step = (hi - lo) / bins
    vol = [0.0] * bins
    for b in bars:
        a = min(bins - 1, int((b["l"] - lo) / step))
        z = max(a, min(bins - 1, math.ceil((b["h"] - lo) / step) - 1))      # a high on a bin edge stays below it
        share = b["v"] / (z - a + 1)
        for k in range(a, z + 1):
            vol[k] += share
    poc = max(range(bins), key=lambda k: vol[k])
    total, inside = sum(vol), vol[poc]
    a = z = poc
    while total and inside < value_area * total and (a > 0 or z < bins - 1):
        down = vol[a - 1] if a > 0 else -1.0
        up = vol[z + 1] if z < bins - 1 else -1.0
        if up >= down:
            z += 1
            inside += vol[z]
        else:
            a -= 1
            inside += vol[a]
    mid = lambda k: lo + (k + 0.5) * step  # noqa: E731
    return {"poc": mid(poc), "vah": lo + (z + 1) * step, "val": lo + a * step, "low": lo, "high": hi}


def volume_curve(bars: List[Bar], tz: _dt.tzinfo, bar_minutes: int, sessions: int = 10) -> Dict[int, float]:
    """Average cumulative volume traded by the END of each bar, keyed by minute of the day,
    over the last `sessions` sessions of `bars` (bars of bar_minutes each)."""
    days = split_sessions(bars, tz)
    curves = []
    for d in sorted(days)[-sessions:]:
        cum, cur = 0, {}
        for b in days[d]:
            cum += b["v"]
            t = to_dt(b["t"], tz)
            cur[t.hour * 60 + t.minute + bar_minutes] = cum
        curves.append(cur)
    out: Dict[int, float] = {}
    for m in sorted({k for c in curves for k in c}):
        vals = [c[m] for c in curves if m in c]
        out[m] = sum(vals) / len(vals)
    return out


def relative_volume(volume_so_far: float, curve: Dict[int, float], minute_of_day: int) -> Optional[float]:
    """Today's cumulative volume against the usual cumulative volume by that minute."""
    base = curve.get(minute_of_day)
    return volume_so_far / base if base else None
