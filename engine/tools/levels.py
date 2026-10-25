"""
tools/levels.py — price levels a stop or a target can lean on.

  prior_session   the last completed session's high / low / close (from daily bars)
  prior_week      the last completed week's high / low / close
  opening_range   high / low of a session's first N minutes
  pivots          classic, camarilla or fibonacci floor pivots from a high / low / close
  fib_levels      retracements of a leg
  sr_zones        support / resistance: swing points clustered by price, with touch counts
  nearest         the closest named level above and below a price
"""
from __future__ import annotations

import datetime as _dt
from typing import Dict, List, Optional, Sequence, Tuple

from .bars import Bar, session_key, to_dt


def prior_session(daily: List[Bar], before: str, tz: _dt.tzinfo) -> Optional[Dict]:
    """High / low / close / open of the last daily bar strictly before session `before` (YYYY-MM-DD)."""
    prior = [b for b in daily if session_key(b["t"], tz) < before]
    if not prior:
        return None
    p = prior[-1]
    return {"high": p["h"], "low": p["l"], "close": p["c"], "open": p["o"], "date": session_key(p["t"], tz)}


def prior_week(daily: List[Bar], before: str, tz: _dt.tzinfo) -> Optional[Dict]:
    """High / low / close of the last full ISO week before the week of session `before`."""
    this = _dt.date.fromisoformat(before).isocalendar()[:2]
    weeks: Dict[Tuple[int, int], List[Bar]] = {}
    for b in daily:
        wk = to_dt(b["t"], tz).date().isocalendar()[:2]
        if wk < this:
            weeks.setdefault(wk, []).append(b)
    if not weeks:
        return None
    bs = weeks[max(weeks)]
    return {"high": max(b["h"] for b in bs), "low": min(b["l"] for b in bs), "close": bs[-1]["c"]}


def opening_range(session: List[Bar], minutes: int) -> Optional[Tuple[float, float]]:
    """(high, low) of the bars that start within the first `minutes` of the session, once
    that window is complete (a later bar exists); None before that."""
    if not session:
        return None
    cut = session[0]["t"] + minutes * 60_000
    first = [b for b in session if b["t"] < cut]
    if len(first) == len(session):
        return None
    return max(b["h"] for b in first), min(b["l"] for b in first)


def pivots(high: float, low: float, close: float, method: str = "classic") -> Dict[str, float]:
    """Floor pivots for the next session from this one's high / low / close."""
    r = high - low
    if method == "camarilla":
        return {"R4": close + r * 1.1 / 2, "R3": close + r * 1.1 / 4, "R2": close + r * 1.1 / 6, "R1": close + r * 1.1 / 12,
                "S1": close - r * 1.1 / 12, "S2": close - r * 1.1 / 6, "S3": close - r * 1.1 / 4, "S4": close - r * 1.1 / 2}
    p = (high + low + close) / 3.0
    if method == "fibonacci":
        return {"P": p, "R1": p + 0.382 * r, "R2": p + 0.618 * r, "R3": p + r,
                "S1": p - 0.382 * r, "S2": p - 0.618 * r, "S3": p - r}
    return {"P": p, "R1": 2 * p - low, "R2": p + r, "R3": high + 2 * (p - low),
            "S1": 2 * p - high, "S2": p - r, "S3": low - 2 * (high - p)}


def fib_levels(low: float, high: float, up: bool = True,
               ratios: Sequence[float] = (0.236, 0.382, 0.5, 0.618, 0.705, 0.786)) -> Dict[str, float]:
    """Retracements of the leg low → high (up=True: measured down from the high) or high → low."""
    r = high - low
    return {f"{x:g}": (high - x * r) if up else (low + x * r) for x in ratios}


def sr_zones(swings: List[Dict], tol: float, min_touches: int = 2) -> List[Dict]:
    """Swing highs and lows clustered by price (within `tol`, a price distance): a level that
    turned price several times. → [{price (mean), low, high, touches, last_t}], most touched first."""
    pts = sorted(swings, key=lambda s: s["price"])
    out: List[Dict] = []
    group: List[Dict] = []

    def flush():
        if len(group) >= min_touches:
            ps = [s["price"] for s in group]
            out.append({"price": sum(ps) / len(ps), "low": min(ps), "high": max(ps), "touches": len(group),
                        "last_t": max(s["t"] for s in group)})
    for s in pts:
        if group and s["price"] - group[0]["price"] > tol:
            flush()
            group = []
        group.append(s)
    flush()
    return sorted(out, key=lambda z: (-z["touches"], -z["last_t"]))


def nearest(levels: Sequence[Tuple[str, Optional[float]]], price: float) -> Tuple[Optional[Tuple[str, float]], Optional[Tuple[str, float]]]:
    """(closest level above, closest level below) price, each as (name, price); None if there is none."""
    xs = [(n, float(x)) for n, x in levels if x]
    up = min((v for v in xs if v[1] > price), key=lambda v: v[1], default=None)
    dn = max((v for v in xs if v[1] < price), key=lambda v: v[1], default=None)
    return up, dn
