"""
tests/test_architecture.py — marketdata / concepter (engines + conductor) / rules / executor (ARCHITECTURE.md).
Offline: recorded bars, paper executor, no model. Run: python3 -m pytest tests/test_architecture.py -q
"""
from __future__ import annotations

import copy
import json

import pytest

from concepter import engine as make_engine
from concepter.base import Concepter
from concepter.claude.providers import FakeProvider
from concepter.conductor import Conductor
from concepter.run import run
from executor.guard import Guard, load_limits
from executor.paper import PaperExecutor
from marketdata import data as MD
from shared import rules as R
from shared.contracts import (Bar, Close, Modify, Open, Reading, Signal, View, command_from_dict,
                              command_to_dict)

INFO = {"point": 0.01, "trade_tick_size": 0.01, "trade_tick_value": 1.0, "digits": 2}   # GOLD-like: $1 per $1 at 0.01
M15 = 900_000


def bar(t, o, h, l, c, spread=0.2):
    return Bar(t=t, o=o, h=h, l=l, c=c, spread=spread)


def paper(limits=None, price=100.0):
    ex = PaperExecutor({"X": INFO, "Y": INFO}, balance=10_000, guard=Guard(limits or load_limits()))
    ex.on_bar("X", bar(0, price, price, price, price), M15)
    ex.on_bar("Y", bar(0, price, price, price, price), M15)
    return ex


# ── contracts ───────────────────────────────────────────────────────────────────────────────────────────────────

def test_commands_round_trip_as_json():
    for c in (Open("s", "X", "buy", sl=90, tp=120, reason="r"), Modify("s", 3, sl=95), Close("s", 3, reason="x")):
        assert command_from_dict(json.loads(json.dumps(command_to_dict(c)))) == c


def test_bad_side_and_limit_without_price_are_refused():
    with pytest.raises(ValueError):
        Open("s", "X", "long", sl=1, tp=2)
    with pytest.raises(ValueError):
        Open("s", "X", "buy", sl=1, tp=2, order="limit")
    with pytest.raises(ValueError):
        Signal("kronos", "direction", "X", "M15", 0, "up")


# ── rules ───────────────────────────────────────────────────────────────────────────────────────────────────────

def test_every_engine_has_concept_rules_and_every_strategy_is_runnable():
    assert R.engines() == ["claude", "kronos", "v5"]
    for e in R.engines():
        c = R.concept(e)
        assert c.p("concept.engine") == e and c.concept.strip()
    for n in R.strategies():
        s = R.strategy(n)
        assert s.problems == [], (n, s.problems)
        assert s.p("strategy.name") == n and s.p("strategy.magic")


def test_a_broken_strategy_says_what_is_wrong():
    s = R.strategy("kronos_direction_claude_bos")
    s.spec = copy.deepcopy(s.spec)
    s.spec["stop"]["at"] = "v5.setup.sl"          # v5 is not in its needs
    s.spec["need"][1]["engine"] = "nobody"
    bad = s.check(R.engines())
    assert any("v5.setup" in b for b in bad) and any("nobody" in b for b in bad)


