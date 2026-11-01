"""
engine/indicators.py — row 6 of the /smc concept table: Fibonacci, ATR, RSI / MACD divergence, VWAP. Researched
2026-10-29 by a Fable 5.1 agent (TA-Lib ta_ATR.c / ta_RSI.c / ta_EMA.c, MT5 ATR.mq5 / RSI.mq5 / MACD.mq5 /
MovingAverages.mqh, Pine ta.rma / ta.ema / ta.vwap, TradingView's "Divergence Indicator" and LonesomeTheBlue's
"Divergence for Many Indicators v4", TradingView VWAP help).

  ATR     TR = max(h, prev c) − min(l, prev c). Wilder / TradingView ta.atr: the SMA of the first 14 TRs, then
          ATR += (TR − ATR) / 14. MT5 iATR is a plain 14-bar SMA of TR (Indicators/Examples/ATR.mq5) — up to
          20–30 % apart around spikes. Both are shown; the engine's own atr14 (major_structure) is the MT5 one.
  RSI     Wilder 14 (identical on TradingView, MT5 and TA-Lib once warmed up): gains / losses seeded with their
          14-bar mean, then avg = (avg·13 + x) / 14; RSI = 100 − 100 / (1 + AG / AL); AL = 0 → 100.
  MACD    12 / 26 / 9, TradingView: EMAs seeded with the first close (α = 2 / (N + 1)), signal = EMA 9 of the MACD
          line, histogram = MACD − signal. (MT5's signal is an SMA 9: its crosses come later.)
  divergence   TradingView's built-in recipe, which never repaints: pivots on the OSCILLATOR, 5 bars each side
          (known 5 bars after the pivot), compared with the previous oscillator pivot of the same kind 5–60 bars
          earlier, price read on the same two bars (low for pivot lows, high for pivot highs):
            regular bull  price lower low,  oscillator higher low      hidden bull  price higher low, osc lower low
            regular bear  price higher high, oscillator lower high     hidden bear  price lower high, osc higher high
          plus LonesomeTheBlue's line test: the oscillator between the two pivots may not cross the line joining
          them. Run on RSI 14 and on the MACD line. Invalid once a close goes beyond the second pivot's price.
  Fibonacci   on the major leg: 1 = the protected swing, 0 = the leg's running extreme (ICT / TradingView Auto
          Fib: price(m) = P0 + m·(P1 − P0)); retracements 0.236 … 0.786 (+ ICT's 0.705), targets beyond the
          extreme −0.27 / −0.618 / −1, beyond the origin 1.272 / 1.618. It re-anchors when the extreme extends.
          Extension (TradingView Auto Fib Extension, 3 pivots) from the latest BOS: A = the swing before the broken
          level B, C = the low / high the break came from; C + m·(B − A), m 0.618 / 1 / 1.272 / 1.618 / 2 / 2.618.
  VWAP    Σ(hlc3 · volume) / Σ volume from the anchor; bands ±1 / 2 / 3 σ with σ² = Σ(v·p²) / Σv − VWAP²
          (TradingView). Anchors: the FxPro server day (= the NY 17:00 forex day, TradingView's "Session" for FX),
          the server week, and the protected swing (anchored VWAP). Volume = MT5 tick volume (price changes, not
          traded size: a level, not "where the money is"); no VWAP when the bars carry no volume.

    indicators(bars, m) -> {"atr": {...}, "rsi": [...], "macd": {...}, "divergences": [...], "fib": {...} | None,
                            "fib_ext": {...} | None, "vwap": {...} | None}
"""
from __future__ import annotations

import datetime as _dt
import math
from typing import Dict, List, Optional

from .smc_marks import SERVER_TZ

N_ATR, N_RSI, MACD_P = 14, 14, (12, 26, 9)
DIV_LB, DIV_RANGE = 5, (5, 60)
FIB_RETRACE = (0, 0.236, 0.382, 0.5, 0.618, 0.705, 0.786, 1)
FIB_TARGETS = (-0.27, -0.618, -1.0, 1.272, 1.618)
FIB_EXT = (0.618, 1.0, 1.272, 1.618, 2.0, 2.618)
Series = List[Optional[float]]


