"""
Offline tests of the structure filter layer (engine/filters.py) and its place in Book.signal — synthetic charts,
fake MT5, no orders:

    cd ~/forex && python3 -m pytest -q engine/test_filters.py
"""
from __future__ import annotations

import datetime as dt

import pytest

from engine import book as B
from engine import filters as FL
from engine import strategy as V
from engine.test_book import env  # noqa: F401  (the fake MT5 / feed fixture)

T0 = 1_792_800_000_000 - 1_792_800_000_000 % 900_000
INFO = {"point": 0.01, "trade_tick_size": 0.01, "trade_stops_level": 10, "digits": 2}


def path(start, legs, wick=0.05, sp=0.01):
    """M15 bars walking in straight lines: legs = [(to price, bars), ...]."""
    out, px = [], start
    for p1, n in legs:
        for k in range(1, n + 1):
            o, c = out[-1]["c"] if out else px, px + (p1 - px) * k / n
            out.append({"o": o, "c": c, "h": max(o, c) + wick, "l": min(o, c) - wick, "sp": sp})
        px = p1
    for i, b in enumerate(out):
        b["t"] = T0 + i * 900_000
    return out


BASE = [(11, 8), (10, 8)] * 8 + [(12, 8), (11, 8), (13, 8), (11.5, 8), (13.5, 8), (12.0, 8)]
FAST = [(11, 3), (10, 3)] * 8 + [(12, 3), (11, 3), (13, 3), (11.5, 3), (13.5, 3), (12.0, 3)]   # bigger bars: ATR ≈ 0.45


def trend(after):
    """An uptrend of clean swings, then a one-bar displacement through the 13.5 high and `after`: (bars, its setup,
    the bar that comes back to the entry)."""
    b = path(9, BASE + [(15.0, 1), (18.0, 1)] + after)
    s = [x for x in V.bos_setups(b, V.structure(b), "M15", "TST", max_age=10 ** 6) if x["complete"]][-1]
    touch = next(i for i in range(s["formed_idx"] + 1, len(b)) if b[i]["l"] <= s["entry"])
    return b, {**s, "symbol": "TST", "status": "waiting pullback", "touch_t": b[touch]["t"]}, touch


def ctx_for(b, rec, touch, **kw):
    done = b[:touch]
    entry = rec["entry"]
    lv = FL.plan_levels(rec, entry, 0.01, INFO, [("M15", done), ("H1", done), ("H4", done)], done)
    c = {"now": b[touch]["t"] + 60_000, "entry": entry, "bid": entry - 0.01, "ask": entry, "info": INFO, "market": "crypto",
         "bars": {"M15": done, "M30": done, "H1": done, "H4": done}, "bias": {"h4": {"bias": "buy"}, "h1": {"bias": "buy"}},
         "plan": lv, "zones": [], "lots": 0.01, "money_per_move": 1.0, "equity": 10_000}
    c.update(kw)
    return c


CLEAN = [(25.0, 4), (14.0, 6), (13.0, 3)]          # runs on to 25, back into the FVG within 9 M15 candles


def test_a_clean_trend_break_passes_every_gate():
    b, rec, touch = trend(CLEAN)
    r = FL.evaluate(rec, ctx_for(b, rec, touch))
    assert r["first_fail"] is None and all(r["gates"].values()) and r["break"] == "BOS"
    v = r["values"]
    assert v["regime"] == "UP" and v["swing_level"] == 13.55 and v["rr"] >= 3 and v["tp"] == 25.05
    assert r["risk_pct"] == pytest.approx(100 * v["stop_dist"] * 0.01 / 10_000, abs=1e-6)   # stop distance × money per move × 0.01 / equity


def test_small_pivots_are_not_structure():
    b = path(9, FAST + [(12.1, 3), (12.0, 3), (13.0, 3)])          # a 0.1 wiggle after the 12.0 low: under 1 ATR
    sig = FL.significant_swings(b)
    assert not any(abs(s["price"] - 12.15) < 1e-9 for s in sig)
    assert [s["label"] for s in sig[-2:]] == ["HH", "HL"] and sig[-1]["price"] == pytest.approx(11.95)