def test_v5_numbers_match_what_the_engine_trades():
    """The running engine reads engine/config.py + engine/profit.py. Until the V5 engine reads rules/, both must say
    the same thing: change one, change the other."""
    from engine.config import FILTER_PROFILES, FILTERS, STRATEGY
    from engine.profit import P
    c, s = R.concept("v5"), R.strategy("v5_supply_demand")
    O = {"c": c, "s": s}
    prof ={**FILTERS, **FILTER_PROFILES[s.p("live_engine.filter_profile")]}
    pairs = {
        ("c", "structure.swing_length"): STRATEGY["swing_length"],
        ("c", "structure.major_swing_length"): STRATEGY["major_swing_length"],
        ("c", "structure.bias_tfs"): STRATEGY["bias_tfs"], ("c", "structure.bias_exempt_tfs"): STRATEGY["bias_exempt_tfs"],
        ("c", "structure.setup_max_age_bars"): STRATEGY["setup_max_age_bars"],
        ("c", "zone.lookback_bars"): STRATEGY["zone_lookback_bars"], ("c", "zone.displacement_mult"): STRATEGY["displacement_mult"],
        ("c", "zone.body_average_bars"): STRATEGY["body_average_bars"],
        ("c", "fvg.pick"): STRATEGY["fvg_pick"], ("c", "fvg.protect_candles"): STRATEGY["fvg_protect_candles"],
        ("c", "fvg.min_runoff_atr"): STRATEGY["fvg_min_runoff_atr"],
        ("c", "setup.fvg_depth"): STRATEGY["fvg_entry_depth"], ("c", "setup.sl_buffer_points"): STRATEGY["sl_buffer_points"],
        ("s", "entry.expires_bars"): prof["SETUP_EXPIRY_M15_BARS"],
        ("s", "entry.no_entry_utc"): list(P["ROLLOVER_UTC"]),
        ("s", "stop.min_spread_x"): prof["SL_MIN_SPREAD_X"], ("s", "stop.max_atr"): prof["SL_MAX_ATR"],
        ("s", "target.min_rr"): prof["MIN_RR"], ("s", "target.min_spread_x"): P["MIN_TARGET_SPREAD_X"],
        ("s", "exit.flat_at_utc"): P["FLAT_BEFORE_SWAP_UTC"],
        ("s", "live_engine.confirm_tf"): STRATEGY["entry_confirm"],
        ("s", "live_engine.confirm_max_bars"): STRATEGY["m5_confirm_max_bars"],
        ("s", "live_engine.sdh4_sl_atr_buffer"): prof["SL_ATR_BUFFER"],
        ("s", "live_engine.sl_widen_to_stops_level"): prof["SL_WIDEN_TO_STOPS_LEVEL"],
        ("s", "live_engine.max_spread_atr"): P["MAX_SPREAD_ATR"],
        ("s", "live_engine.layer_depth_weak"): STRATEGY["layer_depth"]["weak"],
        ("s", "live_engine.layer_depth_moderate"): STRATEGY["layer_depth"]["moderate"],
        ("s", "live_engine.layer_depth_strong"): STRATEGY["layer_depth"]["strong"],
        ("s", "live_engine.near_target_progress"): STRATEGY["near_target_progress"],
        ("s", "live_engine.reversal_giveback"): STRATEGY["reversal_giveback"],
        ("s", "live_engine.tp1_fraction"): STRATEGY["tp1_fraction"],
        ("s", "live_engine.lock_start_r"): STRATEGY["lock_start_r"], ("s", "live_engine.lock_gap_r"): STRATEGY["lock_gap_r"],
    }
    diff = {k: (O[o].p(k), v) for (o, k), v in pairs.items() if O[o].p(k) != v}
    assert not diff, f"rules/ vs engine (rules, engine): {diff}"


def test_kronos_numbers_match_the_engine():
    from engine.config import KRONOS as K
    c, s = R.concept("kronos"), R.strategy("kronos_forecast")
    O = {"c": c, "s": s}
    pairs = {("c", "forecast.tf"): K["TF"], ("c", "forecast.context"): K["CONTEXT"], ("c", "forecast.horizon"): K["HORIZON"],
             ("c", "forecast.paths"): K["PATHS"], ("s", "strategy.magic"): K["MAGIC"],
             ("s", "stop.atr"): K["SL_ATR"], ("s", "target.atr"): K["TP_ATR"], ("s", "stop.max_spread_frac"): K["MAX_SPREAD_SL"],
             ("s", "exit.hold_bars"): K["HOLD_BARS"], ("s", "entry.friday_last_utc"): K["FRIDAY_LAST_ENTRY_UTC"],
             ("s", "live_engine.min_free_margin_pct"): K["MIN_FREE_MARGIN_PCT"],
             ("s", "live_engine.signal_max_age_sec"): K["SIGNAL_MAX_AGE_SEC"]}
    diff = {k: (O[o].p(k), v) for (o, k), v in pairs.items() if O[o].p(k) != v}
    need = s.needs[0]
    assert need["min"] == {"p": K["P_MIN"], "move_spread_x": K["MIN_MOVE_SPREAD_X"]}
    assert not diff, f"rules/ vs engine/config.py KRONOS: {diff}"


# ── executor guard + paper fills ────────────────────────────────────────────────────────────────────────────────

def test_guard_refuses_a_stop_on_the_wrong_side_and_a_target_behind_the_entry():
    ex = paper()
    assert "SL below" in ex.submit(Open("s", "X", "buy", sl=101, tp=110)).why
    assert "SL above" in ex.submit(Open("s", "X", "sell", sl=99, tp=90)).why
    assert "wrong side" in ex.submit(Open("s", "X", "buy", sl=95, tp=99)).why


