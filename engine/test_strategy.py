"""
Offline tests of the BOS-first setup (strategy.py) on hand-made candles shaped like David's pictures:

    cd ~/forex && python3 -m pytest -q engine/test_strategy.py
"""
from __future__ import annotations

import pytest

from engine import strategy as V

# (after K lead-in bars) HL 9.2 → HH 10.6 (bar 7) → HL 9.5 (bar 10) → red candle (13) → displacement (14) →
# close 10.75 above the HH (bar 15 = BOS); FVGs with middle candles 14 and 15 inside the BOS move, a third (16)
# after it → peak 11.7 (18) → pullback (21). Indices below are written as K + the bar number.
K = 5                                                   # a lower swing high first (10.3), so 10.6 is an HH
UP = [(9.6, 9.8, 9.5, 9.7), (9.7, 10.0, 9.6, 9.9), (9.9, 10.3, 9.8, 10.2), (10.2, 10.25, 9.95, 10.0), (10.0, 10.2, 9.9, 10.0),
      (10.0, 10.1, 9.8, 9.9), (9.9, 10.0, 9.6, 9.7), (9.7, 9.8, 9.4, 9.5), (9.5, 9.6, 9.2, 9.3),
      (9.3, 9.7, 9.3, 9.6), (9.6, 10.0, 9.5, 9.9), (9.9, 10.4, 9.8, 10.3), (10.3, 10.6, 10.1, 10.5),
      (10.5, 10.55, 10.0, 10.1), (10.1, 10.2, 9.7, 9.8), (9.8, 9.9, 9.5, 9.6), (9.6, 9.75, 9.55, 9.7),
      (9.7, 9.9, 9.6, 9.85), (9.85, 9.9, 9.7, 9.75), (9.75, 10.5, 9.74, 10.45), (10.45, 10.8, 10.4, 10.75),
      (10.75, 11.2, 10.7, 11.15), (11.15, 11.6, 11.1, 11.55), (11.55, 11.7, 11.1, 11.4), (11.4, 11.5, 11.0, 11.1),
      (11.1, 11.2, 10.9, 11.0), (11.0, 11.05, 10.6, 10.65)]


def bars(rows):
    return [{"t": i * 900_000, "o": o, "h": h, "l": l, "c": c} for i, (o, h, l, c) in enumerate(rows)]


def mirror(rows):
    """The same picture upside down: a downtrend."""
    return [(20 - o, 20 - l, 20 - h, 20 - c) for o, h, l, c in rows]


def test_bos_up_on_the_close_above_the_hh():
    st = V.structure(bars(UP))
    bos = [e for e in st["events"] if e["kind"] == "BOS"]
    assert len(bos) == 1
    e = bos[0]
    assert e["side"] == "buy" and e["idx"] == K + 15 and e["level"] == 10.6 and e["level_idx"] == K + 7 and e["level_label"] == "HH"
    assert e["origin"]["idx"] == K + 10 and e["origin"]["price"] == 9.5       # the HL the move started from
    assert st["trend"] == "up"


def test_a_wick_through_is_not_a_bos():
    rows = list(UP)
    rows[K + 15] = (10.45, 10.8, 10.4, 10.55)                                # high above 10.6, close below
    e = [e for e in V.structure(bars(rows))["events"] if e["kind"] == "BOS"][0]
    assert e["idx"] == K + 16                                                # the next candle closes above


def test_bos_down_is_the_mirror():
    st = V.structure(bars(mirror(UP)))
    e = [e for e in st["events"] if e["kind"] == "BOS"][0]
    assert e["side"] == "sell" and e["idx"] == K + 15 and e["level"] == pytest.approx(9.4) and e["level_label"] == "LL"
    assert st["trend"] == "down"


def test_close_below_the_last_hl_is_choch_not_bos():
    rows = UP + [(10.65, 10.7, 9.9, 10.0), (10.0, 10.05, 9.4, 9.45)]         # closes 9.45 < the HL 9.5
    st = V.structure(bars(rows))
    last = st["events"][-1]
    assert last["kind"] == "CHoCH" and last["side"] == "sell" and last["idx"] == K + 23 and last["level"] == 9.5
    assert last["level_label"] == "HL" and last["origin"]["price"] == 11.7


