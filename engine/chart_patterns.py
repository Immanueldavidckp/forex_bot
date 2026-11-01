"""
engine/chart_patterns.py — row 5 of the /smc concept table: classic chart patterns on a pivot zigzag, every
tolerance in ATR(14) frozen at the pattern's last pivot, so a pattern never changes shape afterwards. Researched
2026-10-29 by a Fable 5.1 agent: Lo, Mamaysky & Wang (2000) "Foundations of Technical Analysis" extrema rules,
Osler & Chang (1995, NY Fed — the one FX head & shoulders study), Bulkowski's thepatternsite.com guidelines and
statistics, Trendoscope's "Auto Chart Patterns" line / slope classification. The %-tolerances of those sources
(daily stocks) are converted to ATR (1.5 % ≈ 0.5–0.75 ATR of a 1990s stock day, Bulkowski's < 3 % ≈ 1–1.5 ATR,
his ≥ 10 % valley ≈ 3–5 ATR): a fixed % would be 16 ATR on EURUSD H1 and 0.2 ATR on gold H4.

  pivots     strict pivot(n) — n 5 on M5 / M15 / M30, 4 on H1, 3 on H4 — alternating, legs ≥ 1 ATR; a pivot is known
             n bars after it. Lines go through exact pivot prices (no regression), in bar-index arithmetic.
  head & shoulders (inverse = mirror) on 7 pivots P, TLL, LS, TL, H, TR, RS (Osler & Chang): H ≥ 1 ATR above both
             shoulders; prior uptrend LS > P and TL > TLL; vertical symmetry RS > mid(LS, TL) > TR and
             LS > mid(RS, TR) > TL; shoulders within 1.5 ATR, armpits within 2 ATR (LMW); time LS→H and H→RS within
             2.5× of each other; LS→RS 12–120 bars. Neckline TL–TR; when it slopes against the break (down on a top)
             the right armpit's level is the trigger (Bulkowski).
  double top / bottom   H1 L1 H2: peaks within 1 ATR, valley ≥ 3 ATR below the lower peak, 10–80 bars apart, H1 the
             highest high of the 20 bars before it. Trigger = the valley.
  triple top / bottom   H1 L1 H2 L2 H3: all three within 1 ATR of their mean, both valleys ≥ 2 ATR below the lowest
             peak, 15–120 bars. Trigger = the lowest valley. Not reported when its last three pivots already made a
             double top that confirmed (one pattern per pivot set).
  triangles / wedges / rectangles   5 pivots (3 touches on one line, 2 on the other, Bulkowski): each line through
             its outer pivots, a middle pivot within 0.5 ATR of its line; a line is flat when it drifts < 1 ATR over
             the pattern; converging when the gap shrinks by > 1 ATR. Upper flat + lower rising = ascending
             triangle, upper falling + lower flat = descending, upper falling + lower rising = symmetrical, both
             rising / falling and converging = rising / falling wedge (≥ 20 bars), both flat with tops and bottoms
             within 0.75 ATR of their means = rectangle. First gap ≥ 3 ATR (rectangle 2), no close outside the lines
             between the first and last pivot, apex beyond 1.2 × the width; 15–150 bars (wedges 20–150).
  flags / pennants   pole = one zigzag leg ≥ 4 ATR in ≤ 12 bars ending at the most extreme price of the last 30;
             body = the next 4 pivots: parallel lines (flag) or converging (pennant), height ≤ ½ the pole, not
             retracing more than 50 % of it, ≤ 20 bars and ≤ 2 × the pole's bars. Only the break in the pole's
             direction counts; a close through the other side voids it.
  confirmation   the first close ≥ 0.1 ATR beyond the trigger line, within the deadline: H&S / double / triple = the
             pattern's own width after its last pivot is known, triangles / wedges = before the apex, rectangles
             = the width, flags = 20 bars from the pole's end. Before it: "forming", after the deadline "expired",
             a close beyond the head / highest peak (or the far line) "invalid".
  after it   target = the height projected from the confirmation close (full measure) and Bulkowski's realistic
             share of it (% of patterns that reached the full target); wedges target their start. "target hit",
             "failed" (a close back across the line by 1 ATR first) or "running". Stop = beyond the last pivot
             + 0.25 ATR.

    patterns(bars, A, tf) -> [{"pattern", "side", "points", "lines", "status", ...}, ...] oldest first
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .trendlines import zigzag

PIVOT_N = {"M5": 5, "M15": 5, "M30": 5, "H1": 4, "H4": 3}
MIN_LEG = 1.0
BRK, FAIL, STOP = 0.1, 1.0, 0.25
REALISTIC = {"head and shoulders top": 0.51, "inverse head and shoulders": 0.71, "double top": 0.64, "double bottom": 0.73,
             "triple top": 0.49, "triple bottom": 0.74, "rectangle up": 0.78, "rectangle down": 0.54,
             "ascending triangle up": 0.70, "ascending triangle down": 0.44, "descending triangle up": 0.64,
             "descending triangle down": 0.50, "symmetrical triangle up": 0.58, "symmetrical triangle down": 0.36,
             "bull flag": 0.46, "bear flag": 0.46, "bull pennant": 0.35, "bear pennant": 0.35}
FAIL_RATE = {"head and shoulders top": 19, "inverse head and shoulders": 11, "double top": 25, "double bottom": 16,
             "triple top": 25, "triple bottom": 13, "ascending triangle": 17, "descending triangle": 22,
             "symmetrical triangle": 25, "rising wedge": 19, "falling wedge": 26, "bull flag": 44, "bear flag": 45,
             "bull pennant": 54, "bear pennant": 54, "rectangle": 15}    # Bulkowski's break-even failure %, bull market


def _flip(bars: List[Dict]) -> List[Dict]:
    return [{"t": b["t"], "o": -b["o"], "h": -b["l"], "l": -b["h"], "c": -b["c"]} for b in bars]


def _line(i1: int, p1: float, i2: int, p2: float):
    s = (p2 - p1) / (i2 - i1)
    return lambda t: p1 + s * (t - i1), s


def _after(bars, A, r: Dict, trig, below: bool, start: int, deadline: int, invalid=None) -> None:
    """confirmation (a close BRK × ATR beyond trig(t) — below it when `below`), then target / failure"""
    a = r["atr"]
    r.update(status="forming", confirm_idx=None, invalid_idx=None, end_idx=None)
    n = len(bars)
    for t in range(start, n):
        c = bars[t]["c"]
        if invalid is not None and invalid(t, c):
            r.update(status="invalid", invalid_idx=t, end_idx=t)
            return
        if (c < trig(t) - BRK * a) if below else (c > trig(t) + BRK * a):
            r.update(status="running", confirm_idx=t, confirm_price=c)
            break
        if t >= deadline:
            r.update(status="expired", end_idx=t)
            return
    else:
        return
    k, h = r["confirm_idx"], r["height"]
    sg = -1 if below else 1
    r["target"] = r.get("target") if r.get("target") is not None else c + sg * h
    real = REALISTIC.get(r["pattern"]) or REALISTIC.get(f"{r['pattern']} {'down' if below else 'up'}")
    r["target_realistic"] = None if real is None else c + sg * h * real
    for t in range(k + 1, n):
        b = bars[t]
        if (b["l"] <= r["target"]) if below else (b["h"] >= r["target"]):
            r.update(status="target hit", end_idx=t)
            return
        if (b["c"] > trig(t) + FAIL * a) if below else (b["c"] < trig(t) - FAIL * a):
            r.update(status="failed", end_idx=t)
            return


def _hs(bars, A, Z, n) -> List[Dict]:
    out = []
    for k in range(6, len(Z)):
        P, TLL, LS, TL, H, TR, RS = Z[k - 6:k + 1]
        if not P["high"]:
            continue
        a = A[RS["idx"]]
        pr = lambda q: q["price"]
        mid1, mid2 = (pr(LS) + pr(TL)) / 2, (pr(RS) + pr(TR)) / 2
        t1, t2 = H["idx"] - LS["idx"], RS["idx"] - H["idx"]
        if not (pr(H) - pr(LS) >= a and pr(H) - pr(RS) >= a and pr(LS) > pr(P) and pr(TL) > pr(TLL)
                and pr(RS) > mid1 > pr(TR) and pr(LS) > mid2 > pr(TL)
                and abs(pr(LS) - pr(RS)) <= 1.5 * a and abs(pr(TL) - pr(TR)) <= 2.0 * a
                and t1 <= 2.5 * t2 and t2 <= 2.5 * t1 and 12 <= RS["idx"] - LS["idx"] <= 120):
            continue
        neck, slope = _line(TL["idx"], pr(TL), TR["idx"], pr(TR))
        trig = neck if slope >= 0 else (lambda t, v=pr(TR): v)       # a down-sloping neckline: the right armpit
        known = RS["idx"] + n
        r = {"pattern": "head and shoulders top", "side": "bear", "atr": a, "known_idx": known,
             "height": pr(H) - neck(H["idx"]), "stop": pr(RS) + STOP * a,
             "points": [{"idx": q["idx"], "price": pr(q), "label": lb} for q, lb in ((LS, "LS"), (TL, "TL"), (H, "H"), (TR, "TR"), (RS, "RS"))],
             "lines": [{"kind": "neckline", "i1": TL["idx"], "p1": pr(TL), "slope": slope}]}
        _after(bars, A, r, trig, True, known, known + (RS["idx"] - LS["idx"]), lambda t, c, h=pr(H): c > h)
        out.append(r)
    return out


def _double_triple(bars, A, Z, n) -> List[Dict]:
    out, dt_ok = [], set()
    for k in range(2, len(Z)):
        H1, L1, H2 = Z[k - 2:k + 1]
        if not H1["high"]:
            continue
        a, sep = A[H2["idx"]], H2["idx"] - H1["idx"]
        before = [bars[i]["h"] for i in range(max(0, H1["idx"] - 20), H1["idx"])]
        if not (abs(H1["price"] - H2["price"]) <= 1.0 * a and min(H1["price"], H2["price"]) - L1["price"] >= 3.0 * a
                and 10 <= sep <= 80 and before and H1["price"] >= max(before)):
            continue
        top = max(H1["price"], H2["price"])
        known = H2["idx"] + n
        r = {"pattern": "double top", "side": "bear", "atr": a, "known_idx": known, "height": top - L1["price"],
             "stop": H2["price"] + STOP * a,
             "points": [{"idx": H1["idx"], "price": H1["price"], "label": "top 1"}, {"idx": L1["idx"], "price": L1["price"], "label": "valley"},
                        {"idx": H2["idx"], "price": H2["price"], "label": "top 2"}],
             "lines": [{"kind": "trigger", "i1": L1["idx"], "p1": L1["price"], "slope": 0.0}]}
        _after(bars, A, r, lambda t, v=L1["price"]: v, True, known, known + sep, lambda t, c, v=top + BRK * a: c > v)
        out.append(r)
        if r["confirm_idx"] is not None:
            dt_ok.add(H2["idx"])
    for k in range(4, len(Z)):
        H1, L1, H2, L2, H3 = Z[k - 4:k + 1]
        if not H1["high"] or H3["idx"] in dt_ok:
            continue
        a = A[H3["idx"]]
        hs = [H1["price"], H2["price"], H3["price"]]
        mean = sum(hs) / 3
        low = min(L1["price"], L2["price"])
        if not (all(abs(x - mean) <= 1.0 * a for x in hs) and min(hs) - max(L1["price"], L2["price"]) >= 2.0 * a
                and 15 <= H3["idx"] - H1["idx"] <= 120):
            continue
        known = H3["idx"] + n
        r = {"pattern": "triple top", "side": "bear", "atr": a, "known_idx": known, "height": max(hs) - low,
             "stop": H3["price"] + STOP * a,
             "points": [{"idx": q["idx"], "price": q["price"], "label": lb} for q, lb in
                        ((H1, "top 1"), (L1, "valley"), (H2, "top 2"), (L2, "valley"), (H3, "top 3"))],
             "lines": [{"kind": "trigger", "i1": min((L1, L2), key=lambda q: q["price"])["idx"], "p1": low, "slope": 0.0}]}
        _after(bars, A, r, lambda t, v=low: v, True, known, known + (H3["idx"] - H1["idx"]), lambda t, c, v=max(hs) + BRK * a: c > v)
        out.append(r)
    return out


def _flag(bars, A, Z, n) -> List[Dict]:
    """bull flags / pennants (bear = the mirror)"""
    out = []
    for k in range(1, len(Z) - 4):
        P0, P1 = Z[k - 1], Z[k]
        if not P1["high"]:
            continue
        a, pole, pbars = A[P1["idx"]], P1["price"] - P0["price"], P1["idx"] - P0["idx"]
        prior = [bars[i]["h"] for i in range(max(0, P1["idx"] - 30), P1["idx"])]
        if not (pole >= 4.0 * a and pbars <= 12 and prior and P1["price"] >= max(prior)):
            continue
        B = Z[k:k + 4]                                           # P1 (high), low, high, low
        L1, H2, L2 = B[1], B[2], B[3]
        w = L2["idx"] - P1["idx"]
        if not (4 <= w <= 20 and w <= 2 * pbars):
            continue
        up, su = _line(P1["idx"], P1["price"], H2["idx"], H2["price"])
        lo, sl = _line(L1["idx"], L1["price"], L2["idx"], L2["price"])
        g0, g1 = up(P1["idx"]) - lo(P1["idx"]), up(L2["idx"]) - lo(L2["idx"])
        if g0 <= 0 or g0 > 0.5 * pole or P1["price"] - min(L1["price"], L2["price"]) > 0.5 * pole or su * w > 1.0 * a:
            continue
        kind = "bull flag" if abs(g1 - g0) <= 1.0 * a else "bull pennant" if g1 < g0 - 1.0 * a and g1 > 0 else None
        if kind is None:
            continue
        known = L2["idx"] + n
        r = {"pattern": kind, "side": "bull", "atr": a, "known_idx": known, "height": pole, "stop": L2["price"] - STOP * a,
             "pole": {"i0": P0["idx"], "p0": P0["price"]},
             "points": [{"idx": q["idx"], "price": q["price"], "label": lb} for q, lb in
                        ((P0, "pole"), (P1, "flag"), (L1, ""), (H2, ""), (L2, ""))],
             "lines": [{"kind": "upper", "i1": P1["idx"], "p1": P1["price"], "slope": su},
                       {"kind": "lower", "i1": L1["idx"], "p1": L1["price"], "slope": sl}]}
        _after(bars, A, r, up, False, known, P1["idx"] + 20, lambda t, c: c < lo(t) - BRK * a)
        out.append(r)
    return out


def _boxes(bars, A, Z, n) -> List[Dict]:
    """triangles, wedges, rectangles on 5 pivots"""
    out = []
    for k in range(4, len(Z)):
        W = Z[k - 4:k + 1]
        a = A[W[-1]["idx"]]
        hi = [q for q in W if q["high"]]
        lo = [q for q in W if not q["high"]]
        i0, i4 = W[0]["idx"], W[-1]["idx"]
        width = i4 - i0
        up, su = _line(hi[0]["idx"], hi[0]["price"], hi[-1]["idx"], hi[-1]["price"])
        dn, sd = _line(lo[0]["idx"], lo[0]["price"], lo[-1]["idx"], lo[-1]["price"])
        if any(abs(q["price"] - up(q["idx"])) > 0.5 * a for q in hi[1:-1]) or any(abs(q["price"] - dn(q["idx"])) > 0.5 * a for q in lo[1:-1]):
            continue
        g0, g1 = up(i0) - dn(i0), up(i4) - dn(i4)
        flat = lambda s: abs(s * width) < 1.0 * a
        conv = g1 < g0 - 1.0 * a
        rising, falling = (lambda s: s * width >= 1.0 * a), (lambda s: s * width <= -1.0 * a)
        kind = None
        if conv and flat(su) and rising(sd):
            kind = "ascending triangle"
        elif conv and falling(su) and flat(sd):
            kind = "descending triangle"
        elif conv and falling(su) and rising(sd):
            kind = "symmetrical triangle"
        elif conv and rising(su) and rising(sd):
            kind = "rising wedge"
        elif conv and falling(su) and falling(sd):
            kind = "falling wedge"
        elif flat(su) and flat(sd) and abs(g1 - g0) <= 1.0 * a:
            mh, ml = sum(q["price"] for q in hi) / len(hi), sum(q["price"] for q in lo) / len(lo)
            if all(abs(q["price"] - mh) <= 0.75 * a for q in hi) and all(abs(q["price"] - ml) <= 0.75 * a for q in lo):
                kind = "rectangle"
        if kind is None:
            continue
        wedge = kind.endswith("wedge")
        if g0 < (2.0 if kind == "rectangle" else 3.0) * a or g1 < 0.25 * g0 or not ((20 if wedge else 15) <= width <= 150):
            continue
        if any(bars[t]["c"] > up(t) + 0.05 * a or bars[t]["c"] < dn(t) - 0.05 * a for t in range(i0, i4 + 1)):
            continue                                              # a close outside the lines
        if kind != "rectangle":
            apex = i0 + g0 / ((g0 - g1) / width)                  # where the lines meet
            if apex - i0 <= 1.2 * width:
                continue
            deadline = int(apex)
        else:
            deadline = i4 + n + width
        known = i4 + n
        r = {"pattern": kind, "side": "bear" if kind == "rising wedge" else "bull" if kind == "falling wedge" else "either",
             "atr": a, "known_idx": known, "height": g0,
             "points": [{"idx": q["idx"], "price": q["price"], "label": ""} for q in W],
             "lines": [{"kind": "upper", "i1": hi[0]["idx"], "p1": hi[0]["price"], "slope": su},
                       {"kind": "lower", "i1": lo[0]["idx"], "p1": lo[0]["price"], "slope": sd}]}
        # either way out: the first close beyond a line confirms that side; a wedge targets its start (Bulkowski)
        rr = dict(r, target=max(q["price"] for q in hi) if wedge else None)
        _after(bars, A, rr, up, False, known, deadline, lambda t, c: c < dn(t) - BRK * a)
        if rr["status"] == "invalid":                             # it broke down first
            rr = dict(r, target=min(q["price"] for q in lo) if wedge else None)
            _after(bars, A, rr, dn, True, known, deadline)
            rr["break"] = "down"
            rr["stop"] = up(rr["confirm_idx"]) + STOP * a if rr["confirm_idx"] is not None else None
        else:
            rr["break"] = "up" if rr["confirm_idx"] is not None else None
            rr["stop"] = dn(rr["confirm_idx"]) - STOP * a if rr["confirm_idx"] is not None else None
        out.append(rr)
    return out


def _mirror(rs: List[Dict], names: Dict[str, str]) -> List[Dict]:
    """patterns found on the flipped bars → real prices"""
    out = []
    for r in rs:
        r = dict(r, pattern=names[r["pattern"]], side={"bear": "bull", "bull": "bear"}.get(r["side"], r["side"]))
        for k in ("stop", "target", "target_realistic", "confirm_price"):
            if r.get(k) is not None:
                r[k] = -r[k]
        r["points"] = [dict(q, price=-q["price"]) for q in r["points"]]
        r["lines"] = [dict(ln, p1=-ln["p1"], slope=-ln["slope"]) for ln in r["lines"]]
        if r.get("pole"):
            r["pole"] = dict(r["pole"], p0=-r["pole"]["p0"])
        out.append(r)
    return out


def patterns(bars: List[Dict], A: List[float], tf: str = "M15") -> List[Dict]:
    n = PIVOT_N.get(tf, 5)
    fb = _flip(bars)
    Z = zigzag(bars, A, n, MIN_LEG)
    FZ = [dict(q, high=not q["high"], price=-q["price"]) for q in Z]
    out = _hs(bars, A, Z, n) + _double_triple(bars, A, Z, n) + _flag(bars, A, Z, n) + _boxes(bars, A, Z, n)
    out += _mirror(_hs(fb, A, FZ, n), {"head and shoulders top": "inverse head and shoulders"})
    out += _mirror(_double_triple(fb, A, FZ, n), {"double top": "double bottom", "triple top": "triple bottom"})
    out += _mirror(_flag(fb, A, FZ, n), {"bull flag": "bear flag", "bull pennant": "bear pennant"})
    for r in out:
        base = r["pattern"]
        r["fail_rate"] = FAIL_RATE.get(base)
        r["first_idx"] = r["points"][0]["idx"] if not r.get("pole") else r["pole"]["i0"]
    return sorted(out, key=lambda r: (r["known_idx"], r["pattern"]))
