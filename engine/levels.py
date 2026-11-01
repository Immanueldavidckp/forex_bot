"""
engine/levels.py — row 2 of the /smc concept table: session highs / lows, the period opens and the depth of the
pullback in the major leg. Swing levels, PDH / PDL and PWH / PWL / PMH / PML are liquidity pools in smc_marks.py
(one lifecycle for every horizontal level). Researched 2026-10-29 by a Fable 5.1 agent (TradingView "Trading
Sessions" + "Auto Trendlines" help, LuxAlgo sessions / ICT killzones / ICT session ranges / pullback concept
pages, babypips session hours, MT5 Fractals.mq5 / ZigZag.mq5).

  sessions   each window in its OWN time zone, so summer time moves it the way the market does (fixed UTC windows
             drift twice a year); a bar belongs to a window when its OPEN time is inside [start, end) (TradingView):
               Asia range  20:00–00:00 New York   (ICT; the pool the London open raids)
               London      08:00–16:30 London
               New York    08:00–17:00 New York
             killzones (New York time): London open 02:00–05:00, NY AM 07:00–10:00, London close 10:00–12:00,
             NY PM 13:30–16:00. A session is dated by the New York (London) date its window STARTS on. Its high /
             low runs while the window is open and is final with the window's last bar; from then on it is a level
             with the liquidity lifecycle of smc_marks (swept = wick ≥ 0.1 ATR beyond and a close back inside;
             broken = a close ≥ 0.25 ATR beyond, held 3 candles). An Asia-range sweep that starts inside the next
             London open killzone is the Judas swing. Not on H4 (one bar spans a window).
  opens      daily open (first bar of the FxPro server day = NY 17:00), midnight open (first bar at / after 00:00
             New York, ICT), NY 08:30 open, weekly open (first bar of the server week), monthly open — levels, the
             current ones only.
  pullback   the major leg (protected swing O → the leg's running extreme E, = the dealing range): depth =
             (E − low) / (E − O) up-leg, mirrored down; the deepest wick since E and the latest close. Classes:
             shallow < 38.2 %, normal 38.2–61.8 %, deep 61.8–78.6 % (OTE lives here), very deep 78.6–100 %, and a
             close beyond O is no pullback (that is the CHoCH). Also the depth each completed pullback reached before
             its BOS (the previous leg's retracement): how deep this market pulls back.

    levels(bars, m, A, tf) -> {"sessions": [...], "killzones": [...], "opens": [...], "pullback": {...} | None,
                           "pullbacks": [...]}
"""
from __future__ import annotations

import datetime as _dt
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from .smc_marks import SERVER_TZ, _new_pool, _step_pool

NY, LDN = ZoneInfo("America/New_York"), ZoneInfo("Europe/London")
SESSIONS = (("asia", "Asia range", (20, 0), (24, 0), NY), ("london", "London", (8, 0), (16, 30), LDN),
            ("ny", "New York", (8, 0), (17, 0), NY))
KILLZONES = (("london_kz", "London open KZ", (2, 0), (5, 0)), ("ny_am_kz", "NY AM KZ", (7, 0), (10, 0)),
             ("london_close_kz", "London close KZ", (10, 0), (12, 0)), ("ny_pm_kz", "NY PM KZ", (13, 30), (16, 0)))
SESSION_DAYS = 10            # sessions kept (per kind): the last 10 days
DEPTH = ((0.382, "shallow"), (0.618, "normal"), (0.786, "deep"), (1.0, "very deep"))


def _local(bars: List[Dict], tz) -> List[_dt.datetime]:
    return [_dt.datetime.fromtimestamp(b["t"] / 1000, tz) for b in bars]


def _windows(loc: List[_dt.datetime], start, end) -> List[tuple]:
    """(date, first idx, last idx) of every window [start, end) local time, by bar open"""
    s, e = start[0] * 60 + start[1], end[0] * 60 + end[1]
    out: List[list] = []
    for i, d in enumerate(loc):
        mm = d.hour * 60 + d.minute
        if s <= mm < e:
            if out and out[-1][0] == d.date() and out[-1][2] == i - 1:
                out[-1][2] = i
            elif out and out[-1][0] == d.date():
                out[-1][2] = i                                     # a gap in the bars (holiday) inside the window
            else:
                out.append([d.date(), i, i])
    return [tuple(w) for w in out]


def _track(bars: List[Dict], A: List[float], pl: Dict, frm: int) -> Dict:
    for x in range(frm, len(bars)):
        if pl["status"] == "broken":
            break
        _step_pool(pl, bars, A, x)
    pl.pop("_exc", None)
    return pl


