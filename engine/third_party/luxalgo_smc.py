# This work is licensed under a Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)
# https://creativecommons.org/licenses/by-nc-sa/4.0/
# Python port of "Smart Money Concepts [LuxAlgo]" © LuxAlgo, following the Pine original statement by statement and
# Ismaël Ladjohounlou's MQL5 port (github.com/GeneralTradingSarl/Smart-Money-Concepts, same licence) for Pine's na
# and float semantics. Made for David's V5 dashboard (2026-10-28), non-commercial use only; same licence.
"""LuxAlgo Smart Money Concepts as data: internal (5) and swing (50) structure with BOS / CHoCH, order blocks
(ATR filter, high/low mitigation), equal highs / lows, fair value gaps (auto threshold), swing points
HH / HL / LH / LL, strong / weak high / low and premium / equilibrium / discount, in Historical mode.

    smc(t, o, h, l, c) -> dict          t = bar times (any int unit, returned as given), every bar computed

Settings are LuxAlgo's defaults plus what David's MT5 chart showed: swing points, swing order blocks, fair value
gaps and premium / discount on. Checked against what the MT5 port drew on our own bars (test_smc_compare.py).
"""
from __future__ import annotations

from typing import Dict, List, Optional

EPS = 1e-10                      # Pine compares floats with an absolute tolerance of 1e-10 (measured by the MQL5 port)
BULLISH, BEARISH = 1, -1
BULLISH_LEG, BEARISH_LEG = 1, 0
NA = None


def gt(a, b): return a - b > EPS
def lt(a, b): return b - a > EPS
def ge(a, b): return not lt(a, b)
def le(a, b): return not gt(a, b)
def eq(a, b): return not gt(a, b) and not lt(a, b)


class _Pivot:
    __slots__ = ("level", "last", "crossed", "t", "i")

    def __init__(self):
        self.level = self.last = self.t = self.i = NA
        self.crossed = False