def true_range(bars: List[Dict]) -> List[float]:
    return [b["h"] - b["l"] if i == 0 else max(b["h"], bars[i - 1]["c"]) - min(b["l"], bars[i - 1]["c"]) for i, b in enumerate(bars)]


def rma(x: List[float], n: int) -> Series:
    """Wilder's moving average (ta.rma): the SMA of the first n values, then avg += (x − avg) / n"""
    out: Series = [None] * len(x)
    if len(x) < n:
        return out
    a = sum(x[:n]) / n
    out[n - 1] = a
    for i in range(n, len(x)):
        a += (x[i] - a) / n
        out[i] = a
    return out


def sma(x: List[float], n: int) -> Series:
    out: Series = [None] * len(x)
    s = 0.0
    for i, v in enumerate(x):
        s += v - (x[i - n] if i >= n else 0)
        if i >= n - 1:
            out[i] = s / n
    return out


def ema(x: Series, n: int) -> Series:
    """ta.ema: seeded with the first value, α = 2 / (n + 1); None until the input starts"""
    out: Series = [None] * len(x)
    k, a = 2 / (n + 1), None
    for i, v in enumerate(x):
        if v is None:
            continue
        a = v if a is None else k * v + (1 - k) * a
        out[i] = a
    return out


def rsi(close: List[float], n: int = N_RSI) -> Series:
    out: Series = [None] * len(close)
    if len(close) <= n:
        return out
    d = [close[i] - close[i - 1] for i in range(1, len(close))]
    g = sum(max(x, 0) for x in d[:n]) / n
    l = sum(max(-x, 0) for x in d[:n]) / n
    val = lambda g, l: 100.0 if l == 0 and g > 0 else 50.0 if l == 0 else 100 - 100 / (1 + g / l)
    out[n] = val(g, l)
    for i in range(n + 1, len(close)):
        x = d[i - 1]
        g, l = (g * (n - 1) + max(x, 0)) / n, (l * (n - 1) + max(-x, 0)) / n
        out[i] = val(g, l)
    return out


def macd(close: List[float], p=MACD_P) -> Dict[str, Series]:
    f, s = ema(close, p[0]), ema(close, p[1])
    line = [a - b for a, b in zip(f, s)]
    sig = ema(line, p[2])
    return {"macd": line, "signal": sig, "hist": [a - b for a, b in zip(line, sig)]}


def _opivot(x: Series, p: int, n: int, low: bool) -> bool:
    w = x[p - n:p + n + 1]
    if len(w) < 2 * n + 1 or any(v is None for v in w):
        return False
    v = x[p]
    return all((v < u) if low else (v > u) for k, u in enumerate(w) if k != n)


def divergences(bars: List[Dict], osc: Series, name: str, lb: int = DIV_LB, rng=DIV_RANGE) -> List[Dict]:
    out, prev = [], {True: None, False: None}
    n = len(bars)
    for p in range(lb, n - lb):
        for low in (True, False):
            if not _opivot(osc, p, lb, low):
                continue
            q = prev[low]
            prev[low] = p
            if q is None or not rng[0] <= p - q <= rng[1]:
                continue
            pp, pq = (bars[p]["l"], bars[q]["l"]) if low else (bars[p]["h"], bars[q]["h"])
            op, oq = osc[p], osc[q]
            if low:
                kind = "regular bull" if pp < pq and op > oq else "hidden bull" if pp > pq and op < oq else None
            else:
                kind = "regular bear" if pp > pq and op < oq else "hidden bear" if pp < pq and op > oq else None
            if kind is None:
                continue
            line = lambda y: oq + (op - oq) * (y - q) / (p - q)
            if any((osc[y] < line(y) if low else osc[y] > line(y)) for y in range(q + 1, p)):
                continue                                           # the oscillator crossed the divergence line
            inv = next((i for i in range(p + lb + 1, n) if (bars[i]["c"] < pp if low else bars[i]["c"] > pp)), None)
            out.append({"osc": name, "kind": kind, "side": "bull" if low else "bear", "idx": p, "prev_idx": q,
                        "price": pp, "prev_price": pq, "osc_val": op, "prev_osc": oq, "known": p + lb, "invalid_idx": inv})
    return out


