"""
intraday/tools — technical-analysis tools for any market (stocks, crypto, forex).

Pure Python, no dependencies, no imports from the engine: copy the folder into any
project. Every tool takes bars {"t": epoch ms, "o", "h", "l", "c", "v"}, oldest first;
where sessions matter the caller passes its timezone (and session start).

  bars        resample, sessions, candle anatomy
  indicators  SMA, EMA, Wilder RMA, ATR, Bollinger, Keltner, Donchian, RSI, MACD,
              stochastic, ADX/DMI, supertrend, VWAP (+ bands), OBV
  structure   swing highs/lows, HH/HL/LH/LL, trend, BOS/CHoCH, equal highs/lows
              (liquidity pools), liquidity sweeps, premium/discount + OTE
  smc         fair value gaps (fill state), order blocks (fresh/tested/broken),
              breaker blocks, displacement candles
  levels      prior session/week, opening range, pivots, Fibonacci, S/R zones, nearest level
  candles     doji, hammer, shooting star, engulfing, inside/outside bar, marubozu, stars
  volume      volume profile (POC/VAH/VAL), volume-by-time curve, relative volume
  summary     read(): all of the above at the last bar; brief(): the same in one line
"""
from .bars import Bar, body, close_position, is_down, is_up, lower_wick, resample, session_key, span, split_sessions, to_dt, upper_wick
from .candles import patterns
from .indicators import (adx, atr, atr_series, bollinger, donchian, ema, keltner, macd, obv, rma, rsi, rsi_series, sma, stochastic,
                         supertrend, true_range, vwap, vwap_bands)
from .levels import fib_levels, nearest, opening_range, pivots, prior_session, prior_week, sr_zones
from .smc import displacement, fair_value_gaps, order_blocks
from .structure import dealing_range, equal_levels, label_swings, market_structure, sweeps, swing_points, trend
from .summary import brief, read
from .volume import relative_volume, volume_curve, volume_profile

__all__ = [
    "Bar", "body", "close_position", "is_down", "is_up", "lower_wick", "resample", "session_key", "span", "split_sessions",
    "to_dt", "upper_wick", "patterns", "adx", "atr", "atr_series", "bollinger", "donchian", "ema", "keltner", "macd", "obv",
    "rma", "rsi", "rsi_series", "sma", "stochastic", "supertrend", "true_range", "vwap", "vwap_bands", "fib_levels", "nearest",
    "opening_range", "pivots", "prior_session", "prior_week", "sr_zones", "displacement", "fair_value_gaps", "order_blocks",
    "dealing_range", "equal_levels", "label_swings", "market_structure", "sweeps", "swing_points", "trend", "brief", "read",
    "relative_volume", "volume_curve", "volume_profile",
]