def smc(t: List[int], o: List[float], h: List[float], l: List[float], c: List[float],
        swing_len: int = 50, internal_len: int = 5, equal_len: int = 3, equal_threshold: float = 0.1,
        ob_shown: int = 5, mitigation: str = "highlow", fvg_extend: int = 1) -> Dict:
    n = len(c)
    out = {"breaks": [], "swings": [], "obs": [], "fvgs": [], "equal": []}
    swingHigh, swingLow, internalHigh, internalLow, equalHigh, equalLow = (_Pivot() for _ in range(6))
    swingTrend = internalTrend = 0
    trail = {"top": NA, "bottom": NA, "t": NA, "i": NA, "top_t": NA, "bottom_t": NA}
    leg_value = [0, 0, 0]
    leg_prev = [NA, NA, NA]
    cross_prev = [NA, NA, NA, NA]
    PH, PL = [0.0] * n, [0.0] * n
    obs = {"internal": [], "swing": []}            # live, newest first (Pine unshift)
    fvgs: List[Dict] = []
    atr, atr_n, atr_sum, cum_fvg = NA, 0, 0.0, 0.0

    def leg(i, size, site):
        j = i - size
        if j >= 0:
            hi, lo = max(h[i - size + 1:i + 1]), min(l[i - size + 1:i + 1])
            if gt(h[j], hi):
                leg_value[site] = BEARISH_LEG
            elif lt(l[j], lo):
                leg_value[site] = BULLISH_LEG
        return leg_value[site]

    def new_pivot(p, i, size, low, equal_hl, internal):
        lvl = l[i - size] if low else h[i - size]
        if equal_hl and p.level is not NA and atr is not NA and lt(abs(p.level - lvl), equal_threshold * atr):
            out["equal"].append({"text": "EQL" if low else "EQH", "level": lvl, "level_from": p.level,
                                 "t_from": p.t, "t": t[i - size], "t_known": t[i]})
        p.last, p.level, p.crossed, p.t, p.i = p.level, lvl, False, t[i - size], i - size
        if not equal_hl and not internal:
            trail["bottom" if low else "top"] = lvl
            trail["t"], trail["i"] = p.t, p.i
            trail["bottom_t" if low else "top_t"] = p.t
            if low:
                txt = "LL" if p.last is not NA and lt(lvl, p.last) else "HL"
            else:
                txt = "HH" if p.last is not NA and gt(lvl, p.last) else "LH"
            out["swings"].append({"text": txt, "price": lvl, "t": p.t, "t_known": t[i]})

    def structure(i, size, equal_hl, internal):
        site = 2 if equal_hl else 1 if internal else 0
        cur = leg(i, size, site)
        prev, leg_prev[site] = leg_prev[site], cur
        if prev is NA or cur == prev:
            return
        if cur - prev == 1:
            new_pivot(equalLow if equal_hl else internalLow if internal else swingLow, i, size, True, equal_hl, internal)
        else:
            new_pivot(equalHigh if equal_hl else internalHigh if internal else swingHigh, i, size, False, equal_hl, internal)

    def store_ob(p, internal, bias, i):
        frm = p.i
        if frm is NA or frm >= i:
            return
        arr = PH if bias == BEARISH else PL
        ext = max(arr[frm:i]) if bias == BEARISH else min(arr[frm:i])
        k = frm
        while k < i - 1 and not eq(arr[k], ext):
            k += 1
        lst = obs["internal" if internal else "swing"]
        if len(lst) >= 100:
            lst.pop()
        ob = {"scope": "internal" if internal else "swing", "side": "bull" if bias == BULLISH else "bear",
              "top": PH[k], "bottom": PL[k], "t0": t[k], "t_born": t[i], "t_end": NA}
        lst.insert(0, ob)
        out["obs"].append(ob)

    def brk(p, trend, i, internal, extra, bull, site):
        level, previous = p.level, cross_prev[site]
        cross_prev[site] = level
        if i == 0 or level is NA or previous is NA:
            return trend
        crossed = (gt(c[i], level) and le(c[i - 1], previous)) if bull else (lt(c[i], level) and ge(c[i - 1], previous))
        if not (crossed and not p.crossed and extra):
            return trend
        choch = trend == (BEARISH if bull else BULLISH)
        p.crossed = True
        out["breaks"].append({"kind": "CHoCH" if choch else "BOS", "side": "bull" if bull else "bear",
                              "scope": "internal" if internal else "swing", "level": level, "t_from": p.t, "t": t[i]})
        store_ob(p, internal, BULLISH if bull else BEARISH, i)
        return BULLISH if bull else BEARISH

    for i in range(n):
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) if i > 0 else h[i] - l[i]
        atr_n += 1
        if atr_n < 200:
            atr_sum += tr
        elif atr_n == 200:
            atr = (atr_sum + tr) / 200
        else:
            atr = tr / 200 + (1 - 1 / 200) * atr
        hv = atr is not NA and ge(h[i] - l[i], 2 * atr)
        PH[i], PL[i] = (l[i], h[i]) if hv else (h[i], l[i])

        # trailing extremes (math.max / math.min stay na while the extreme is na)
        if trail["top"] is not NA:
            trail["top"] = max(h[i], trail["top"])
            if eq(trail["top"], h[i]):
                trail["top_t"] = t[i]
        if trail["bottom"] is not NA:
            trail["bottom"] = min(l[i], trail["bottom"])
            if eq(trail["bottom"], l[i]):
                trail["bottom_t"] = t[i]

        # fair value gaps mitigated (Pine's for-in skips the element after a removed one)
        k = 0
        while k < len(fvgs):
            f = fvgs[k]
            if (lt(l[i], f["bottom"]) and f["side"] == "bull") or (gt(h[i], f["top"]) and f["side"] == "bear"):
                f["t_end"] = t[i]
                fvgs.pop(k)
            k += 1

        structure(i, swing_len, False, False)
        structure(i, internal_len, False, True)
        structure(i, equal_len, True, False)

        # internal structure: no break on a level the swing structure holds too
        extra = internalHigh.level is not NA and swingHigh.level is not NA and not eq(internalHigh.level, swingHigh.level)
        internalTrend = brk(internalHigh, internalTrend, i, True, extra, True, 0)
        extra = internalLow.level is not NA and swingLow.level is not NA and not eq(internalLow.level, swingLow.level)
        internalTrend = brk(internalLow, internalTrend, i, True, extra, False, 1)
        swingTrend = brk(swingHigh, swingTrend, i, False, True, True, 2)
        swingTrend = brk(swingLow, swingTrend, i, False, True, False, 3)

        bear_src = c[i] if mitigation == "close" else h[i]
        bull_src = c[i] if mitigation == "close" else l[i]
        for scope in ("internal", "swing"):
            lst, k = obs[scope], 0
            while k < len(lst):
                ob = lst[k]
                if (ob["side"] == "bear" and gt(bear_src, ob["top"])) or (ob["side"] == "bull" and lt(bull_src, ob["bottom"])):
                    ob["t_end"] = t[i]
                    lst.pop(k)
                k += 1

        # fair value gaps, chart timeframe, auto threshold
        if i >= 1:
            delta = (c[i - 1] - o[i - 1]) / (o[i - 1] * 100)
            cum_fvg += abs(delta)
            thr = cum_fvg / i * 2
            if i >= 2:
                if gt(l[i], h[i - 2]) and gt(c[i - 1], h[i - 2]) and gt(delta, thr):
                    f = {"side": "bull", "top": l[i], "bottom": h[i - 2], "t0": t[i - 1], "t1": t[i] + fvg_extend * (t[i] - t[i - 1]),
                         "t_born": t[i], "t_end": NA}
                    fvgs.insert(0, f); out["fvgs"].append(f)
                if lt(h[i], l[i - 2]) and lt(c[i - 1], l[i - 2]) and gt(-delta, thr):
                    # LuxAlgo keeps the bearish gap as top = this bar's high (the LOWER edge): any wick into the gap
                    # mitigates it, while a bullish gap needs a wick through its whole width
                    f = {"side": "bear", "top": h[i], "bottom": l[i - 2], "t0": t[i - 1], "t1": t[i] + fvg_extend * (t[i] - t[i - 1]),
                         "t_born": t[i], "t_end": NA}
                    fvgs.insert(0, f); out["fvgs"].append(f)

    for scope in ("internal", "swing"):
        for k, ob in enumerate(obs[scope]):
            ob["shown"] = k < ob_shown          # LuxAlgo draws the newest 5 live order blocks per kind
    for f in out["fvgs"]:                       # stored as Pine does; for drawing: low / high edge
        f["lo"], f["hi"] = min(f["top"], f["bottom"]), max(f["top"], f["bottom"])
    top, bot = trail["top"], trail["bottom"]
    zones = None
    if top is not NA and bot is not NA:
        zones = {"premium": (0.95 * top + 0.05 * bot, top), "equilibrium": (0.525 * bot + 0.475 * top, 0.525 * top + 0.475 * bot),
                 "discount": (bot, 0.95 * bot + 0.05 * top), "t0": trail["t"]}
    out.update(trend={"swing": swingTrend, "internal": internalTrend},
               trailing={"top": top, "bottom": bot, "top_t": trail["top_t"], "bottom_t": trail["bottom_t"],
                         "top_text": "Strong High" if swingTrend == BEARISH else "Weak High",
                         "bottom_text": "Strong Low" if swingTrend == BULLISH else "Weak Low"},
               zones=zones)
    return out
