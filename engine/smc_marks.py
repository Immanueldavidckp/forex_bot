"""
engine/smc_marks.py — the SMC marks of the /smc page, all hung on David's MAJOR structure (major_structure.py), so
nothing internal is marked (David 2026-10-29: "search the whole thing in the internet and create the remaining
things: OB, FVG, liquidity, premium/discount, mitigation", the way BOS / CHoCH were done). Researched against
public sources by three Fable 5.1 agents (2026-10-29); where David's V5 rules define a thing, they win.

  FVG    a 3-candle gap (closed candles) whose middle candle lies inside the displacement of a major BOS / CHoCH
         (origin < middle ≤ break candle, same side — V5 §5, new rules §12-16) and is ≥ 0.3 ATR(14) (filters G2;
         allanninal 0.2, MQL5 0.5). The gaps of one break are one cluster (new rules §15).
         status: fresh → touched (a wick into it) → ce (a wick to its 50 %, ICT consequent encroachment) → filled
         (a wick through the far edge: LuxAlgo / allanninal "mitigated") → inverted (a CLOSE beyond the far edge:
         ICT IFVG — the box flips side). David's own invalidation (strategy.fvg_untaken) is a separate flag:
         traded back into within 2 candles of forming, or before a 0.5 ATR run. superseded = a CHoCH closed
         against its side afterwards. live = fresh / touched / ce, not invalid, not superseded.
  OB     the order block of each major BOS / CHoCH: the last opposite candle (≤ zone_lookback_bars before) the LAST
         displacement candle of the breaking move (body ≥ displacement_mult × the average body of the
         body_average_bars before — David's V5 §3-4 values; ICT / most public tools: "the last opposite candle
         before the displacement that broke structure"). V5 _zone() takes the FIRST displacement after the origin,
         which on long moves puts the box days back and already re-entered before the break; the last one does
         not. Without a displacement: the opposite candle at the origin (else ≤ 3 bars before it). Box = the full
         wick, 50 % = ICT mean threshold.
         status from the break on: fresh → touched (a wick into it) → mean (a wick past 50 %) → invalid (a CLOSE
         beyond the far edge, V5 §33) → breaker (price comes back to it from the other side: it now works the
         other way) → dead (a close through the breaker's other edge). A fresh one 600 bars old is stale.
  liquidity  resting stops beyond a level ("pools"): EQH / EQL = ≥ 2 swing points (3 bars each side) within 0.5 ATR
         of each other with a real pullback (≥ 1 ATR) between the tests (LuxAlgo "meaningful pullback"; 0.1 ATR as
         in LuxAlgo misses the 10-28 4065.67 equal highs David traded into — their highs spread 0.6–0.9 ATR on M5);
         every major swing high / low; the previous FxPro day's, week's (ISO week) and month's high / low
         (the server day = the NY 17:00 day TradingView / LuxAlgo use, except in the 1–3 weeks a year US and EU
         summer time differ).
         status from the bar the pool is known: untaken → swept (a wick ≥ 0.1 ATR beyond, then a close back
         inside: on the same candle = "wick", after closes beyond = "failed break") → broken (a close ≥ 0.25 ATR
         beyond — the BOS margin — not back inside within 3 candles). Swept pools are spent (not re-armed); a later
         acceptance still breaks them. Built in one pass through time: a pool only knows what had happened by then,
         and a swept pool takes no new touches (its sweep candle is a grab, not a 3rd equal high). The 10-28 05:30
         IST gold run to 4070.72, back inside by 06:15 / 06:20, is a failed-break sweep of the EQH below 4065.67 and
         of the 4065.67 swing high / PDH on M5 and M15 (the run that stopped David's 5 sells).
  range  premium / discount of the major dealing range: the protected swing ↔ the leg's running extreme (up:
         protected higher low → highest high since; down mirrored). EQ 50 %, OTE 62–79 % back from the extreme.
         It re-anchors on every BOS / CHoCH; a new extreme only extends it.

    marks(bars, m) -> {"fvgs": [...], "fvg_clusters": [...], "obs": [...], "pools": [...], "range": {...} | None}
        bars  [{t, o, h, l, c}, ...] (the last one may be forming: it never completes a gap)
        m     major_structure(bars, ...) result
"""
from __future__ import annotations

