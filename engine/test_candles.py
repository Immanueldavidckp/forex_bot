"""engine/test_candles.py — the 61 candle patterns give TA-Lib's own output, bar for bar, on 4000 GOLD M15 candles
(the reference file was written by TA-Lib 0.8.2 on 2026-10-29; TA-Lib itself is not needed here)."""
import gzip
import json
import os

import numpy as np

from engine import candles

REF = os.path.join(os.path.dirname(__file__), "testdata", "talib_cdl_GOLD_M15.json.gz")


def test_all_61_patterns_match_talib():
    with gzip.open(REF, "rt") as f:
        ref = json.load(f)
    a = np.array(ref["ohlc"], dtype=float)
    out = candles.patterns(a[:, 0], a[:, 1], a[:, 2], a[:, 3])
    assert len(out) == 61 and set(out) == set(ref["talib"]) == set(candles.INFO)
    for name, want in ref["talib"].items():
        got = [[int(i), int(out[name][i])] for i in np.nonzero(out[name])[0]]
        assert got == want, name


def test_every_pattern_is_described():
    for name, info in candles.INFO.items():
        assert info["kind"] in ("reversal", "continuation", "indecision") and info["label"] and info["candles"] >= 1, name
