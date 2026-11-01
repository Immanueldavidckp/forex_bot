"""
engine/order_blocks.py — ORDER BLOCKS the way ICT and the SMC indicators draw them, researched 2026-11-01 for David
(the "misunderstanding between the order block and supply and demand"). Report with every source:
engine/research/ob_sd/order_block.md §9 (and ob_vs_sd.md for the difference to a supply / demand zone).

An order block is ONE candle (or a few down candles in a row, blended): the opposite-colour candle at the EXTREME of
the leg that broke structure — not the base of small candles (that is the supply / demand zone: engine/sd_classic.py).

  1 structure   David's major structure: a break = a CLOSE beyond the protected swing (BOS / CHoCH)
  2 leg         origin = the lowest low (bullish) since the broken swing … the break bar x
  3 displacement the leg has a candle of its own direction with body ≥ 1.5 × the average body of the 10 before (David),
                and the run from the block's top to the break is ≥ 2 × the block's body (ICT "two to three times")
  4 the candle  kind "extreme" (ICT 2016, LuxAlgo, joshyattridge): among the DOWN-close candles of [origin − 5 … x − 1]
                the one with the lowest low (tie → the bigger body). kind "last" (David's V5 text / the OB layer in
                smc_marks.py): the last down-close candle ≤ 5 bars before the first displacement candle
  5 none        the extreme candle is an up candle with no down candle in the 5 before it → no block
  6 blend       adjacent down candles before it join the block (≤ 4 in a row): ICT "blend them together"
  7 box         full high – low; body_top = the highest open (ICT's entry), mean = 50 % of the body (ICT's mean
                threshold), mid = 50 % of the box
  8 grades      FVG in the leg after the block +2 · the block swept a prior swing low +2 (swept) · in discount (lower
                half of the last 200 bars) +2 · body ≥ 50 % of its range +1 · it is the leg's extreme bar +2 · BOS (not
                CHoCH) +1  → 0–10, shown, never a filter
  9 one per break; a block overlapping a live same-side block of an earlier break is not drawn again
 10 life        fresh → tested (a wick into the box) → mean (past the body's 50 %) → invalid on a CLOSE beyond the far
                edge → breaker (if it had swept liquidity) else mitigation block → dead on a close back through the
                near edge; a fresh block older than 600 bars is stale

    blocks(bars, m, kind="extreme") → one block per major break, oldest first     bars [{t, o, h, l, c}]
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .major_structure import atr14, major_structure

AVG_BARS = 10
DISP_X = 1.5
RUN_BODY_X = 2.0
NEAR = 5                 # the block must sit within 5 bars of the leg's extreme
BLEND_MAX = 4
SWEEP_LOOK = 50
STALE_BARS = 600
CURVE_BARS = 200
PIVOT = 3


def _body(b):
    return abs(b["c"] - b["o"])


def _against(b, side):            # the block's own colour: a DOWN candle for a bullish block
    return b["c"] < b["o"] if side == "buy" else b["c"] > b["o"]


def blocks(bars: List[Dict], m: Optional[Dict] = None, kind: str = "extreme", n: int = 5) -> List[Dict]:
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
    for e in m["events"]:
        side, o, x = e["side"], e["origin"]["idx"], e["idx"]
        buy = side == "buy"
        disp = [i for i in range(o, x + 1) if avg[i] and not _against(bars[i], side) and bodies[i] >= DISP_X * avg[i]
                and bars[i]["c"] != bars[i]["o"]]
        if not disp:
            continue                                                        # 3: no displacement, no order block
        if kind == "last":
            cands = [i for i in range(max(0, disp[0] - NEAR), disp[0]) if _against(bars[i], side)]
            c = cands[-1] if cands else None
        else:
            lo = max(0, o - NEAR)
            if not _against(bars[o], side) and not any(_against(bars[i], side) for i in range(lo, o)):
                continue                                                    # 5: no down candle at the extreme
            cands = [i for i in range(lo, x) if _against(bars[i], side)]
            key = (lambda i: (bars[i]["l"], -bodies[i])) if buy else (lambda i: (-bars[i]["h"], -bodies[i]))
            c = min(cands, key=key) if cands else None
        if c is None:
            continue
        run = [c]                                                           # 6: blend the down candles before it
        while len(run) < BLEND_MAX and run[0] - 1 >= 0 and _against(bars[run[0] - 1], side):
            run.insert(0, run[0] - 1)
        top, bot = max(bars[i]["h"] for i in run), min(bars[i]["l"] for i in run)
        body_top = max(bars[i]["o"] for i in run) if buy else max(bars[i]["c"] for i in run)
        body_bot = min(bars[i]["c"] for i in run) if buy else min(bars[i]["o"] for i in run)
        body_h = max(body_top - body_bot, 1e-12)
        far = max(b["h"] for b in bars[c:x + 1]) - top if buy else bot - min(b["l"] for b in bars[c:x + 1])
        if far < RUN_BODY_X * body_h:
            continue                                                        # 3: the run is not 2 × the block's body
        z = {"side": "bull" if buy else "bear", "dir": side, "kind": kind, "event_kind": e["kind"], "break_idx": x,
             "idx": run[0], "idx_last": c, "n": len(run), "top": top, "bottom": bot, "body_top": body_top,
             "body_bottom": body_bot, "mean": (body_top + body_bot) / 2, "mid": (top + bot) / 2,
             "extreme": bool(c == o or bars[c]["l" if buy else "h"] == bars[o]["l" if buy else "h"])}
        _grades(bars, z, A, x, m)
        _track(bars, z)
        if any(q["dir"] == side and q["idx"] != z["idx"] and z["bottom"] < q["top"] and z["top"] > q["bottom"]
               and (q["end_idx"] is None or q["end_idx"] > x) for q in out):
            continue                                                        # 9: one live block per area
        if any(q["idx"] == z["idx"] and q["dir"] == side for q in out):
            continue
        out.append(z)
    return out


def _grades(bars, z, A, x, m) -> None:
    buy = z["dir"] == "buy"
    c = z["idx_last"]
    fvg = any((bars[i + 1]["l"] > bars[i - 1]["h"]) if buy else (bars[i + 1]["h"] < bars[i - 1]["l"]) for i in range(c + 1, x))
    swept = False
    lo = max(PIVOT, z["idx"] - SWEEP_LOOK)
    for p in range(z["idx"] - 1, lo, -1):                               # the latest pivot before the block
        win = bars[p - PIVOT:p + PIVOT + 1]
        if len(win) < 2 * PIVOT + 1:
            continue
        if buy and bars[p]["l"] == min(b["l"] for b in win):
            swept = z["bottom"] < bars[p]["l"]
            break
        if not buy and bars[p]["h"] == max(b["h"] for b in win):
            swept = z["top"] > bars[p]["h"]
            break
    w = bars[max(0, z["idx"] - CURVE_BARS):z["idx"] + 1]
    hi, lo2 = max(b["h"] for b in w), min(b["l"] for b in w)
    disc = (z["mid"] < (hi + lo2) / 2) if buy else (z["mid"] > (hi + lo2) / 2)
    b = bars[c]
    strong = b["h"] > b["l"] and abs(b["c"] - b["o"]) >= 0.5 * (b["h"] - b["l"])
    parts = {"fvg": 2 if fvg else 0, "swept": 2 if swept else 0, "discount" if buy else "premium": 2 if disc else 0,
             "body": 1 if strong else 0, "extreme": 2 if z["extreme"] else 0, "bos": 1 if z["event_kind"] == "BOS" else 0}
    z.update(fvg=bool(fvg), swept=bool(swept), parts=parts, score=int(sum(parts.values())))


def _track(bars, z) -> None:
    buy = z["dir"] == "buy"
    z.update(status="fresh", touch_idx=None, mean_idx=None, invalid_idx=None, flip=None, dead_idx=None, stale_idx=None)
    for k in range(z["break_idx"] + 1, len(bars)):
        b = bars[k]
        if z["invalid_idx"] is None:
            if (buy and b["c"] < z["bottom"]) or (not buy and b["c"] > z["top"]):
                z["invalid_idx"], z["flip"] = k, "breaker" if z["swept"] else "mitigation block"
                z["status"] = z["flip"]
                continue
            if z["touch_idx"] is None and ((buy and b["l"] <= z["top"]) or (not buy and b["h"] >= z["bottom"])):
                z["touch_idx"], z["status"] = k, "tested"
            if z["mean_idx"] is None and ((buy and b["l"] <= z["mean"]) or (not buy and b["h"] >= z["mean"])):
                z["mean_idx"], z["status"] = k, "mean"
            if z["touch_idx"] is None and k - z["idx"] > STALE_BARS:
                z["stale_idx"], z["status"] = k, "stale"
                break
        elif (buy and b["c"] > z["top"]) or (not buy and b["c"] < z["bottom"]):
            z["dead_idx"], z["status"] = k, "dead"
            break
    z["end_idx"] = z["invalid_idx"] if z["invalid_idx"] is not None else z["stale_idx"]
    z["live"] = z["end_idx"] is None