def test_a_break_of_a_minor_pivot_is_drift_not_structure():
    b = path(9, FAST + [(12.1, 3), (12.0, 3), (13.2, 1), (13.4, 3), (12.9, 3)])   # closes above the 12.15 wiggle, under 13.55
    st = V.structure(b)
    e = next(x for x in reversed(st["events"]) if x["side"] == "buy")
    rec = {**V.setup_for(b, st, e, "M15", "TST"), "symbol": "TST", "touch_t": b[-1]["t"]}
    if not rec.get("complete"):
        rec.update(fvg=None, poi={"top": 12.2, "bottom": 12.1, "t": b[-10]["t"]}, entry=13.0, formed_t=b[-5]["t"])
    r = FL.evaluate(rec, {**ctx_for(b, {**rec, "entry": 13.0, "invalidation": 12.1, "parent": None}, len(b) - 1), "entry": 13.0})
    assert not r["gates"]["G1"] and r["break"] == "drift" and "minor pivot" in r["why"]["G1"]


def test_no_room_to_the_nearest_structure():
    b, rec, touch = trend([(18.5, 2), (14.0, 5), (13.0, 2)])        # the move ends at 18.55: RR 1.3 to it
    r = FL.evaluate(rec, ctx_for(b, rec, touch))
    assert r["first_fail"] == "G5" and "mostly done" in r["why"]["G5"] and not r["gates"]["G6"] and r["values"]["rr"] == pytest.approx(1.32)


def test_late_pullback_expires():
    b, rec, touch = trend([(25.0, 4), (26.0, 6), (14.0, 6), (13.0, 3)])   # back in the FVG after 18 M15 candles
    r = FL.evaluate(rec, ctx_for(b, rec, touch))
    assert not r["gates"]["G7"] and "expired" in r["why"]["G7"] and r["values"]["waited_m15"] > 12


def test_counter_bias_and_m30_against():
    b, rec, touch = trend(CLEAN)
    r = FL.evaluate(rec, ctx_for(b, rec, touch, bias={"h4": {"bias": "buy"}, "h1": {"bias": "sell"}}))
    assert r["first_fail"] == "G4" and "CHoCH candidate" in r["why"]["G4"]
    down = path(30, [(25, 8), (27, 8), (22, 8), (24, 8), (19, 8)])
    r = FL.evaluate(rec, ctx_for(b, rec, touch, bars={**ctx_for(b, rec, touch)["bars"], "M30": down}))
    assert r["first_fail"] == "G4" and "M30 is sell" in r["why"]["G4"]


def test_one_trade_per_h4_zone_and_no_reentry_after_a_loss():
    b, rec, touch = trend(CLEAN)
    rec["parent"] = "TST-H4-D-1"
    taken = [{"id": "TST-H4M15-D-9", "parent": "TST-H4-D-1", "side": "buy", "top": 1, "bottom": 0.5, "lost": False}]
    r = FL.evaluate(rec, ctx_for(b, rec, touch, zones=taken))
    assert not r["gates"]["G7"] and "one trade per H4 zone" in r["why"]["G7"]
    lost = [{"id": "TST-M15-D-8", "parent": None, "side": "buy", "top": 12.1, "bottom": 11.9, "lost": True}]
    rec["parent"] = None
    r = FL.evaluate(rec, ctx_for(b, rec, touch, zones=lost))
    assert not r["gates"]["G7"] and "no re-entry" in r["why"]["G7"]


def test_regime_range():
    flat = path(10, [(10.4, 3), (10.0, 3)] * 10)                   # 0.5 swings with 0.23 ATR bars
    reg, band = FL.market_regime(FL.significant_swings(flat), V.tools.atr(flat, 14))
    assert reg == "RANGE" and band < 3
    reg, _ = FL.market_regime(FL.significant_swings(path(9, BASE)), 0.3)
    assert reg == "UP"


