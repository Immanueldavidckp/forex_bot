"""engine/sdd_book.py: the limit order of a fresh S&D David zone (spread-aware), and when it is not placed."""
from engine.sdd_book import levels

INFO = {"digits": 2, "point": 0.01, "trade_stops_level": 0}


def zone(d, proximal, distal, t1):
    return {"dir": d, "proximal": proximal, "distal": distal, "targets": [{"fib": 0.618, "price": t1}]}


def test_demand_buy_limit_fills_when_the_bid_touches_A_high():
    lv = levels(zone("buy", 4058.51, 4055.24, 4092.26), {"bid": 4129.09, "ask": 4129.24}, INFO)
    assert lv["price"] == 4058.66 and lv["sl"] == 4055.14 and lv["tp"] == 4092.26     # stop 10 points below A's low
    assert lv["rr"] == round((4092.26 - 4058.66) / (4058.66 - 4055.14), 2)


def test_supply_sell_limit_stop_and_target_carry_the_spread():
    lv = levels(zone("sell", 2000.0, 2010.0, 1980.0), {"bid": 1990.0, "ask": 1990.5}, INFO)
    assert lv["price"] == 2000.0 and lv["sl"] == 2010.6 and lv["tp"] == 1980.5        # A high + spread + 10 points


def test_price_already_past_the_entry_places_nothing():
    assert "why" in levels(zone("buy", 4058.51, 4055.24, 4092.26), {"bid": 4058.0, "ask": 4058.15}, INFO)
    assert "why" in levels(zone("sell", 2000.0, 2010.0, 1980.0), {"bid": 2001.0, "ask": 2001.5}, INFO)


def test_spread_too_big_for_the_stop_places_nothing():
    lv = levels(zone("buy", 100.0, 99.99, 101.0), {"bid": 105.0, "ask": 105.05}, INFO)   # stop 0.16 away, spread 31 %
    assert "spread" in lv["why"]


def test_no_target_places_nothing():
    z = zone("buy", 100.0, 99.0, 101.0)
    z["targets"] = []
    assert levels(z, {"bid": 105.0, "ask": 105.01}, INFO) == {"why": "no target"}
