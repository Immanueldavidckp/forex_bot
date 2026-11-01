"""
engine/major_structure.py — market structure the way David draws it (2026-10-28, his TradingView sketch: "the
internal BOS after the 1st CHOCH — we don't need those"). Only two levels exist at any time, so nothing
internal is ever marked:

  BOS level     the leg's extreme once a pullback has confirmed it (a swing of n bars each side AT the leg's
                high / low). A close beyond it = BOS. The low (high) the breaking move started from becomes
                the protected level.
  protected     the higher low (lower high) that produced the last BOS. A close beyond it = CHoCH: the trend
                turns, and the top (bottom) of the old trend — the extreme between the protected swing and the
                CHoCH candle — becomes the new protected level. Highs and lows made inside the pullback that
                follows are internal: they are never levels, so breaking them is no event. The next event is
                either a BOS of the new leg's extreme or a CHoCH back through that top.

Breaks are by candle CLOSE, and the close must clear the level by margin_atr × ATR(14) (a 0.4-pip poke through
is no break). Before the first break the trend is unknown: the first close beyond the latest confirmed swing
starts it (a BOS).

A leg's extreme becomes the BOS level only after a REAL pullback: an n-bar swing at the extreme AND price
coming back from it by pullback_atr × ATR(14). A few-pip bounce is internal, so its high / low never becomes a
level — that is what used to turn small bounces into BOS and the next rally into a false CHoCH (EURUSD M15
10-12 → 10-13, where David kept the trend down). A wick above the level without a close leaves the level where
it is (a sweep, not a break). Research behind both (2026-10-28, public SMC tools — LuxAlgo, TL Structure Pro,
MQL5 "Automating BOS and ChoCH"): breaks by close, sweeps are not breaks, majors need a valid pullback; the
ATR sizes are fitted to David's drawn lines (k 3: 2 does not fix the 10-12 case, 4 loses his GBPUSD H1 lines;
margin 0.25: 0.5 loses his 2-pip 09-28 break).

    major_structure(bars, n=5, pullback_atr=3.0, margin_atr=0.25) -> {trend, events, points, protected, bos_level}
        bars   [{t, o, h, l, c}, ...]
        events like strategy.structure's: kind BOS / CHoCH, side buy / sell, level, level_t, level_idx, t, idx,
               close, origin {price, t, idx} (where the breaking move started)
        points the zigzag of the structure (leg extremes and protected swings), oldest first
"""
from __future__ import annotations

from typing import Dict, List, Optional


def _pivot(bars: List[Dict], p: int, n: int, high: bool) -> bool:
    """bar p is a swing high (low): strictly beyond the n bars before it, not exceeded by the n bars after."""
    if p < n or p + n >= len(bars):
        return False
    v = bars[p]["h" if high else "l"]
    for k in range(1, n + 1):
        a, b = bars[p - k]["h" if high else "l"], bars[p + k]["h" if high else "l"]
        if (high and (a >= v or b > v)) or (not high and (a <= v or b < v)):
            return False
    return True


def atr14(bars: List[Dict]) -> List[float]:
    """mean true range of the last 14 bars, per bar"""
    out, tr = [], []
    for i, b in enumerate(bars):
        tr.append(b["h"] - b["l"] if i == 0 else max(b["h"] - b["l"], abs(b["h"] - bars[i - 1]["c"]), abs(b["l"] - bars[i - 1]["c"])))
        w = tr[-14:]
        out.append(sum(w) / len(w))
    return out


