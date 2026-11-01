"""
engine/trendlines.py — row 4 of the /smc concept table: trend lines and channels. Researched 2026-10-29 by a
Fable 5.1 agent (TradingView "Auto Trendlines" help, LuxAlgo "Trendlines with Breaks" source, MQL5 articles 3215
"Automatic construction of support and resistance lines" + 24253 "Smart Chart Objects", the TradingView
"Regression Trend" / "Linear Regression Channel" built-ins).

  pivots     strict pivot(5, 5) (ta.pivothigh / the engine's swing), alternating, legs ≥ 2 ATR between them
             (TradingView Auto Trendlines' "small" tier: 5 / 5 and > 2 × ATR(14)); a pivot is known 5 bars later.
  line       support = two pivot lows, the newer HIGHER, 5–100 bars apart; resistance = two pivot highs, the newer
             LOWER by ≥ 0.5 ATR (a flat line is a level, not a trend line). Bar-index arithmetic (weekends do not bend it):
             y(t) = p1 + (p2 − p1)·(t − b1)/(b2 − b1). Valid only when no close between the first anchor and the
             bar the line is known on is beyond it by more than 0.1 ATR. Known at b2 + 5.
  touches    a later pivot(3) whose wick comes within 0.5 ATR of the line without closing through it by 0.1 ATR
             (TradingView: a 3 / 3 pivot inside the 0.5 ATR touch area); 3 touches = a confirmed line.
  break      a close ≥ 0.25 ATR beyond (the structure margin): broken; "held" when the next 2 closes stay beyond
             (3 in a row, TradingView), "false break" when price closes back on the line's side within 10 bars
             (a sweep of the line). A line expires when it runs more than 2 × its base (first anchor → last touch)
             past its last touch (TradingView's extension limit).
  shown      the best live support and resistance (touches → length), and the latest broken ones.
  channels   parallel: the shown line + its opposite extreme between the anchors (TradingView "Parallel Channel"
             made deterministic); regression: least squares of the closes from the protected swing (the major
             leg's origin) to now, ±2σ of the residuals, Pearson's R — a "trend channel" when |R| ≥ 0.7, needs ≥ 20
             bars (it moves with every bar: context, not a level).

    trendlines(bars, m, A) -> {"lines": [...], "shown": [...], "regression": {...} | None}
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

from .major_structure import _pivot

PIVOT_N, MIN_LEG_ATR = 5, 2.0
MIN_BASE, MAX_BASE = 5, 100
CROSS_ATR, TOUCH_ATR, TOUCH_N = 0.1, 0.5, 3
FLAT_ATR = 0.5               # anchors closer than this in price: a horizontal level (row 2), not a trend line
BREAK_ATR, HOLD_CLOSES, FALSE_BARS, EXTEND = 0.25, 3, 10, 2.0
REG_MIN_BARS, REG_SIGMA, REG_R = 20, 2.0, 0.7


def zigzag(bars: List[Dict], A: List[float], n: int = PIVOT_N, min_leg: float = MIN_LEG_ATR) -> List[Dict]:
    """alternating strict pivots of n bars, legs ≥ min_leg × ATR (the more extreme of two same-kind pivots stays)"""
    cand = []
    for p in range(n, len(bars) - n):
        for high in (True, False):
            if _pivot(bars, p, n, high):
                cand.append({"idx": p, "high": high, "price": bars[p]["h" if high else "l"]})
    out: List[Dict] = []
    for q in cand:
        if out and out[-1]["high"] == q["high"]:
            if (q["price"] > out[-1]["price"]) == q["high"]:
                out[-1] = q
        elif not out or abs(q["price"] - out[-1]["price"]) >= min_leg * A[q["idx"]]:
            out.append(q)
    return out


def _track(bars: List[Dict], A: List[float], ln: Dict) -> None:
    """touches, break, expiry from the bar the line is known"""
    up = ln["side"] == "support"
    y = lambda t: ln["p1"] + ln["slope"] * (t - ln["b1"])
    n, base_end = len(bars), ln["b2"]
    for t in range(ln["known"] + 1, n):
        if t - base_end > EXTEND * (base_end - ln["b1"]):
            ln.update(status="expired", end=t)
            return
        b, v, a = bars[t], y(t), A[t]
        if (b["c"] < v - BREAK_ATR * a) if up else (b["c"] > v + BREAK_ATR * a):
            nxt = [bars[k]["c"] for k in range(t + 1, min(n, t + FALSE_BARS + 1))]
            inside = lambda k, c: c > y(k) if up else c < y(k)
            back = next((k for k, c in enumerate(nxt, t + 1) if inside(k, c)), None)
            held = len(nxt) >= HOLD_CLOSES - 1 and not any(inside(k, c) for k, c in enumerate(nxt[:HOLD_CLOSES - 1], t + 1))
            ln.update(status="false break" if back is not None else "broken", end=t, break_idx=t, held=held, back_idx=back)
            return
        p = t - TOUCH_N                                         # a pivot(3) at p is known on bar t
        if p > ln["touches"][-1] + TOUCH_N - 1 and p > ln["b2"] and _pivot(bars, p, TOUCH_N, not up):
            q, v, a = bars[p], y(p), A[p]
            near = (q["l"] <= v + TOUCH_ATR * a and q["c"] >= v - CROSS_ATR * a) if up else (q["h"] >= v - TOUCH_ATR * a and q["c"] <= v + CROSS_ATR * a)
            if near:
                ln["touches"].append(p)
                base_end = p
    ln.update(status="live", end=n - 1)


def _lines(bars: List[Dict], A: List[float], Z: List[Dict], side: str) -> List[Dict]:
    up = side == "support"
    piv = [q for q in Z if q["high"] != up]
    out = []
    for j, q2 in enumerate(piv):
        for q1 in reversed(piv[:j]):
            base = q2["idx"] - q1["idx"]
            if base > MAX_BASE:
                break
            rise = (q2["price"] - q1["price"]) if up else (q1["price"] - q2["price"])
            if base < MIN_BASE or rise < FLAT_ATR * A[q2["idx"]]:
                continue
            slope = (q2["price"] - q1["price"]) / base
            known = q2["idx"] + PIVOT_N
            if known >= len(bars):
                continue
            ok = all((bars[t]["c"] >= q1["price"] + slope * (t - q1["idx"]) - CROSS_ATR * A[t]) if up else
                     (bars[t]["c"] <= q1["price"] + slope * (t - q1["idx"]) + CROSS_ATR * A[t]) for t in range(q1["idx"], known + 1))
            if not ok:
                continue
            ln = {"side": side, "b1": q1["idx"], "p1": q1["price"], "b2": q2["idx"], "p2": q2["price"], "slope": slope,
                  "known": known, "touches": [q1["idx"], q2["idx"]], "break_idx": None}
            _track(bars, A, ln)
            ln["confirmed"] = len(ln["touches"]) >= 3
            far = range(ln["b1"], ln["b2"] + 1)                 # the parallel channel's offset
            ln["offset"] = (max(bars[t]["h"] - (ln["p1"] + slope * (t - ln["b1"])) for t in far) if up else
                            min(bars[t]["l"] - (ln["p1"] + slope * (t - ln["b1"])) for t in far))
            out.append(ln)
    return out


def regression(bars: List[Dict], m: Dict) -> Optional[Dict]:
    prot = m.get("protected")
    if not prot:
        return None
    a0, n = prot["idx"], len(bars)
    N = n - a0
    if N < REG_MIN_BARS:
        return None
    xs, ys = range(a0, n), [bars[i]["c"] for i in range(a0, n)]
    mx, my = sum(xs) / N, sum(ys) / N
    vx = sum((x - mx) ** 2 for x in xs) / N
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / N
    b = cov / vx
    a = my - b * mx
    sd = math.sqrt(sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys)) / N)
    vy = sum((y - my) ** 2 for y in ys) / N
    r = cov / math.sqrt(vx * vy) if vy > 0 else 0.0
    return {"from_idx": a0, "to_idx": n - 1, "slope": b, "at_from": a + b * a0, "at_to": a + b * (n - 1), "sigma": sd,
            "k": REG_SIGMA, "r": round(float(r), 3), "trend_channel": bool(abs(r) >= REG_R)}


def trendlines(bars: List[Dict], m: Dict, A: List[float]) -> Dict:
    Z = zigzag(bars, A)
    lines = _lines(bars, A, Z, "support") + _lines(bars, A, Z, "resistance")
    rank = lambda ln: (len(ln["touches"]), ln["touches"][-1] - ln["b1"])
    shown = []
    for side in ("support", "resistance"):
        live = sorted((ln for ln in lines if ln["side"] == side and ln["status"] == "live"), key=rank, reverse=True)
        shown += live[:1]
        done = sorted((ln for ln in lines if ln["side"] == side and ln["status"] in ("broken", "false break")),
                      key=lambda ln: ln["break_idx"], reverse=True)
        seen = set()
        for ln in done:                                          # the latest breaks, one per break bar
            if ln["break_idx"] not in seen and len(seen) < 2 and len(ln["touches"]) >= 2:
                seen.add(ln["break_idx"])
                shown.append(ln)
    return {"lines": lines, "shown": shown, "regression": regression(bars, m), "pivots": Z}