def test_guard_blocks_the_opposite_side_on_one_symbol_even_for_another_strategy():
    ex = paper()
    assert ex.submit(Open("v5_supply_demand", "X", "buy", sl=95, tp=110)).ok
    r = ex.submit(Open("kronos_forecast", "X", "sell", sl=105, tp=90))
    assert not r.ok and "v5_supply_demand holds a buy" in r.why
    assert ex.submit(Open("kronos_forecast", "Y", "sell", sl=105, tp=90)).ok


def test_a_strategy_cannot_touch_another_strategys_trade():
    ex = paper()
    t = ex.submit(Open("a", "X", "buy", sl=95, tp=110)).ticket
    assert "belongs to a" in ex.submit(Close("b", t, reason="mine now")).why
    assert "belongs to a" in ex.submit(Modify("b", t, sl=99)).why
    assert ex.submit(Close("a", t, reason="exit rule")).ok


def test_stops_only_move_toward_profit():
    ex = paper()
    t = ex.submit(Open("s", "X", "buy", sl=95, tp=110)).ticket
    assert "toward profit" in ex.submit(Modify("s", t, sl=90)).why
    assert ex.submit(Modify("s", t, sl=97)).ok
    assert "past the current price" in ex.submit(Modify("s", t, sl=100.5)).why


def test_kill_switch_and_daily_loss_limit(tmp_path):
    L = copy.deepcopy(load_limits())
    L["account"]["halt_file"] = str(tmp_path / "HALT")
    L["order"]["max_lots"] = L["order"]["default_lots"] = 10.0
    L["order"]["max_risk_pct"] = 100
    ex = paper(L)
    (tmp_path / "HALT").write_text("")
    assert "halted" in ex.submit(Open("s", "X", "buy", sl=95, tp=110)).why
    (tmp_path / "HALT").unlink()
    r = ex.submit(Open("s", "X", "buy", sl=95, tp=110))               # 10 lots: $1000 per $1, fills at 100.2
    assert r.ok, r.why
    ex.on_bar("X", bar(M15, 100, 100, 99.4, 99.5), 2 * M15)           # −$700 open = −7 % of 10 000
    assert "daily loss limit" in ex.submit(Open("s", "Y", "buy", sl=95, tp=110)).why
    assert ex.submit(Close("s", r.ticket, reason="x")).ok             # closing is always allowed


def test_risk_cap_in_percent_of_balance():
    L = copy.deepcopy(load_limits())
    L["order"]["max_lots"] = L["order"]["default_lots"] = 1.0       # $100 per $1
    ex = paper(L)
    assert "of the balance" in ex.submit(Open("s", "X", "buy", sl=90, tp=130)).why   # $1000 = 10 % > 2.5 %
    assert ex.submit(Open("s", "X", "buy", sl=98, tp=110)).ok                        # $200 = 2 %


def test_paper_tp_stop_first_and_limit_fill():
    ex = paper()
    ex.submit(Open("s", "X", "buy", sl=95.2, tp=110.2))               # fills at the ask 100.2: risk 5
    ex.on_bar("X", bar(M15, 100, 111, 99, 110), 2 * M15)
    (t,) = ex.trades()
    assert t.exit_reason == "tp" and t.r == pytest.approx(2.0)
    ex.submit(Open("s", "Y", "sell", sl=105, tp=90))
    ex.on_bar("Y", bar(M15, 100, 106, 89, 100), 2 * M15)              # both touched: the stop counts
    assert ex.trades()[-1].exit_reason == "sl"
    ex.submit(Open("s", "X", "buy", sl=95, tp=120, order="limit", price=98))
    ex.on_bar("X", bar(2 * M15, 110, 110, 99, 100), 3 * M15)          # ask low 99.2: not yet
    assert ex.positions()[0].status == "pending"
    ex.on_bar("X", bar(3 * M15, 100, 100, 97.5, 99), 4 * M15)         # ask low 97.7: filled at 98
    assert ex.positions()[0].status == "open" and ex.positions()[0].entry == 98


# ── conductor: a strategy across engines ────────────────────────────────────────────────────────────────────────

class Stub(Concepter):
    """An engine that reports whatever the test gives it, and counts how often it was asked."""
    timeframes = ["M15"]
    lookback = 50

    def __init__(self, name, signals_at):
        self.name, self.signals_at, self.asked = name, signals_at, 0

    def on_bar(self, view):
        self.asked += 1
        return Reading(signals=list(self.signals_at(view.now)))


