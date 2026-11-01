"""
engine/orderflow.py — the order-flow (footprint) chart of the /smc page (David 2026-10-29: "add the order flow chart,
research all sources, verify, implement"). Researched by three Fable 5.1 agents (Sierra Chart Numbers Bars, ATAS,
NinjaTrader Volumetric Bars, TradingView footprint / Pine request.footprint, MotiveWave, Exocharts, flowsurface,
openalgo-charts, MQL5; 18 worked examples from their docs reproduced, the open-source code ported and compared).

FxPro has NO trades on its feed (no BUY / SELL tick flags, `last` = the bid, `volume` a constant quote size), so the
buy / sell numbers are ESTIMATED from quote changes — what every MT5 / Sierra / TradingView forex delta does:
    side     a tick whose bid went up = 1 buy, down = 1 sell, unchanged = not counted (65 % of FxPro's ticks change
             nothing; carrying the last side forward only adds noise); binned at the new bid
    rows     row = median bar range / 12 → the nearest 1-2-5 step, never below the point; row = floor(points / row)
    per bar  volume, delta = buy − sell, delta %, max / min of the running delta, POC (tie: nearest the middle, then
             lower), value area 70 % grown one row at a time from the POC (bigger neighbour, tie: upper)
    imbalance  diagonal: buy at row r ≥ 3 × sell at r − 1, sell at r ≥ 3 × buy at r + 1; the opposite cell must be
             > 0 (a zero is no comparison: Sierra / flowsurface) and the dominant one ≥ 1 % of the bar's volume
    stacked  ≥ 3 imbalances on consecutive rows → a zone (buy = support, sell = resistance) from the lowest to the
             highest row; touched when a later bar's wick enters it, broken when one closes beyond its far edge
    CVD      Σ delta, reset at each FxPro server day (00:00 Cyprus time — the broker's session)
    CVD divergence  pivots of 3 bars each side; bear = a pivot high above the previous one (≤ 60 bars back, same CVD
             day) with the CVD lower there, bull mirrored; known 3 bars after the 2nd pivot, invalid on a close beyond it
    spike    a bar's count ≥ 1.5 × the average of the 20 before it (undirected: the next bars move more, either way)
Left out on purpose (the signals research, 2026-10-29): the "unfinished auction" — with quote changes the bar's top
price can only be reached by an up-tick, so it would measure the row size; and stacked imbalances are computed but
not drawn — with changed quotes the rows are ~50 / 50, so 3 : 1 runs hardly exist (4 in 7 days of GOLD M5) and none
of 18 published order-flow signals showed an edge on this feed. On 7 days of GOLD the bar delta followed the bar's
own move (ρ 0.42) but did not predict the next bar (M5 ρ −0.03, p 0.24): it shows how price got here.
"""
from __future__ import annotations

import datetime as _dt
import math
import time
from typing import Dict, List, Optional

import numpy as np

from . import learn, ticks
from .smc_marks import SERVER_TZ

PIVOT = 3             # CVD divergence: LuxAlgo 2–5, the signals research 3 for M5 / M15
DIV_BARS = 60
SPIKE = 1.5           # vendors use 2 / 4 × on real volume; quote counts are smoother (99th percentile ≈ 1.7 ×)
RATIO = 3.0           # 300 %: TradingView, Pine, openalgo, flowsurface, MQL5, most educators (ATAS / NinjaTrader 150 %)
MIN_SHARE = 0.01      # the dominant cell needs ≥ 1 % of its bar's volume (tick-rule sweeps fill whole runs of rows)
STACK = 3
VA_PCT = 0.70
TARGET_ROWS = 12
CACHE_S = 15
_CACHE: Dict[tuple, tuple] = {}


def classify(bid_pts: np.ndarray) -> np.ndarray:
    """+1 buy / −1 sell / 0 not counted, per tick: the direction of the bid's change (the first tick: 0)."""
    return np.sign(np.diff(bid_pts, prepend=bid_pts[:1])).astype(np.int8)


def round_125(x: float) -> float:
    e = math.floor(math.log10(x))
    return min((k * 10 ** e for k in (1, 2, 5, 10)), key=lambda u: abs(math.log(u / x)))


def row_points(rows: List[list], point: float) -> int:
    """Row size in points: median bar range / TARGET_ROWS → 1-2-5 (GOLD M5 0.20 $, M15 0.50 $; EURUSD 0.2 / 0.5 pip)."""
    rng = [r[2] - r[3] for r in rows if r[2] > r[3]]
    raw = max(float(np.median(rng)) / TARGET_ROWS if rng else point, point)
    return max(1, int(round(round_125(raw) / point)))