import datetime as _dt
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from .config import ENGINE
from .config import STRATEGY as S
from .major_structure import _pivot, atr14

FVG_MIN_ATR = 0.3
FVG_PROTECT_CANDLES = 2        # strategy.fvg_untaken: STRATEGY fvg_protect_candles / fvg_min_runoff_atr
FVG_MIN_RUNOFF_ATR = 0.5
OTE = (0.62, 0.79)
OB_STALE_BARS = 600
EQ_N, EQ_TOL_ATR, EQ_SEP_ATR, EQ_MIN_TOUCHES = 3, 0.5, 1.0, 2
SWEEP_PEN_ATR, BREAK_MARGIN_ATR, FAIL_BARS = 0.1, 0.25, 3
SERVER_TZ = ZoneInfo(ENGINE["server_tz"])
SIDE = {"buy": "bull", "sell": "bear"}


def _gaps(bars: List[Dict]) -> List[Dict]:
    """every 3-candle gap whose third candle has closed; idx = the middle candle"""
    out = []
    for i in range(1, len(bars) - 2):
        a, c = bars[i - 1], bars[i + 1]
        if c["l"] > a["h"]:
            out.append({"side": "bull", "top": c["l"], "bottom": a["h"], "idx": i})
        elif c["h"] < a["l"]:
            out.append({"side": "bear", "top": a["l"], "bottom": c["h"], "idx": i})
    return out


def _track_fvg(bars: List[Dict], f: Dict, a: float) -> None:
    """fill statuses after the gap completes, and David's invalidation"""
    c3, bull = f["idx"] + 1, f["side"] == "bull"
    top, bot = f["top"], f["bottom"]
    mid = (top + bot) / 2
    f.update(touched_idx=None, ce_idx=None, filled_idx=None, inverted_idx=None, invalid=None)
    run = 0.0
    for j in range(c3 + 1, len(bars)):
        b = bars[j]
        if not (b["l"] < top if bull else b["h"] > bot):
            run = max(run, (b["h"] - top) if bull else (bot - b["l"]))
            continue
        if f["touched_idx"] is None:
            f["touched_idx"] = j
            if j - c3 <= FVG_PROTECT_CANDLES:
                f["invalid"] = f"traded back into {j - c3} candle(s) after forming (must stay clear for {FVG_PROTECT_CANDLES})"
            elif a and run < FVG_MIN_RUNOFF_ATR * a:
                f["invalid"] = f"retraced after only {run / a:.2f} ATR of run (need {FVG_MIN_RUNOFF_ATR:g})"
        if f["ce_idx"] is None and (b["l"] <= mid if bull else b["h"] >= mid):
            f["ce_idx"] = j
        if f["filled_idx"] is None and (b["l"] <= bot if bull else b["h"] >= top):
            f["filled_idx"] = j
        if b["c"] < bot if bull else b["c"] > top:
            f["inverted_idx"] = j
            break
    f["status"] = ("inverted" if f["inverted_idx"] is not None else "filled" if f["filled_idx"] is not None
                   else "ce" if f["ce_idx"] is not None else "touched" if f["touched_idx"] is not None else "fresh")


def fvgs(bars: List[Dict], m: Dict, A: List[float]) -> Dict:
    ev = m["events"]
    gaps = _gaps(bars)
    out, clusters = [], []
    for k, e in enumerate(ev):
        o, x, side = e["origin"]["idx"], e["idx"], SIDE[e["side"]]
        mine = []
        for g in gaps:
            if o < g["idx"] <= x and g["side"] == side and g["top"] - g["bottom"] >= FVG_MIN_ATR * A[g["idx"] - 1]:
                f = dict(g, event=k, event_kind=e["kind"], atr_mult=round((g["top"] - g["bottom"]) / A[g["idx"] - 1], 2))
                _track_fvg(bars, f, A[g["idx"] + 1])
                f["superseded"] = any(q["kind"] == "CHoCH" and SIDE[q["side"]] != side and q["idx"] > f["idx"] + 1 for q in ev)
                f["live"] = f["status"] in ("fresh", "touched", "ce") and not f["invalid"] and not f["superseded"]
                mine.append(f)
        out += mine
        if mine:
            clusters.append({"event": k, "kind": e["kind"], "side": side, "n": len(mine), "top": max(f["top"] for f in mine),
                             "bottom": min(f["bottom"] for f in mine), "idx": mine[0]["idx"], "nearest": len(out) - 1,
                             "live": any(f["live"] for f in mine)})
    return {"fvgs": out, "fvg_clusters": clusters}


