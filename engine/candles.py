"""engine/candles.py — row 3 of the /smc concept table: a pure-Python / numpy port of TA-Lib's 61 candlestick
pattern functions, so every candle pattern has one fixed definition (TA-Lib's C source, the reference most tools
use). Written and verified 2026-10-29 by a Fable 5.1 agent: 0 mismatches for all 61 against TA-Lib 0.8.2 on
GOLD M5–H4, EURUSD M5 / M15 / H1 and 36 synthetic series (test_candles.py keeps a TA-Lib reference file).

    patterns(o, h, l, c) -> {"CDL2CROWS": int32[n], ..., "CDLXSIDEGAP3METHODS": int32[n]}

Values are exactly TA-Lib's (0, +-80, +-100, +-200) bar for bar, including the
leading lookback bars (0) - verified against TA-Lib 0.8.x (C lib 0.8.1) by verify.py.

Port notes (what has to be replicated to be bit-exact, not only rule-exact):
  * The "average" thresholds (long body, doji, near, equal ...) are a running total
    over the previous `period` candles that TA-Lib carries forward with
    total = total + (range[i-k] - range[i-k-period]).  Floating point makes this
    differ in the last ulp from a fresh window sum, so `_Bars.avg` builds the same
    sequential running total (np.cumsum is sequential).
  * TA_CANDLEAVERAGE = factor * (total / period) / (2 if range type is Shadows else 1);
    with period 0 (ShadowLong / ShadowVeryLong) the candle's own real body is used.
  * A few comparisons in the C source use fma(); those use math.fma here.
  * CDLHIKKAKE / CDLHIKKAKEMOD carry state (confirmation within 3 bars -> +-200) and
    warm that state up from 3 bars before the lookback, like the C code.

Source of the rules: TA-Lib src/ta_func/ta_CDL*.c and src/ta_common/ta_global.c
(https://github.com/TA-Lib/ta-lib).
"""

import math

import numpy as np

# --------------------------------------------------------------------------------------
# CandleSettings defaults (ta_global.c): name -> (range type, averaging period, factor)
# --------------------------------------------------------------------------------------
SETTINGS = {
    "BodyLong":        ("RealBody", 10, 1.0),   # body longer than the avg body of the 10 prior candles
    "BodyVeryLong":    ("RealBody", 10, 3.0),   # body > 3 x that average
    "BodyShort":       ("RealBody", 10, 1.0),   # body shorter than that average
    "BodyDoji":        ("HighLow",  10, 0.1),   # body < 10 % of the avg high-low range of 10 prior candles
    "ShadowLong":      ("RealBody",  0, 1.0),   # shadow longer than the candle's own real body
    "ShadowVeryLong":  ("RealBody",  0, 2.0),   # shadow > 2 x the candle's own real body
    "ShadowShort":     ("Shadows",  10, 1.0),   # shadow < half the avg (upper+lower shadow) of 10 prior candles
    "ShadowVeryShort": ("HighLow",  10, 0.1),   # shadow < 10 % of the avg high-low range of 10 prior candles
    "Near":            ("HighLow",   5, 0.2),   # distance <= 20 % of the avg high-low range of 5 prior candles
    "Far":             ("HighLow",   5, 0.6),   # distance >= 60 % of that average
    "Equal":           ("HighLow",   5, 0.05),  # distance <= 5 % of that average
}

# optInPenetration defaults
PENETRATION = {
    "CDLABANDONEDBABY": 0.3, "CDLDARKCLOUDCOVER": 0.5, "CDLEVENINGDOJISTAR": 0.3,
    "CDLEVENINGSTAR": 0.3, "CDLMATHOLD": 0.5, "CDLMORNINGDOJISTAR": 0.3, "CDLMORNINGSTAR": 0.3,
}


def period(name):
    return SETTINGS[name][1]


_fma = np.frompyfunc(math.fma, 3, 1)


def fma(a, b, c):
    """Element-wise fused multiply-add a*b+c with a single rounding, like C fma()."""
    return _fma(a, b, c).astype(np.float64)


# --------------------------------------------------------------------------------------
# Shared candle helpers
# --------------------------------------------------------------------------------------
class _Bars:
    """OHLC arrays plus the TA-Lib candle macros, all aligned to the bar index i.

    Every accessor takes k = how many bars back (0 = the current bar), so a rule written
    in the C source as inClose[i - 2] reads b.c(2) here.  The first k values of a shifted
    array are NaN (comparisons with NaN are False) and are masked anyway by the lookback.
    """

    def __init__(self, o, h, l, c):
        self.O = np.ascontiguousarray(o, dtype=np.float64)
        self.H = np.ascontiguousarray(h, dtype=np.float64)
        self.L = np.ascontiguousarray(l, dtype=np.float64)
        self.C = np.ascontiguousarray(c, dtype=np.float64)
        self.n = len(self.C)
        white = self.C >= self.O
        self.COLOR = np.where(white, 1, -1).astype(np.int64)        # TA_CANDLECOLOR
        self.BODY = np.abs(self.C - self.O)                         # TA_REALBODY
        self.TOP = np.where(white, self.C, self.O)                  # max(open, close)
        self.BOT = np.where(white, self.O, self.C)                  # min(open, close)
        self.UPPER = self.H - self.TOP                              # TA_UPPERSHADOW
        self.LOWER = self.BOT - self.L                              # TA_LOWERSHADOW
        self.HL = self.H - self.L                                   # TA_HIGHLOWRANGE
        self._range = {"RealBody": self.BODY, "HighLow": self.HL,
                       "Shadows": self.UPPER + self.LOWER}          # TA_CANDLERANGE
        self._avg_cache = {}

    # -- shifted views -----------------------------------------------------------------
    def sh(self, x, k):
        if k == 0:
            return x
        y = np.empty_like(x)
        y[:k] = 0 if x.dtype.kind == "i" else np.nan
        y[k:] = x[:-k]
        return y

    def o(self, k): return self.sh(self.O, k)
    def h(self, k): return self.sh(self.H, k)
    def l(self, k): return self.sh(self.L, k)
    def c(self, k): return self.sh(self.C, k)
    def col(self, k): return self.sh(self.COLOR, k)
    def body(self, k): return self.sh(self.BODY, k)
    def top(self, k): return self.sh(self.TOP, k)
    def bot(self, k): return self.sh(self.BOT, k)
    def up(self, k): return self.sh(self.UPPER, k)
    def lo(self, k): return self.sh(self.LOWER, k)

    # -- gap macros --------------------------------------------------------------------
    def rb_gap_up(self, k2, k1):     # TA_REALBODYGAPUP(i-k2, i-k1)
        return self.bot(k2) > self.top(k1)

    def rb_gap_down(self, k2, k1):   # TA_REALBODYGAPDOWN
        return self.top(k2) < self.bot(k1)

    def gap_up(self, k2, k1):        # TA_CANDLEGAPUP
        return self.l(k2) > self.h(k1)

    def gap_down(self, k2, k1):      # TA_CANDLEGAPDOWN
        return self.h(k2) < self.l(k1)

    # -- TA_CANDLEAVERAGE with TA-Lib's running total -----------------------------------
    def avg(self, name, k, first):
        """Threshold for candle i-k as evaluated at bar i, for every i >= first.

        Reproduces TA_CANDLEAVERAGE(name, <PeriodTotal>, i-k) where the period total is
        seeded with a sequential sum over range[first-k-period : first-k] and then rolled
        forward one bar at a time from bar `first` on (first = the pattern's lookback,
        except CDLHIKKAKEMOD which starts its warm-up 3 bars earlier).
        """
        rtype, per, fac = SETTINGS[name]
        r = self._range[rtype]
        div = 2.0 if rtype == "Shadows" else 1.0
        if per == 0:
            return fac * self.sh(r, k) / div
        key = (name, k, first)
        if key not in self._avg_cache:
            n = self.n
            tot = np.full(n, np.nan)
            if first < n:
                init = 0.0
                for j in range(first - k - per, first - k):
                    init = init + r[j]
                step = r[first - k:n - k] - r[first - k - per:n - k - per]
                tot[first:] = np.cumsum(np.concatenate(([init], step[:-1])))
            self._avg_cache[key] = fac * (tot / per) / div
        return self._avg_cache[key]

    # -- result ------------------------------------------------------------------------
    def out(self, cond, value, lookback):
        res = np.where(cond, value, 0).astype(np.int32)
        res[:lookback] = 0
        return res


