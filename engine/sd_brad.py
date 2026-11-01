"""
engine/sd_brad.py — SUPPLY / DEMAND the way Brad Goh (The Trading Geek) teaches it in "Market Mechanics Ep 7:
Institutional Supply & Demand Zones" (https://www.youtube.com/watch?v=52aKS7HN_jI, watched 2026-11-01 for David via
its captions and frames; notes in engine/research/ob_sd/brad_goh_ep7.md). His method, in short:

  find the imbalance first (the big candles), then trace it back to its ORIGIN — the consolidation it broke out
  of — and that is the zone; the stronger the move away, the more the zone matters (7:43–8:45)
  RANGE method (10:18): box from the highest to the lowest point of that consolidation (wicks); in a pullback with no
  real consolidation, from the pullback's high to its low (12:55); wide boxes are fine (19:42)
  PIVOT method (14:58): only the single candle that caused the reversal, wick included (25:25)
  MITIGATION (23:20): a zone is used only when price comes back into its 50 % line; touching the edge is not enough

Made deterministic (Brad gives no numbers; each choice is named so it can be changed):
  1 imbalance   a "big juicy" candle d: body > 50 % of its range AND body ≥ 1.5 × the average body of the 10 before
                (David's displacement) — the first of a run
  2 origin      the consolidation / pullback = from the latest swing point against the move (for demand: the last
                pivot HIGH, 3 bars each side, within 40 bars before d) to the bar before d — when that span is a
                pullback (≤ 3 ATR tall, ≤ 20 bars): "the high of the pullback to the low of the pullback"; when it is a
                whole move into a turn (spike top / V bottom): only the bars after that move's last big candle (that
                candle too when its wick is the extreme — then it is the pivot candle)
  3 breakout    within 3 bars the move must CLOSE beyond that consolidation's far side (demand: above its high)
  4 range box   highest high → lowest low of the consolidation (wick to wick)
  5 pivot box   the candle with the lowest low (demand) / highest high (supply) of the consolidation, its full range
  6 strength    how far the move went beyond the box within 10 bars, in box heights; zones whose move did not get at
                least 1 range height away are not drawn ("the most obvious ones"); BOS = the move made a major BOS /
                CHoCH (Brad: "causing price to break structure") — shown, not required
  7 overlap     a zone lying at least half inside an earlier live zone of the same side is not drawn twice
  8 life        unmitigated → (touched: the edge only) → MITIGATED when a candle reaches the 50 % line → broken on a close
                beyond the far edge

    zones(bars, m) → oldest first       bars [{t, o, h, l, c}]      m = major_structure(bars, 5)
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .major_structure import atr14, major_structure

AVG_BARS = 10
BIG_BODY_X = 1.5
LOOK = 40
PIVOT = 3
BREAK_BARS = 3
AWAY_BARS = 10
MIN_AWAY = 1.0
PULLBACK_ATR = 3.0          # a span from the last swing up to 3 ATR / 20 bars = a pullback: the WHOLE pullback is the zone
PULLBACK_BARS = 20
OVERLAP = 0.5               # a zone at least half inside an older live zone of the same side is that zone again


def _body(b):
    return abs(b["c"] - b["o"])


def zones(bars: List[Dict], m: Optional[Dict] = None, n: int = 5) -> List[Dict]:
    N = len(bars)
    if N < AVG_BARS + 2 * PIVOT + 2:
        return []
    m = m or major_structure(bars, n)
    A = atr14(bars)
    bodies = [_body(b) for b in bars]
    avg = [None] * N
    for i in range(AVG_BARS, N):
        avg[i] = sum(bodies[i - AVG_BARS:i]) / AVG_BARS

    def big(i, side):
        b = bars[i]
        r = b["h"] - b["l"]
        up = b["c"] > b["o"]
        return bool(r > 0 and bodies[i] > 0.5 * r and avg[i] and bodies[i] >= BIG_BODY_X * avg[i]
                    and (up if side == "buy" else not up))

    def pivot(i, high):
        lo, hi = i - PIVOT, i + PIVOT
        if lo < 0 or hi >= N:
            return False
        w = bars[lo:hi + 1]
        return bars[i]["h"] == max(b["h"] for b in w) if high else bars[i]["l"] == min(b["l"] for b in w)

    out: List[Dict] = []
    for d in range(AVG_BARS + 1, N):
        for side in ("buy", "sell"):
            if not big(d, side) or big(d - 1, side):
                continue
            buy = side == "buy"
            s = next((i for i in range(d - 1 - PIVOT, max(0, d - LOOK) - 1, -1) if pivot(i, high=buy)), None)
            if s is None:
                continue
            a = A[d] if A[d] == A[d] else None
            span_h = max(bars[i]["h"] for i in range(s, d)) - min(bars[i]["l"] for i in range(s, d))
            if (a and span_h > PULLBACK_ATR * a) or d - s > PULLBACK_BARS:
                # not a pullback but a whole move into the turn (a spike top / V bottom): the consolidation is what
                # came AFTER that move's last big candle; if that candle holds the extreme (its wick), it is the pivot
                opp = "sell" if buy else "buy"
                j = next((i for i in range(d - 1, max(0, d - LOOK) - 1, -1) if big(i, opp)), None)
                if j is None:
                    continue
                ext = (min if buy else max)(range(j, d), key=lambda i: bars[i]["l"] if buy else bars[i]["h"])
                s = j if ext == j or j == d - 1 else j + 1
            cons = range(s, d)
            top, bot = max(bars[i]["h"] for i in cons), min(bars[i]["l"] for i in cons)
            H = top - bot
            if H <= 0:
                continue
            brk = next((k for k in range(d, min(d + BREAK_BARS, N)) if (bars[k]["c"] > top if buy else bars[k]["c"] < bot)), None)
            if brk is None:
                continue
            far = bars[d:min(d + AWAY_BARS + 1, N)]
            away = (max(b["h"] for b in far) - top) if buy else (bot - min(b["l"] for b in far))
            if away < MIN_AWAY * H:
                continue
            p = min(cons, key=lambda i: bars[i]["l"]) if buy else max(cons, key=lambda i: bars[i]["h"])
            z = {"side": "demand" if buy else "supply", "dir": side, "s": s, "d": d, "brk": brk, "p": p,
                 "top": top, "bottom": bot, "mid": (top + bot) / 2,
                 "p_top": bars[p]["h"], "p_bottom": bars[p]["l"], "p_mid": (bars[p]["h"] + bars[p]["l"]) / 2,
                 "n": d - s, "away_h": round(away / H, 2),
                 "bos": bool(any(e["side"] == side and e["origin"]["idx"] - 2 <= d <= e["idx"] for e in m["events"]))}
            _track(bars, z)
            if any(q["dir"] == side and (q["end_idx"] is None or q["end_idx"] > d)
                   and min(z["top"], q["top"]) - max(z["bottom"], q["bottom"]) >= OVERLAP * H for q in out):
                continue                                      # half or more of it inside an older live zone: same zone
            out.append(z)
    return out


def _track(bars, z) -> None:
    buy = z["dir"] == "buy"
    z.update(status="unmitigated", touch_idx=None, mitigated_idx=None, broken_idx=None,
             p_mitigated_idx=None)
    for k in range(z["brk"] + 1, len(bars)):
        b = bars[k]
        if (buy and b["c"] < z["bottom"]) or (not buy and b["c"] > z["top"]):
            z["broken_idx"], z["status"] = k, "broken"
            break
        if z["touch_idx"] is None and ((buy and b["l"] <= z["top"]) or (not buy and b["h"] >= z["bottom"])):
            z["touch_idx"] = k
            if z["status"] == "unmitigated":
                z["status"] = "touched"
        if z["p_mitigated_idx"] is None and ((buy and b["l"] <= z["p_mid"]) or (not buy and b["h"] >= z["p_mid"])):
            z["p_mitigated_idx"] = k
        if z["mitigated_idx"] is None and ((buy and b["l"] <= z["mid"]) or (not buy and b["h"] >= z["mid"])):
            z["mitigated_idx"], z["status"] = k, "mitigated"
    z["end_idx"] = z["broken_idx"]
    z["live"] = z["broken_idx"] is None