def sessions(bars: List[Dict], A: List[float]) -> Dict:
    n, out, kz = len(bars), [], []
    if not bars:
        return {"sessions": [], "killzones": []}
    locs = {NY: _local(bars, NY), LDN: _local(bars, LDN)}
    lkz = _windows(locs[NY], *KILLZONES[0][2:])
    for key, label, start, end, tz in SESSIONS:
        for date, a, b in _windows(locs[tz], start, end)[-SESSION_DAYS:]:
            hi = max(range(a, b + 1), key=lambda i: bars[i]["h"])
            lo = min(range(a, b + 1), key=lambda i: bars[i]["l"])
            final = b + 1 < n                                     # a later bar exists outside the window
            s = {"key": key, "label": label, "date": date.isoformat(), "first": a, "last": b, "final": final,
                 "high": bars[hi]["h"], "high_idx": hi, "low": bars[lo]["l"], "low_idx": lo}
            if final:
                ph = _track(bars, A, _new_pool(label + " high", True, s["high"], b, hi), b + 1)
                pl = _track(bars, A, _new_pool(label + " low", False, s["low"], b, lo), b + 1)
                s["high_status"], s["low_status"] = ph["status"], pl["status"]
                s["high_sweeps"] = [{"start": w["start"], "end": w["end"], "extreme": w["extreme"], "kind": w["kind"]} for w in ph["sweeps"]]
                s["low_sweeps"] = [{"start": w["start"], "end": w["end"], "extreme": w["extreme"], "kind": w["kind"]} for w in pl["sweeps"]]
                s["high_broken_idx"], s["low_broken_idx"] = ph["broken_idx"], pl["broken_idx"]
                if key == "asia":                                  # the Judas swing: swept inside the next London open KZ
                    nd = date + _dt.timedelta(days=1)
                    w = next(((wa, wb) for d, wa, wb in lkz if d == nd), None)
                    s["judas"] = None if w is None else next(
                        ({"side": side, "start": q["start"], "extreme": q["extreme"]} for side, sw in (("high", s["high_sweeps"]), ("low", s["low_sweeps"]))
                         for q in sw if w[0] <= q["start"] <= w[1]), None)
            out.append(s)
    for key, label, start, end in KILLZONES:
        for date, a, b in _windows(locs[NY], start, end)[-SESSION_DAYS:]:
            kz.append({"key": key, "label": label, "date": date.isoformat(), "first": a, "last": b})
    out.sort(key=lambda s: s["first"])
    kz.sort(key=lambda s: s["first"])
    return {"sessions": out, "killzones": kz}


def opens(bars: List[Dict]) -> List[Dict]:
    """the current daily / midnight / 08:30 / weekly / monthly open"""
    if not bars:
        return []
    srv, ny = _local(bars, SERVER_TZ), _local(bars, NY)
    out = []
    first = lambda key: next(i for i in range(len(bars) - 1, -1, -1) if i == 0 or key(i) != key(i - 1))
    for label, key, whole in (("daily open", lambda i: srv[i].date(), True), ("weekly open", lambda i: srv[i].isocalendar()[:2], True),
                              ("monthly open", lambda i: (srv[i].year, srv[i].month), True)):
        i = first(key)
        if i > 0 or not whole:
            out.append({"label": label, "idx": i, "price": bars[i]["o"]})
    for label, hm in (("midnight open", (0, 0)), ("NY 08:30 open", (8, 30))):
        day = ny[-1].date()
        for d in (day, day - _dt.timedelta(days=1)):              # today's if it happened, else yesterday's
            i = next((k for k in range(len(bars)) if ny[k].date() == d and (ny[k].hour, ny[k].minute) >= hm), None)
            if i is not None and (i == 0 or ny[i - 1].date() != d or (ny[i - 1].hour, ny[i - 1].minute) < hm):
                out.append({"label": label, "idx": i, "price": bars[i]["o"], "date": d.isoformat()})
                break
    return out


def _depth_class(d: float) -> str:
    return next((name for lim, name in DEPTH if d < lim), "beyond the origin")


def pullback(bars: List[Dict], m: Dict) -> Optional[Dict]:
    trend, prot = m["trend"], m["protected"]
    if trend is None or prot is None:
        return None
    o, up = prot["idx"], trend == "up"
    e = max(range(o, len(bars)), key=lambda i: bars[i]["h"]) if up else min(range(o, len(bars)), key=lambda i: bars[i]["l"])
    O, E = prot["price"], bars[e]["h"] if up else bars[e]["l"]
    if E == O:
        return None
    after = range(e, len(bars))
    worst = min(after, key=lambda i: bars[i]["l"]) if up else max(after, key=lambda i: bars[i]["h"])
    depth = lambda p: (E - p) / (E - O)
    deep = depth(bars[worst]["l"] if up else bars[worst]["h"])
    now = depth(bars[-1]["c"])
    return {"trend": trend, "origin": O, "origin_idx": o, "extreme": E, "extreme_idx": e, "deepest": round(deep, 4),
            "deepest_idx": worst, "now": round(now, 4), "class": _depth_class(deep),
            "levels": {f"{k:g}": E - k * (E - O) for k in (0.236, 0.382, 0.5, 0.618, 0.705, 0.786)}}


def pullbacks(m: Dict) -> List[Dict]:
    """the retracement each BOS came out of: the previous leg O → E, pulled back to the break's origin"""
    ev, out = m["events"], []
    for k in range(1, len(ev)):
        e, p = ev[k], ev[k - 1]
        if e["kind"] != "BOS" or e["side"] != p["side"]:
            continue
        E, O, low = e["level"], p["origin"]["price"], e["origin"]["price"]
        if E != O:
            d = (E - low) / (E - O)
            out.append({"t": e["t"], "idx": e["idx"], "side": e["side"], "depth": round(d, 4), "class": _depth_class(d)})
    return out


def levels(bars: List[Dict], m: Dict, A: List[float], tf: str = "M15") -> Dict:
    out = sessions(bars, A) if tf != "H4" else {"sessions": [], "killzones": []}   # one H4 bar spans a whole window
    out["opens"] = opens(bars)
    out["pullback"] = pullback(bars, m)
    out["pullbacks"] = pullbacks(m)
    return out