# --------------------------------------------------------------------------------------
# The 61 patterns, one small function each (lookback = TA_CDLxxx_Lookback())
# --------------------------------------------------------------------------------------
def cdl2crows(b):
    lb = period("BodyLong") + 2
    cond = ((b.col(2) == 1) & (b.body(2) > b.avg("BodyLong", 2, lb))
            & (b.col(1) == -1) & b.rb_gap_up(1, 2)
            & (b.col(0) == -1) & (b.o(0) < b.o(1)) & (b.o(0) > b.c(1))
            & (b.c(0) > b.o(2)) & (b.c(0) < b.c(2)))
    return b.out(cond, -100, lb)


def cdl3blackcrows(b):
    lb = period("ShadowVeryShort") + 3
    cond = ((b.col(3) == 1) & (b.col(2) == -1) & (b.col(1) == -1) & (b.col(0) == -1)
            & (b.o(1) < b.o(2)) & (b.o(1) > b.c(2))
            & (b.o(0) < b.o(1)) & (b.o(0) > b.c(1))
            & (b.h(3) > b.c(2)) & (b.c(2) > b.c(1)) & (b.c(1) > b.c(0))
            & (b.lo(2) < b.avg("ShadowVeryShort", 2, lb))
            & (b.lo(1) < b.avg("ShadowVeryShort", 1, lb))
            & (b.lo(0) < b.avg("ShadowVeryShort", 0, lb)))
    return b.out(cond, -100, lb)


def cdl3inside(b):
    lb = max(period("BodyShort"), period("BodyLong")) + 2
    cond = ((b.top(1) < b.top(2)) & (b.bot(1) > b.bot(2))
            & (((b.col(2) == 1) & (b.col(0) == -1) & (b.c(0) < b.o(2)))
               | ((b.col(2) == -1) & (b.col(0) == 1) & (b.c(0) > b.o(2))))
            & (b.body(2) > b.avg("BodyLong", 2, lb))
            & (b.body(1) <= b.avg("BodyShort", 1, lb)))
    return b.out(cond, -b.col(2) * 100, lb)


def cdl3linestrike(b):
    lb = period("Near") + 3
    near3, near2 = b.avg("Near", 3, lb), b.avg("Near", 2, lb)
    cond = ((b.col(3) == b.col(2)) & (b.col(2) == b.col(1)) & (b.col(0) == -b.col(1))
            & (b.o(2) >= b.bot(3) - near3) & (b.o(2) <= b.top(3) + near3)
            & (b.o(1) >= b.bot(2) - near2) & (b.o(1) <= b.top(2) + near2)
            & (((b.col(1) == 1) & (b.c(1) > b.c(2)) & (b.c(2) > b.c(3))
                & (b.o(0) > b.c(1)) & (b.c(0) < b.o(3)))
               | ((b.col(1) == -1) & (b.c(1) < b.c(2)) & (b.c(2) < b.c(3))
                  & (b.o(0) < b.c(1)) & (b.c(0) > b.o(3)))))
    return b.out(cond, b.col(1) * 100, lb)


def cdl3outside(b):
    lb = 3
    cond = (((b.col(1) == 1) & (b.col(2) == -1) & (b.c(1) > b.o(2)) & (b.o(1) < b.c(2))
             & (b.c(0) > b.c(1)))
            | ((b.col(1) == -1) & (b.col(2) == 1) & (b.o(1) > b.c(2)) & (b.c(1) < b.o(2))
               & (b.c(0) < b.c(1))))
    return b.out(cond, b.col(1) * 100, lb)


def cdl3starsinsouth(b):
    lb = max(period("ShadowVeryShort"), period("ShadowLong"),
             period("BodyLong"), period("BodyShort")) + 2
    svs0 = b.avg("ShadowVeryShort", 0, lb)
    cond = ((b.col(2) == -1) & (b.col(1) == -1) & (b.col(0) == -1)
            & (b.body(2) > b.avg("BodyLong", 2, lb))
            & (b.lo(2) > b.avg("ShadowLong", 2, lb))
            & (b.body(1) < b.body(2))
            & (b.o(1) > b.c(2)) & (b.o(1) <= b.h(2))
            & (b.l(1) < b.c(2)) & (b.l(1) >= b.l(2))
            & (b.lo(1) > b.avg("ShadowVeryShort", 1, lb))
            & (b.body(0) < b.avg("BodyShort", 0, lb))
            & (b.lo(0) < svs0) & (b.up(0) < svs0)
            & (b.l(0) > b.l(1)) & (b.h(0) < b.h(1)))
    return b.out(cond, 100, lb)


def cdl3whitesoldiers(b):
    lb = max(period("ShadowVeryShort"), period("BodyShort"), period("Far"), period("Near")) + 2
    cond = ((b.col(2) == 1) & (b.up(2) < b.avg("ShadowVeryShort", 2, lb))
            & (b.col(1) == 1) & (b.up(1) < b.avg("ShadowVeryShort", 1, lb))
            & (b.col(0) == 1) & (b.up(0) < b.avg("ShadowVeryShort", 0, lb))
            & (b.c(0) > b.c(1)) & (b.c(1) > b.c(2))
            & (b.o(1) > b.o(2)) & (b.o(1) <= b.c(2) + b.avg("Near", 2, lb))
            & (b.o(0) > b.o(1)) & (b.o(0) <= b.c(1) + b.avg("Near", 1, lb))
            & (b.body(1) > b.body(2) - b.avg("Far", 2, lb))
            & (b.body(0) > b.body(1) - b.avg("Far", 1, lb))
            & (b.body(0) > b.avg("BodyShort", 0, lb)))
    return b.out(cond, 100, lb)


def cdlabandonedbaby(b, pen=PENETRATION["CDLABANDONEDBABY"]):
    lb = max(period("BodyDoji"), period("BodyLong"), period("BodyShort")) + 2
    cond = ((b.body(2) > b.avg("BodyLong", 2, lb))
            & (b.body(1) <= b.avg("BodyDoji", 1, lb))
            & (b.body(0) > b.avg("BodyShort", 0, lb))
            & (((b.col(2) == 1) & (b.col(0) == -1)
                & (b.c(0) < b.c(2) - b.body(2) * pen)
                & b.gap_up(1, 2) & b.gap_down(0, 1))
               | ((b.col(2) == -1) & (b.col(0) == 1)
                  & (b.c(0) > fma(b.body(2), pen, b.c(2)))
                  & b.gap_down(1, 2) & b.gap_up(0, 1))))
    return b.out(cond, b.col(0) * 100, lb)


def cdladvanceblock(b):
    lb = max(period("ShadowLong"), period("ShadowShort"), period("Far"), period("Near"),
             period("BodyLong")) + 2
    far2, far1 = b.avg("Far", 2, lb), b.avg("Far", 1, lb)
    near2, near1 = b.avg("Near", 2, lb), b.avg("Near", 1, lb)
    cond = ((b.col(2) == 1) & (b.col(1) == 1) & (b.col(0) == 1)
            & (b.c(0) > b.c(1)) & (b.c(1) > b.c(2))
            & (b.o(1) > b.o(2)) & (b.o(1) <= b.c(2) + near2)
            & (b.o(0) > b.o(1)) & (b.o(0) <= b.c(1) + near1)
            & (b.body(2) > b.avg("BodyLong", 2, lb))
            & (b.up(2) < b.avg("ShadowShort", 2, lb))
            & (((b.body(1) < b.body(2) - far2) & (b.body(0) < b.body(1) + near1))
               | (b.body(0) < b.body(1) - far1)
               | ((b.body(0) < b.body(1)) & (b.body(1) < b.body(2))
                  & ((b.up(0) > b.avg("ShadowShort", 0, lb))
                     | (b.up(1) > b.avg("ShadowShort", 1, lb))))
               | ((b.body(0) < b.body(1)) & (b.up(0) > b.avg("ShadowLong", 0, lb)))))
    return b.out(cond, -100, lb)


def cdlbelthold(b):
    lb = max(period("BodyLong"), period("ShadowVeryShort"))
    svs = b.avg("ShadowVeryShort", 0, lb)
    cond = ((b.body(0) > b.avg("BodyLong", 0, lb))
            & (((b.col(0) == 1) & (b.lo(0) < svs)) | ((b.col(0) == -1) & (b.up(0) < svs))))
    return b.out(cond, b.col(0) * 100, lb)


def cdlbreakaway(b):
    lb = period("BodyLong") + 4
    cond = ((b.col(4) == b.col(3)) & (b.col(3) == b.col(1)) & (b.col(1) == -b.col(0))
            & (b.body(4) > b.avg("BodyLong", 4, lb))
            & (((b.col(4) == -1) & b.rb_gap_down(3, 4)
                & (b.h(2) < b.h(3)) & (b.l(2) < b.l(3))
                & (b.h(1) < b.h(2)) & (b.l(1) < b.l(2))
                & (b.c(0) > b.o(3)) & (b.c(0) < b.c(4)))
               | ((b.col(4) == 1) & b.rb_gap_up(3, 4)
                  & (b.h(2) > b.h(3)) & (b.l(2) > b.l(3))
                  & (b.h(1) > b.h(2)) & (b.l(1) > b.l(2))
                  & (b.c(0) < b.o(3)) & (b.c(0) > b.c(4)))))
    return b.out(cond, b.col(0) * 100, lb)