def flat_series(n=60, price=100.0):
    return [bar(i * M15, price, price + 1, price - 1, price, spread=0.02) for i in range(n)]


def conduct(strategy, engines, n=60):
    bars = flat_series(n)
    ex = PaperExecutor({"X": INFO}, balance=10_000)
    cond = Conductor(R.strategy(strategy), engines, ex)

    def view_for(sym, now, tfs, lookback):
        return View(sym, now, {tf: [b for b in bars if b.t + M15 <= now][-lookback:] for tf in tfs}, INFO)
    return bars, ex, cond, view_for


def test_kronos_direction_then_claude_bos_opens_with_stop_at_the_bos_origin():
    now = 60 * M15
    kron = Stub("kronos", lambda t: [Signal("kronos", "direction", "X", "M15", t, "buy", level=100,
                                            data={"p": 0.8, "move_spread_x": 5})])
    clau = Stub("claude", lambda t: [Signal("claude", "bos", "X", "M15", t - M15, "buy", level=100.5,
                                            data={"origin": 96.0})])
    bars, ex, cond, vf = conduct("kronos_direction_claude_bos", {"kronos": kron, "claude": clau})
    ex.on_bar("X", bars[-1], now)
    d, res = cond.step("X", now, vf)
    (o,) = d.commands
    assert res[0].ok and o.side == "buy" and o.owner == "kronos_direction_claude_bos"
    risk_atr = 2.0                                                     # every flat bar ranges 2 → ATR 2
    assert o.sl == pytest.approx(96.0 - 0.25 * risk_atr - 0.02)        # origin − 0.25 ATR − spread
    entry = 100.02
    assert o.tp == pytest.approx(entry + 2 * (entry - o.sl))           # RR 2
    assert "kronos direction buy" in o.reason and "claude bos buy" in o.reason
    d2, _ = cond.step("X", now, vf)
    assert d2.commands == []                                           # the same signals never trade twice


def test_claude_is_not_asked_when_kronos_does_not_agree():
    kron = Stub("kronos", lambda t: [Signal("kronos", "direction", "X", "M15", t, "buy", data={"p": 0.6, "move_spread_x": 5})])
    clau = Stub("claude", lambda t: [])
    bars, ex, cond, vf = conduct("kronos_direction_claude_bos", {"kronos": kron, "claude": clau})
    ex.on_bar("X", bars[-1], 60 * M15)
    d = cond.on_bar("X", 60 * M15, vf)
    assert d.commands == [] and "need 1 not met" in d.notes and clau.asked == 0


def test_claude_bos_against_kronos_or_too_old_is_no_trade():
    kron = Stub("kronos", lambda t: [Signal("kronos", "direction", "X", "M15", t, "buy", data={"p": 0.9, "move_spread_x": 5})])
    for clau_sig in (lambda t: [Signal("claude", "bos", "X", "M15", t, "sell", level=99, data={"origin": 103})],
                     lambda t: [Signal("claude", "bos", "X", "M15", t - 10 * M15, "buy", level=100, data={"origin": 96})]):
        bars, ex, cond, vf = conduct("kronos_direction_claude_bos", {"kronos": kron, "claude": Stub("claude", clau_sig)})
        ex.on_bar("X", bars[-1], 60 * M15)
        d = cond.on_bar("X", 60 * M15, vf)
        assert d.commands == [] and "need 2 not met" in d.notes


def test_exit_rules_choch_against_and_time_exit():
    state = {"choch": False}
    kron = Stub("kronos", lambda t: [Signal("kronos", "direction", "X", "M15", t, "buy", data={"p": 0.9, "move_spread_x": 5})])
    clau = Stub("claude", lambda t: [Signal("claude", "bos", "X", "M15", t, "buy", level=100, data={"origin": 96})]
                + ([Signal("claude", "choch", "X", "M15", t, "sell", level=99)] if state["choch"] else []))
    bars, ex, cond, vf = conduct("kronos_direction_claude_bos", {"kronos": kron, "claude": clau}, n=80)
    now = 60 * M15
    ex.on_bar("X", bars[59], now)
    assert cond.step("X", now, vf)[1][0].ok
    now += M15
    ex.on_bar("X", bars[60], now)
    state["choch"] = True
    d, res = cond.step("X", now, vf)
    assert isinstance(d.commands[0], Close) and "choch sell against" in d.commands[0].reason and res[0].ok
    # time exit: a fresh trade, then 8 bars later
    state["choch"] = False
    cond.used.clear()
    now += M15
    ex.on_bar("X", bars[61], now)
    assert cond.step("X", now, vf)[1][0].ok
    for i in range(62, 70):
        now += M15
        ex.on_bar("X", bars[i], now)
        d, _ = cond.step("X", now, vf)
    assert any(isinstance(c, Close) and "time exit" in c.reason for c in d.commands)