def test_breaking_a_small_lh_inside_the_pullback_keeps_the_hh_breakable():
    rows = list(UP[:K + 13])                                                  # up to the HL at 9.5 and a bounce
    rows += [(9.85, 9.95, 9.8, 9.9), (9.9, 10.0, 9.85, 9.95), (9.95, 10.05, 9.6, 9.65),   # small swing high 10.05 (LH)
             (9.65, 9.7, 9.55, 9.6), (9.6, 9.7, 9.56, 9.65),
             (9.65, 10.2, 9.6, 10.15),                                        # closes above the LH: CHoCH
             (10.15, 10.7, 10.1, 10.65)]                                      # closes above the HH 10.6: BOS
    ev = V.structure(bars(rows))["events"]
    assert [(e["kind"], e["level"]) for e in ev[-2:]] == [("CHoCH", 10.05), ("BOS", 10.6)]


def test_setup_demand_second_fvg_entry_ten_percent():
    b = bars(UP)
    s = [x for x in V.bos_setups(b, V.structure(b), "M15", "TEST") if x["complete"]][0]
    assert s["id"] == f"TEST-M15-D-{(K + 15) * 900}" and s["kind"] == "demand"
    assert s["zone"]["idx"] == K + 13 and (s["zone"]["bottom"], s["zone"]["top"]) == (9.7, 9.9)   # last red candle before the push
    assert s["zone"]["displacement"]["idx"] == K + 14 and s["mb"] is None
    assert [f["idx"] for f in s["fvgs"]] == [K + 14, K + 15] and s["fvg_pick"] == 2          # inside the BOS move → the 2nd
    assert (s["fvg"]["bottom"], s["fvg"]["top"]) == (10.5, 10.7)
    assert s["entry"] == pytest.approx(10.68)                                                 # 10 % inside from the top
    assert s["invalidation"] == 9.7 and s["leg"]["end_idx"] == K + 18


def test_mitigation_block_only_when_there_is_no_supply_demand(monkeypatch):
    monkeypatch.setitem(V.S, "displacement_mult", 100.0)                    # no candle is a displacement → no zone
    b = bars(UP)
    s = [x for x in V.bos_setups(b, V.structure(b), "M15", "TEST") if x["complete"]][0]
    assert s["zone"] is None and s["kind"] == "MB" and s["poi"]["idx"] == K + 13              # GREEN GREEN RED GREEN GREEN
    assert s["invalidation"] == 9.7


def test_supply_setup_is_the_mirror():
    b = bars(mirror(UP))
    s = [x for x in V.bos_setups(b, V.structure(b), "M15", "TEST") if x["complete"]][0]
    assert s["kind"] == "supply" and s["side"] == "sell" and s["fvg_pick"] == 2
    assert (s["fvg"]["bottom"], s["fvg"]["top"]) == pytest.approx((9.3, 9.5))
    assert s["entry"] == pytest.approx(9.32)                                                  # 10 % inside from the bottom


def test_pullback_reaches_the_entry():
    b = bars(UP)
    s = [x for x in V.bos_setups(b, V.structure(b), "M15") if x["complete"]][0]
    seq = [x for x in b if x["t"] > s["formed_t"]]
    i = V.pullback(s, seq)
    assert seq[i]["t"] == b[K + 21]["t"]                                     # low 10.6 ≤ entry 10.68


# ── David's SL/TP bug fix (2026-10-24) ──
LOWS = [(10, 10.2, 9.8, 10), (10, 10.1, 9.6, 9.7), (9.7, 9.8, 9.0, 9.5), (9.5, 9.9, 9.4, 9.8), (9.8, 10.0, 9.6, 9.9),
        (9.9, 9.95, 9.3, 9.4), (9.4, 9.5, 8.5, 8.7), (8.7, 9.2, 8.6, 9.1), (9.1, 9.6, 9.0, 9.5), (9.5, 9.7, 9.2, 9.6)]


def test_stop_comes_from_the_setups_own_zone_only():
    b = bars(UP)
    s = [x for x in V.bos_setups(b, V.structure(b), "M15", "TEST") if x["complete"]][0]
    assert s["invalidation"] == s["poi"]["bottom"] == 9.7
    m = bars(mirror(UP))
    s = [x for x in V.bos_setups(m, V.structure(m), "M15", "TEST") if x["complete"]][0]
    assert s["invalidation"] == s["poi"]["top"]


def test_target_levels_skip_structure_already_traded_through():
    lv = V.opposite_levels("sell", ("M15", bars(LOWS)))
    assert [p for p, _ in lv] == [8.5]                                       # the 9.0 low was taken by the 8.5 bar


def test_target_is_real_structure_or_no_trade():
    lv = V.opposite_levels("sell", ("M15", bars(LOWS)))
    t = V.final_target("sell", 10.0, 10.4, lv)                               # risk 0.4 → 3R at 8.8; 8.5 is beyond it
    assert t["price"] == 8.5 and t["rr"] == 3.75
    t = V.final_target("sell", 10.0, 10.6, lv)                               # 3R at 8.2: no structure that far
    assert t["price"] is None and t["rr"] is None and "no structure target" in t["label"]


