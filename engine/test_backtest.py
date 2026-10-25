"""
Offline tests of the backtest's outcome simulation (engine/backtest.py):

    cd ~/forex && python3 -m pytest -q engine/test_backtest.py
"""
from __future__ import annotations

import pytest

from engine import backtest as BT

INFO = {"point": 0.01, "digits": 2, "trade_stops_level": 0}


def m5(prices, sp=0.0, t0=1_000_000_000_000):
    """(open, high, low, close) per 5 min."""
    return [{"t": t0 + i * 300_000, "o": o, "h": h, "l": lo, "c": c, "sp": sp} for i, (o, h, lo, c) in enumerate(prices)]


def test_sell_reaches_the_target():
    bars = m5([(100, 100.2, 99.8, 100), (100, 100.1, 98, 98.5), (98.5, 98.6, 93.5, 94), (94, 95, 93, 95)])
    r = BT.fixed_outcome("sell", 100.0, 102.0, 94.0, bars, 0)
    assert r["exit"] == "tp" and r["r"] == 3.0 and r["bars"] == 2 and r["mfe_r"] == pytest.approx(3.5)


def test_stop_counts_first_when_one_bar_holds_both():
    bars = m5([(100, 100.1, 99.9, 100), (100, 102.5, 93, 95)])
    assert BT.fixed_outcome("sell", 100.0, 102.0, 94.0, bars, 0)["exit"] == "sl"


def test_a_sell_is_stopped_on_the_ask():
    bars = m5([(100, 100.1, 99.9, 100), (100, 101.95, 99.5, 101)], sp=0.1)     # bid 101.95 + 0.1 spread ≥ 102
    assert BT.fixed_outcome("sell", 100.0, 102.0, 94.0, bars, 0)["r"] == -1.0


def test_buy_target_ignored_on_the_touch_bar():
    bars = m5([(100, 106.5, 99.9, 100), (100, 100.5, 99.5, 100)])              # the touch bar's high: order unknown
    assert BT.fixed_outcome("buy", 100.0, 98.0, 106.0, bars, 0)["exit"] == "open"


def test_managed_layer_fill_and_stop_loses_both_legs():
    BT._quiet()
    bars = m5([(100, 100.2, 99.9, 100), (100, 100.9, 99.9, 100.85), (100.85, 102.2, 100.8, 102)])
    r = BT.managed_outcome("TEST", INFO, "sell", "M15", 100.0, 102.0, 94.0, 100.8, bars, 0, None)
    assert r["layer"] == "filled" and r["exit"] == "sl" and r["pct"] == pytest.approx(-4.0)   # −2.5 % normal −1.5 % layer


def test_managed_target_one_moves_the_stop_past_the_entry():
    BT._quiet()
    bars = m5([(100, 100.9, 99.9, 100.85),                                     # layer fills at 100.8 → Mode B, Target 1 = 97
               (100.85, 100.9, 96.9, 97), (97, 97.1, 96.9, 97),               # Target 1 reached → stop 99.8 (−0.1R past the entry)
               (97, 99.9, 96.9, 99.9)])                                       # back up: the new stop takes both out
    r = BT.managed_outcome("TEST", INFO, "sell", "M15", 100.0, 102.0, 94.0, 100.8, bars, 0, None)
    assert r["exit"] == "sl" and r["final_stop"] == pytest.approx(99.8) and r["pct"] > 0
