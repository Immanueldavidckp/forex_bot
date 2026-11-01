"""
engine/elliott.py — Elliott wave counts on David's MAJOR structure zigzag (major_structure.py points), so the wave
degree is fixed: one count per timeframe, nothing internal, no sub-wave recursion. Researched 2026-10-29 by a
Fable 5.1 agent (Frost & Prechter's rules as reproduced by TradingView / StockCharts / WaveBasis, Neely / Levin's
numeric rules, LuxAlgo "Elliott Wave" + "Elliott Hard Rules", MQL5 code 76711, HKUDS elliott-wave skill).

Hard rules (all sources agree) on 6 pivots P0..P5, bull = P0 a low (mirrored for bear), Ln = length of wave n:
  R1  wave 2 never beyond the start of wave 1            P2 > P0
  R1b wave 3 goes beyond the end of wave 1               P3 > P1
  R2  wave 3 is never the shortest of 1 / 3 / 5          not (L3 < L1 and L3 < L5)
  R3  wave 4 never enters wave 1's territory              P4 > P1   (OVERLAP_TOL × ATR allowed, default 0)
  diagonal (when only R3 fails)  P4 above P2, waves contracting (L3 < L1, L4 < L2, L5 < L3) or expanding (all >)
  wave 5 may truncate (P5 ≤ P3): flagged, still an impulse.
Corrections (A-B-C after a complete impulse, A = the first leg against it):
  zigzag  B retraces < 100 % of A and C ends beyond A            (guideline B 38–79 %, C = 0.618 / 1 / 1.618 A)
  flat    B retraces ≥ 90 % of A (and < 200 %), C reaches back into A's range: regular (B ≤ 105 %), expanded
          (B > 105 % and C beyond A's end), running (B > 100 % and C short of A's end)
Score (codeable guideline, not a rule): Σ w · max(0, 1 − |ratio − nearest ideal| / 0.15) over wave 2 retrace
(0.5, 0.618), wave 3 / wave 1 (1.618, 2.618, 4.236), wave 4 retrace (0.382), wave 5 / wave 1 (0.618, 1, 1.618),
alternation (one of waves 2 / 4 deep > 50 %, the other shallow) and one extended wave (≥ 1.618 × the other two).

The newest pivot of the zigzag is the running extreme (not confirmed): a count using it is provisional and
forming ("in wave 5"), like every public counter. Live invalidation (a WICK beyond, as LuxAlgo): waves 2 / 3
→ P0, waves 4 / 5 → P1 (impulse) or P2 (diagonal); a flat C beyond 1.65 A. Subjective, not attempted: sub-wave
subdivision (5-3-5 vs 3-3-5), triangles and W-X-Y combinations, choosing between equally valid counts (the best
two are shown with their scores).

    elliott(bars, points, A) -> {"counts": [...best first], "abc": {...} | None}
        points  major_structure(...)["points"] (alternating high / low, oldest first)
"""
from __future__ import annotations

from typing import Dict, List, Optional

OVERLAP_TOL = 0.0          # × ATR: wave 4 may poke into wave 1 by this much (gold spreads: 0.1 is the option)
FIB_TOL = 0.15
MAX_LOOKBACK = 12          # windows ending at the newest 12 pivots
IDEAL = {"w2": (0.5, 0.618), "w3": (1.618, 2.618, 4.236), "w4": (0.382,), "w5": (0.618, 1.0, 1.618)}
WEIGHT = {"w2": 1.0, "w3": 1.5, "w4": 1.0, "w5": 1.0, "alternation": 0.5, "extension": 0.5}


def _fit(r: float, ideals) -> float:
    return max(0.0, 1 - min(abs(r - x) for x in ideals) / FIB_TOL)


def _lengths(v: List[float]) -> List[float]:
    return [abs(v[k + 1] - v[k]) for k in range(len(v) - 1)]