def _ob_candle(bars: List[Dict], o: int, x: int, side: str) -> Optional[Dict]:
    """the OB candle of the move o..x (side buy = a bullish OB) and the displacement it came before"""
    body = lambda b: abs(b["c"] - b["o"])
    opp = (lambda b: b["c"] < b["o"]) if side == "buy" else (lambda b: b["c"] > b["o"])
    same = (lambda b: b["c"] > b["o"]) if side == "buy" else (lambda b: b["c"] < b["o"])
    k, mult, look = int(S["body_average_bars"]), float(S["displacement_mult"]), int(S["zone_lookback_bars"])
    d = None
    for i in range(x, max(o, k) - 1, -1):
        if same(bars[i]):
            avg = sum(body(b) for b in bars[i - k:i]) / k
            if avg > 0 and body(bars[i]) >= mult * avg:
                d = i
                break
    if d is not None:
        j = next((i for i in range(d - 1, max(d - 1 - look, -1), -1) if opp(bars[i])), None)
    else:
        j = o if opp(bars[o]) else next((i for i in range(o - 1, max(o - 4, -1), -1) if opp(bars[i])), None)
    return None if j is None else {"idx": j, "disp": d, "top": bars[j]["h"], "bottom": bars[j]["l"]}


def order_blocks(bars: List[Dict], m: Dict) -> List[Dict]:
    n, out = len(bars), []
    for k, e in enumerate(m["events"]):
        side, o, x = e["side"], e["origin"]["idx"], e["idx"]
        z = _ob_candle(bars, o, x, side)
        if not z:
            continue
        bull, top, bot = side == "buy", z["top"], z["bottom"]
        mid = (top + bot) / 2
        r = {"event": k, "event_kind": e["kind"], "side": SIDE[side], "idx": z["idx"], "disp_idx": z["disp"], "break_idx": x,
             "top": top, "bottom": bot, "mid": mid, "status": "fresh",
             "touch_idx": None, "mean_idx": None, "invalid_idx": None, "breaker_idx": None, "dead_idx": None,
             "has_fvg": any((bars[c + 1]["l"] > bars[c - 1]["h"]) if bull else (bars[c + 1]["h"] < bars[c - 1]["l"])
                            for c in range(z["idx"] + 1, min(x, z["idx"] + 3, n - 2) + 1))}
        for i in range(x + 1, n):
            b = bars[i]
            if r["status"] in ("fresh", "touched", "mean"):
                if r["touch_idx"] is None and (b["l"] <= top if bull else b["h"] >= bot):
                    r["touch_idx"], r["status"] = i, "touched"
                if r["mean_idx"] is None and (b["l"] <= mid if bull else b["h"] >= mid):
                    r["mean_idx"], r["status"] = i, "mean"
                if b["c"] < bot if bull else b["c"] > top:
                    r["invalid_idx"], r["status"] = i, "invalid"
            elif r["status"] == "invalid":
                if b["h"] >= bot if bull else b["l"] <= top:          # back at it from the other side
                    r["breaker_idx"], r["status"] = i, "breaker"
            elif r["status"] == "breaker":
                if b["c"] > top if bull else b["c"] < bot:
                    r["dead_idx"], r["status"] = i, "dead"
                    break
        if r["status"] == "fresh" and n - 1 - x > OB_STALE_BARS:
            r["status"] = "stale"
        r["live"] = r["status"] in ("fresh", "touched", "mean")
        out.append(r)
    return out


