"""
engine/sd_david.py — David's supply / demand, the CLASS rule (class video 6 + 6.1, OK'd by David 2026-11-04;
rules + sources: engine/research/ob_sd/class_video6/supply_demand_rules.md, pictures class6_demand.png / class6_supply.png)

  1 the break    a BOS of David's structure (major_structure.py: BOS at the leg's extreme by close; CHoCH is not a BOS
                 and gives no zone). Bull BOS → DEMAND (buy side only), bear BOS → SUPPLY (sell side only).
  2 A-B-C        inside the move that made the BOS (its origin candle → the break candle, not before it, not past it)
                 three candles A-B-C whose wicks do NOT touch: bull A.high < C.low, bear A.low > C.high. That gap is the
                 FVG. Colour does not matter. ANY gap size counts ("even if it is a small gap you can consider it").
                 No gap → no zone.
  3 the zone     candle A, wick to wick: demand = the candle BELOW the gap, supply = the candle ABOVE the gap
                 (= the class's order-block candle). Dashed 50 % line in the middle (drawn only).
  4 4th candle   the candle after C fills the gap (bull: its low ≤ A.high, bear: its high ≥ A.low) → that gap is NOT valid.
  ONE per BOS    "each BOS gives one demand / one supply": the FIRST valid A-B-C from where the BOS move starts (the
                 corner of the leg, as drawn in the class); the leg's other gaps are kept in "others" (not drawn).
  5 entry        price comes back and touches A's wick: demand = A.high, supply = A.low (proximal).
     stop        beyond candle A: demand below A.low, supply above A.high (distal).
     targets     a Fib from the entry (1) to the recent high (0) for demand / recent low for supply; T1 = its 0.618,
                 T2 = 0.5, T3 = 0.382 ("you can set your target up to 0.382", class 6.1 at 43:43, frame: 1 = 4176.44
                 entry, 0 = 4215.94 high, target 0.382 = 4200.85). Recent high/low = the leg's extreme from candle A up to
                 the candle before price comes back to the zone (or up to now while it hasn't).
  6 life         fresh → tested (the wick touch) → broken on a CLOSE beyond the far edge; a CHoCH against it ends it too.

    zones(bars, m) → one entry per BOS, oldest first, valid and not valid (valid=False + why)
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .major_structure import atr14, major_structure


def zones(bars: List[Dict], m: Optional[Dict] = None, n: int = 5) -> List[Dict]:
    N = len(bars)
    if N < 5:
        return []
    m = m or major_structure(bars, n)
    A = atr14(bars)
    out: List[Dict] = []
    for k, e in enumerate(m["events"]):
        if e["kind"] != "BOS":
            continue
        side, o, x = e["side"], e["origin"]["idx"], e["idx"]
        buy = side == "buy"
        # David 2026-11-09 (NZDUSD: candle A 9 days before the BOS, crossed 146 times): the "BOS move" is the LAST swing
        # before the break, not the whole leg from its extreme; a candle A price came back through before the BOS is no zone
        o = move_start(bars, o, x, buy, n)
        base = {"side": "demand" if buy else "supply", "dir": side, "event": k, "bos_level": e["level"],
                "level_idx": e["level_idx"], "origin": o, "leg_origin": e["origin"]["idx"], "break": x}
        gaps = []
        for a in range(max(o, 0), x - 1):                     # A = a, B = a+1, C = a+2, all inside the BOS move
            c = a + 2
            ba, bc = bars[a], bars[c]
            if buy and bc["l"] > ba["h"]:
                gap = (ba["h"], bc["l"])
            elif not buy and bc["h"] < ba["l"]:
                gap = (bc["h"], ba["l"])
            else:
                continue
            d = c + 1                                          # the 4th candle
            filled = d < N and ((buy and bars[d]["l"] <= ba["h"]) or (not buy and bars[d]["h"] >= ba["l"]))
            at = A[a] if A[a] == A[a] else None
            # price back into candle A before the BOS = the zone was already used; not fresh, not a zone
            touched = any((bars[i]["l"] <= ba["h"]) if buy else (bars[i]["h"] >= ba["l"]) for i in range(d + 1, x))
            gaps.append({"a": a, "bottom": gap[0], "top": gap[1], "filled": filled or touched, "touched_before_bos": touched,
                         "atr": round((gap[1] - gap[0]) / at, 2) if at else None})
        pick = next((g for g in gaps if not g["filled"]), None)
        if pick is None:
            why = ("the 4th candle filled every gap in the BOS move, or price came back through candle A before the BOS"
                   if gaps else "no gap (A-B-C) inside the BOS move")
            out.append(dict(base, a=None, top=None, bottom=None, mid=None, proximal=None, distal=None, fvg=None,
                            others=gaps, valid=False, why=why, status=None, touch_idx=None, broken_idx=None,
                            superseded_idx=None, end_idx=None, live=False))
            continue
        ba = bars[pick["a"]]
        z = dict(base, a=pick["a"], top=ba["h"], bottom=ba["l"], mid=(ba["h"] + ba["l"]) / 2,
                 proximal=ba["h"] if buy else ba["l"], distal=ba["l"] if buy else ba["h"],
                 fvg={"bottom": pick["bottom"], "top": pick["top"], "atr": pick["atr"]},
                 others=[g for g in gaps if g is not pick], valid=True, why=None)
        _track(bars, z, m)
        _targets(bars, z)
        out.append(z)
    return out


def move_start(bars: List[Dict], o: int, x: int, buy: bool, n: int = 5) -> int:
    """Where the move that broke structure starts: the last n-bar swing (low for a bull BOS, high for a bear BOS)
    before the break candle x, inside the leg [o, x]. No swing in the leg → the leg's origin o."""
    for i in range(x - n, o, -1):
        lo, hi = max(o, i - n), min(x, i + n)
        if buy and bars[i]["l"] <= min(bars[j]["l"] for j in range(lo, hi + 1)):
            return i
        if not buy and bars[i]["h"] >= max(bars[j]["h"] for j in range(lo, hi + 1)):
            return i
    return o


