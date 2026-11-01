"""
engine/wyckoff.py — row 8 of the /smc concept table (with elliott.py): Wyckoff trading ranges as a state machine
on David's major structure. Researched 2026-10-29 by a Fable 5.1 agent (Pruden & von Lichtenstein "Wyckoff
Schematics" STA paper, StockCharts' Wyckoff tutorial, MQL5 "Automating Classic Market Methods" part 1 — the only
complete published algorithm —, TradingView Climax Detector / Wyckoff Pattern Indicator / Wyckoff Elite).

Accumulation (distribution = the mirror: BC, AR, ST, UT / UTAD, SOW, LPSY):
  SC      a major swing low ending a down leg of ≥ 4 ATR. "climactic" when within its last 3 bars the range is
          ≥ 1.5 ATR and the tick volume ≥ 2 × its 20-bar mean (Climax Detector); without that it is "SC?"
          (Pruden: phase A can end without dramatic spread or volume).
  AR      the first pivot(3) high after the SC that rallied ≥ 1.5 ATR from it: the range top (resistance).
          A rally of more than 8 ATR is a V turn, not a range. A close 0.25 ATR below the SC first = no SC.
  ST      a later pivot(3) low within 0.5 ATR of the support, on less volume and range than the SC (else
          "ST (heavy)"); the support = the lowest SC / ST low. The first ST ends phase A, B runs on.
  Spring  (phase C) = the liquidity sweep of smc_marks: a wick ≥ 0.1 ATR below the support and a close back
          above within 3 candles. Graded by volume: ≤ 0.8 × mean "low volume" (ready), ≥ 1.5 × "shakeout" (needs
          its Test). Three closes 0.25 ATR below the support instead = the range broke down (failed); a close
          below the spring's low later fails it too (MQL5).
  Test    the next pivot(3) low above the spring's low.
  SOS     (phase D) a close ≥ 0.25 ATR above the resistance (= a BOS of the range top); "on volume" when the
          breaking bar's volume ≥ 1.2 × mean and its range ≥ 1 ATR. With no spring before it: schematic #2.
  LPS     the first pivot(3) low after the SOS that holds above the old resistance − 0.25 ATR, on volume below
          1.2 × mean; within 8 bars × the timeframe scale (MQL5 InpLPSBars 8 on H4).
  E       a close above the highest high between the SOS and the LPS: markup, the range is left.
  A range that sees no spring / SOS within 60 bars × scale of its SC expires (MQL5: 10–60 bars on H4).
Phases A–E follow from the events, and stay "provisional" until the SOS (Pruden: whether it is accumulation or
re-distribution is not known before then). Not attempted: PS / PSY (only known afterwards), the cause / P&F count,
effort-vs-result — those stay judgement.

    wyckoff(bars, m, A, tf) -> {"ranges": [...newest first], "volume": bool}
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .indicators import sma
from .major_structure import _pivot

PRIOR_LEG_ATR, AR_MIN_ATR, TR_MAX_ATR = 4.0, 1.5, 8.0
ST_TOL_ATR, SWEEP_ATR, BREAK_ATR, FAIL_BARS = 0.5, 0.1, 0.25, 3
CLIMAX_VOL, CLIMAX_RANGE, LOW_VOL, HIGH_VOL, SHAKEOUT_VOL = 2.0, 1.5, 0.8, 1.2, 1.5
PIV_N, VOL_N, MAX_BARS, LPS_BARS, CANDIDATES = 3, 20, 60, 8, 4
SCALE = {"M5": 6, "M15": 4, "M30": 3, "H1": 2, "H4": 1}
NAMES = {"acc": {"SC": "SC", "AR": "AR", "ST": "ST", "Spring": "Spring", "Test": "Test", "SOS": "SOS", "LPS": "LPS", "E": "markup"},
         "dist": {"SC": "BC", "AR": "AR", "ST": "ST", "Spring": "UTAD", "Test": "Test", "SOS": "SOW", "LPS": "LPSY", "E": "markdown"}}


def _flip(bars: List[Dict]) -> List[Dict]:
    return [{"t": b["t"], "o": -b["o"], "h": -b["l"], "l": -b["h"], "c": -b["c"], "v": b.get("v") or 0.0} for b in bars]


def _run(bars: List[Dict], sc: int, A: List[float], rv, scale: int) -> Optional[Dict]:
    """the accumulation state machine from the SC bar; rv(i) = volume / its mean (None without volume)"""
    n = len(bars)
    H, L, C = (lambda i: bars[i]["h"]), (lambda i: bars[i]["l"]), (lambda i: bars[i]["c"])
    rng = lambda i: (bars[i]["h"] - bars[i]["l"]) / A[i] if A[i] else 0
    w = range(max(0, sc - 2), sc + 1)
    vols = [rv(i) for i in w]
    climax = bool(max(rng(i) for i in w) >= CLIMAX_RANGE) and (None if vols[0] is None else bool(max(vols) >= CLIMAX_VOL))
    ev = [{"key": "SC", "idx": sc, "price": L(sc), "climax": climax, "vol": rv(sc)}]
    tr = {"sc": sc, "support": L(sc), "resistance": None, "phase": "A", "state": "SC", "status": "forming", "events": ev,
          "schematic": None, "end": n - 1}
    exc, below, spring, sos, lps, st_n = None, 0, None, None, None, 0
    for x in range(sc + 1, n):
        a, c = A[x], C(x)
        st = tr["state"]
        if st in ("SC", "A", "B") and x - sc > MAX_BARS * scale and not spring:
            tr.update(status="expired", end=x)
            return tr
        if st in ("SC", "A") and c < tr["support"] - BREAK_ATR * a:
            return None                                            # a lower close: that was not the low
        if st in ("A", "B", "C") and c > tr["resistance"] + BREAK_ATR * a:   # SOS: a close beyond the range top
            r = rv(x)
            sos = x
            ev.append({"key": "SOS", "idx": x, "price": c, "vol": r,
                       "strong": bool((r is None or r >= HIGH_VOL) and rng(x) >= 1.0)})
            tr.update(state="D", phase="D", schematic=1 if spring is not None else 2)
            continue
        if st == "C" and c < L(spring):
            tr.update(status="failed", end=x, why="a close below the spring's low")
            return tr
        if st == "B":                                              # the spring: a sweep of the support
            sup = tr["support"]
            if exc is None and L(x) < sup - SWEEP_ATR * a:
                exc, below = {"start": x, "low": L(x)}, 0
            if exc is not None:
                exc["low"] = min(exc["low"], L(x))
                if c > sup:
                    r = max((rv(i) or 0) for i in range(exc["start"], x + 1)) if rv(x) is not None else None
                    grade = None if r is None else "low volume" if r <= LOW_VOL else "shakeout" if r >= SHAKEOUT_VOL else "moderate"
                    k = min(range(exc["start"], x + 1), key=L)
                    spring = k
                    ev.append({"key": "Spring", "idx": k, "price": exc["low"], "vol": rv(k), "grade": grade, "back_idx": x,
                               "late": st_n >= 2})
                    tr.update(state="C", phase="C")
                    exc = None
                elif c < sup - BREAK_ATR * a:
                    below += 1
                    if below >= FAIL_BARS:
                        tr.update(status="failed", end=x, why="three closes below the support: the range broke down")
                        return tr
        if st == "E":
            continue
        if st == "D" and lps is not None:
            top = max(H(i) for i in range(sos, lps + 1))
            if c > top:
                ev.append({"key": "E", "idx": x, "price": c})
                tr.update(state="E", phase="E", status="markup", end=x)
                return tr
        p = x - PIV_N                                              # a pivot(3) at p is known on bar x
        if p <= ev[-1]["idx"] or p < PIV_N:
            continue
        if st == "SC" and _pivot(bars, p, PIV_N, True) and H(p) - tr["support"] >= AR_MIN_ATR * A[p]:
            if H(p) - tr["support"] > TR_MAX_ATR * A[p]:
                return None                                        # a V turn, no range
            ev.append({"key": "AR", "idx": p, "price": H(p), "vol": rv(p)})
            tr.update(resistance=H(p), state="A")
        elif st in ("A", "B") and _pivot(bars, p, PIV_N, False) and abs(L(p) - tr["support"]) <= ST_TOL_ATR * A[p]:
            r, r0 = rv(p), ev[0]["vol"]
            heavy = bool(r is not None and r0 is not None and (r >= r0 or bars[p]["h"] - L(p) >= bars[sc]["h"] - L(sc)))
            st_n += 1
            ev.append({"key": "ST", "idx": p, "price": L(p), "vol": r, "heavy": heavy})
            tr["support"] = min(tr["support"], L(p))
            tr.update(state="B", phase="B")
        elif st == "C" and spring is not None and _pivot(bars, p, PIV_N, False) and L(p) > L(spring) \
                and not any(e["key"] == "Test" for e in ev):
            ev.append({"key": "Test", "idx": p, "price": L(p), "vol": rv(p)})
        elif st == "D" and lps is None and _pivot(bars, p, PIV_N, False) and p > sos:
            if p - sos > LPS_BARS * scale:                         # no LPS in time: the move left without one
                tr.update(status="left without an LPS", end=x)
                return tr
            r = rv(p)
            if L(p) >= tr["resistance"] - BREAK_ATR * A[p] and (r is None or r < HIGH_VOL):
                lps = p
                ev.append({"key": "LPS", "idx": p, "price": L(p), "vol": r})
    return tr


def _scan(bars: List[Dict], pts: List[Dict], A: List[float], rv, scale: int) -> List[Dict]:
    out = []
    for k in range(len(pts) - 1, 0, -1):
        q, prev = pts[k], pts[k - 1]
        if q["kind"] != "low" or prev["kind"] != "high" or prev["price"] - q["price"] < PRIOR_LEG_ATR * A[q["idx"]]:
            continue
        tr = _run(bars, q["idx"], A, rv, scale)
        if tr and tr["resistance"] is not None:
            tr["prior_leg_from"] = prev["idx"]
            out.append(tr)
        if len(out) >= CANDIDATES:
            break
    return out


def wyckoff(bars: List[Dict], m: Dict, A: List[float], tf: str = "M15") -> Dict:
    scale = SCALE.get(tf, 1)
    vol = any(b.get("v") for b in bars)
    mean = sma([b.get("v") or 0.0 for b in bars], VOL_N)
    rv = (lambda i: (bars[i]["v"] / mean[i]) if mean[i] else None) if vol else (lambda i: None)
    pts = m["points"]
    flipped = [{**q, "price": -q["price"], "kind": "low" if q["kind"] == "high" else "high"} for q in pts]
    ranges = []
    for kind, bs, ps, sgn in (("acc", bars, pts, 1), ("dist", _flip(bars), flipped, -1)):
        for tr in _scan(bs, ps, A, rv, scale):
            sup, res = tr["support"] * sgn, tr["resistance"] * sgn
            ranges.append({"kind": "accumulation" if kind == "acc" else "distribution", "phase": tr["phase"],
                           "status": "markdown" if kind == "dist" and tr["status"] == "markup" else tr["status"], "why": tr.get("why"), "schematic": tr["schematic"],
                           "provisional": tr["phase"] in ("A", "B", "C"),
                           "low": min(sup, res), "high": max(sup, res), "from_idx": tr["sc"], "to_idx": tr["end"],
                           "events": [{**e, "label": NAMES[kind][e["key"]], "price": e["price"] * sgn} for e in tr["events"]]})
    live = sorted((r for r in ranges if r["status"] == "forming"), key=lambda r: -r["from_idx"])
    done = sorted((r for r in ranges if r["status"] != "forming"), key=lambda r: -r["from_idx"])
    return {"ranges": (live[:1] + done[:2]) if live else done[:2], "volume": vol}