def test_sessions():
    at = lambda s: int(dt.datetime.fromisoformat(s).timestamp() * 1000)
    assert FL.session_open("EURUSD", "forex", at("2026-10-26T10:00:00+00:00"))[0]           # Monday, London
    assert not FL.session_open("EURUSD", "forex", at("2026-10-26T03:00:00+00:00"))[0]       # Asia only
    assert FL.session_open("USDJPY", "forex", at("2026-10-26T03:00:00+00:00"))[0]           # Tokyo is one of its sessions
    assert FL.session_open("BITCOIN", "crypto", at("2026-10-25T03:00:00+00:00"))[0]         # 24/7


def test_sdh4_stop_is_the_m15_swing_not_the_h4_zone():
    b, rec, touch = trend(CLEAN)
    rec.update(parent="TST-H4-D-1", entry_type="S&D H4")
    done = b[:touch]
    a15 = V.sl_atr(done)
    lv = FL.plan_levels(rec, rec["entry"], 0.02, INFO, [("M15", done)], done)
    o = rec["bos"]["origin"]["price"]
    assert lv["stop"] == FL.round_tick(o - (0.02 + 0.25 * a15), 0.01, up=False) and lv["stop"] < o - 0.02
    assert "M15 swing" in lv["stop_rule"]


def test_stop_checks_reject_the_cosmos_shape():
    """The trade David saw: sell 1.612 with the stop at 1.671 and the target at 1.603 → RR 0.15."""
    ok, why, rr = FL.stop_checks("sell", 1.612, 1.671, {"price": 1.603}, 0.002, 0.015, 0.011)
    assert not ok and rr == pytest.approx(0.153, abs=1e-3) and "ATR(M15)" in why
    ok, why, _ = FL.stop_checks("sell", 1.612, 1.590, {"price": 1.500}, 0.002, 0.015, 0.011)
    assert not ok and "out of order" in why
    assert FL.stop_checks("buy", 10.0, 9.9, {"price": 10.31}, 0.01, 0.05, 0.1)[0]


def test_round_tick():
    assert FL.round_tick(1.61234, 0.001, up=True) == 1.613 and FL.round_tick(1.61234, 0.001, up=False) == 1.612
    assert FL.round_tick(80592.4567, 0.01, up=True) == 80592.46 and FL.round_tick(1.2, 0.001, up=True) == 1.2


def test_signal_with_the_layer_refuses_at_the_first_gate_and_logs(env, monkeypatch):  # noqa: F811
    from engine.test_book import _bos_setup
    bk, fake, feed = env
    monkeypatch.setattr(FL, "FORCE", True)
    got = []
    monkeypatch.setattr(FL, "SINK", got.append)
    rec, b = _bos_setup(bk, feed, fake)
    h1 = [{"t": i * 3_600_000, "o": 12, "h": h, "l": 11, "c": 12} for i, h in enumerate((12, 13, 15, 13, 12))]
    bk.signal(rec, True, h1, b, b)
    assert rec["status"] == "refused" and rec["why"].startswith(rec["gate"]) and not [c for c in fake.calls if c[0] == "order"]
    assert len(got) == 1 and got[0]["id"] == rec["id"] and got[0]["first_fail"] == rec["gate"]
    assert set(got[0]["gates"]) == set(FL.GATES) and got[0]["old_logic"] == "take"          # the engine without the layer would have traded it


def test_position_cap_and_switch(env, monkeypatch):  # noqa: F811
    bk, _, _ = env
    assert bk.max_slots() == 20
    monkeypatch.setattr(FL, "FORCE", True)
    assert bk.max_slots() == 5
    monkeypatch.setattr(FL, "FORCE", None)
    monkeypatch.setattr(FL, "load_control", lambda: {"trading": True, "structure_filters": False})
    assert not FL.enabled()
    monkeypatch.setattr(FL, "load_control", lambda: {"trading": True})
    assert FL.enabled() == FL.STRUCTURE_FILTERS_ENABLED
