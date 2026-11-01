"""engine/test_profit.py — the cost layer (David 2026-10-30: more profit, all valid trades, no caps, 0.01 lot)."""
import datetime as _dt

import pytest

from engine import filters as FL
from engine import profit as PR


def ms(h, m=0):
    return int(_dt.datetime(2026, 10, 30, h, m, tzinfo=_dt.timezone.utc).timestamp() * 1000)


COSTS = {"EURUSD": {"median_spread": 0.00002, "spread_atr": 0.038, "tradeable": True},
         "TRUMP": {"median_spread": 0.01, "spread_atr": 284.1, "tradeable": False}}


def test_a_symbol_whose_spread_eats_an_atr_is_refused():
    ok, why, _ = PR.cost_gate("TRUMP", "crypto", 0.01, 0.00004, 1.0, ms(12), costs=COSTS)
    assert not ok and "costs" in why and "ATR" in why


def test_a_cheap_major_passes_in_the_middle_of_the_day():
    ok, why, val = PR.cost_gate("EURUSD", "forex", 0.00002, 0.0005, 0.001, ms(12), costs=COSTS)
    assert ok and why == "" and val["target_spread_x"] == 50.0


def test_the_rollover_blowout_is_refused_even_on_a_cheap_symbol():
    # 21:00 UTC: the hour where the recorded spread runs 5-27x its median on the crosses
    ok, why, _ = PR.cost_gate("EURUSD", "forex", 0.00002, 0.0005, 0.001, ms(21), costs=COSTS)
    assert not ok and "rollover" in why


def test_a_spread_far_over_its_own_median_is_refused():
    ok, why, _ = PR.cost_gate("EURUSD", "forex", 0.0002, 0.0005, 0.01, ms(12), costs=COSTS)
    assert not ok and "usual" in why


def test_a_target_too_near_to_pay_for_the_spread_is_refused():
    # target 5 spreads away: the toll is 20 % of everything the trade can win
    ok, why, _ = PR.cost_gate("EURUSD", "forex", 0.00002, 0.0005, 0.0001, ms(12), costs=COSTS)
    assert not ok and "spreads away" in why


def test_an_unknown_symbol_is_not_refused_for_lack_of_history():
    ok, why, _ = PR.cost_gate("NEWPAIR", "forex", 0.00002, 0.0005, 0.001, ms(12), costs=COSTS)
    assert ok and why == ""


def test_the_gate_never_looks_at_direction():
    a = PR.cost_gate("EURUSD", "forex", 0.00002, 0.0005, 0.001, ms(12), costs=COSTS)
    b = PR.cost_gate("EURUSD", "forex", 0.00002, 0.0005, -0.001, ms(12), costs=COSTS)
    assert a[0] == b[0]


def test_minutes_to_swap_wraps_past_midnight():
    assert PR.minutes_to_swap(ms(20, 0)) == 45
    assert PR.minutes_to_swap(ms(23, 0)) == 21 * 60 + 45


def test_g9_is_a_real_gate_in_the_layer():
    assert FL.GATES["G9"] == "cost"


def test_zero_max_positions_means_unlimited(monkeypatch):
    """David 2026-10-30: 'no limit for trade and position'."""
    from engine.config import FILTER_PROFILES
    assert FILTER_PROFILES["profit"]["MAX_POSITIONS"] == 0
    assert FILTER_PROFILES["profit"]["NO_REENTRY_AFTER_LOSS"] is False
    assert FILTER_PROFILES["profit"]["ONE_TRADE_PER_H4_ZONE"] is False


def test_the_cost_table_rules_out_every_crypto():
    t = PR.load_costs()
    if not t:
        pytest.skip("symbol_cost.json not built here")
    crypto = [s for s, v in t.items() if v.get("market") == "crypto"]
    assert crypto and not [s for s in crypto if t[s]["tradeable"]]
    assert t["EURUSD"]["tradeable"] and t["GOLD"]["tradeable"]