def cdlclosingmarubozu(b):
    lb = max(period("BodyLong"), period("ShadowVeryShort"))
    svs = b.avg("ShadowVeryShort", 0, lb)
    cond = ((b.body(0) > b.avg("BodyLong", 0, lb))
            & (((b.col(0) == 1) & (b.up(0) < svs)) | ((b.col(0) == -1) & (b.lo(0) < svs))))
    return b.out(cond, b.col(0) * 100, lb)


def cdlconcealbabyswall(b):
    lb = period("ShadowVeryShort") + 3
    svs3, svs2, svs1 = (b.avg("ShadowVeryShort", k, lb) for k in (3, 2, 1))
    cond = ((b.col(3) == -1) & (b.col(2) == -1) & (b.col(1) == -1) & (b.col(0) == -1)
            & (b.lo(3) < svs3) & (b.up(3) < svs3)
            & (b.lo(2) < svs2) & (b.up(2) < svs2)
            & b.rb_gap_down(1, 2) & (b.up(1) > svs1) & (b.h(1) > b.c(2))
            & (b.h(0) > b.h(1)) & (b.l(0) < b.l(1)))
    return b.out(cond, 100, lb)


def cdlcounterattack(b):
    lb = max(period("Equal"), period("BodyLong")) + 1
    eq = b.avg("Equal", 1, lb)
    cond = ((b.col(1) == -b.col(0))
            & (b.body(1) > b.avg("BodyLong", 1, lb)) & (b.body(0) > b.avg("BodyLong", 0, lb))
            & (b.c(0) <= b.c(1) + eq) & (b.c(0) >= b.c(1) - eq))
    return b.out(cond, b.col(0) * 100, lb)


def cdldarkcloudcover(b, pen=PENETRATION["CDLDARKCLOUDCOVER"]):
    lb = period("BodyLong") + 1
    cond = ((b.col(1) == 1) & (b.body(1) > b.avg("BodyLong", 1, lb))
            & (b.col(0) == -1) & (b.o(0) > b.h(1)) & (b.c(0) > b.o(1))
            & (b.c(0) < b.c(1) - b.body(1) * pen))
    return b.out(cond, -100, lb)


def cdldoji(b):
    lb = period("BodyDoji")
    return b.out(b.body(0) <= b.avg("BodyDoji", 0, lb), 100, lb)


def cdldojistar(b):
    lb = max(period("BodyDoji"), period("BodyLong")) + 1
    cond = ((b.body(1) > b.avg("BodyLong", 1, lb)) & (b.body(0) <= b.avg("BodyDoji", 0, lb))
            & (((b.col(1) == 1) & b.rb_gap_up(0, 1)) | ((b.col(1) == -1) & b.rb_gap_down(0, 1))))
    return b.out(cond, -b.col(1) * 100, lb)


def cdldragonflydoji(b):
    lb = max(period("BodyDoji"), period("ShadowVeryShort"))
    svs = b.avg("ShadowVeryShort", 0, lb)
    cond = (b.body(0) <= b.avg("BodyDoji", 0, lb)) & (b.up(0) < svs) & (b.lo(0) > svs)
    return b.out(cond, 100, lb)


def cdlengulfing(b):
    lb = 2
    cond = (((b.col(0) == 1) & (b.col(1) == -1)
             & (((b.c(0) >= b.o(1)) & (b.o(0) < b.c(1))) | ((b.c(0) > b.o(1)) & (b.o(0) <= b.c(1)))))
            | ((b.col(0) == -1) & (b.col(1) == 1)
               & (((b.o(0) >= b.c(1)) & (b.c(0) < b.o(1))) | ((b.o(0) > b.c(1)) & (b.c(0) <= b.o(1))))))
    strict = (b.o(0) != b.c(1)) & (b.c(0) != b.o(1))
    return b.out(cond, np.where(strict, b.col(0) * 100, b.col(0) * 80), lb)


def cdleveningdojistar(b, pen=PENETRATION["CDLEVENINGDOJISTAR"]):
    lb = max(period("BodyDoji"), period("BodyLong"), period("BodyShort")) + 2
    cond = ((b.col(2) == 1) & (b.col(0) == -1) & b.rb_gap_up(1, 2)
            & (b.c(0) < b.c(2) - b.body(2) * pen)
            & (b.body(2) > b.avg("BodyLong", 2, lb))
            & (b.body(1) <= b.avg("BodyDoji", 1, lb))
            & (b.body(0) > b.avg("BodyShort", 0, lb)))
    return b.out(cond, -100, lb)


def cdleveningstar(b, pen=PENETRATION["CDLEVENINGSTAR"]):
    lb = max(period("BodyShort"), period("BodyLong")) + 2
    cond = ((b.col(2) == 1) & (b.col(0) == -1) & b.rb_gap_up(1, 2)
            & (b.c(0) < b.c(2) - b.body(2) * pen)
            & (b.body(2) > b.avg("BodyLong", 2, lb))
            & (b.body(1) <= b.avg("BodyShort", 1, lb))
            & (b.body(0) > b.avg("BodyShort", 0, lb)))
    return b.out(cond, -100, lb)


def cdlgapsidesidewhite(b):
    lb = max(period("Near"), period("Equal")) + 2
    near, eq = b.avg("Near", 1, lb), b.avg("Equal", 1, lb)
    up_gap = b.rb_gap_up(1, 2)
    cond = (((up_gap & b.rb_gap_up(0, 2)) | (b.rb_gap_down(1, 2) & b.rb_gap_down(0, 2)))
            & (b.col(1) == 1) & (b.col(0) == 1)
            & (b.body(0) >= b.body(1) - near) & (b.body(0) <= b.body(1) + near)
            & (b.o(0) >= b.o(1) - eq) & (b.o(0) <= b.o(1) + eq))
    return b.out(cond, np.where(up_gap, 100, -100), lb)


def cdlgravestonedoji(b):
    lb = max(period("BodyDoji"), period("ShadowVeryShort"))
    svs = b.avg("ShadowVeryShort", 0, lb)
    cond = (b.body(0) <= b.avg("BodyDoji", 0, lb)) & (b.lo(0) < svs) & (b.up(0) > svs)
    return b.out(cond, 100, lb)


def _hammer_core(b, lb):
    return ((b.body(0) < b.avg("BodyShort", 0, lb))
            & (b.lo(0) > b.avg("ShadowLong", 0, lb))
            & (b.up(0) < b.avg("ShadowVeryShort", 0, lb)))


def cdlhammer(b):
    lb = max(period("BodyShort"), period("ShadowLong"), period("ShadowVeryShort"), period("Near")) + 1
    cond = _hammer_core(b, lb) & (b.bot(0) <= b.l(1) + b.avg("Near", 1, lb))
    return b.out(cond, 100, lb)


def cdlhangingman(b):
    lb = max(period("BodyShort"), period("ShadowLong"), period("ShadowVeryShort"), period("Near")) + 1
    cond = _hammer_core(b, lb) & (b.bot(0) >= b.h(1) - b.avg("Near", 1, lb))
    return b.out(cond, -100, lb)


def _harami(b, second_setting):
    lb = max(period(second_setting), period("BodyLong")) + 1
    ok = (b.body(1) > b.avg("BodyLong", 1, lb)) & (b.body(0) <= b.avg(second_setting, 0, lb))
    strict = (b.top(0) < b.top(1)) & (b.bot(0) > b.bot(1))
    loose = (b.top(0) <= b.top(1)) & (b.bot(0) >= b.bot(1))
    value = np.where(strict, -b.col(1) * 100, np.where(loose, -b.col(1) * 80, 0))
    return b.out(ok, value, lb)


def cdlharami(b):
    return _harami(b, "BodyShort")


def cdlharamicross(b):
    return _harami(b, "BodyDoji")


def cdlhighwave(b):
    lb = max(period("BodyShort"), period("ShadowVeryLong"))
    svl = b.avg("ShadowVeryLong", 0, lb)
    cond = (b.body(0) < b.avg("BodyShort", 0, lb)) & (b.up(0) > svl) & (b.lo(0) > svl)
    return b.out(cond, b.col(0) * 100, lb)