def impulse(P: List[Dict], A: List[float]) -> Optional[Dict]:
    """P0..P5 (or P0..P3 / P0..P4 for a forming one) → the count, or None when a hard rule fails"""
    s = 1 if P[0]["kind"] == "low" else -1
    v = [s * q["price"] for q in P]
    if any((v[k + 1] - v[k]) * (1 if k % 2 == 0 else -1) <= 0 for k in range(len(v) - 1)):
        return None                                                # not an up-down-up… sequence
    L = _lengths(v)
    if v[2] <= v[0] or v[3] <= v[1]:                               # R1, R1b
        return None
    kind, why = "impulse", []
    if len(v) >= 5 and v[4] <= v[1] + OVERLAP_TOL * A[P[4]["idx"]]:  # R3 fails: a diagonal or nothing
        if v[4] <= v[2]:
            return None
        if len(v) == 6 and not ((L[2] < L[0] and L[3] < L[1] and L[4] < L[2]) or (L[2] > L[0] and L[3] > L[1] and L[4] > L[2])):
            return None
        kind = "diagonal"
    if len(v) == 6 and L[2] < L[0] and L[2] < L[4]:                # R2
        return None
    sc = {"w2": _fit(L[1] / L[0], IDEAL["w2"]), "w3": _fit(L[2] / L[0], IDEAL["w3"])}
    if len(v) >= 5:
        sc["w4"] = _fit(L[3] / L[2], IDEAL["w4"])
        r2, r4 = L[1] / L[0], L[3] / L[2]
        sc["alternation"] = 1.0 if (r2 > 0.5) != (r4 > 0.5) else 0.0
    if len(v) == 6:
        sc["w5"] = _fit(L[4] / L[0], IDEAL["w5"])
        w = [L[0], L[2], L[4]]
        sc["extension"] = 1.0 if sum(w[k] >= 1.618 * max(w[j] for j in range(3) if j != k) for k in range(3)) == 1 else 0.0
        if v[5] <= v[3]:
            why.append("wave 5 truncated (ends short of wave 3)")
    score = round(sum(WEIGHT[k] * x for k, x in sc.items()), 2)
    P0, P1, P2 = P[0]["price"], P[1]["price"], P[2]["price"]
    if len(v) <= 4:
        inv, rule = P0, "R1: wave 2 / 3 below the start of wave 1" if s > 0 else "R1: wave 2 / 3 above the start of wave 1"
    else:
        inv = P2 if kind == "diagonal" else P1
        rule = "a diagonal's wave 4 / 5 beyond wave 2's end" if kind == "diagonal" else "R3: wave 4 / 5 into wave 1's territory"
    tg = {}
    d = s
    if len(v) == 4:                                                # in wave 4: where it should stop, where 5 aims
        tg["w4 (0.236–0.5 of 3)"] = [P[3]["price"] - d * 0.236 * L[2], P[3]["price"] - d * 0.5 * L[2]]
    if len(v) == 5:
        tg["w5 = 0.618–1 × (0→3)"] = [P[4]["price"] + d * 0.618 * (v[3] - v[0]), P[4]["price"] + d * 1.0 * (v[3] - v[0])]
        tg["w5 = w1"] = [P[4]["price"] + d * L[0]]
    if len(v) == 6:
        tg["ABC retrace 0.382–0.618 of 0→5"] = [P[5]["price"] - d * 0.382 * (v[5] - v[0]), P[5]["price"] - d * 0.618 * (v[5] - v[0])]
    return {"pattern": kind, "side": "bull" if s > 0 else "bear", "score": score, "fit": {k: round(x, 2) for k, x in sc.items()},
            "ratios": {"w2/w1": round(L[1] / L[0], 3), "w3/w1": round(L[2] / L[0], 3),
                       **({"w4/w3": round(L[3] / L[2], 3)} if len(v) >= 5 else {}),
                       **({"w5/w1": round(L[4] / L[0], 3)} if len(v) == 6 else {})},
            "invalidation": inv, "rule": rule, "targets": tg, "notes": why}