def fib(bars: List[Dict], m: Dict) -> Optional[Dict]:
    trend, prot = m["trend"], m["protected"]
    if trend is None or prot is None:
        return None
    span = range(prot["idx"], len(bars))
    e = max(span, key=lambda i: bars[i]["h"]) if trend == "up" else min(span, key=lambda i: bars[i]["l"])
    P1, P0 = prot["price"], bars[e]["h"] if trend == "up" else bars[e]["l"]
    lv = lambda ms: [{"m": k, "price": P0 + k * (P1 - P0)} for k in ms]
    return {"trend": trend, "one": P1, "one_idx": prot["idx"], "zero": P0, "zero_idx": e,
            "retrace": lv(FIB_RETRACE), "targets": lv(FIB_TARGETS)}


def fib_ext(m: Dict) -> Optional[Dict]:
    ev = [e for e in m["events"] if e["kind"] == "BOS"]
    if not ev:
        return None
    e = ev[-1]
    pts = m["points"]
    k = next((i for i, q in enumerate(pts) if q["idx"] == e["level_idx"]), None)
    if not k:
        return None
    A, B, C = pts[k - 1]["price"], e["level"], e["origin"]["price"]
    if (B - A) * (1 if e["side"] == "buy" else -1) <= 0:
        return None
    return {"side": "bull" if e["side"] == "buy" else "bear", "A": A, "A_idx": pts[k - 1]["idx"], "B": B, "B_idx": e["level_idx"],
            "C": C, "C_idx": e["origin"]["idx"], "levels": [{"m": x, "price": C + x * (B - A)} for x in FIB_EXT]}


def _vwap(bars: List[Dict], key=None, start: int = 0) -> Dict[str, Series]:
    """VWAP and its σ, reset whenever key(i) changes (key None: one anchor at start)"""
    n = len(bars)
    vw: Series = [None] * n
    sd: Series = [None] * n
    sv = spv = sp2v = 0.0
    for i in range(start, n):
        if key is not None and i > start and key(i) != key(i - 1):
            sv = spv = sp2v = 0.0
        b = bars[i]
        p, v = (b["h"] + b["l"] + b["c"]) / 3, b.get("v") or 0.0
        sv, spv, sp2v = sv + v, spv + p * v, sp2v + p * p * v
        if sv > 0:
            vw[i] = spv / sv
            sd[i] = math.sqrt(max(sp2v / sv - vw[i] ** 2, 0.0))
    return {"vwap": vw, "sd": sd}


def vwap(bars: List[Dict], m: Dict) -> Optional[Dict]:
    if not any(b.get("v") for b in bars):
        return None
    day = [_dt.datetime.fromtimestamp(b["t"] / 1000, SERVER_TZ).date() for b in bars]
    out = {"session": _vwap(bars, lambda i: day[i]), "week": _vwap(bars, lambda i: day[i].isocalendar()[:2])["vwap"],
           "starts": [i for i in range(1, len(bars)) if day[i] != day[i - 1]]}
    prot = m.get("protected")
    out["anchored"] = _vwap(bars, None, prot["idx"])["vwap"] if prot else None
    out["anchored_idx"] = prot["idx"] if prot else None
    return out


def indicators(bars: List[Dict], m: Dict) -> Dict:
    tr = true_range(bars)
    close = [b["c"] for b in bars]
    r = rsi(close)
    md = macd(close)
    return {"atr": {"wilder": rma(tr, N_ATR), "mt5": sma(tr, N_ATR)}, "rsi": r, "macd": md,
            "divergences": divergences(bars, r, "RSI") + divergences(bars, md["macd"], "MACD"),
            "fib": fib(bars, m), "fib_ext": fib_ext(m), "vwap": vwap(bars, m)}
