"""engine/test_status.py — the strategy status panel (David 2026-10-30, on /smc)."""
import json
import os

from engine import status as ST


def view(tmp, sym, setups, bars=None):
    d = {"symbol": sym, "setups": setups, "bars": bars or {}}
    with open(os.path.join(tmp, f"{sym}.json"), "w") as f:
        json.dump(d, f)


def setup(tf="M15", st="waiting pullback", entry=1.1, prev=None, side="sell"):
    r = {"id": f"X-{tf}-{st}", "tf": tf, "status": st, "side": side, "entry": entry}
    if prev:
        r["preview"] = prev
    return r


PREV = {"entry": 1.1, "stop": 1.11, "target": {"price": 1.08, "label": "M15 LL", "rr": 2.0},
        "atr": 0.001, "sl_atr_x": 2.0}


def test_only_live_setups_are_approaching(tmp_path, monkeypatch):
    monkeypatch.setattr(ST, "VIEW_DIR", str(tmp_path))
    view(tmp_path, "EURUSD", [setup(st="waiting pullback", prev=PREV),
                              setup(tf="M30", st="invalid"), setup(tf="H1", st="missed")])
    ov = {"symbols": [{"symbol": "EURUSD", "price": 1.105}]}
    a = ST.approaching({}, ov)
    assert len(a) == 1 and a[0]["status"] == "waiting pullback"


def test_distance_to_entry_is_measured_in_atr(tmp_path, monkeypatch):
    monkeypatch.setattr(ST, "VIEW_DIR", str(tmp_path))
    view(tmp_path, "EURUSD", [setup(prev=PREV)])
    a = ST.approaching({}, {"symbols": [{"symbol": "EURUSD", "price": 1.105}]})[0]
    assert abs(a["distance"] - 0.005) < 1e-9 and a["distance_atr"] == 5.0
    assert a["rr"] == 2.0 and a["stop"] == 1.11 and a["target"] == 1.08


def test_a_symbol_the_cost_gate_refuses_is_flagged_not_hidden(tmp_path, monkeypatch):
    monkeypatch.setattr(ST, "VIEW_DIR", str(tmp_path))
    view(tmp_path, "TRUMP", [setup(prev=PREV)])
    monkeypatch.setattr("engine.profit.load_costs",
                        lambda: {"TRUMP": {"tradeable": False, "spread_atr": 284.1}})
    a = ST.approaching({}, {"symbols": [{"symbol": "TRUMP", "price": 1.105}]})
    assert len(a) == 1 and a[0]["tradeable"] is False and "ATR" in a[0]["cost_why"]


def test_tradeable_setups_sort_above_the_dear_ones(tmp_path, monkeypatch):
    monkeypatch.setattr(ST, "VIEW_DIR", str(tmp_path))
    view(tmp_path, "TRUMP", [setup(prev=PREV)])                 # right at its entry
    view(tmp_path, "EURUSD", [setup(prev={**PREV, "entry": 1.2})])   # far away
    monkeypatch.setattr("engine.profit.load_costs",
                        lambda: {"TRUMP": {"tradeable": False, "spread_atr": 284.1},
                                 "EURUSD": {"tradeable": True, "spread_atr": 0.038}})
    a = ST.approaching({}, {"symbols": [{"symbol": "TRUMP", "price": 1.1},
                                        {"symbol": "EURUSD", "price": 1.105}]})
    assert a[0]["symbol"] == "EURUSD"          # what we can trade comes first, however near the other is


def test_atr_falls_back_to_the_view_bars_when_there_is_no_preview(tmp_path, monkeypatch):
    monkeypatch.setattr(ST, "VIEW_DIR", str(tmp_path))
    bars = {"H4": [[i, 1.0, 1.01, 0.99, 1.0, 0, 0] for i in range(40)]}
    view(tmp_path, "EURUSD", [setup(tf="H4", entry=1.05)], bars=bars)
    a = ST.approaching({}, {"symbols": [{"symbol": "EURUSD", "price": 1.0}]})[0]
    assert a["distance_atr"] is not None and a["distance_atr"] > 0


def test_in_trade_reports_pnl_sl_tp_and_r(tmp_path):
    ov = {"positions": [{"ticket": 1, "symbol": "GOLD", "type": 0, "volume": 0.01,
                         "price_open": 4000.0, "price_current": 4004.0, "sl": 3990.0,
                         "tp": 4020.0, "profit": 4.0, "comment": "V5"}], "trades": []}
    t = ST.in_trade({}, ov)[0]
    assert t["pnl"] == 4.0 and t["sl"] == 3990.0 and t["tp"] == 4020.0
    assert t["r_now"] == 0.4 and t["to_sl"] == 14.0 and t["to_tp"] == 16.0


def test_a_sell_measures_r_the_other_way(tmp_path):
    ov = {"positions": [{"ticket": 2, "symbol": "GOLD", "type": 1, "volume": 0.01,
                         "price_open": 4000.0, "price_current": 3996.0, "sl": 4010.0,
                         "tp": 3980.0, "profit": 4.0}], "trades": []}
    assert ST.in_trade({}, ov)[0]["r_now"] == 0.4


def test_levels_carry_entry_sl_and_tp_for_the_chart(tmp_path, monkeypatch):
    monkeypatch.setattr(ST, "VIEW_DIR", str(tmp_path))
    view(tmp_path, "EURUSD", [setup(prev=PREV)])
    ov = {"symbols": [{"symbol": "EURUSD", "price": 1.105}], "positions": [], "trades": []}
    L = ST.levels("EURUSD", {}, ov)
    assert {x["kind"] for x in L} == {"entry", "sl", "tp"} and all(x["live"] for x in L)


def test_levels_of_another_symbol_are_not_drawn(tmp_path, monkeypatch):
    monkeypatch.setattr(ST, "VIEW_DIR", str(tmp_path))
    view(tmp_path, "EURUSD", [setup(prev=PREV)])
    ov = {"symbols": [{"symbol": "EURUSD", "price": 1.105}], "positions": [], "trades": []}
    assert ST.levels("GOLD", {}, ov) == []


def test_build_never_throws_on_empty_data(tmp_path, monkeypatch):
    monkeypatch.setattr(ST, "VIEW_DIR", str(tmp_path))
    monkeypatch.setattr(ST, "STATE_FILE", str(tmp_path / "none.json"))
    monkeypatch.setattr(ST, "OVERVIEW_FILE", str(tmp_path / "none.json"))
    monkeypatch.setattr(ST, "PNL_FILE", str(tmp_path / "none.json"))
    d = ST.build("GOLD")
    assert d["counts"] == {"approaching": 0, "ready": 0, "in_trade": 0} and d["open_pnl"] == 0