def cdlhikkake(b):
    """Stateful: +-100 on the pattern bar, +-200 on a confirming close within 3 bars."""
    lb = 5
    H, L, C = b.H.tolist(), b.L.tolist(), b.C.tolist()
    out = np.zeros(b.n, dtype=np.int32)
    cd, result, saved_high, saved_low = 0, 0, 0.0, 0.0
    for i in range(lb - 3, b.n):               # warm-up from startIdx-3, exactly like the C code
        if (H[i - 1] < H[i - 2] and L[i - 1] > L[i - 2]
                and ((H[i] < H[i - 1] and L[i] < L[i - 1]) or (H[i] > H[i - 1] and L[i] > L[i - 1]))):
            result = 100 if H[i] < H[i - 1] else -100
            saved_high, saved_low = H[i - 1], L[i - 1]
            cd = 4
            if i >= lb:
                out[i] = result
        elif cd > 0 and ((result > 0 and C[i] > saved_high) or (result < 0 and C[i] < saved_low)):
            if i >= lb:
                out[i] = result + (100 if result > 0 else -100)
            cd = 0
        if cd > 0:
            cd -= 1
    return out


def cdlhikkakemod(b):
    """Stateful like CDLHIKKAKE; the 2nd candle must close near its low (bull) / high (bear)."""
    lb = max(1, period("Near")) + 5
    first = lb - 3                              # the C code warms the state up from startIdx-3
    near2 = b.avg("Near", 2, first).tolist()
    H, L, C = b.H.tolist(), b.L.tolist(), b.C.tolist()
    out = np.zeros(b.n, dtype=np.int32)
    count, result, p_high, p_low = 0, 0, 0.0, 0.0
    for i in range(first, b.n):
        if (H[i - 2] < H[i - 3] and L[i - 2] > L[i - 3]
                and H[i - 1] < H[i - 2] and L[i - 1] > L[i - 2]
                and ((H[i] < H[i - 1] and L[i] < L[i - 1] and C[i - 2] <= L[i - 2] + near2[i])
                     or (H[i] > H[i - 1] and L[i] > L[i - 1] and C[i - 2] >= H[i - 2] - near2[i]))):
            result = 100 if H[i] < H[i - 1] else -100
            p_high, p_low = H[i - 1], L[i - 1]
            count = 4
            if i >= lb:
                out[i] = result
        elif count > 0 and ((result > 0 and C[i] > p_high) or (result < 0 and C[i] < p_low)):
            if i >= lb:
                out[i] = result + (100 if result > 0 else -100)
            count = 0
        if count > 0:
            count -= 1
    return out


def cdlhomingpigeon(b):
    lb = max(period("BodyShort"), period("BodyLong")) + 1
    cond = ((b.col(1) == -1) & (b.col(0) == -1)
            & (b.body(1) > b.avg("BodyLong", 1, lb)) & (b.body(0) <= b.avg("BodyShort", 0, lb))
            & (b.o(0) < b.o(1)) & (b.c(0) > b.c(1)))
    return b.out(cond, 100, lb)


def cdlidentical3crows(b):
    lb = max(period("ShadowVeryShort"), period("Equal")) + 2
    eq2, eq1 = b.avg("Equal", 2, lb), b.avg("Equal", 1, lb)
    cond = ((b.col(2) == -1) & (b.lo(2) < b.avg("ShadowVeryShort", 2, lb))
            & (b.col(1) == -1) & (b.lo(1) < b.avg("ShadowVeryShort", 1, lb))
            & (b.col(0) == -1) & (b.lo(0) < b.avg("ShadowVeryShort", 0, lb))
            & (b.c(2) > b.c(1)) & (b.c(1) > b.c(0))
            & (b.o(1) <= b.c(2) + eq2) & (b.o(1) >= b.c(2) - eq2)
            & (b.o(0) <= b.c(1) + eq1) & (b.o(0) >= b.c(1) - eq1))
    return b.out(cond, -100, lb)


def cdlinneck(b):
    lb = max(period("Equal"), period("BodyLong")) + 1
    cond = ((b.col(1) == -1) & (b.body(1) > b.avg("BodyLong", 1, lb))
            & (b.col(0) == 1) & (b.o(0) < b.l(1))
            & (b.c(0) <= b.c(1) + b.avg("Equal", 1, lb)) & (b.c(0) >= b.c(1)))
    return b.out(cond, -100, lb)


def cdlinvertedhammer(b):
    lb = max(period("BodyShort"), period("ShadowLong"), period("ShadowVeryShort")) + 1
    cond = (b.rb_gap_down(0, 1)
            & (b.body(0) < b.avg("BodyShort", 0, lb))
            & (b.up(0) > b.avg("ShadowLong", 0, lb))
            & (b.lo(0) < b.avg("ShadowVeryShort", 0, lb)))
    return b.out(cond, 100, lb)


def _kicking_cond(b, lb):
    svs1, svs0 = b.avg("ShadowVeryShort", 1, lb), b.avg("ShadowVeryShort", 0, lb)
    return ((b.col(1) == -b.col(0))
            & (b.body(1) > b.avg("BodyLong", 1, lb)) & (b.up(1) < svs1) & (b.lo(1) < svs1)
            & (b.body(0) > b.avg("BodyLong", 0, lb)) & (b.up(0) < svs0) & (b.lo(0) < svs0)
            & (((b.col(1) == -1) & b.gap_up(0, 1)) | ((b.col(1) == 1) & b.gap_down(0, 1))))


def cdlkicking(b):
    lb = max(period("ShadowVeryShort"), period("BodyLong")) + 1
    return b.out(_kicking_cond(b, lb), b.col(0) * 100, lb)


def cdlkickingbylength(b):
    lb = max(period("ShadowVeryShort"), period("BodyLong")) + 1
    longer = np.where(b.body(0) > b.body(1), b.col(0), b.col(1))
    return b.out(_kicking_cond(b, lb), longer * 100, lb)


def cdlladderbottom(b):
    lb = period("ShadowVeryShort") + 4
    cond = ((b.col(4) == -1) & (b.col(3) == -1) & (b.col(2) == -1)
            & (b.o(4) > b.o(3)) & (b.o(3) > b.o(2))
            & (b.c(4) > b.c(3)) & (b.c(3) > b.c(2))
            & (b.col(1) == -1) & (b.up(1) > b.avg("ShadowVeryShort", 1, lb))
            & (b.col(0) == 1) & (b.o(0) > b.o(1)) & (b.c(0) > b.h(1)))
    return b.out(cond, 100, lb)


def cdllongleggeddoji(b):
    lb = max(period("BodyDoji"), period("ShadowLong"))
    sl = b.avg("ShadowLong", 0, lb)
    cond = (b.body(0) <= b.avg("BodyDoji", 0, lb)) & ((b.lo(0) > sl) | (b.up(0) > sl))
    return b.out(cond, 100, lb)


def cdllongline(b):
    lb = max(period("BodyLong"), period("ShadowShort"))
    ss = b.avg("ShadowShort", 0, lb)
    cond = (b.body(0) > b.avg("BodyLong", 0, lb)) & (b.up(0) < ss) & (b.lo(0) < ss)
    return b.out(cond, b.col(0) * 100, lb)


def cdlmarubozu(b):
    lb = max(period("BodyLong"), period("ShadowVeryShort"))
    svs = b.avg("ShadowVeryShort", 0, lb)
    cond = (b.body(0) > b.avg("BodyLong", 0, lb)) & (b.up(0) < svs) & (b.lo(0) < svs)
    return b.out(cond, b.col(0) * 100, lb)


def cdlmatchinglow(b):
    lb = period("Equal") + 1
    eq = b.avg("Equal", 1, lb)
    cond = ((b.col(1) == -1) & (b.col(0) == -1)
            & (b.c(0) <= b.c(1) + eq) & (b.c(0) >= b.c(1) - eq))
    return b.out(cond, 100, lb)


def cdlmathold(b, pen=PENETRATION["CDLMATHOLD"]):
    lb = max(period("BodyShort"), period("BodyLong")) + 4
    floor = b.c(4) - b.body(4) * pen
    cond = ((b.col(4) == 1) & (b.col(3) == -1) & (b.col(0) == 1)
            & b.rb_gap_up(3, 4)
            & (b.bot(2) < b.c(4)) & (b.bot(1) < b.c(4))
            & (b.bot(2) > floor) & (b.bot(1) > floor)
            & (b.top(2) < b.o(3)) & (b.top(1) < b.top(2))
            & (b.o(0) > b.c(1))
            & (b.c(0) > np.maximum(np.maximum(b.h(3), b.h(2)), b.h(1)))
            & (b.body(4) > b.avg("BodyLong", 4, lb))
            & (b.body(3) < b.avg("BodyShort", 3, lb))
            & (b.body(2) < b.avg("BodyShort", 2, lb))
            & (b.body(1) < b.avg("BodyShort", 1, lb)))
    return b.out(cond, 100, lb)


