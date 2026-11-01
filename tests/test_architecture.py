"""
tests/test_architecture.py — rules / concepters / executor (ARCHITECTURE.md). Offline: sample bars, paper executor,
fake LLM. Run: python3 -m pytest tests/test_architecture.py -q
"""
from __future__ import annotations

import copy
import json

import pytest

from concepters import make
from concepters.llm.concepter import LLMConcepter
from concepters.llm.providers import FakeProvider
from concepters.run import run
from executor.guard import Guard, load_limits
from executor.paper import PaperExecutor
from shared import data as DATA
from shared import rules as RULES
from shared.contracts import Bar, Close, Modify, Open, View, command_from_dict, command_to_dict

INFO = {"point": 0.01, "trade_tick_size": 0.01, "trade_tick_value": 1.0, "digits": 2}   # GOLD-like: $1 per $1 at 0.01


def bar(t, o, h, l, c, spread=0.2):
    return Bar(t=t, o=o, h=h, l=l, c=c, spread=spread)


def paper(limits=None, price=100.0):
    ex = PaperExecutor({"X": INFO, "Y": INFO}, balance=10_000, guard=Guard(limits or load_limits()))
    ex.on_bar("X", bar(0, price, price, price, price), 900_000)
    ex.on_bar("Y", bar(0, price, price, price, price), 900_000)
    return ex


# ── contracts ───────────────────────────────────────────────────────────────────────────────────────────────────

def test_commands_round_trip_as_json():
    for c in (Open("a", "X", "buy", sl=90, tp=120, reason="r"), Modify("a", 3, sl=95), Close("a", 3, reason="x")):
        assert command_from_dict(json.loads(json.dumps(command_to_dict(c)))) == c


def test_open_rejects_bad_side_and_limit_without_price():
    with pytest.raises(ValueError):
        Open("a", "X", "long", sl=1, tp=2)
    with pytest.raises(ValueError):
        Open("a", "X", "buy", sl=1, tp=2, order="limit")


# ── rules ───────────────────────────────────────────────────────────────────────────────────────────────────────

def test_every_strategy_loads_with_the_four_trade_sections():
    names = RULES.available()
    assert "supply_demand" in names and "_template" not in names
    for n in names:
        r = RULES.load(n)
        assert r.p("strategy.name") == n and r.version != "?"
        for s in RULES.TRADE_SECTIONS:
            assert s in r.trade


def test_supply_demand_numbers_match_what_the_engine_trades():
    """The running engine reads engine/config.py + engine/profit.py. Until the V5 concepter reads params.toml, the
    two must say the same thing: change one, change the other."""
    from engine.config import FILTER_PROFILES, FILTERS, STRATEGY
    from engine.profit import P
    r = RULES.load("supply_demand")
    prof = {**FILTERS, **FILTER_PROFILES[r.p("strategy.filter_profile")]}
    pairs = {
        "structure.swing_length": STRATEGY["swing_length"], "structure.major_swing_length": STRATEGY["major_swing_length"],
        "structure.bias_tfs": STRATEGY["bias_tfs"], "structure.bias_exempt_tfs": STRATEGY["bias_exempt_tfs"],
        "structure.setup_max_age_bars": STRATEGY["setup_max_age_bars"],
        "zone.lookback_bars": STRATEGY["zone_lookback_bars"], "zone.displacement_mult": STRATEGY["displacement_mult"],
        "zone.body_average_bars": STRATEGY["body_average_bars"],
        "fvg.pick": STRATEGY["fvg_pick"], "fvg.protect_candles": STRATEGY["fvg_protect_candles"],
        "fvg.min_runoff_atr": STRATEGY["fvg_min_runoff_atr"],
        "entry.fvg_depth": STRATEGY["fvg_entry_depth"], "entry.confirm_tf": STRATEGY["entry_confirm"],
        "entry.confirm_max_bars": STRATEGY["m5_confirm_max_bars"],
        "layer.depth_weak": STRATEGY["layer_depth"]["weak"], "layer.depth_moderate": STRATEGY["layer_depth"]["moderate"],
        "layer.depth_strong": STRATEGY["layer_depth"]["strong"],
        "stops.sl_buffer_points": STRATEGY["sl_buffer_points"], "stops.sdh4_sl_atr_buffer": prof["SL_ATR_BUFFER"],
        "stops.sl_min_spread_x": prof["SL_MIN_SPREAD_X"], "stops.sl_max_atr": prof["SL_MAX_ATR"],
        "stops.min_rr": prof["MIN_RR"],
        "manage.near_target_progress": STRATEGY["near_target_progress"],
        "manage.reversal_giveback": STRATEGY["reversal_giveback"], "manage.tp1_fraction": STRATEGY["tp1_fraction"],
        "manage.lock_start_r": STRATEGY["lock_start_r"], "manage.lock_gap_r": STRATEGY["lock_gap_r"],
        "exit.flat_before_utc": P["FLAT_BEFORE_SWAP_UTC"],
        "filters.setup_expiry_m15_bars": prof["SETUP_EXPIRY_M15_BARS"],
        "filters.sl_widen_to_stops_level": prof["SL_WIDEN_TO_STOPS_LEVEL"],
        "filters.max_spread_atr": P["MAX_SPREAD_ATR"], "filters.min_target_spread_x": P["MIN_TARGET_SPREAD_X"],
        "filters.rollover_utc": list(P["ROLLOVER_UTC"]),
    }
    diff = {k: (r.p(k), v) for k, v in pairs.items() if r.p(k) != v}
    assert not diff, f"rules/supply_demand/params.toml vs engine (params, engine): {diff}"


