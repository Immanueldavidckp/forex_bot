"""
engine/sd_classic.py — SUPPLY / DEMAND the way the supply/demand school draws it (Seiden / Online Trading Academy and
the S&D educators), researched 2026-11-01 for David ("the supply and demand are fully wrong … there is a
misunderstanding on the internet between the order block and supply and demand"). Report with every source:
engine/research/ob_sd/supply_demand.md §11 (and ob_vs_sd.md for the difference to an order block).

A zone is the BASE where price paused before a strong move away, at the ORIGIN of the move — not the last opposite
candle (that is the order block: engine/order_blocks.py).

  1 candles     base = body ≤ 50 % of its range (doji = base); leg = body > 50 %; explosive = leg AND (body ≥ 1.5 × the
                average body of the 10 before [David] OR range ≥ 1.5 × ATR14)
  2 departure   an explosive candle d that CLOSES beyond the high (demand) / low (supply) of every base candle before it
  3 base        the run of base candles right before d, 1–6 (7+ = a range → no zone); none → the single opposite-colour
                candle right before d (the one case where zone = order block); a same-colour leg before d → no zone
                (d is inside a leg)
  4 pattern     leg-in = the nearest leg candle before the base: up → R, down → D;  RBR / DBR demand, RBD / DBD supply;
                DBR / RBD = reversal (at the extremes), RBR / DBD = continuation
  5 box         demand: proximal = the highest BODY of the base, distal = the lowest wick of the base ∪ d (reversal: ∪ the
                leg-in candle next to the base); supply mirrored. The wick proximal is kept too.
  6 departure   the move must get ≥ 2 × the box height (and ≥ 1.5 ATR) beyond the proximal within 10 bars, with at
     test       least one whole candle outside the box, before price comes back. The zone exists from that bar on.
  7 width       a box taller than 1.5 ATR is refined to the last base candles; still too tall → no zone
  8 origin      per leg of David's major structure (swing low → swing high for demand): the ORIGIN zone is the first
                valid zone whose base holds the swing bar or starts ≤ 2 bars after it; later ones in the same leg are
                CONTINUATION zones, dropped when they overlap the origin box
  9 BOS         not required by this school; a zone whose departure made a major BOS / CHoCH is flagged (bos = True)
 10 score 0–10  departure 0–2 · time at level 0–2 (1–2 base candles 2, 3–4 1, 5–6 0) · freshness 0–2 · profit zone 0–2
                (room to the nearest opposing zone ≥ 4 / ≥ 2 box heights) · curve 0–2 (thirds of the last 200 bars)
 11 life        fresh → tested (a wick reaches the proximal) → spent after 3 visits (a visit ends 3 bars outside) →
                broken on one CLOSE beyond the distal; superseded by a CHoCH against it

    zones(bars, m) → every zone, oldest first        bars [{t, o, h, l, c}]      m = major_structure(bars, 5)
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .major_structure import atr14, major_structure

BASE_BODY = 0.50            # body / range at or below → base candle
EXPLOSIVE_BODY_X = 1.5      # × the average body of the 10 before (David)
EXPLOSIVE_RANGE_ATR = 1.5   # or range ≥ 1.5 ATR14
AVG_BARS = 10
MAX_BASE = 6
LEGIN_LOOK = 5
DEPART_H = 2.0              # the departure must reach 2 × the box height beyond the proximal …
DEPART_ATR = 1.5            # … and 1.5 ATR
DEPART_BARS = 10            # … within 10 bars
MAX_HEIGHT_ATR = 1.5
ORIGIN_SLACK = 2            # the base may start ≤ 2 bars after the swing bar and still be the origin
VISIT_GAP, SPENT_VISITS = 3, 3
CURVE_BARS = 200
SIDE = {"buy": "demand", "sell": "supply"}


def _body(b):
    return abs(b["c"] - b["o"])


def _rng(b):
    return b["h"] - b["l"]


def _is_base(b):
    r = _rng(b)
    return r <= 0 or _body(b) <= BASE_BODY * r


def _up(b):
    return b["c"] > b["o"]


def _down(b):
    return b["c"] < b["o"]


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

    def explosive(i, side):
        b = bars[i]
        if _is_base(b) or (side == "buy" and not _up(b)) or (side == "sell" and not _down(b)):
            return False
        a = A[i] if A[i] == A[i] else None
        return bool((avg[i] and bodies[i] >= EXPLOSIVE_BODY_X * avg[i]) or (a and _rng(b) >= EXPLOSIVE_RANGE_ATR * a))

    out: List[Dict] = []
    for d in range(AVG_BARS + 1, N):
        for side in ("buy", "sell"):
            if not explosive(d, side):
                continue
            z = _zone_at(bars, A, d, side)
            if z:
                out.append(z)
    _legs(bars, m, out)
    out = [z for z in out if z["role"] != "drop"]
    for z in out:
        _track(bars, z, m)
    _score(bars, out, avg)
    return out


def _zone_at(bars, A, d, side) -> Optional[Dict]:
    buy = side == "buy"
    # 3 the base: consecutive base candles right before d
    j = d - 1
    base = []
    while j >= 0 and _is_base(bars[j]) and len(base) <= MAX_BASE:
        base.insert(0, j)
        j -= 1
    if len(base) > MAX_BASE:
        return None                                      # 7+ small candles = a range, not a base
    single = False
    if not base:
        p = bars[d - 1]
        if (buy and _down(p)) or (not buy and _up(p)):
            base, single = [d - 1], True                 # no pause: the opposite candle itself (= the order block)
        else:
            return None                                  # a same-colour leg before d: d is inside a leg
    # 2 the departure closes beyond the whole base
    if buy and not bars[d]["c"] > max(bars[i]["h"] for i in base):
        return None
    if not buy and not bars[d]["c"] < min(bars[i]["l"] for i in base):
        return None
    # 4 leg-in
    k0 = base[0] - 1
    legin = next((k for k in range(k0, max(-1, k0 - LEGIN_LOOK), -1) if not _is_base(bars[k])), None)
    li = "R" if legin is not None and _up(bars[legin]) else "D" if legin is not None else ("R" if buy else "D")
    kind = li + "B" + ("R" if buy else "D")
    reversal = kind in ("DBR", "RBD")
    # 5 the box
    ext = base + [d] + ([k0] if reversal and legin == k0 else [])
    if buy:
        prox = max(max(bars[i]["o"], bars[i]["c"]) for i in base)
        prox_w = max(bars[i]["h"] for i in base)
        dist = min(bars[i]["l"] for i in ext)
    else:
        prox = min(min(bars[i]["o"], bars[i]["c"]) for i in base)
        prox_w = min(bars[i]["l"] for i in base)
        dist = max(bars[i]["h"] for i in ext)
    a = A[d] if A[d] == A[d] else None
    # 7 width: refine to the last base candles
    if a and abs(prox - dist) > MAX_HEIGHT_ATR * a and len(base) > 1:
        for k in range(len(base) - 1, 0, -1):
            sub = base[k:]
            p2 = max(max(bars[i]["o"], bars[i]["c"]) for i in sub) if buy else min(min(bars[i]["o"], bars[i]["c"]) for i in sub)
            d2 = min(bars[i]["l"] for i in sub + [d]) if buy else max(bars[i]["h"] for i in sub + [d])
            if abs(p2 - d2) <= MAX_HEIGHT_ATR * a:
                base, prox, dist = sub, p2, d2
                prox_w = max(bars[i]["h"] for i in sub) if buy else min(bars[i]["l"] for i in sub)
                break
    H = abs(prox - dist)
    if H <= 0 or (a and H > MAX_HEIGHT_ATR * a):
        return None
    # 6 the departure test: ≥ 2 H and ≥ 1.5 ATR beyond the proximal within 10 bars, a whole candle outside, no return
    need = max(DEPART_H * H, DEPART_ATR * (a or 0))
    best, outside, valid = 0.0, False, None
    for k in range(d + 1, min(d + 1 + DEPART_BARS, len(bars))):
        b = bars[k]
        if (buy and b["l"] <= prox) or (not buy and b["h"] >= prox):
            break
        best = max(best, (b["h"] - prox) if buy else (prox - b["l"]))
        outside = True
        if best >= need:
            valid = k
            break
    if valid is None:
        return None
    return {"side": SIDE[side], "dir": side, "kind": kind, "reversal": reversal, "single": single,
            "base": [base[0], base[-1]], "base_n": len(base), "d": d, "valid_idx": valid,
            "proximal": prox, "proximal_wick": prox_w, "distal": dist,
            "top": max(prox, dist), "bottom": min(prox, dist), "height_atr": round(H / a, 2) if a else None,
            "run_h": round(best / H, 2), "disp_x": round(_body(bars[d]) / (sum(_body(bars[i]) for i in range(d - AVG_BARS, d)) / AVG_BARS), 2)}


def _legs(bars, m, zs) -> None:
    """8: origin vs continuation per leg of the major structure; overlapping boxes of one leg merge into the earliest."""
    pts = sorted(m["points"], key=lambda q: q["idx"])
    for z in zs:
        z["role"], z["leg"], z["bos"] = "continuation", None, False
    for z in zs:
        want = "low" if z["dir"] == "buy" else "high"
        start = max((q for q in pts if q["kind"] == want and q["idx"] <= z["d"]), key=lambda q: q["idx"], default=None)
        if start is None:
            continue
        z["leg"] = start["idx"]
        if z["base"][0] - ORIGIN_SLACK <= start["idx"] <= z["base"][1] + 1 or 0 <= z["base"][0] - start["idx"] <= ORIGIN_SLACK:
            z["role"] = "origin"
        # 9 BOS flag: a major break of this side whose move contains the departure
        z["bos"] = bool(any(e["side"] == z["dir"] and e["origin"]["idx"] - ORIGIN_SLACK <= z["d"] <= e["idx"] for e in m["events"]))
    by_leg: Dict = {}
    for z in sorted(zs, key=lambda q: q["d"]):
        key = (z["dir"], z["leg"])
        kept = by_leg.setdefault(key, [])
        if any(z["bottom"] < q["top"] and z["top"] > q["bottom"] for q in kept):
            z["role"] = "drop"
            continue
        if z["role"] == "origin" and any(q["role"] == "origin" for q in kept):
            z["role"] = "continuation"
        kept.append(z)


def _track(bars, z, m) -> None:
    """11: life from the bar the zone became valid."""
    buy = z["dir"] == "buy"
    prox, dist = z["proximal"], z["distal"]
    z.update(status="fresh", touches=0, touch_idx=None, deep=False, broken_idx=None, spent_idx=None, superseded_idx=None)
    inside, out_n = False, 0
    for k in range(z["valid_idx"] + 1, len(bars)):
        b = bars[k]
        if (buy and b["c"] < dist) or (not buy and b["c"] > dist):
            z["broken_idx"], z["status"] = k, "broken"
            break
        hit = (b["l"] <= prox) if buy else (b["h"] >= prox)
        if hit:
            if not inside:
                z["touches"] += 1
                z["touch_idx"] = z["touch_idx"] if z["touch_idx"] is not None else k
                if z["touches"] >= SPENT_VISITS:
                    z["spent_idx"], z["status"] = k, "spent"
                    break
                z["status"] = "tested"
            inside, out_n = True, 0
            mid = (prox + dist) / 2
            if (buy and b["l"] <= mid) or (not buy and b["h"] >= mid):
                z["deep"] = True
        elif inside:
            out_n += 1
            if out_n >= VISIT_GAP:
                inside = False
    against = [e for e in m["events"] if e["kind"] == "CHoCH" and e["side"] != z["dir"] and e["idx"] > z["valid_idx"]]
    if against:
        z["superseded_idx"] = against[0]["idx"]
    end = [x for x in (z["broken_idx"], z["spent_idx"], z["superseded_idx"]) if x is not None]
    z["end_idx"] = min(end) if end else None
    z["live"] = z["end_idx"] is None


def _score(bars, zs, avg) -> None:
    """10: the OTA odds enhancers, 0–10 (shown, never a filter)."""
    for z in zs:
        H = z["top"] - z["bottom"]
        dep = 2 if z["run_h"] >= 4 or (z["disp_x"] or 0) >= 2.5 else 1
        tal = 2 if z["base_n"] <= 2 else 1 if z["base_n"] <= 4 else 0
        fresh = 2 if z["touches"] == 0 else 1 if z["touches"] == 1 else 0
        opp = [q for q in zs if q["dir"] != z["dir"] and q["valid_idx"] <= z["valid_idx"]
               and (q["end_idx"] is None or q["end_idx"] > z["valid_idx"])]
        if z["dir"] == "buy":
            room = min((q["bottom"] - z["proximal"] for q in opp if q["bottom"] > z["proximal"]), default=None)
        else:
            room = min((z["proximal"] - q["top"] for q in opp if q["top"] < z["proximal"]), default=None)
        profit = 2 if room is None or room >= 4 * H else 1 if room >= 2 * H else 0
        w = bars[max(0, z["valid_idx"] - CURVE_BARS):z["valid_idx"] + 1]
        hi, lo = max(b["h"] for b in w), min(b["l"] for b in w)
        pos = (z["proximal"] - lo) / (hi - lo) if hi > lo else 0.5
        curve = (2 if pos < 1 / 3 else 1 if pos < 2 / 3 else 0) if z["dir"] == "buy" else (2 if pos > 2 / 3 else 1 if pos > 1 / 3 else 0)
        z["parts"] = {"departure": dep, "time_at_level": tal, "freshness": fresh, "profit_zone": profit, "curve": curve}
        z["score"] = dep + tal + fresh + profit + curve
