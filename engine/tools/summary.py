"""
tools/summary.py — every tool on one series, boiled down to what matters at the last bar.

  read(bars)       a compact dict: trend, the last BOS/CHoCH, recent swings, the nearest
                   unfilled FVGs, live order blocks and breakers, liquidity pools, the last
                   sweep, premium/discount, and the last bar's candle patterns
  brief(r, ...)    the same in one short line (for a table with one stock per line)

Distances ("dist") are from the last close to the zone's nearest edge, in ATRs
(0 = price is inside the zone).
"""
from __future__ import annotations

import datetime as _dt
from typing import Dict, List, Optional

from . import candles, indicators, smc, structure
from .bars import Bar, to_dt


def _fmt_t(t: int, last_t: int, tz: Optional[_dt.tzinfo]):
    if tz is None:
        return t
    d, last = to_dt(t, tz), to_dt(last_t, tz)
    return d.strftime("%H:%M") if d.date() == last.date() else d.strftime("%d %b %H:%M")


def _zone_dist(z: Dict, price: float, atr: float) -> float:
    gap = z["bottom"] - price if price < z["bottom"] else price - z["top"] if price > z["top"] else 0.0
    return round(gap / atr, 2) if atr else 0.0


def read(bars: List[Bar], atr: Optional[float] = None, tz: Optional[_dt.tzinfo] = None,
         left: int = 2, right: int = 2, recent: int = 24, max_zones: int = 3) -> Dict:
    """`atr` sizes the filters and distances (default: the series' own ATR14); `tz` turns
    times into HH:MM; `recent` = how many bars back a sweep still counts as recent."""
    if len(bars) < left + right + 3:
        return {}
    price, last_t = bars[-1]["c"], bars[-1]["t"]
    a = atr or indicators.atr(bars, 14) or 0.0
    sw = structure.label_swings(structure.swing_points(bars, left, right))
    st = structure.market_structure(bars, sw)
    fvgs = [g for g in smc.fair_value_gaps(bars, 0.05 * a) if g["state"] in ("open", "partial")]
    obs = smc.order_blocks(bars, st["events"])
    live = [o for o in obs if o["state"] != "broken"]
    breakers = [{**o, "kind": "bear" if o["kind"] == "bull" else "bull"} for o in obs if o["breaker"]]
    pools = structure.equal_levels(bars, sw, 0.1 * a if a else price * 0.001)
    swept = [s for s in structure.sweeps(bars, sw) if s["idx"] >= len(bars) - recent]
    dr = structure.dealing_range(bars, st)
    t = lambda x: _fmt_t(x, last_t, tz)  # noqa: E731

    def zones(zs: List[Dict], extra: tuple) -> List[Dict]:
        rows = [{"kind": z["kind"], "top": round(z["top"], 2), "bottom": round(z["bottom"], 2), "t": t(z["t"]),
                 "dist": _zone_dist(z, price, a), **{k: z[k] for k in extra}} for z in zs]
        return sorted(rows, key=lambda z: z["dist"])[:max_zones]
    ev = st["events"][-1] if st["events"] else None
    return {
        "trend": structure.trend(sw), "bias": st["bias"],
        "last_break": {"kind": ev["kind"], "dir": ev["dir"], "level": round(ev["level"], 2), "t": t(ev["t"])} if ev else None,
        "swing_highs": [{"price": round(s["price"], 2), "label": s["label"], "t": t(s["t"])} for s in sw if s["kind"] == "high"][-3:],
        "swing_lows": [{"price": round(s["price"], 2), "label": s["label"], "t": t(s["t"])} for s in sw if s["kind"] == "low"][-3:],
        "fvgs": zones(fvgs, ("state", "fill")),
        "order_blocks": zones(live, ("state", "event")),
        "breakers": zones(breakers, ())[:2],
        "liquidity": sorted(({"kind": p["kind"], "price": round(p["price"], 2), "touches": p["touches"],
                              "dist": round(abs(p["price"] - price) / a, 2) if a else 0.0} for p in pools),
                            key=lambda p: p["dist"])[:2],
        "sweep": {"side": swept[-1]["side"], "level": round(swept[-1]["level"], 2), "t": t(swept[-1]["t"])} if swept else None,
        "range": {"zone": dr["zone"], "position": round(dr["position"], 2), "high": round(dr["high"], 2),
                  "low": round(dr["low"], 2)} if dr else None,
        "patterns": candles.patterns(bars),
    }


def brief(r: Dict, price: float) -> str:
    """One short line: trend and last break; nearest support zone below and resistance zone
    above (FVG / OB / breaker, with distance in ATRs); a recent sweep."""
    if not r:
        return "-"
    parts = [r.get("trend") or "-"]
    if r.get("last_break"):
        b = r["last_break"]
        parts[0] += f" {b['kind']} {b['dir']} {b['level']:g}"
    tagged = ([("FVG", z) for z in r.get("fvgs") or []] + [("OB", z) for z in r.get("order_blocks") or []]
              + [("BRK", z) for z in r.get("breakers") or []])
    sup = [(n, z) for n, z in tagged if z["kind"] == "bull" and z["bottom"] <= price]
    res = [(n, z) for n, z in tagged if z["kind"] == "bear" and z["top"] >= price]
    for side, zs in (("sup", sup), ("res", res)):
        if zs:
            n, z = min(zs, key=lambda v: v[1]["dist"])
            parts.append(f"{side} {n} {z['bottom']:g}-{z['top']:g} ({z['dist']:.2f})")
    if r.get("sweep"):
        parts.append(f"swept {r['sweep']['side']} {r['sweep']['level']:g}")
    return "; ".join(parts)
