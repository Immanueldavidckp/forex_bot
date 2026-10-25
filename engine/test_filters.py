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

@pytest.fixture(autouse=True)
def strict(monkeypatch):
    """The gates as the spec wrote them, whatever profile config / control.json picks."""
    monkeypatch.setattr(FL, "PROFILE", "strict")


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


def test_the_test_profile_takes_2r_to_the_nearest_structure(monkeypatch):
    b, rec, touch = trend([(21.0, 2), (14.0, 5), (13.0, 2)])          # the move ends at 21.05: RR 2.18 to it
    r = FL.evaluate(rec, ctx_for(b, rec, touch))
    assert r["fails"] == ["G5", "G6"] and r["profile"] == "strict" and r["values"]["rr"] == pytest.approx(2.18)
    monkeypatch.setattr(FL, "PROFILE", "test")
    r = FL.evaluate(rec, ctx_for(b, rec, touch))
    assert r["first_fail"] is None and r["profile"] == "test"
    b, rec, touch = trend([(18.5, 2), (14.0, 5), (13.0, 2)])          # 1.32: still no room
    assert FL.evaluate(rec, ctx_for(b, rec, touch))["fails"] == ["G5", "G6"]


def test_the_test_profile_logs_location_and_freshness_without_requiring_them(monkeypatch):
    b, rec, touch = trend(CLEAN)
    h4 = path(5, [(13, 6), (5, 6), (13, 6), (5, 6), (13, 6), (9, 6)])  # H4 leg 4.95-13.05: the buy starts at 86% of it
    c = ctx_for(b, rec, touch, bars={**ctx_for(b, rec, touch)["bars"], "H4": h4})
    r = FL.evaluate(rec, c)
    assert r["fails"] == ["G5"] and "86% of the H4 leg (needs the discount half)" in r["why"]["G5"]
    monkeypatch.setattr(FL, "PROFILE", "test")
    r2 = FL.evaluate(rec, c)
    assert r2["gates"]["G5"] and r2["values"]["pd_pos"] == r["values"]["pd_pos"]


def test_the_test_profile_moves_a_stop_inside_the_stops_level_out_to_it(monkeypatch):
    b, rec, touch = trend(CLEAN)
    done = b[:touch]
    wide = {**INFO, "trade_stops_level": 400}                         # 4.00 in price: wider than the setup's 2.93 stop
    lv = FL.plan_levels(rec, rec["entry"], 0.01, wide, [("M15", done)], done)
    assert rec["entry"] - lv["stop"] < 4.0
    monkeypatch.setattr(FL, "PROFILE", "test")
    lv = FL.plan_levels(rec, rec["entry"], 0.01, wide, [("M15", done)], done)
    assert 4.0 < rec["entry"] - lv["stop"] < 4.03 and "stops level" in lv["stop_rule"]


def test_profile_switch(monkeypatch):
    monkeypatch.setattr(FL, "PROFILE", None)
    monkeypatch.setattr(FL, "_prof", (-1e9, "strict"))
    monkeypatch.setattr(FL, "load_control", lambda: {"trading": True, "filter_profile": "test"})
    assert FL.profile() == "test" and FL.F["MIN_RR"] == 2.0
    monkeypatch.setattr(FL, "_prof", (-1e9, "strict"))
    monkeypatch.setattr(FL, "load_control", lambda: {"trading": True, "filter_profile": "nonsense"})
    assert FL.profile() == FL.FILTER_PROFILE
    monkeypatch.setattr(FL, "PROFILE", "strict")
    assert FL.F["MIN_RR"] == 3.0 and FL.F["SWING_LEFT"] == 3


def test_pretrade_follows_the_profile_limits(monkeypatch):
    """forex-46 2026-10-25: V.pretrade kept STRATEGY's RR 3 / 3 ATR even when the test profile allows RR 2,
    so a trade passing every gate was still refused. The layer now hands pretrade its profile's limits."""
    b, rec, touch = trend([(21.0, 2), (14.0, 5), (13.0, 2)])          # RR 2.18 to the move's end at 21.05
    done = b[:touch]
    entry = rec["entry"]
    lv = FL.plan_levels(rec, entry, 0.01, INFO, [("M15", done)], done)
    atr = V.sl_atr(done)
    why = V.pretrade(rec, entry, lv["stop"], lv["target"], atr)
    assert why is not None and "is under 3" in why                     # STRATEGY alone still refuses it
    assert V.pretrade(rec, entry, lv["stop"], lv["target"], atr, min_rr=2, sl_max=FL.F["SL_MAX_ATR"]) is None


def mk(seq):
    return [{"o": o, "h": h, "l": l, "c": c, "t": T0 + i * 900_000, "sp": 0.01} for i, (o, h, l, c) in enumerate(seq)]


def test_an_fvg_traded_back_into_within_2_candles_is_invalid():
    """David 2026-10-25 (COSMOS M30): BOS ok, zone ok, FVG ok — but the very next candles traded through the FVG."""
    pad = [(10, 10.5, 9.5, 10)] * 20
    gap = [(10, 10.6, 9.9, 10.5), (10.5, 12.5, 10.4, 12.4), (12.4, 12.6, 11.6, 12.5)]   # gap 10.6 – 11.6
    rec = {"side": "buy", "fvg": {"idx": 21, "top": 11.6, "bottom": 10.6}}
    b = mk(pad + gap + [(12.5, 12.6, 11.0, 11.2)])                     # the 1st candle after dips to 11.0
    assert "1 candle(s) after forming" in V.fvg_untaken(b, rec)
    b = mk(pad + gap + [(12.5, 12.7, 11.7, 12.6), (12.6, 12.7, 11.0, 11.2)])            # the 2nd one does
    assert "2 candle(s) after forming" in V.fvg_untaken(b, rec)


def test_an_fvg_needs_a_run_before_the_retrace():
    pad = [(10, 10.5, 9.5, 10)] * 20                                   # ATR ≈ 1 → need ≈ 0.5 beyond the FVG
    gap = [(10, 10.6, 9.9, 10.5), (10.5, 12.5, 10.4, 12.4), (12.4, 12.6, 12.3, 12.5)]   # gap 10.6 – 12.3
    rec = {"side": "buy", "fvg": {"idx": 21, "top": 12.3, "bottom": 10.6}}
    clear = [(12.5, 12.65, 12.35, 12.6), (12.6, 12.7, 12.4, 12.65)]    # 2 protect candles stay out; run 0.4 so far
    b = mk(pad + gap + clear + [(12.65, 12.7, 11.9, 12.0)])            # retrace after only 0.4 = 0.4 ATR
    assert "running only" in V.fvg_untaken(b, rec)
    assert "running only" in V.fvg_untaken(mk(pad + gap + clear), rec, touching=True)    # the live touch, same judgement
    far = [(12.65, 13.4, 12.5, 13.3)]                                  # runs 1.1 beyond the FVG first
    b = mk(pad + gap + clear + far + [(13.3, 13.4, 11.9, 12.0)])
    assert V.fvg_untaken(b, rec) is None
    assert V.fvg_untaken(mk(pad + gap + clear + far), rec, touching=True) is None
    assert V.fvg_untaken(mk(pad + gap + clear), rec) is None           # no retrace yet: still valid, still waiting
    assert "1 candle(s) after the FVG" in V.fvg_untaken(mk(pad + gap), rec, touching=True)   # touched inside the protect window