def value_area(tot: np.ndarray, poc: int, pct: float = VA_PCT) -> tuple:
    """Rows [lo, hi] holding ≥ pct of the volume, grown from the POC one row at a time (bigger side; tie: upper)."""
    n, target, lo, hi = len(tot), pct * tot.sum(), poc, poc
    va = tot[poc]
    while va < target and (hi < n - 1 or lo > 0):
        up = tot[hi + 1] if hi < n - 1 else -1
        dn = tot[lo - 1] if lo > 0 else -1
        if up >= dn:
            hi += 1
            va += up
        else:
            lo -= 1
            va += dn
    return lo, hi


def runs(mask: np.ndarray, k: int = STACK) -> List[tuple]:
    """Maximal runs of ≥ k consecutive True rows → [(first, last)]."""
    out, start = [], None
    for r in range(len(mask) + 1):
        on = r < len(mask) and mask[r]
        if on and start is None:
            start = r
        elif not on and start is not None:
            if r - start >= k:
                out.append((start, r - 1))
            start = None
    return out


def bar(rix: np.ndarray, side: np.ndarray) -> Dict:
    """One bar's footprint from its counted ticks (row index, side ±1), in time order."""
    lo, hi = int(rix.min()), int(rix.max())
    n = hi - lo + 1
    return {"r0": lo, **cells(np.bincount(rix[side < 0] - lo, minlength=n), np.bincount(rix[side > 0] - lo, minlength=n),
                               np.cumsum(side))}


def cells(sell: np.ndarray, buy: np.ndarray, run: np.ndarray) -> Dict:
    """The numbers of one bar from its rows (index 0 = the lowest) and its running delta."""
    n = len(sell)
    tot = buy + sell
    mid = (n - 1) / 2
    poc = max(range(n), key=lambda r: (tot[r], -abs(r - mid), -r))
    va = value_area(tot, poc)
    vol = int(tot.sum())
    floor = max(1.0, MIN_SHARE * vol)
    ib = np.zeros(n, bool)
    isl = np.zeros(n, bool)
    ib[1:] = (buy[1:] >= floor) & (sell[:-1] > 0) & (buy[1:] >= RATIO * sell[:-1])
    isl[:-1] = (sell[:-1] >= floor) & (buy[1:] > 0) & (sell[:-1] >= RATIO * buy[1:])
    return {"sell": sell.tolist(), "buy": buy.tolist(), "vol": vol, "delta": int(buy.sum() - sell.sum()),
            "dmax": int(max(0, run.max())), "dmin": int(min(0, run.min())), "poc": poc, "va": list(va),
            "ib": np.flatnonzero(ib).tolist(), "is": np.flatnonzero(isl).tolist(),
            "stack_buy": runs(ib), "stack_sell": runs(isl)}


def footprints(t: np.ndarray, bid_pts: np.ndarray, bar_t: List[int], tf_ms: int, row_pts: int) -> List[Optional[Dict]]:
    """The footprint of each bar in bar_t (open times, ascending) from the ticks inside [open, open + tf); None = no ticks."""
    side = classify(bid_pts)
    keep = side != 0
    t, rix, side = t[keep], bid_pts[keep] // row_pts, side[keep]
    B = np.asarray(bar_t, dtype=np.int64)
    k = np.searchsorted(B, t, side="right") - 1
    ok = (k >= 0) & (t < B[np.clip(k, 0, None)] + tf_ms)
    k, rix, side = k[ok], rix[ok], side[ok]
    out: List[Optional[Dict]] = [None] * len(B)
    cuts = np.flatnonzero(np.diff(k)) + 1
    for a, b in zip(np.r_[0, cuts], np.r_[cuts, len(k)]):
        if b > a:
            out[int(k[a])] = bar(rix[a:b], side[a:b])
    return out


def cvd(fps: List[Optional[Dict]], bar_t: List[int]) -> List[Optional[list]]:
    """Cumulative delta as candles [open, high, low, close], reset at each FxPro server day."""
    out, acc, day = [], 0, None
    for f, t in zip(fps, bar_t):
        d = _dt.datetime.fromtimestamp(t / 1000, SERVER_TZ).date()
        if d != day:
            acc, day = 0, d
        if f is None:
            out.append(None)
            continue
        out.append([acc, acc + f["dmax"], acc + f["dmin"], acc + f["delta"]])
        acc += f["delta"]
    return out


def zones(fps: List[Optional[Dict]], rows: List[list], row_pts: int, point: float) -> List[Dict]:
    """Stacked-imbalance zones of the closed bars: fresh → touched (a later wick in) → broken (a later close beyond)."""
    out = []
    for i, f in enumerate(fps):
        if f is None:
            continue
        for side, key in (("buy", "stack_buy"), ("sell", "stack_sell")):
            for a, b in f[key]:
                lo, hi = (f["r0"] + a) * row_pts * point, (f["r0"] + b + 1) * row_pts * point
                z = {"side": side, "lo": round(lo, 10), "hi": round(hi, 10), "t0": rows[i][0], "status": "fresh",
                     "t_touch": None, "t_end": None, "rows": b - a + 1}
                for r in rows[i + 1:]:
                    if (side == "buy" and r[4] < lo) or (side == "sell" and r[4] > hi):
                        z["status"], z["t_end"] = "broken", r[0]
                        break
                    if z["t_touch"] is None and ((side == "buy" and r[3] <= hi) or (side == "sell" and r[2] >= lo)):
                        z["status"], z["t_touch"] = "touched", r[0]
                out.append(z)
    return out