def cdlmorningdojistar(b, pen=PENETRATION["CDLMORNINGDOJISTAR"]):
    lb = max(period("BodyDoji"), period("BodyLong"), period("BodyShort")) + 2
    cond = ((b.col(2) == -1) & (b.col(0) == 1) & b.rb_gap_down(1, 2)
            & (b.c(0) > fma(b.body(2), pen, b.c(2)))
            & (b.body(2) > b.avg("BodyLong", 2, lb))
            & (b.body(1) <= b.avg("BodyDoji", 1, lb))
            & (b.body(0) > b.avg("BodyShort", 0, lb)))
    return b.out(cond, 100, lb)


def cdlmorningstar(b, pen=PENETRATION["CDLMORNINGSTAR"]):
    lb = max(period("BodyShort"), period("BodyLong")) + 2
    cond = ((b.col(2) == -1) & (b.col(0) == 1) & b.rb_gap_down(1, 2)
            & (b.c(0) > fma(b.body(2), pen, b.c(2)))
            & (b.body(2) > b.avg("BodyLong", 2, lb))
            & (b.body(1) <= b.avg("BodyShort", 1, lb))
            & (b.body(0) > b.avg("BodyShort", 0, lb)))
    return b.out(cond, 100, lb)


def cdlonneck(b):
    lb = max(period("Equal"), period("BodyLong")) + 1
    eq = b.avg("Equal", 1, lb)
    cond = ((b.col(1) == -1) & (b.body(1) > b.avg("BodyLong", 1, lb))
            & (b.col(0) == 1) & (b.o(0) < b.l(1))
            & (b.c(0) <= b.l(1) + eq) & (b.c(0) >= b.l(1) - eq))
    return b.out(cond, -100, lb)


def cdlpiercing(b):
    lb = period("BodyLong") + 1
    cond = ((b.col(1) == -1) & (b.body(1) > b.avg("BodyLong", 1, lb))
            & (b.col(0) == 1) & (b.body(0) > b.avg("BodyLong", 0, lb))
            & (b.o(0) < b.l(1)) & (b.c(0) < b.o(1))
            & (b.c(0) > fma(b.body(1), 0.5, b.c(1))))
    return b.out(cond, 100, lb)


def cdlrickshawman(b):
    lb = max(period("BodyDoji"), period("ShadowLong"), period("Near"))
    sl, near = b.avg("ShadowLong", 0, lb), b.avg("Near", 0, lb)
    mid = b.l(0) + (b.h(0) - b.l(0)) / 2
    cond = ((b.body(0) <= b.avg("BodyDoji", 0, lb))
            & (b.lo(0) > sl) & (b.up(0) > sl)
            & (b.bot(0) <= mid + near) & (b.top(0) >= mid - near))
    return b.out(cond, 100, lb)


def cdlrisefall3methods(b):
    lb = max(period("BodyShort"), period("BodyLong")) + 4
    s = b.col(4)
    cond = ((b.col(4) == -b.col(3)) & (b.col(3) == b.col(2)) & (b.col(2) == b.col(1))
            & (b.col(1) == -b.col(0))
            & (b.bot(3) < b.h(4)) & (b.top(3) > b.l(4))
            & (b.bot(2) < b.h(4)) & (b.top(2) > b.l(4))
            & (b.bot(1) < b.h(4)) & (b.top(1) > b.l(4))
            & (b.c(2) * s < b.c(3) * s) & (b.c(1) * s < b.c(2) * s)
            & (b.o(0) * s > b.c(1) * s) & (b.c(0) * s > b.c(4) * s)
            & (b.body(4) > b.avg("BodyLong", 4, lb))
            & (b.body(3) < b.avg("BodyShort", 3, lb))
            & (b.body(2) < b.avg("BodyShort", 2, lb))
            & (b.body(1) < b.avg("BodyShort", 1, lb))
            & (b.body(0) > b.avg("BodyLong", 0, lb)))
    return b.out(cond, 100 * s, lb)


def cdlseparatinglines(b):
    lb = max(period("ShadowVeryShort"), period("BodyLong"), period("Equal")) + 1
    eq, svs = b.avg("Equal", 1, lb), b.avg("ShadowVeryShort", 0, lb)
    cond = ((b.col(1) == -b.col(0))
            & (b.o(0) <= b.o(1) + eq) & (b.o(0) >= b.o(1) - eq)
            & (b.body(0) > b.avg("BodyLong", 0, lb))
            & (((b.col(0) == 1) & (b.lo(0) < svs)) | ((b.col(0) == -1) & (b.up(0) < svs))))
    return b.out(cond, b.col(0) * 100, lb)


def cdlshootingstar(b):
    lb = max(period("BodyShort"), period("ShadowLong"), period("ShadowVeryShort")) + 1
    cond = (b.rb_gap_up(0, 1)
            & (b.body(0) < b.avg("BodyShort", 0, lb))
            & (b.up(0) > b.avg("ShadowLong", 0, lb))
            & (b.lo(0) < b.avg("ShadowVeryShort", 0, lb)))
    return b.out(cond, -100, lb)


def cdlshortline(b):
    lb = max(period("BodyShort"), period("ShadowShort"))
    ss = b.avg("ShadowShort", 0, lb)
    cond = (b.body(0) < b.avg("BodyShort", 0, lb)) & (b.up(0) < ss) & (b.lo(0) < ss)
    return b.out(cond, b.col(0) * 100, lb)


def cdlspinningtop(b):
    lb = period("BodyShort")
    cond = ((b.up(0) > b.body(0)) & (b.lo(0) > b.body(0))
            & (b.body(0) < b.avg("BodyShort", 0, lb)))
    return b.out(cond, b.col(0) * 100, lb)


def cdlstalledpattern(b):
    lb = max(period("BodyLong"), period("BodyShort"), period("ShadowVeryShort"), period("Near")) + 2
    cond = ((b.col(2) == 1) & (b.col(1) == 1) & (b.col(0) == 1)
            & (b.c(0) > b.c(1)) & (b.c(1) > b.c(2))
            & (b.body(2) > b.avg("BodyLong", 2, lb))
            & (b.body(1) > b.avg("BodyLong", 1, lb))
            & (b.up(1) < b.avg("ShadowVeryShort", 1, lb))
            & (b.o(1) > b.o(2)) & (b.o(1) <= b.c(2) + b.avg("Near", 2, lb))
            & (b.body(0) < b.avg("BodyShort", 0, lb))
            & (b.o(0) >= b.c(1) - b.body(0) - b.avg("Near", 1, lb)))
    return b.out(cond, -100, lb)


def cdlsticksandwich(b):
    lb = period("Equal") + 2
    eq = b.avg("Equal", 2, lb)
    cond = ((b.col(2) == -1) & (b.col(1) == 1) & (b.col(0) == -1)
            & (b.l(1) > b.c(2))
            & (b.c(0) <= b.c(2) + eq) & (b.c(0) >= b.c(2) - eq))
    return b.out(cond, 100, lb)


def cdltakuri(b):
    lb = max(period("BodyDoji"), period("ShadowVeryShort"), period("ShadowVeryLong"))
    cond = ((b.body(0) <= b.avg("BodyDoji", 0, lb))
            & (b.up(0) < b.avg("ShadowVeryShort", 0, lb))
            & (b.lo(0) > b.avg("ShadowVeryLong", 0, lb)))
    return b.out(cond, 100, lb)


def cdltasukigap(b):
    lb = period("Near") + 2
    near = b.avg("Near", 1, lb)
    same_size = np.abs(b.body(1) - b.body(0)) < near
    cond = ((b.rb_gap_up(1, 2) & (b.col(1) == 1) & (b.col(0) == -1)
             & (b.o(0) < b.c(1)) & (b.o(0) > b.o(1)) & (b.c(0) < b.o(1))
             & (b.c(0) > b.top(2)) & same_size)
            | (b.rb_gap_down(1, 2) & (b.col(1) == -1) & (b.col(0) == 1)
               & (b.o(0) < b.o(1)) & (b.o(0) > b.c(1)) & (b.c(0) > b.o(1))
               & (b.c(0) < b.bot(2)) & same_size))
    return b.out(cond, b.col(1) * 100, lb)


def cdlthrusting(b):
    lb = max(period("Equal"), period("BodyLong")) + 1
    cond = ((b.col(1) == -1) & (b.body(1) > b.avg("BodyLong", 1, lb))
            & (b.col(0) == 1) & (b.o(0) < b.l(1))
            & (b.c(0) > b.c(1) + b.avg("Equal", 1, lb))
            & (b.c(0) <= fma(b.body(1), 0.5, b.c(1))))
    return b.out(cond, -100, lb)