def major_structure(bars: List[Dict], n: int = 5, pullback_atr: float = 3.0, margin_atr: float = 0.25) -> Dict:
    A = atr14(bars)
    H = lambda i: bars[i]["h"]
    L = lambda i: bars[i]["l"]
    pt = lambda i, kind: {"price": H(i) if kind == "high" else L(i), "t": bars[i]["t"], "idx": i, "kind": kind}
    trend: Optional[str] = None
    prot: Optional[Dict] = None          # the CHoCH level
    level: Optional[Dict] = None         # the BOS level
    ext: Optional[int] = None            # the running extreme of the current leg
    pending: Optional[int] = None        # the leg's extreme, a confirmed swing, waiting for a deep enough pullback
    last = {"high": None, "low": None}   # before the first break: the latest confirmed swings
    events: List[Dict] = []
    points: List[Dict] = []

    def event(kind, side, lv, x, o):
        events.append({"kind": kind, "side": side, "level": lv["price"], "level_t": lv["t"], "level_idx": lv["idx"],
                       "t": bars[x]["t"], "idx": x, "close": bars[x]["c"],
                       "origin": {"price": H(o) if side == "sell" else L(o), "t": bars[o]["t"], "idx": o}})
        points.extend([lv, pt(o, "low" if side == "buy" else "high")])

    for x, b in enumerate(bars):
        c, mg = b["c"], margin_atr * A[x]
        if trend is None:
            for side, kind in (("buy", "high"), ("sell", "low")):
                lv = last[kind]
                if lv and (c > lv["price"] + mg if side == "buy" else c < lv["price"] - mg):
                    rng = range(lv["idx"], x + 1)
                    o = min(rng, key=L) if side == "buy" else max(rng, key=H)
                    event("BOS", side, lv, x, o)
                    trend, prot, level, ext, pending = side, pt(o, "low" if side == "buy" else "high"), None, x, None
                    break
        elif trend == "buy":
            if level and c > level["price"] + mg:
                o = min(range(level["idx"], x + 1), key=L)          # the higher low the break came from
                event("BOS", "buy", level, x, o)
                prot, level, ext, pending = pt(o, "low"), None, x, None
            elif c < prot["price"] - mg:
                o = max(range(prot["idx"], x + 1), key=H)          # the top of the old trend
                event("CHoCH", "sell", prot, x, o)
                trend, prot, level, pending = "sell", pt(o, "high"), None, None
                ext = min(range(o, x + 1), key=L)
        else:
            if level and c < level["price"] - mg:
                o = max(range(level["idx"], x + 1), key=H)
                event("BOS", "sell", level, x, o)
                prot, level, ext, pending = pt(o, "high"), None, x, None
            elif c > prot["price"] + mg:
                o = min(range(prot["idx"], x + 1), key=L)
                event("CHoCH", "buy", prot, x, o)
                trend, prot, level, pending = "buy", pt(o, "low"), None, None
                ext = max(range(o, x + 1), key=H)
        if ext is not None:                                       # the leg extreme runs with the trend
            if trend == "buy" and H(x) >= H(ext):
                ext, pending = x, None
            elif trend == "sell" and L(x) <= L(ext):
                ext, pending = x, None
        p = x - n                                                 # the swing n bars back is known from this bar
        if p >= n:
            for kind in ("high", "low"):
                if not _pivot(bars, p, n, kind == "high"):
                    continue
                if trend is None:
                    last[kind] = pt(p, kind)
                elif (trend == "buy") == (kind == "high") and ext is not None and \
                        (H(p) >= H(ext) if kind == "high" else L(p) <= L(ext)):
                    pending = p                                   # a swing at the leg's extreme: is the pullback real?
        if pending is not None and level is None:
            pull = H(pending) - min(L(i) for i in range(pending, x + 1)) if trend == "buy" else \
                max(H(i) for i in range(pending, x + 1)) - L(pending)
            if pull >= pullback_atr * A[x]:
                level, pending = pt(pending, "high" if trend == "buy" else "low"), None
    if ext is not None:
        points.append(pt(ext, "high" if trend == "buy" else "low"))
        if ext < len(bars) - 1:                                   # the pullback running now, up to the last bar
            rest = range(ext + 1, len(bars))
            points.append(pt(min(rest, key=L), "low") if trend == "buy" else pt(max(rest, key=H), "high"))
    zz: List[Dict] = []                                           # alternate high / low, keeping the extreme
    for q in sorted({(q["idx"], q["kind"]): q for q in points}.values(), key=lambda q: q["idx"]):
        if zz and zz[-1]["kind"] == q["kind"]:
            if (q["price"] > zz[-1]["price"]) == (q["kind"] == "high"):
                zz[-1] = q
            continue
        zz.append(q)
    return {"trend": {"buy": "up", "sell": "down"}.get(trend), "events": events, "points": zz,
            "protected": prot, "bos_level": level}