class _Range:
    """max / min of bars[a:b] in O(1) (sparse table)"""

    def __init__(self, vals: List[float], fn):
        self.fn, self.t = fn, [list(vals)]
        k = 1
        while 2 * k <= len(vals):
            prev = self.t[-1]
            self.t.append([fn(prev[i], prev[i + k]) for i in range(len(prev) - k)])
            k *= 2

    def q(self, a: int, b: int) -> Optional[float]:
        if b <= a:
            return None
        j = (b - a).bit_length() - 1
        return self.fn(self.t[j][a], self.t[j][b - (1 << j)])


def _new_pool(kind: str, high: bool, level: float, born: int, first: int, touches: int = 1, zone=None) -> Dict:
    return {"kind": kind, "high": high, "level": level, "born": born, "first": first, "zone": zone or [level, level],
            "touches": touches, "status": "untaken", "sweeps": [], "broken_idx": None, "_exc": None}


def _step_pool(pl: Dict, bars: List[Dict], A: List[float], x: int) -> None:
    """bar x for one pool: untaken → swept (wick / failed break) → broken"""
    high, lvl, b, a = pl["high"], pl["level"], bars[x], A[x]
    beyond = (lambda v: v - lvl) if high else (lambda v: lvl - v)
    far, exc = (b["h"] if high else b["l"]), pl["_exc"]
    if exc is None:
        if beyond(far) < SWEEP_PEN_ATR * a:
            return
        last = pl["sweeps"][-1] if pl["sweeps"] else None
        if last and x - last["end"] <= FAIL_BARS:                    # a quick second poke: the same sweep,
            exc = pl["sweeps"].pop()                                 # its acceptance clock starts again
            exc.update(earlier=exc.get("earlier", 0) + exc["closes"], bos_any=exc.get("bos_any") or exc["margin_close"] is not None,
                       closes=0, margin_close=None)
        else:
            exc = {"start": x, "extreme": far, "closes": 0, "margin_close": None}
        pl["_exc"] = exc
    if beyond(far) > beyond(exc["extreme"]):
        exc["extreme"] = far
    cb = beyond(b["c"])
    if cb > 0:
        exc["closes"] += 1
        if cb >= BREAK_MARGIN_ATR * a and exc["margin_close"] is None:
            exc["margin_close"] = x
        mc = exc["margin_close"]
        if (mc is not None and x - mc >= FAIL_BARS) or exc["closes"] > 2 * FAIL_BARS:
            pl["status"], pl["broken_idx"], pl["_exc"] = "broken", x, None
        return
    exc.update(end=x, kind="wick" if exc["closes"] + exc.get("earlier", 0) == 0 else "failed break",
               bos=exc["margin_close"] is not None or bool(exc.get("bos_any")))
    pl["sweeps"].append(exc)
    pl["status"], pl["_exc"] = "swept", None