def cdltristar(b):
    lb = period("BodyDoji") + 2
    doji = b.avg("BodyDoji", 2, lb)                 # the same (1st-candle) threshold for all three
    three = (b.body(2) <= doji) & (b.body(1) <= doji) & (b.body(0) <= doji)
    bear = b.rb_gap_up(1, 2) & (b.top(0) < b.top(1))
    bull = b.rb_gap_down(1, 2) & (b.bot(0) > b.bot(1))
    value = np.where(bull, 100, np.where(bear, -100, 0))   # bull test runs last in C and wins
    return b.out(three, value, lb)


def cdlunique3river(b):
    lb = max(period("BodyShort"), period("BodyLong")) + 2
    cond = ((b.col(2) == -1) & (b.col(1) == -1) & (b.col(0) == 1)
            & (b.c(1) > b.c(2)) & (b.o(1) <= b.o(2)) & (b.l(1) < b.l(2))
            & (b.o(0) > b.l(1))
            & (b.body(2) > b.avg("BodyLong", 2, lb))
            & (b.body(0) < b.avg("BodyShort", 0, lb)))
    return b.out(cond, 100, lb)


def cdlupsidegap2crows(b):
    lb = max(period("BodyShort"), period("BodyLong")) + 2
    cond = ((b.col(2) == 1) & (b.body(2) > b.avg("BodyLong", 2, lb))
            & (b.col(1) == -1) & (b.body(1) <= b.avg("BodyShort", 1, lb))
            & b.rb_gap_up(1, 2)
            & (b.col(0) == -1) & (b.o(0) > b.o(1)) & (b.c(0) < b.c(1)) & (b.c(0) > b.c(2)))
    return b.out(cond, -100, lb)


def cdlxsidegap3methods(b):
    lb = 2
    cond = ((b.col(2) == b.col(1)) & (b.col(1) == -b.col(0))
            & (b.o(0) < b.top(1)) & (b.o(0) > b.bot(1))
            & (b.c(0) < b.top(2)) & (b.c(0) > b.bot(2))
            & (((b.col(2) == 1) & b.rb_gap_up(1, 2)) | ((b.col(2) == -1) & b.rb_gap_down(1, 2))))
    return b.out(cond, b.col(2) * 100, lb)


PATTERNS = {
    "CDL2CROWS": cdl2crows, "CDL3BLACKCROWS": cdl3blackcrows, "CDL3INSIDE": cdl3inside,
    "CDL3LINESTRIKE": cdl3linestrike, "CDL3OUTSIDE": cdl3outside,
    "CDL3STARSINSOUTH": cdl3starsinsouth, "CDL3WHITESOLDIERS": cdl3whitesoldiers,
    "CDLABANDONEDBABY": cdlabandonedbaby, "CDLADVANCEBLOCK": cdladvanceblock,
    "CDLBELTHOLD": cdlbelthold, "CDLBREAKAWAY": cdlbreakaway,
    "CDLCLOSINGMARUBOZU": cdlclosingmarubozu, "CDLCONCEALBABYSWALL": cdlconcealbabyswall,
    "CDLCOUNTERATTACK": cdlcounterattack, "CDLDARKCLOUDCOVER": cdldarkcloudcover,
    "CDLDOJI": cdldoji, "CDLDOJISTAR": cdldojistar, "CDLDRAGONFLYDOJI": cdldragonflydoji,
    "CDLENGULFING": cdlengulfing, "CDLEVENINGDOJISTAR": cdleveningdojistar,
    "CDLEVENINGSTAR": cdleveningstar, "CDLGAPSIDESIDEWHITE": cdlgapsidesidewhite,
    "CDLGRAVESTONEDOJI": cdlgravestonedoji, "CDLHAMMER": cdlhammer,
    "CDLHANGINGMAN": cdlhangingman, "CDLHARAMI": cdlharami, "CDLHARAMICROSS": cdlharamicross,
    "CDLHIGHWAVE": cdlhighwave, "CDLHIKKAKE": cdlhikkake, "CDLHIKKAKEMOD": cdlhikkakemod,
    "CDLHOMINGPIGEON": cdlhomingpigeon, "CDLIDENTICAL3CROWS": cdlidentical3crows,
    "CDLINNECK": cdlinneck, "CDLINVERTEDHAMMER": cdlinvertedhammer, "CDLKICKING": cdlkicking,
    "CDLKICKINGBYLENGTH": cdlkickingbylength, "CDLLADDERBOTTOM": cdlladderbottom,
    "CDLLONGLEGGEDDOJI": cdllongleggeddoji, "CDLLONGLINE": cdllongline,
    "CDLMARUBOZU": cdlmarubozu, "CDLMATCHINGLOW": cdlmatchinglow, "CDLMATHOLD": cdlmathold,
    "CDLMORNINGDOJISTAR": cdlmorningdojistar, "CDLMORNINGSTAR": cdlmorningstar,
    "CDLONNECK": cdlonneck, "CDLPIERCING": cdlpiercing, "CDLRICKSHAWMAN": cdlrickshawman,
    "CDLRISEFALL3METHODS": cdlrisefall3methods, "CDLSEPARATINGLINES": cdlseparatinglines,
    "CDLSHOOTINGSTAR": cdlshootingstar, "CDLSHORTLINE": cdlshortline,
    "CDLSPINNINGTOP": cdlspinningtop, "CDLSTALLEDPATTERN": cdlstalledpattern,
    "CDLSTICKSANDWICH": cdlsticksandwich, "CDLTAKURI": cdltakuri, "CDLTASUKIGAP": cdltasukigap,
    "CDLTHRUSTING": cdlthrusting, "CDLTRISTAR": cdltristar, "CDLUNIQUE3RIVER": cdlunique3river,
    "CDLUPSIDEGAP2CROWS": cdlupsidegap2crows, "CDLXSIDEGAP3METHODS": cdlxsidegap3methods,
}


def patterns(o, h, l, c, names=None):
    """All (or `names`) TA-Lib candle patterns on one OHLC series.

    Returns {name: int32 array}: 0 = no pattern, +100 bullish / -100 bearish (sign = the
    pattern's direction as TA-Lib reports it), +-80 for the "loose" engulfing / harami,
    +-200 for a confirmed hikkake.  Leading lookback bars are 0.
    """
    b = _Bars(o, h, l, c)
    return {name: PATTERNS[name](b) for name in (names or PATTERNS)}


