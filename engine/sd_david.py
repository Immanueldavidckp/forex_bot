"""
engine/sd_david.py — David's OWN supply / demand (2026-11-01, after the internet versions were "fully wrong"):

  "if the BULL BOS then mark the DEMAND, if the BEAR BOS then the SUPPLY — only these places we can take the entry;
   once the BOS happened, inside that BOS we should have the FVG, then only that supply or demand is valid"

  1 the break    a BOS of David's structure (major_structure.py: BOS at the leg's extreme by close; CHoCH is not a BOS
                 and gives no zone here). Bull BOS → DEMAND, bear BOS → SUPPLY.
  2 the FVG      the BOS move (its origin → the break candle) must hold an FVG of its own side: a 3-candle gap whose
                 middle candle is inside the move and that is ≥ 0.3 ATR(14) — the same FVGs as the /smc FVG layer
                 (smc_marks.py). No FVG → the zone is NOT valid and is not drawn.
  3 the zone     where the BOS move started (first version, for David to check): the move's origin candle (its lowest
                 low for demand / highest high for supply) and the candles after it up to the first displacement
                 candle of the move (body ≥ 1.5 × the 10 before, David's V5 number), at most 6 candles.
                   demand: far edge = the lowest low (wick), near edge = the highest candle BODY of those candles
                   supply: far edge = the highest high (wick), near edge = the lowest candle BODY
                 If the origin candle is itself the displacement, the zone is that candle's low → open (high → open).
  4 life         fresh → tested (price back at the near edge = the entry place) → broken on a CLOSE beyond the far edge;
                 a CHoCH against it ends it too (the trend it belonged to is over)

    zones(bars, m) → one zone per BOS, oldest first, valid and not valid (valid=False + why)
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .major_structure import atr14, major_structure

FVG_MIN_ATR = 0.3          # = smc_marks.FVG_MIN_ATR (the page's FVG layer)
DISP_X, AVG_BARS = 1.5, 10  # David's displacement
MAX_BASE = 6


def _body(b):
    return abs(b["c"] - b["o"])


def zones(bars: List[Dict], m: Optional[Dict] = None, n: int = 5) -> List[Dict]:
    N = len(bars)
    if N < AVG_BARS + 3:
        return []
    m = m or major_structure(bars, n)
    A = atr14(bars)
    bodies = [_body(b) for b in bars]
    avg = [None] * N
    for i in range(AVG_BARS, N):
        avg[i] = sum(bodies[i - AVG_BARS:i]) / AVG_BARS
    out: List[Dict] = []
    for k, e in enumerate(m["events"]):
        if e["kind"] != "BOS":
            continue
        side, o, x = e["side"], e["origin"]["idx"], e["idx"]
        buy = side == "buy"
        # 2 the FVG inside the BOS move
        fvgs = []
        for i in range(max(o + 1, 1), min(x, N - 2) + 1):
            if i + 1 > x:
                break
            a = A[i - 1] if A[i - 1] == A[i - 1] else None
            if buy and bars[i + 1]["l"] > bars[i - 1]["h"]:
                gap = (bars[i - 1]["h"], bars[i + 1]["l"])
            elif not buy and bars[i + 1]["h"] < bars[i - 1]["l"]:
                gap = (bars[i + 1]["h"], bars[i - 1]["l"])
            else:
                continue
            if a and gap[1] - gap[0] >= FVG_MIN_ATR * a:
                fvgs.append({"bottom": gap[0], "top": gap[1], "idx": i, "atr": round((gap[1] - gap[0]) / a, 2)})
        # 3 the zone where the move started
        d = next((i for i in range(o, x + 1) if avg[i] and bodies[i] >= DISP_X * avg[i]
                  and ((bars[i]["c"] > bars[i]["o"]) if buy else (bars[i]["c"] < bars[i]["o"]))), None)
        if d == o:
            base = [o]
            prox = bars[o]["o"]
        else:
            base = list(range(o, min(d if d is not None else o + 1, o + MAX_BASE)))
            prox = max(max(bars[i]["o"], bars[i]["c"]) for i in base) if buy else min(min(bars[i]["o"], bars[i]["c"]) for i in base)
        dist = min(bars[i]["l"] for i in base) if buy else max(bars[i]["h"] for i in base)
        z = {"side": "demand" if buy else "supply", "dir": side, "event": k, "bos_level": e["level"], "level_idx": e["level_idx"],
             "origin": o, "break": x, "disp": d, "base": [base[0], base[-1]], "proximal": prox, "distal": dist,
             "top": max(prox, dist), "bottom": min(prox, dist), "fvgs": fvgs, "valid": bool(fvgs),
             "why": None if fvgs else "no FVG (≥ 0.3 ATR) inside the BOS move"}
        _track(bars, z, m)
        out.append(z)
    return out


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
