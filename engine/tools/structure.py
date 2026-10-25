"""
tools/structure.py — swing points and market structure.

No look-ahead: a swing high at bar i needs `right` lower bars after it, so it only
exists from bar i + right on ("confirmed"). Structure, sweeps and liquidity pools
use a swing only from its confirmed bar, as a live engine would see it.

  swing_points   fractal swing highs / lows
  label_swings   HH / HL / LH / LL against the previous swing of the same kind
  trend          up / down / range from the last two swing highs and lows
  market_structure  BOS (break with the trend) and CHoCH (break against it) on closes
  equal_levels   liquidity pools: two or more swing highs (lows) at about one price, not taken yet
  sweeps         a wick through a swing level that closes back inside (stop hunt)
  dealing_range  the current swing range: premium / discount / equilibrium and OTE bands
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .bars import Bar


def swing_points(bars: List[Bar], left: int = 2, right: int = 2) -> List[Dict]:
    """A swing high is above the `left` bars before it and not below the `right` bars after it
    (mirrored for lows). Each: {kind: high|low, idx, t, price, confirmed: idx + right}."""
    out: List[Dict] = []
    for i in range(left, len(bars) - right):
        hi, lo = bars[i]["h"], bars[i]["l"]
        if all(bars[j]["h"] < hi for j in range(i - left, i)) and all(bars[j]["h"] <= hi for j in range(i + 1, i + right + 1)):
            out.append({"kind": "high", "idx": i, "t": bars[i]["t"], "price": hi, "confirmed": i + right})
        if all(bars[j]["l"] > lo for j in range(i - left, i)) and all(bars[j]["l"] >= lo for j in range(i + 1, i + right + 1)):
            out.append({"kind": "low", "idx": i, "t": bars[i]["t"], "price": lo, "confirmed": i + right})
    return out


def label_swings(swings: List[Dict]) -> List[Dict]:
    """Adds label HH / LH to highs and HL / LL to lows (the first of each kind: H / L)."""
    last = {"high": None, "low": None}
    for s in swings:
        p = last[s["kind"]]
        if s["kind"] == "high":
            s["label"] = "H" if p is None else "HH" if s["price"] > p else "LH"
        else:
            s["label"] = "L" if p is None else "HL" if s["price"] > p else "LL"
        last[s["kind"]] = s["price"]
    return swings


def trend(swings: List[Dict]) -> Optional[str]:
    """up = higher high and higher low, down = lower high and lower low, range = mixed."""
    hs = [s for s in swings if s["kind"] == "high"][-2:]
    ls = [s for s in swings if s["kind"] == "low"][-2:]
    if len(hs) < 2 or len(ls) < 2:
        return None
    hh, hl = hs[1]["price"] > hs[0]["price"], ls[1]["price"] > ls[0]["price"]
    return "up" if hh and hl else "down" if not hh and not hl else "range"


def market_structure(bars: List[Bar], swings: List[Dict]) -> Dict:
    """Walk the closes against the latest confirmed, unbroken swing high and low. A close
    beyond one is a break: BOS when it goes the way of the current bias, CHoCH when it
    flips it (the first one sets the bias and counts as a CHoCH).
    → {bias: up|down|None, events: [{kind, dir, level, idx, t, swing_idx, swing_t}],
       last_high, last_low (the swings still unbroken)}"""
    by_conf: Dict[int, List[Dict]] = {}
    for s in swings:
        by_conf.setdefault(s["confirmed"], []).append(s)
    events: List[Dict] = []
    bias: Optional[str] = None
    hi: Optional[Dict] = None
    lo: Optional[Dict] = None
    for i, b in enumerate(bars):
        if hi and b["c"] > hi["price"]:
            events.append({"kind": "BOS" if bias == "up" else "CHoCH", "dir": "up", "level": hi["price"], "idx": i,
                           "t": b["t"], "swing_idx": hi["idx"], "swing_t": hi["t"]})
            bias, hi = "up", None
        elif lo and b["c"] < lo["price"]:
            events.append({"kind": "BOS" if bias == "down" else "CHoCH", "dir": "down", "level": lo["price"], "idx": i,
                           "t": b["t"], "swing_idx": lo["idx"], "swing_t": lo["t"]})
            bias, lo = "down", None
        for s in by_conf.get(i, []):
            if s["kind"] == "high":
                hi = s
            else:
                lo = s
    return {"bias": bias, "events": events, "last_high": hi, "last_low": lo}


def equal_levels(bars: List[Bar], swings: List[Dict], tol: float) -> List[Dict]:
    """Liquidity pools: two or more swing highs (lows) within `tol` of each other (a price
    distance, e.g. 0.1 × ATR) that no later bar has traded through yet. Stops rest beyond them.
    → [{kind: equal_highs|equal_lows, price (the outermost), touches, t (last touch)}]"""
    out: List[Dict] = []
    for kind, name in (("high", "equal_highs"), ("low", "equal_lows")):
        pts = sorted((s for s in swings if s["kind"] == kind), key=lambda s: s["price"])
        group: List[Dict] = []
        groups: List[List[Dict]] = []
        for s in pts:
            if group and s["price"] - group[0]["price"] > tol:
                groups.append(group)
                group = []
            group.append(s)
        if group:
            groups.append(group)
        for g in groups:
            if len(g) < 2:
                continue
            price = max(s["price"] for s in g) if kind == "high" else min(s["price"] for s in g)
            after = max(s["idx"] for s in g) + 1
            taken = any((b["h"] > price) if kind == "high" else (b["l"] < price) for b in bars[after:])
            if not taken:
                out.append({"kind": name, "price": price, "touches": len(g), "t": max(s["t"] for s in g)})
    return out


def sweeps(bars: List[Bar], swings: List[Dict]) -> List[Dict]:
    """A bar that trades through a confirmed swing level but closes back inside: a stop hunt.
    Each swing counts once; a close beyond it is a break, not a sweep, and ends it.
    → [{side: high|low (which side's liquidity was taken), level, idx, t, swing_t}]"""
    out: List[Dict] = []
    live: List[Dict] = []
    by_conf: Dict[int, List[Dict]] = {}
    for s in swings:
        by_conf.setdefault(s["confirmed"], []).append(s)
    for i, b in enumerate(bars):
        keep = []
        for s in live:
            p = s["price"]
            if s["kind"] == "high" and b["h"] > p:
                if b["c"] < p:
                    out.append({"side": "high", "level": p, "idx": i, "t": b["t"], "swing_t": s["t"]})
                continue
            if s["kind"] == "low" and b["l"] < p:
                if b["c"] > p:
                    out.append({"side": "low", "level": p, "idx": i, "t": b["t"], "swing_t": s["t"]})
                continue
            keep.append(s)
        live = keep + by_conf.get(i, [])
    return out


def dealing_range(bars: List[Bar], struct: Dict) -> Optional[Dict]:
    """The range between the latest unbroken swing high and low (or the window's extremes).
    position: where the last close sits, 0 = at the low, 1 = at the high. Above 0.5 is
    premium (better for selling), below is discount (better for buying). OTE = the
    0.62–0.79 retracement: for a long, measured down from the high; for a short, up from the low."""
    if not bars:
        return None
    hi = struct["last_high"]["price"] if struct.get("last_high") else max(b["h"] for b in bars)
    lo = struct["last_low"]["price"] if struct.get("last_low") else min(b["l"] for b in bars)
    if hi <= lo:
        return None
    r = hi - lo
    pos = (bars[-1]["c"] - lo) / r
    return {"high": hi, "low": lo, "eq": lo + r / 2, "position": pos,
            "zone": "premium" if pos > 0.55 else "discount" if pos < 0.45 else "equilibrium",
            "ote_long": (hi - 0.79 * r, hi - 0.62 * r), "ote_short": (lo + 0.62 * r, lo + 0.79 * r)}