FIB_TARGETS = (0.618, 0.5, 0.382)       # T1, T2, T3 — Fib levels with 1 = the entry and 0 = the recent high / low


def _targets(bars, z) -> None:
    buy = z["dir"] == "buy"
    end = next(i for i in (z["touch_idx"], z["end_idx"], len(bars)) if i is not None)
    seg = bars[z["a"]:max(end, z["break"] + 1)]
    ext = max(b["h"] for b in seg) if buy else min(b["l"] for b in seg)
    e = z["proximal"]
    z["fib_ext"] = ext
    z["targets"] = [{"fib": f, "price": ext + f * (e - ext)} for f in FIB_TARGETS]
    risk = abs(e - z["distal"])
    for t in z["targets"]:
        t["rr"] = round(abs(t["price"] - e) / risk, 2) if risk else None


def _track(bars, z, m) -> None:
    buy = z["dir"] == "buy"
    z.update(status="fresh", touch_idx=None, broken_idx=None, superseded_idx=None)
    for k in range(z["break"] + 1, len(bars)):
        b = bars[k]
        if (buy and b["c"] < z["distal"]) or (not buy and b["c"] > z["distal"]):
            z["broken_idx"], z["status"] = k, "broken"
            break
        if z["touch_idx"] is None and ((buy and b["l"] <= z["proximal"]) or (not buy and b["h"] >= z["proximal"])):
            z["touch_idx"], z["status"] = k, "tested"
    ch = next((e["idx"] for e in m["events"] if e["kind"] == "CHoCH" and e["side"] != z["dir"] and e["idx"] > z["break"]), None)
    z["superseded_idx"] = ch
    ends = [i for i in (z["broken_idx"], ch) if i is not None]
    z["end_idx"] = min(ends) if ends else None
    z["live"] = z["end_idx"] is None
    if z["touch_idx"] is not None and z["end_idx"] is not None and z["touch_idx"] > z["end_idx"]:
        z["touch_idx"] = None                         # came back only after the zone was over → no entry