def test_kronos_numbers_match_the_engine():
    from engine.config import KRONOS as K
    r = RULES.load("kronos_forecast")
    pairs = {"forecast.context": K["CONTEXT"], "forecast.horizon": K["HORIZON"], "forecast.paths": K["PATHS"],
             "forecast.p_min": K["P_MIN"], "forecast.min_move_spread_x": K["MIN_MOVE_SPREAD_X"],
             "forecast.signal_max_age_sec": K["SIGNAL_MAX_AGE_SEC"], "stops.sl_atr": K["SL_ATR"],
             "stops.tp_atr": K["TP_ATR"], "stops.max_spread_sl": K["MAX_SPREAD_SL"], "exit.hold_bars": K["HOLD_BARS"],
             "exit.min_free_margin_pct": K["MIN_FREE_MARGIN_PCT"], "exit.friday_last_entry_utc": K["FRIDAY_LAST_ENTRY_UTC"]}
    diff = {k: (r.p(k), v) for k, v in pairs.items() if r.p(k) != v}
    assert not diff, f"rules/kronos_forecast/params.toml vs engine/config.py KRONOS: {diff}"


# ── guard ───────────────────────────────────────────────────────────────────────────────────────────────────────

def test_guard_refuses_a_stop_on_the_wrong_side_and_a_target_behind_the_entry():
    ex = paper()
    assert "SL below" in ex.submit(Open("a", "X", "buy", sl=101, tp=110)).why
    assert "SL above" in ex.submit(Open("a", "X", "sell", sl=99, tp=90)).why
    assert "wrong side" in ex.submit(Open("a", "X", "buy", sl=95, tp=99)).why


def test_guard_blocks_the_opposite_side_on_one_symbol_even_for_another_concepter():
    ex = paper()
    assert ex.submit(Open("v5", "X", "buy", sl=95, tp=110)).ok
    r = ex.submit(Open("gpt", "X", "sell", sl=105, tp=90))
    assert not r.ok and "v5 holds a buy" in r.why
    assert ex.submit(Open("gpt", "Y", "sell", sl=105, tp=90)).ok


def test_a_concepter_cannot_touch_another_concepters_trade():
    ex = paper()
    t = ex.submit(Open("v5", "X", "buy", sl=95, tp=110)).ticket
    assert "belongs to v5" in ex.submit(Close("gpt", t, reason="mine now")).why
    assert "belongs to v5" in ex.submit(Modify("gpt", t, sl=99)).why
    assert ex.submit(Close("v5", t, reason="exit rule")).ok


def test_stops_only_move_toward_profit():
    ex = paper()
    t = ex.submit(Open("a", "X", "buy", sl=95, tp=110)).ticket
    assert "toward profit" in ex.submit(Modify("a", t, sl=90)).why
    assert ex.submit(Modify("a", t, sl=97)).ok
    assert "past the current price" in ex.submit(Modify("a", t, sl=100.5)).why


def test_kill_switch_and_daily_loss_limit(tmp_path):
    L = copy.deepcopy(load_limits())
    L["account"]["halt_file"] = str(tmp_path / "HALT")
    L["order"]["max_lots"] = L["order"]["default_lots"] = 10.0
    L["order"]["max_risk_pct"] = 100
    ex = paper(L)
    (tmp_path / "HALT").write_text("")
    assert "halted" in ex.submit(Open("a", "X", "buy", sl=95, tp=110)).why
    (tmp_path / "HALT").unlink()
    r = ex.submit(Open("a", "X", "buy", sl=95, tp=110))               # 10 lots: $1000 per $1, fills at 100.2
    assert r.ok, r.why
    t = r.ticket
    ex.on_bar("X", bar(900_000, 100, 100, 99.4, 99.5), 1_800_000)     # −$700 open = −7 % of 10 000
    assert "daily loss limit" in ex.submit(Open("a", "Y", "buy", sl=95, tp=110)).why
    assert ex.submit(Close("a", t, reason="x")).ok                   # closing is always allowed


