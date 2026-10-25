"""
tools/indicators.py — classic indicators on any bars.

Series functions return one value per input (None until there is enough data), so
they line up with the bars. `atr()` and `rsi()` return only the last value.
"""
from __future__ import annotations

import datetime as _dt
import math
from typing import List, Optional, Tuple

from .bars import Bar, session_key

Series = List[Optional[float]]


# ── averages ────────────────────────────────────────────────────────────────

def sma(vals: List[Optional[float]], n: int) -> Series:
    out: Series = []
    for i in range(len(vals)):
        w = vals[i + 1 - n:i + 1] if i + 1 >= n else []
        out.append(sum(w) / n if w and None not in w else None)
    return out


def ema(vals: List[Optional[float]], n: int) -> Series:
    """Seeded with the SMA of the first n values; a None input repeats the last value."""
    out: Series = []
    k = 2.0 / (n + 1)
    e = None
    for i, v in enumerate(vals):
        if v is None:
            out.append(e)
            continue
        if e is None:
            if i + 1 >= n:
                e = sum(vals[i + 1 - n:i + 1]) / n
            out.append(e)
            continue
        e = v * k + e * (1 - k)
        out.append(e)
    return out


def rma(vals: List[float], n: int) -> Series:
    """Wilder's smoothing (the average inside ATR, RSI and ADX)."""
    out: Series = []
    a = None
    for i, v in enumerate(vals):
        if a is None:
            if i + 1 >= n:
                a = sum(vals[i + 1 - n:i + 1]) / n
            out.append(a)
            continue
        a = (a * (n - 1) + v) / n
        out.append(a)
    return out


# ── volatility ──────────────────────────────────────────────────────────────

def true_range(bars: List[Bar]) -> List[float]:
    """Per bar; the first bar has no previous close, so its range is high − low."""
    out = []
    for i, b in enumerate(bars):
        if i == 0:
            out.append(b["h"] - b["l"])
        else:
            pc = bars[i - 1]["c"]
            out.append(max(b["h"] - b["l"], abs(b["h"] - pc), abs(b["l"] - pc)))
    return out


def atr(bars: List[Bar], n: int = 14) -> Optional[float]:
    """Wilder ATR of the last bar (needs n + 1 bars: true ranges start at the second bar)."""
    if len(bars) < n + 1:
        return None
    trs = true_range(bars)[1:]
    a = sum(trs[:n]) / n
    for tr in trs[n:]:
        a = (a * (n - 1) + tr) / n
    return a


def atr_series(bars: List[Bar], n: int = 14) -> Series:
    trs = true_range(bars)[1:]
    return [None] + rma(trs, n) if bars else []


def bollinger(closes: List[float], n: int = 20, k: float = 2.0) -> Tuple[Series, Series, Series]:
    """(middle, upper, lower)."""
    mid = sma(closes, n)
    up: Series = []
    lo: Series = []
    for i, m in enumerate(mid):
        if m is None:
            up.append(None)
            lo.append(None)
            continue
        w = closes[i + 1 - n:i + 1]
        sd = math.sqrt(sum((x - m) ** 2 for x in w) / n)
        up.append(m + k * sd)
        lo.append(m - k * sd)
    return mid, up, lo


def keltner(bars: List[Bar], n: int = 20, mult: float = 2.0) -> Tuple[Series, Series, Series]:
    """(middle EMA, upper, lower) with ATR bands."""
    mid = ema([b["c"] for b in bars], n)
    a = atr_series(bars, n)
    up = [m + mult * x if m is not None and x is not None else None for m, x in zip(mid, a)]
    lo = [m - mult * x if m is not None and x is not None else None for m, x in zip(mid, a)]
    return mid, up, lo


def donchian(bars: List[Bar], n: int = 20) -> Tuple[Series, Series]:
    """(highest high, lowest low) of the last n bars, this bar included."""
    up: Series = []
    lo: Series = []
    for i in range(len(bars)):
        if i + 1 < n:
            up.append(None)
            lo.append(None)
            continue
        w = bars[i + 1 - n:i + 1]
        up.append(max(b["h"] for b in w))
        lo.append(min(b["l"] for b in w))
    return up, lo


# ── momentum ────────────────────────────────────────────────────────────────

def rsi(closes: List[float], n: int = 14) -> Optional[float]:
    """Wilder RSI of the last close (needs n + 1 closes)."""
    s = rsi_series(closes, n)
    return s[-1] if s else None