# ── the real engines on recorded bars ───────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def gold_view():
    info, bars = MD.load("GOLD")
    m15 = bars["M15"][:400]
    now = m15[-1].t + M15
    return View("GOLD", now, {"M15": m15, "H1": [b for b in bars["H1"] if b.t + 4 * M15 <= now],
                              "H4": [b for b in bars["H4"] if b.t + 16 * M15 <= now]}, info)


def test_claude_engine_gets_its_concept_rules_and_only_grounded_breaks_count(gold_view):
    last = gold_view.bars["M15"][-1]
    hi = max(b.c for b in gold_view.bars["M15"][-40:])

    def answer(system, user):
        return json.dumps({"signals": [
            {"signal": "bos", "side": "buy", "level": last.c - 0.01, "origin": last.c - 20, "reason": "closed above"},
            {"signal": "bos", "side": "buy", "level": hi + 50, "origin": hi, "reason": "made up"},
            {"signal": "direction", "side": "sell", "reason": "lower highs"}]})
    p = FakeProvider(answer)
    r = make_engine("claude", provider=p).on_bar(gold_view)
    assert "Concept rules: claude" in p.calls[0]["system"] and "margin_atr = 0.25" in p.calls[0]["system"]
    assert {"structure_m15", "live_zones_m15", "bars_m15"} <= set(json.loads(p.calls[0]["user"]))
    kinds = sorted((s.kind, s.side) for s in r.signals)
    assert kinds == [("bos", "buy"), ("direction", "sell")], r.notes      # the made-up BOS is dropped
    assert "dropped" in r.notes


def test_claude_engine_survives_garbage_and_a_dead_model(gold_view):
    assert make_engine("claude", provider=FakeProvider(["the market looks bullish"])).on_bar(gold_view).signals == []

    def boom(s, u):
        raise TimeoutError("network")
    r = make_engine("claude", provider=FakeProvider(boom)).on_bar(gold_view)
    assert r.signals == [] and "failed" in r.notes


def test_toolkit_baseline_and_v5_report_signals(gold_view):
    tk = make_engine("claude", provider="toolkit").on_bar(gold_view)
    assert any(s.kind in ("bos", "choch") for s in tk.signals) or "dropped" in tk.notes
    v5 = make_engine("v5").on_bar(gold_view)
    assert any(s.kind in ("bos", "choch") for s in v5.signals)
    for s in (s for s in v5.signals if s.kind == "setup"):
        assert s.data["entry"] == s.level and (s.data["sl"] < s.level if s.side == "buy" else s.data["sl"] > s.level)


def test_kronos_engine_reads_recorded_forecasts_without_looking_ahead():
    k = make_engine("kronos")
    fc = MD.load_kronos("GOLD")
    assert fc, "marketdata/sample/kronos_GOLD.jsonl.gz"
    f0 = fc[5]
    now = f0["bar_t"] + M15
    info, bars = MD.load("GOLD")
    view = View("GOLD", now, {"M15": [b for b in bars["M15"] if b.t + M15 <= now][-60:]}, info)
    (s,) = k.on_bar(view).signals
    assert s.t == now and s.data["p_up"] == f0["p_up"] and s.side == ("buy" if f0["p_up"] >= 0.5 else "sell")
    early = View("GOLD", fc[0]["bar_t"], view.bars, info)                 # before the first forecast bar closed
    assert k.on_bar(early).signals == []


@pytest.mark.parametrize("strategy", ["kronos_direction_claude_bos", "kronos_forecast", "v5_supply_demand"])
def test_every_strategy_runs_end_to_end_on_the_sample(strategy):
    out = run(strategy, ["GOLD"], days=4, quiet=True)
    s = out["summary"]
    assert s["bars"] > 100 and s["refused"] == 0