def _setup():
    b = bars(UP)
    return [x for x in V.bos_setups(b, V.structure(b), "M15", "TEST") if x["complete"]][0]


def test_pretrade_passes_a_clean_setup():
    s = _setup()                                                             # buy: entry 10.68, stop 9.5, risk 1.18
    assert V.pretrade(s, 10.68, 9.5, {"price": 15.0}, 1.0) is None


@pytest.mark.parametrize("change, why", [
    (dict(atr=0.3), "abnormal stop"),                                        # 1.18 > 3 × 0.3: rejected, never moved closer
    (dict(stop=10.8), "is not below the entry"),
    (dict(tgt={"price": None, "label": "no structure target at ≥ 1:3"}), "no structure target"),
    (dict(tgt={"price": 10.0}), "wrong side"),
    (dict(tgt={"price": 10.68 + 2 * 1.18}), "RR 2.00 is under 3"),
])
def test_pretrade_rejects(change, why):
    a = {"entry": 10.68, "stop": 9.5, "tgt": {"price": 15.0}, "atr": 1.0, **change}
    assert why in V.pretrade(_setup(), a["entry"], a["stop"], a["tgt"], a["atr"])


def test_pretrade_rejects_levels_from_another_setup():
    s = _setup()
    assert "FVG is not this setup's" in V.pretrade({**s, "fvg": {"top": 10.9, "bottom": 10.6, "t": 0, "idx": 1}}, 10.68, 9.5, {"price": 15.0}, 1.0)
    assert "not from this setup's own zone" in V.pretrade({**s, "invalidation": 9.2}, 10.68, 9.5, {"price": 15.0}, 1.0)
    assert "BOS" in V.pretrade({**s, "bos": {**s["bos"], "kind": "CHoCH"}}, 10.68, 9.5, {"price": 15.0}, 1.0)


# ── David 2026-10-25: H4 + H1 bias, S&D H4 ──

def test_trade_bias_needs_h4_and_h1_to_agree():
    up, down = bars(UP), bars(mirror(UP))
    assert V.trade_bias(up, up)["bias"] == "buy" and V.trade_bias(down, down)["bias"] == "sell"
    tb = V.trade_bias(down, up)                                              # H4 down, H1 up
    assert tb["bias"] is None and "must agree" in tb["why"] and tb["h4"]["bias"] == "sell" and tb["h1"]["bias"] == "buy"


def test_sdh4_m15_breaks_from_inside_the_h4_zone_make_setups():
    b = bars(UP)
    st = V.structure(b)
    h4 = {"id": "X-H4-D-1", "side": "buy", "entry": 9.8, "invalidation": 9.0, "touch_t": b[8]["t"]}
    kids, broken = V.sdh4_setups(h4, b, st, "M15", "X")
    assert broken is None
    assert [(k["bos"]["kind"], k["complete"]) for k in kids] == [("CHoCH", True), ("BOS", True)]   # the CHoCH counts inside an H4 zone
    assert all(k["parent"] == "X-H4-D-1" and k["entry_type"] == "S&D H4" and k["id"].startswith("X-H4M15-D-") for k in kids)


def test_sdh4_ignores_breaks_from_outside_the_h4_zone():
    b = bars(UP)
    kids, _ = V.sdh4_setups({"id": "P", "side": "buy", "entry": 10.0, "invalidation": 9.6, "touch_t": b[8]["t"]}, b, V.structure(b), "M15")
    assert kids == []                                                        # both moves started below the H4 zone (9.2, 9.5)


def test_sdh4_stops_at_a_close_beyond_the_h4_invalidation():
    b = bars(UP)
    kids, broken = V.sdh4_setups({"id": "P", "side": "buy", "entry": 9.9, "invalidation": 9.65, "touch_t": b[10]["t"]}, b, V.structure(b), "M15")
    assert broken == b[15]["t"] and kids == []                               # closed 9.6 < 9.65 before the BOS


def test_pretrade_takes_a_choch_only_for_s_and_d_h4():
    b = bars(UP)
    st = V.structure(b)
    k = V.sdh4_setups({"id": "P", "side": "buy", "entry": 9.8, "invalidation": 9.0, "touch_t": b[8]["t"]}, b, st, "M15")[0][0]
    tgt = {"price": 20.0, "label": "test", "rr": 9}
    assert V.pretrade(k, k["entry"], 9.1, tgt, 1.0) != "not this setup's BOS"
    assert V.pretrade({**k, "parent": None}, k["entry"], 9.1, tgt, 1.0) == "not this setup's BOS"