def divergences(rows: List[list], cv: List[Optional[list]], bar_t: List[int]) -> List[Dict]:
    """CVD divergences at price pivots of the closed bars (see the module text)."""
    n, out = len(rows), []
    day = [_dt.datetime.fromtimestamp(t / 1000, SERVER_TZ).date() for t in bar_t[:n]]
    for side, col, better in (("bear", 2, lambda a, b: a > b), ("bull", 3, lambda a, b: a < b)):
        piv = [i for i in range(PIVOT, n - PIVOT) if cv[i] is not None
               and all(better(rows[i][col], rows[j][col]) for j in range(i - PIVOT, i))
               and all(not better(rows[j][col], rows[i][col]) for j in range(i + 1, i + PIVOT + 1))]
        for a, b in zip(piv, piv[1:]):
            if b - a > DIV_BARS or day[a] != day[b]:
                continue
            ca, cb = cv[a][3], cv[b][3]
            if better(rows[b][col], rows[a][col]) and better(ca, cb):          # price further, CVD not
                bad = next((r[0] for r in rows[b + 1:] if better(r[4], rows[b][col])), None)
                out.append({"side": side, "t1": rows[a][0], "p1": rows[a][col], "c1": ca, "t2": rows[b][0], "p2": rows[b][col],
                            "c2": cb, "t_known": rows[b + PIVOT][0], "t_invalid": bad})
    return sorted(out, key=lambda d: d["t2"])


def spikes(fps: List[Optional[Dict]]) -> List[int]:
    """Indices of the bars whose count is ≥ SPIKE × the average of the 20 bars before it."""
    v = [f["vol"] if f else 0 for f in fps]
    return [i for i in range(20, len(v)) if v[i] and v[i] >= SPIKE * sum(v[i - 20:i]) / 20]


def page(sym: str, tf: str) -> Dict:
    """Everything the /smc page draws for the order flow of one chart (the closed bars that have stored ticks + the
    forming one)."""
    hit = _CACHE.get((sym, tf))
    if hit and time.time() - hit[0] < CACHE_S:
        return hit[1]
    d = _build(sym, tf)
    if len(_CACHE) > 64:
        _CACHE.clear()
    _CACHE[(sym, tf)] = (time.time(), d)
    return d


def _build(sym: str, tf: str) -> Dict:
    tf_ms = learn.TF_MS[tf]
    days = ticks._days(sym)
    if not days:
        return {"sym": sym, "tf": tf, "error": "no ticks recorded for this symbol yet — they start while the page is open (≈ 1 min)"}
    start = ticks._day_ms(days[0])
    rows = [r for r in learn.load_bars(sym, tf, 3000) if r[0] >= start]
    if not rows:
        return {"sym": sym, "tf": tf, "error": "no closed bars inside the recorded ticks yet"}
    now = int(time.time() * 1000)
    forming = rows[-1][0] + tf_ms
    a, point = ticks.load(sym, rows[0][0], now + 1)
    if not len(a) or not point:
        return {"sym": sym, "tf": tf, "error": "no ticks in the chart's range yet"}
    row_pts = row_points(rows, point)
    bar_t = [r[0] for r in rows] + ([forming] if a["t"][-1] >= forming else [])
    fps = footprints(a["t"], a["bid"].astype(np.int64), bar_t, tf_ms, row_pts)
    zs = zones(fps[:len(rows)], rows, row_pts, point)        # the forming bar makes no zone
    cv = cvd(fps, bar_t)
    for f in fps:
        if f is not None:
            del f["stack_buy"], f["stack_sell"]
    return {"sym": sym, "tf": tf, "point": point, "row": round(row_pts * point, 10), "row_pts": row_pts,
            "from": rows[0][0], "ticks_to": int(a["t"][-1]), "n_ticks": int(len(a)),
            "t": bar_t, "bars": fps,
            "forming": len(bar_t) > len(rows), "cvd": cv, "zones": zs,
            "div": divergences(rows, cv, bar_t), "spike": [bar_t[i] for i in spikes(fps[:len(rows)])],
            "rules": {"ratio": RATIO, "min_share": MIN_SHARE, "stack": STACK, "va": VA_PCT, "side": "bid change",
                      "cvd_reset": "FxPro server day"}}