def liquidity(bars: List[Dict], m: Dict, A: List[float]) -> List[Dict]:
    """one pass through time, so a pool only ever knows what had happened by then: EQH / EQL clusters grow while
    their pool is untaken (a sweep candle that later turns into a swing never joins the pool it swept)"""
    HI, LO = _Range([b["h"] for b in bars], max), _Range([b["l"] for b in bars], min)
    n = len(bars)
    born: Dict[int, List[Dict]] = {}
    for q in m["points"]:                                          # every major swing high / low
        born.setdefault(q["idx"], []).append(_new_pool("major high" if q["kind"] == "high" else "major low",
                                                       q["kind"] == "high", q["price"], q["idx"], q["idx"]))
    days = [_dt.datetime.fromtimestamp(b["t"] / 1000, SERVER_TZ).date() for b in bars]
    for key, names in ((lambda d: d, ("PDH", "PDL")), (lambda d: d.isocalendar()[:2], ("PWH", "PWL")),
                       (lambda d: (d.year, d.month), ("PMH", "PML"))):  # previous FxPro day / week / month
        start, k = 0, [key(d) for d in days]
        for x in range(1, n):
            if k[x] != k[x - 1]:
                if start > 0 or names[0] == "PDH":                 # a week / month cut off at the first bar is not one
                    hi = max(range(start, x), key=lambda i: bars[i]["h"])
                    lo = min(range(start, x), key=lambda i: bars[i]["l"])
                    born.setdefault(x - 1, []).extend([_new_pool(names[0], True, bars[hi]["h"], x - 1, hi),
                                                       _new_pool(names[1], False, bars[lo]["l"], x - 1, lo)])
                start = x
    pools, active = [], []
    clusters = {True: [], False: []}                              # EQH / EQL candidates
    for x in range(n):
        for pl in active:
            _step_pool(pl, bars, A, x)
        active = [pl for pl in active if pl["status"] != "broken"]
        new = born.get(x, [])
        p = x - EQ_N                                               # the swing p is known at bar x
        for high in (True, False):
            if p < EQ_N or not _pivot(bars, p, EQ_N, high):
                continue
            v, a = bars[p]["h" if high else "l"], A[p]
            joined = None
            for c in clusters[high]:
                if c.get("pool") and c["pool"]["status"] != "untaken":
                    continue                                       # swept / broken: the stops are gone
                ext = HI.q(c["last"] + 1, p) if high else LO.q(c["last"] + 1, p)
                taken = ext is not None and ((ext - c["level"]) if high else (c["level"] - ext)) > EQ_TOL_ATR * a
                pull = (c["level"] - LO.q(c["last"], p + 1)) if high else (HI.q(c["last"], p + 1) - c["level"])
                if not taken and abs(v - c["level"]) <= EQ_TOL_ATR * a and pull >= EQ_SEP_ATR * a:
                    c["members"].append(p)
                    c["last"], c["lo"], c["hi"] = p, min(c["lo"], v), max(c["hi"], v)
                    c["level"] = c["hi"] if high else c["lo"]
                    joined = c
                    break
            if joined is None:
                clusters[high].append({"level": v, "lo": v, "hi": v, "members": [p], "last": p})
            elif len(joined["members"]) == EQ_MIN_TOUCHES:
                joined["pool"] = _new_pool("EQH" if high else "EQL", high, joined["level"], x, joined["members"][0],
                                           EQ_MIN_TOUCHES, [joined["lo"], joined["hi"]])
                new.append(joined["pool"])
            else:                                                  # a 3rd / 4th test, before any sweep
                joined["pool"].update(level=joined["level"], zone=[joined["lo"], joined["hi"]], touches=len(joined["members"]))
            clusters[high] = [c for c in clusters[high] if p - c["last"] <= 400][-40:]
        pools += new
        active += new
    for pl in pools:
        pl.pop("_exc", None)
    return pools


def dealing_range(bars: List[Dict], m: Dict) -> Optional[Dict]:
    trend, prot = m["trend"], m["protected"]
    if trend is None or prot is None:
        return None
    span = range(prot["idx"], len(bars))
    if trend == "up":
        k = max(span, key=lambda i: bars[i]["h"])
        lo, hi, lo_i, hi_i = prot["price"], bars[k]["h"], prot["idx"], k
        ote = (hi - OTE[1] * (hi - lo), hi - OTE[0] * (hi - lo))            # longs: 62–79 % down from the high
    else:
        k = min(span, key=lambda i: bars[i]["l"])
        hi, lo, hi_i, lo_i = prot["price"], bars[k]["l"], prot["idx"], k
        ote = (lo + OTE[0] * (hi - lo), lo + OTE[1] * (hi - lo))            # shorts: 62–79 % up from the low
    price = bars[-1]["c"]
    pos = (price - lo) / (hi - lo) if hi > lo else None
    zone = None if pos is None else "equilibrium" if abs(pos - 0.5) < 0.025 else "premium" if pos > 0.5 else "discount"
    return {"trend": trend, "high": hi, "high_idx": hi_i, "low": lo, "low_idx": lo_i, "eq": (hi + lo) / 2,
            "ote": list(ote), "price": price, "pos": pos, "zone": zone, "in_ote": bool(ote[0] <= price <= ote[1]),
            "from_idx": min(hi_i, lo_i)}


def marks(bars: List[Dict], m: Dict) -> Dict:
    A = atr14(bars)
    out = fvgs(bars, m, A)
    out["obs"] = order_blocks(bars, m)
    out["pools"] = liquidity(bars, m, A)
    out["range"] = dealing_range(bars, m)
    return out