def test_risk_cap_in_percent_of_balance():
    L = copy.deepcopy(load_limits())
    L["order"]["max_lots"] = L["order"]["default_lots"] = 1.0       # $100 per $1
    ex = paper(L)
    assert "of the balance" in ex.submit(Open("a", "X", "buy", sl=90, tp=130)).why   # $1000 = 10 % > 2.5 %
    assert ex.submit(Open("a", "X", "buy", sl=98, tp=110)).ok                        # $200 = 2 %


# ── paper fills ─────────────────────────────────────────────────────────────────────────────────────────────────

def test_paper_buy_reaches_tp_and_reports_r():
    ex = paper()
    ex.submit(Open("a", "X", "buy", sl=95.2, tp=110.2))               # fills at the ask 100.2: risk 5
    ex.on_bar("X", bar(900_000, 100, 111, 99, 110), 1_800_000)
    (t,) = ex.trades()
    assert t.exit_reason == "tp" and t.exit == 110.2 and t.r == pytest.approx(2.0)


def test_paper_counts_the_stop_when_one_bar_touches_both():
    ex = paper()
    ex.submit(Open("a", "X", "sell", sl=105, tp=90))
    ex.on_bar("X", bar(900_000, 100, 106, 89, 100), 1_800_000)
    assert ex.trades()[0].exit_reason == "sl"


def test_paper_limit_waits_then_fills():
    ex = paper()
    t = ex.submit(Open("a", "X", "buy", sl=95, tp=110, order="limit", price=98)).ticket
    assert ex.positions()[0].status == "pending"
    ex.on_bar("X", bar(900_000, 100, 101, 99, 100), 1_800_000)        # ask low 99.2: not yet
    assert ex.positions()[0].status == "pending"
    ex.on_bar("X", bar(1_800_000, 100, 100, 97.5, 99), 2_700_000)     # ask low 97.7: filled at 98
    p = ex.positions()[0]
    assert p.status == "open" and p.entry == 98 and p.ticket == t


# ── concepters ──────────────────────────────────────────────────────────────────────────────────────────────────

def test_demo_concepter_runs_end_to_end_on_the_sample():
    out = run(make("demo", RULES.load("supply_demand")), ["GOLD"], days=10, quiet=True)
    s = out["summary"]
    assert s["bars"] > 500 and s["trades"] + s["open_at_end"] > 0
    kinds = {r["command"]["kind"] for j in out["journal"] if j["event"] == "decision" for r in j["results"]}
    assert "open" in kinds


@pytest.fixture(scope="module")
def gold_view():
    info, bars = DATA.load("GOLD")
    m15, h1 = bars["M15"][:400], bars["H1"]
    now = m15[-1].t + 900_000
    return View(symbol="GOLD", now=now, bars={"M15": m15, "H1": [b for b in h1 if b.t + 3_600_000 <= now]},
                positions=[], info=info)


def llm(reply, rules="supply_demand"):
    p = FakeProvider(reply if callable(reply) else [reply])
    p.name = "gpt"
    return LLMConcepter(RULES.load(rules), provider=p, ask="every_bar"), p


def test_llm_gets_the_rules_and_the_chart_and_its_open_becomes_a_command(gold_view):
    def answer(system, user):
        pk = json.loads(user)
        a = pk["ask"]
        return json.dumps({"action": "open", "side": "buy", "order": "market", "sl": a - 10, "tp": a + 25,
                           "reason": "BOS up, demand zone, FVG 10 % touched"})
    c, p = llm(answer)
    d = c.on_bar(gold_view)
    system = p.calls[0]["system"]
    assert "Exit when it goes wrong" in system and "fvg_depth = 0.10" in system    # the words AND the numbers
    pk = json.loads(p.calls[0]["user"])
    assert {"structure_m15", "live_zones_m15", "bars_m15", "my_positions"} <= set(pk)
    (cmd,) = d.commands
    assert isinstance(cmd, Open) and cmd.concepter == "gpt" and cmd.side == "buy"


def test_llm_answer_that_breaks_the_rules_is_not_traded(gold_view):
    def low_rr(system, user):
        a = json.loads(user)["ask"]
        return json.dumps({"action": "open", "side": "buy", "sl": a - 10, "tp": a + 5, "reason": "x"})
    for reply in (low_rr, "I think gold goes up!", '{"action": "open", "side": "buy"}',
                  '{"action": "close", "ticket": 99, "reason": "x"}'):
        d = llm(reply)[0].on_bar(gold_view)
        assert d.commands == [], d.notes


def test_llm_provider_failure_is_a_wait(gold_view):
    def boom(system, user):
        raise TimeoutError("network")
    d = llm(boom)[0].on_bar(gold_view)
    assert d.commands == [] and "provider failed" in d.notes