def correction(P: List[Dict]) -> Optional[Dict]:
    """start, A, B, C (or start, A, B with B forming) → zigzag / flat, or None. side = A's direction"""
    s = 1 if P[0]["kind"] == "low" else -1                         # s > 0: A goes up (a correction of a down move)
    v = [s * q["price"] for q in P]
    LA, LB = v[1] - v[0], v[1] - v[2]
    if LA <= 0 or LB <= 0 or LB >= 2.0 * LA:
        return None
    b = LB / LA
    flat = b >= 0.9
    out = {"pattern": "flat" if flat else "zigzag", "side": "bull" if s > 0 else "bear", "b_retrace": round(b, 3),
           "targets": {f"C = {k:g} × A": P[2]["price"] + s * k * LA for k in (0.618, 1.0, 1.618)}}
    if flat:
        out.update(invalidation=P[2]["price"] + s * 1.65 * LA, inv_above=s > 0, rule="C longer than 1.65 × A")
    else:
        out.update(invalidation=P[0]["price"], inv_above=s < 0, rule="B beyond the start of A")
    fit_b = _fit(b, (1.0, 1.236, 1.382) if flat else (0.382, 0.5, 0.618))
    if len(P) == 3:
        out["score"] = round(fit_b, 2)
        return out
    LC = v[3] - v[2]
    if LC <= 0:
        return None
    if not flat and (v[3] <= v[1] or LC > 2.618 * LA):             # a zigzag's C passes A's end; far beyond = an impulse
        return None
    if flat:
        if v[3] <= v[0] or LC > 1.65 * LA:
            return None
        out["pattern"] = ("expanded flat" if b > 1.05 and v[3] > v[1] else "running flat" if b > 1.0 and v[3] < v[1] else "flat")
    out["c_vs_a"] = round(LC / LA, 3)
    out["score"] = round(fit_b + _fit(LC / LA, (0.618, 1.0, 1.618)), 2)
    return out


def _breached(bars: List[Dict], after: int, level: float, bull: bool) -> Optional[int]:
    """the first bar after `after` whose wick passes level (bull: below it, else above it)"""
    for i in range(after + 1, len(bars)):
        if (bars[i]["l"] < level) if bull else (bars[i]["h"] > level):
            return i
    return None


def _pts(P: List[Dict], labels) -> List[Dict]:
    return [{"t": q["t"], "idx": q["idx"], "price": q["price"], "label": lb} for q, lb in zip(P, labels)]


def elliott(bars: List[Dict], points: List[Dict], A: List[float]) -> Dict:
    Z, counts = points, []
    last = len(Z) - 1
    for e in range(last, max(last - MAX_LOOKBACK, 2), -1):
        forming = e == last
        for n in ((6, 5, 4) if forming else (6,)):                # a forming count may stop at wave 3 / 4 / 5
            if e - n + 1 < 0:
                continue
            P = Z[e - n + 1:e + 1]
            c = impulse(P, A)
            if not c:
                continue
            bull = c["side"] == "bull"
            if forming and _breached(bars, P[-1]["idx"], c["invalidation"], bull) is not None:
                continue
            c.update(points=_pts(P, "012345"), provisional=forming, end_idx=P[-1]["idx"],
                     stage=("wave 5 (forming)" if n == 6 else "wave 4 (forming)" if n == 5 else "wave 3 (forming)") if forming
                     else "complete")
            counts.append(c)
    counts.sort(key=lambda c: (-c["end_idx"], -len(c["points"]), -c["score"]))
    best = counts[:2]
    abc = None
    done = next((c for c in counts if c["stage"] == "complete" and len(c["points"]) == 6), None)
    if done:
        k = next(i for i, q in enumerate(Z) if q["idx"] == done["end_idx"])
        for n in (4, 3):
            P = Z[k:k + n]
            if len(P) == n and (n == 4 or k + n - 1 == last):
                c = correction(P)
                if c and k + n - 1 == last and _breached(bars, P[-1]["idx"], c["invalidation"], not c["inv_above"]) is not None:
                    c = None
                if c:
                    c.update(points=_pts(P, ["5", "A", "B", "C"]), provisional=k + n - 1 == last,
                             stage="complete" if n == 4 and k + n - 1 < last else f"wave {'C' if n == 4 else 'B'} (forming)",
                             after=done["end_idx"])
                    abc = c
                    break
        if done not in best:
            best.append(done)
    return {"counts": best, "abc": abc}