# --------------------------------------------------------------------------------------
# What each pattern means.  kind: reversal / continuation / indecision.  Sign convention is
# TA-Lib's: +100 bullish, -100 bearish (patterns with one direction only ever emit one sign).
# Sources: TA-Lib function docs (https://ta-lib.org/functions/ and the C source comments),
# Bulkowski's candlestick pages (https://thepatternsite.com/CandleEntry.html), Nison "Japanese
# Candlestick Charting Techniques" (2nd ed.) and Morris "Candlestick Charting Explained".
# --------------------------------------------------------------------------------------
_TALIB = "https://ta-lib.org/functions/"
_BULK = "https://thepatternsite.com/"
INFO = {
    "CDL2CROWS": {"label": "Two Crows", "candles": 3, "kind": "reversal", "direction": "bearish",
                  "notes": "Long white, then a black candle gapping up, then a black that opens inside the 2nd body and closes inside the 1st. Top reversal.", "source": _BULK + "TwoCrows.html"},
    "CDL3BLACKCROWS": {"label": "Three Black Crows", "candles": 3, "kind": "reversal", "direction": "bearish",
                       "notes": "Three declining black candles, each opening inside the prior body, with no/very short lower shadows, after a white candle. Top reversal.", "source": _BULK + "ThreeBlackCrows.html"},
    "CDL3INSIDE": {"label": "Three Inside Up / Down", "candles": 3, "kind": "reversal", "direction": "both",
                   "notes": "Harami (long body + short body inside it) confirmed by a 3rd candle closing beyond the 1st candle's open. +100 three inside up (bullish), -100 three inside down.", "source": _BULK + "ThreeInsideUp.html"},
    "CDL3LINESTRIKE": {"label": "Three-Line Strike", "candles": 4, "kind": "continuation", "direction": "both",
                       "notes": "Three soldiers/crows then a 4th opposite candle that erases them. Classic reading (Nison/Morris): continuation in the direction of the first three (TA-Lib sign = colour of the three); Bulkowski's statistics find it mostly reverses instead.", "source": _BULK + "ThreeLineStrikeBull.html"},
    "CDL3OUTSIDE": {"label": "Three Outside Up / Down", "candles": 3, "kind": "reversal", "direction": "both",
                    "notes": "Engulfing pattern confirmed by a 3rd candle closing further in the engulfing direction. +100 up (bullish), -100 down.", "source": _BULK + "ThreeOutsideUp.html"},
    "CDL3STARSINSOUTH": {"label": "Three Stars in the South", "candles": 3, "kind": "reversal", "direction": "bullish",
                         "notes": "Long black with long lower shadow, a smaller black inside its range, then a small black marubozu inside the 2nd. Rare bottom reversal.", "source": _BULK + "ThreeStarsSouth.html"},
    "CDL3WHITESOLDIERS": {"label": "Three Advancing White Soldiers", "candles": 3, "kind": "reversal", "direction": "bullish",
                          "notes": "Three white candles with higher closes, each opening inside/near the prior body, very short upper shadows, not far shorter than the previous. Bottom reversal / strong advance.", "source": _BULK + "ThreeWhiteSoldiers.html"},
    "CDLABANDONEDBABY": {"label": "Abandoned Baby", "candles": 3, "kind": "reversal", "direction": "both",
                         "notes": "Long body, a doji that gaps away (shadows do not touch), then an opposite body gapping back and closing well (penetration 0.3) inside the 1st body. +100 bullish, -100 bearish.", "source": _BULK + "AbandonBabyBull.html"},
    "CDLADVANCEBLOCK": {"label": "Advance Block", "candles": 3, "kind": "reversal", "direction": "bearish",
                        "notes": "Three rising white candles showing weakening: shrinking bodies and/or long upper shadows. Warning of a top.", "source": _BULK + "AdvanceBlock.html"},
    "CDLBELTHOLD": {"label": "Belt-hold", "candles": 1, "kind": "reversal", "direction": "both",
                    "notes": "Long white opening at its low (bullish, +100) or long black opening at its high (bearish, -100).", "source": _BULK + "BeltHoldBull.html"},
    "CDLBREAKAWAY": {"label": "Breakaway", "candles": 5, "kind": "reversal", "direction": "both",
                     "notes": "Long candle, a gap in the trend direction, two more candles drifting the same way, then an opposite candle closing inside the gap. +100 bullish, -100 bearish.", "source": _BULK + "BullBreakaway.html"},
    "CDLCLOSINGMARUBOZU": {"label": "Closing Marubozu", "candles": 1, "kind": "continuation", "direction": "both",
                           "notes": "Long body closing at its extreme (no shadow on the close side). Trend-strength candle; sign = colour.", "source": _BULK + "CloseBlkMarubozu.html"},
    "CDLCONCEALBABYSWALL": {"label": "Concealing Baby Swallow", "candles": 4, "kind": "reversal", "direction": "bullish",
                            "notes": "Two black marubozu, a black that gaps down but whose upper shadow pokes into the prior body, then a black engulfing it. Rare bottom reversal.", "source": _BULK + "ConcealBaby.html"},
    "CDLCOUNTERATTACK": {"label": "Counterattack (Meeting Lines)", "candles": 2, "kind": "reversal", "direction": "both",
                         "notes": "Two long opposite candles closing at the same level. +100 bullish, -100 bearish.", "source": _BULK + "MeetingLinesBull.html"},
    "CDLDARKCLOUDCOVER": {"label": "Dark Cloud Cover", "candles": 2, "kind": "reversal", "direction": "bearish",
                          "notes": "Long white, then a black that opens above the prior high and closes below the midpoint (penetration 0.5) of the white body. Top reversal.", "source": _BULK + "DarkCloudCover.html"},
    "CDLDOJI": {"label": "Doji", "candles": 1, "kind": "indecision", "direction": "neutral",
                "notes": "Open about equal to close (body < 10% of the average range). Indecision; a reversal warning only in a trend.", "source": _BULK + "NorthernDoji.html"},
    "CDLDOJISTAR": {"label": "Doji Star", "candles": 2, "kind": "reversal", "direction": "both",
                    "notes": "Long body followed by a doji gapping away from it. Reversal warning needing confirmation (TA-Lib sign is opposite to the 1st candle).", "source": _BULK + "DojiStarBull.html"},
    "CDLDRAGONFLYDOJI": {"label": "Dragonfly Doji", "candles": 1, "kind": "reversal", "direction": "bullish",
                         "notes": "Doji with a long lower shadow and no upper shadow (open/close at the high). Bullish reversal at a bottom.", "source": _BULK + "Dragonfly.html"},
    "CDLENGULFING": {"label": "Engulfing", "candles": 2, "kind": "reversal", "direction": "both",
                     "notes": "Opposite-colour body that engulfs the prior body. +100 bullish, -100 bearish; +-80 when one end of the bodies is exactly equal.", "source": _BULK + "BullEngulfing.html"},
    "CDLEVENINGDOJISTAR": {"label": "Evening Doji Star", "candles": 3, "kind": "reversal", "direction": "bearish",
                           "notes": "Long white, a doji gapping up, then a black closing well (0.3) into the white body. Top reversal.", "source": _BULK + "EveningDojiStar.html"},
    "CDLEVENINGSTAR": {"label": "Evening Star", "candles": 3, "kind": "reversal", "direction": "bearish",
                       "notes": "Long white, a short body gapping up, then a black closing well (0.3) into the white body. Top reversal.", "source": _BULK + "EveningStar.html"},
    "CDLGAPSIDESIDEWHITE": {"label": "Up/Down-gap Side-by-side White Lines", "candles": 3, "kind": "continuation", "direction": "both",
                            "notes": "A gap, then two white candles of similar size and open that do not close the gap. +100 upside gap (bullish continuation), -100 downside gap (bearish continuation).", "source": _BULK + "SidebySideWhiteLinesBull.html"},
    "CDLGRAVESTONEDOJI": {"label": "Gravestone Doji", "candles": 1, "kind": "reversal", "direction": "bearish",
                          "notes": "Doji with a long upper shadow and no lower shadow (open/close at the low). Bearish at a top. TA-Lib emits +100 (pattern present).", "source": _BULK + "Gravestone.html"},
    "CDLHAMMER": {"label": "Hammer", "candles": 1, "kind": "reversal", "direction": "bullish",
                  "notes": "Small body at the top, lower shadow longer than the body, tiny upper shadow, body near the prior candle's low. Bottom reversal.", "source": _BULK + "Hammer.html"},
    "CDLHANGINGMAN": {"label": "Hanging Man", "candles": 1, "kind": "reversal", "direction": "bearish",
                      "notes": "Same shape as a hammer but with the body near the prior candle's high (after a rise). Top reversal warning.", "source": _BULK + "HangingMan.html"},
    "CDLHARAMI": {"label": "Harami", "candles": 2, "kind": "reversal", "direction": "both",
                  "notes": "Long body followed by a short body inside it. Sign opposite to the 1st candle; +-80 when one body end is exactly equal.", "source": _BULK + "HaramiBull.html"},
    "CDLHARAMICROSS": {"label": "Harami Cross", "candles": 2, "kind": "reversal", "direction": "both",
                       "notes": "Harami whose 2nd candle is a doji. Stronger than a plain harami; +-80 on an equal end.", "source": _BULK + "HaramiCrossBull.html"},
    "CDLHIGHWAVE": {"label": "High-Wave Candle", "candles": 1, "kind": "indecision", "direction": "neutral",
                    "notes": "Short body with very long upper and lower shadows. Indecision / loss of trend conviction; sign = colour.", "source": _BULK + "HighWave.html"},
    "CDLHIKKAKE": {"label": "Hikkake", "candles": 3, "kind": "reversal", "direction": "both",
                   "notes": "Inside bar then a bar breaking out of it; the trade is the failure of that breakout. +100 bullish / -100 bearish setup, +-200 when confirmed by a close back through the inside bar within 3 bars.", "source": _BULK + "HikkakeBull.html"},
    "CDLHIKKAKEMOD": {"label": "Modified Hikkake", "candles": 4, "kind": "reversal", "direction": "both",
                      "notes": "Hikkake preceded by a context candle whose close is near its low (bull) / high (bear). Same +-100 / +-200 confirmation logic.", "source": _BULK + "HikkakeBull.html"},
    "CDLHOMINGPIGEON": {"label": "Homing Pigeon", "candles": 2, "kind": "reversal", "direction": "bullish",
                        "notes": "Long black followed by a short black inside its body (a black-black harami). Bottom reversal.", "source": _BULK + "HomingPigeon.html"},
    "CDLIDENTICAL3CROWS": {"label": "Identical Three Crows", "candles": 3, "kind": "reversal", "direction": "bearish",
                           "notes": "Three black candles each opening at the prior close, no lower shadows. Top reversal.", "source": _BULK + "Identical3Crows.html"},
    "CDLINNECK": {"label": "In-Neck", "candles": 2, "kind": "continuation", "direction": "bearish",
                  "notes": "Long black, then a white that opens below the low and closes just into the black body (at/just above its close). Bearish continuation.", "source": _BULK + "InNeck.html"},
    "CDLINVERTEDHAMMER": {"label": "Inverted Hammer", "candles": 1, "kind": "reversal", "direction": "bullish",
                          "notes": "Small body gapping down with a long upper shadow and no lower shadow. Bottom reversal needing confirmation.", "source": _BULK + "HammerInv.html"},
    "CDLKICKING": {"label": "Kicking", "candles": 2, "kind": "reversal", "direction": "both",
                   "notes": "Two opposite marubozu with a gap between them. Sign = colour of the 2nd candle.", "source": _BULK + "KickingBull.html"},
    "CDLKICKINGBYLENGTH": {"label": "Kicking (by length)", "candles": 2, "kind": "reversal", "direction": "both",
                           "notes": "Kicking where the sign follows the longer of the two marubozu.", "source": _BULK + "KickingBull.html"},
    "CDLLADDERBOTTOM": {"label": "Ladder Bottom", "candles": 5, "kind": "reversal", "direction": "bullish",
                        "notes": "Three falling black candles, a black with an upper shadow, then a white gapping above the prior body and closing above its high. Bottom reversal.", "source": _BULK + "LadderBottom.html"},
    "CDLLONGLEGGEDDOJI": {"label": "Long-Legged Doji", "candles": 1, "kind": "indecision", "direction": "neutral",
                          "notes": "Doji with at least one shadow longer than the (tiny) body. Indecision; reversal warning in a trend.", "source": _BULK + "LongLegDoji.html"},
    "CDLLONGLINE": {"label": "Long Line Candle", "candles": 1, "kind": "continuation", "direction": "both",
                    "notes": "Long body with short shadows. Momentum candle in the direction of its colour.", "source": _BULK + "LongWhiteDay.html"},
    "CDLMARUBOZU": {"label": "Marubozu", "candles": 1, "kind": "continuation", "direction": "both",
                    "notes": "Long body with no (very short) shadows at either end. Strong one-sided session; sign = colour.", "source": _BULK + "WhiteMarubozu.html"},
    "CDLMATCHINGLOW": {"label": "Matching Low", "candles": 2, "kind": "reversal", "direction": "bullish",
                       "notes": "Two black candles closing at the same level: support found. Bottom reversal (Bulkowski: acts as continuation more often).", "source": _BULK + "MatchingLow.html"},
    "CDLMATHOLD": {"label": "Mat Hold", "candles": 5, "kind": "continuation", "direction": "bullish",
                   "notes": "Long white, a small black gapping up, two more small falling candles holding above 50% of the white body, then a white closing above the reaction highs. Bullish continuation.", "source": _BULK + "MatHold.html"},
    "CDLMORNINGDOJISTAR": {"label": "Morning Doji Star", "candles": 3, "kind": "reversal", "direction": "bullish",
                           "notes": "Long black, a doji gapping down, then a white closing well (0.3) into the black body. Bottom reversal.", "source": _BULK + "MorningDojiStar.html"},
    "CDLMORNINGSTAR": {"label": "Morning Star", "candles": 3, "kind": "reversal", "direction": "bullish",
                       "notes": "Long black, a short body gapping down, then a white closing well (0.3) into the black body. Bottom reversal.", "source": _BULK + "MorningStar.html"},
    "CDLONNECK": {"label": "On-Neck", "candles": 2, "kind": "continuation", "direction": "bearish",
                  "notes": "Long black, then a white opening below the low and closing at the prior low. Bearish continuation.", "source": _BULK + "OnNeck.html"},
    "CDLPIERCING": {"label": "Piercing Line", "candles": 2, "kind": "reversal", "direction": "bullish",
                    "notes": "Long black, then a long white opening below the low and closing above the midpoint of the black body. Bottom reversal.", "source": _BULK + "Piercing.html"},
    "CDLRICKSHAWMAN": {"label": "Rickshaw Man", "candles": 1, "kind": "indecision", "direction": "neutral",
                       "notes": "Long-legged doji with the body near the middle of the range. Indecision.", "source": _BULK + "RickshawMan.html"},
    "CDLRISEFALL3METHODS": {"label": "Rising / Falling Three Methods", "candles": 5, "kind": "continuation", "direction": "both",
                            "notes": "Long candle, three small opposite candles held inside its range, then a long candle closing beyond the first. +100 rising (bullish continuation), -100 falling.", "source": _BULK + "Rising3Methods.html"},
    "CDLSEPARATINGLINES": {"label": "Separating Lines", "candles": 2, "kind": "continuation", "direction": "both",
                           "notes": "Opposite candle followed by a belt-hold opening at the same open. Continuation in the 2nd candle's direction (sign = its colour).", "source": _BULK + "SeparateLinesBull.html"},
    "CDLSHOOTINGSTAR": {"label": "Shooting Star", "candles": 1, "kind": "reversal", "direction": "bearish",
                        "notes": "Small body gapping up with a long upper shadow and no lower shadow. Top reversal.", "source": _BULK + "ShootingStar.html"},
    "CDLSHORTLINE": {"label": "Short Line Candle", "candles": 1, "kind": "indecision", "direction": "neutral",
                     "notes": "Short body with short shadows: a quiet session. Sign = colour.", "source": _BULK + "ShortWhiteCandle.html"},
    "CDLSPINNINGTOP": {"label": "Spinning Top", "candles": 1, "kind": "indecision", "direction": "neutral",
                       "notes": "Short body with both shadows longer than the body. Indecision; sign = colour.", "source": _BULK + "SpinTopWhite.html"},
    "CDLSTALLEDPATTERN": {"label": "Stalled Pattern (Deliberation)", "candles": 3, "kind": "reversal", "direction": "bearish",
                          "notes": "Two long whites then a small white riding on the shoulder of the 2nd: the advance is stalling. Top reversal warning.", "source": _BULK + "Deliberation.html"},
    "CDLSTICKSANDWICH": {"label": "Stick Sandwich", "candles": 3, "kind": "reversal", "direction": "bullish",
                         "notes": "Black, a white trading above its close, then a black closing at the 1st close. Support / bottom reversal.", "source": _BULK + "StickSandwich.html"},
    "CDLTAKURI": {"label": "Takuri (Dragonfly Doji, very long shadow)", "candles": 1, "kind": "reversal", "direction": "bullish",
                  "notes": "Dragonfly doji whose lower shadow is very long (> 2 x body average rule). Bottom reversal.", "source": _BULK + "TakuriLine.html"},
    "CDLTASUKIGAP": {"label": "Upside / Downside Tasuki Gap", "candles": 3, "kind": "continuation", "direction": "both",
                     "notes": "A gap, a candle in the gap direction, then an opposite candle of similar size that opens in that body and closes into (not across) the gap. +100 upside, -100 downside continuation.", "source": _BULK + "UpsideTasukiGap.html"},
    "CDLTHRUSTING": {"label": "Thrusting", "candles": 2, "kind": "continuation", "direction": "bearish",
                     "notes": "Long black, then a white opening below the low and closing into the body but below its midpoint. Bearish continuation.", "source": _BULK + "Thrusting.html"},
    "CDLTRISTAR": {"label": "Tristar", "candles": 3, "kind": "reversal", "direction": "both",
                   "notes": "Three dojis, the middle one a star (gapping). +100 bottom (gap down), -100 top (gap up).", "source": _BULK + "TriStarBull.html"},
    "CDLUNIQUE3RIVER": {"label": "Unique Three River", "candles": 3, "kind": "reversal", "direction": "bullish",
                        "notes": "Long black, a black harami with a lower low, then a small white opening above that low. Bottom reversal.", "source": _BULK + "Unique3RiverBottom.html"},
    "CDLUPSIDEGAP2CROWS": {"label": "Upside Gap Two Crows", "candles": 3, "kind": "reversal", "direction": "bearish",
                           "notes": "Long white, a short black gapping up, then a black engulfing it but closing above the white close. Top reversal.", "source": _BULK + "UpGapTwoCrows.html"},
    "CDLXSIDEGAP3METHODS": {"label": "Upside / Downside Gap Three Methods", "candles": 3, "kind": "continuation", "direction": "both",
                            "notes": "Two same-colour candles with a gap between their bodies, then an opposite candle that fills the gap. +100 upside (bullish continuation), -100 downside.", "source": _BULK + "UpGap3Methods.html"},
}
for _name, _info in INFO.items():
    _info["talib_doc"] = _TALIB  # function reference index; the C source comments carry the exact rules

assert set(INFO) == set(PATTERNS) and len(PATTERNS) == 61