def rsi_series(closes: List[float], n: int = 14) -> Series:
    out: Series = [None] * len(closes)
    if len(closes) < n + 1:
        return out
    up = sum(max(closes[i] - closes[i - 1], 0.0) for i in range(1, n + 1)) / n
    dn = sum(max(closes[i - 1] - closes[i], 0.0) for i in range(1, n + 1)) / n
    out[n] = 100.0 if dn == 0 else 100.0 - 100.0 / (1.0 + up / dn)
    for i in range(n + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        up = (up * (n - 1) + max(d, 0.0)) / n
        dn = (dn * (n - 1) + max(-d, 0.0)) / n
        out[i] = 100.0 if dn == 0 else 100.0 - 100.0 / (1.0 + up / dn)
    return out


def macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[Series, Series, Series]:
    """(macd line, signal line, histogram)."""
    f, s = ema(closes, fast), ema(closes, slow)
    line = [a - b if a is not None and b is not None else None for a, b in zip(f, s)]
    first = next((i for i, v in enumerate(line) if v is not None), len(line))
    sig = [None] * first + ema(line[first:], signal)
    hist = [a - b if a is not None and b is not None else None for a, b in zip(line, sig)]
    return line, sig, hist


def stochastic(bars: List[Bar], k: int = 14, d: int = 3) -> Tuple[Series, Series]:
    """(%K, %D): where the close sits in the last k bars' range, and its d-bar average."""
    pk: Series = []
    for i in range(len(bars)):
        if i + 1 < k:
            pk.append(None)
            continue
        w = bars[i + 1 - k:i + 1]
        hi, lo = max(b["h"] for b in w), min(b["l"] for b in w)
        pk.append(100.0 * (bars[i]["c"] - lo) / (hi - lo) if hi > lo else 50.0)
    first = next((i for i, v in enumerate(pk) if v is not None), len(pk))
    return pk, [None] * first + sma(pk[first:], d)


def adx(bars: List[Bar], n: int = 14) -> Tuple[Series, Series, Series]:
    """(ADX, +DI, −DI), Wilder. ADX above ~25 = trending, below ~20 = ranging."""
    size = len(bars)
    if size < 2 * n + 1:
        return [None] * size, [None] * size, [None] * size
    pdm, mdm = [], []
    for i in range(1, size):
        up, dn = bars[i]["h"] - bars[i - 1]["h"], bars[i - 1]["l"] - bars[i]["l"]
        pdm.append(up if up > dn and up > 0 else 0.0)
        mdm.append(dn if dn > up and dn > 0 else 0.0)
    tr = true_range(bars)[1:]
    a, p, m = rma(tr, n), rma(pdm, n), rma(mdm, n)
    pdi = [100.0 * x / y if x is not None and y else None for x, y in zip(p, a)]
    mdi = [100.0 * x / y if x is not None and y else None for x, y in zip(m, a)]
    dx = [100.0 * abs(x - y) / (x + y) if x is not None and y is not None and x + y else None for x, y in zip(pdi, mdi)]
    first = next((i for i, v in enumerate(dx) if v is not None), len(dx))
    ax = [None] * first + rma([v or 0.0 for v in dx[first:]], n)
    return [None] + ax, [None] + pdi, [None] + mdi


def supertrend(bars: List[Bar], n: int = 10, mult: float = 3.0) -> Tuple[Series, List[Optional[int]]]:
    """(line, direction): direction +1 = up (line below price), −1 = down."""
    a = atr_series(bars, n)
    line: Series = []
    dirn: List[Optional[int]] = []
    fu = fl = None
    d = 1
    for i, b in enumerate(bars):
        if a[i] is None:
            line.append(None)
            dirn.append(None)
            continue
        mid = (b["h"] + b["l"]) / 2.0
        bu, bl = mid + mult * a[i], mid - mult * a[i]
        pc = bars[i - 1]["c"] if i else b["c"]
        fu = bu if fu is None or bu < fu or pc > fu else fu
        fl = bl if fl is None or bl > fl or pc < fl else fl
        if d == 1 and b["c"] < fl:
            d = -1
        elif d == -1 and b["c"] > fu:
            d = 1
        line.append(fl if d == 1 else fu)
        dirn.append(d)
    return line, dirn


# ── volume-weighted ─────────────────────────────────────────────────────────

def vwap(bars: List[Bar], tz: _dt.tzinfo) -> Series:
    """Session VWAP per bar (typical price × volume), reset at each new session."""
    out: Series = []
    day = None
    pv = 0.0
    vv = 0
    for b in bars:
        d = session_key(b["t"], tz)
        if d != day:
            day, pv, vv = d, 0.0, 0
        pv += (b["h"] + b["l"] + b["c"]) / 3.0 * b["v"]
        vv += b["v"]
        out.append(pv / vv if vv else None)
    return out


def vwap_bands(bars: List[Bar], tz: _dt.tzinfo, mult: float = 1.0) -> Tuple[Series, Series, Series]:
    """(vwap, upper, lower): bands at mult × the volume-weighted standard deviation."""
    mid: Series = []
    up: Series = []
    lo: Series = []
    day = None
    pv = pv2 = 0.0
    vv = 0
    for b in bars:
        d = session_key(b["t"], tz)
        if d != day:
            day, pv, pv2, vv = d, 0.0, 0.0, 0
        tp = (b["h"] + b["l"] + b["c"]) / 3.0
        pv += tp * b["v"]
        pv2 += tp * tp * b["v"]
        vv += b["v"]
        if not vv:
            mid.append(None)
            up.append(None)
            lo.append(None)
            continue
        m = pv / vv
        sd = math.sqrt(max(pv2 / vv - m * m, 0.0))
        mid.append(m)
        up.append(m + mult * sd)
        lo.append(m - mult * sd)
    return mid, up, lo


def obv(bars: List[Bar]) -> List[float]:
    """On-balance volume."""
    out, total = [], 0.0
    for i, b in enumerate(bars):
        if i and b["c"] > bars[i - 1]["c"]:
            total += b["v"]
        elif i and b["c"] < bars[i - 1]["c"]:
            total -= b["v"]
        out.append(total)
    return out
