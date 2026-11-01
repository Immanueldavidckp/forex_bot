"""engine/test_smc_marks.py — order blocks, FVG, liquidity and the dealing range on hand-made candles."""
from engine import smc_marks
from engine.major_structure import atr14


def _bar(t, o, h, l, c):
    return {"t": t * 900_000, "o": o, "h": h, "l": l, "c": c}


def _ob_case():
    """12 quiet candles, the down candle 12 (the OB), the displacement 13, the break 14, then: a wick into the box,
    past its 50 %, a close below it (invalid), back up into it (breaker), a close above it (dead)"""
    bars = [_bar(i, 10.0, 10.7, 9.8, 10.5) if i % 2 else _bar(i, 10.5, 10.7, 9.8, 10.0) for i in range(12)]
    bars += [_bar(12, 10.4, 10.5, 9.7, 9.9), _bar(13, 9.9, 13.1, 9.85, 13.0), _bar(14, 13.0, 13.6, 12.9, 13.5),
             _bar(15, 13.5, 13.6, 10.4, 12.0), _bar(16, 12.0, 12.1, 10.0, 11.0), _bar(17, 11.0, 11.0, 9.4, 9.5),
             _bar(18, 9.5, 9.75, 9.3, 9.6), _bar(19, 9.6, 10.9, 9.5, 10.8), _bar(20, 10.8, 11.0, 10.6, 10.9)]
    m = {"events": [{"kind": "BOS", "side": "buy", "origin": {"idx": 12, "price": 9.7}, "idx": 14}], "points": [],
         "trend": "up", "protected": {"idx": 12, "price": 9.7}}
    return bars, m


def test_the_order_block_is_the_last_opposite_candle_before_the_displacement_and_lives_out_its_states():
    bars, m = _ob_case()
    [ob] = smc_marks.order_blocks(bars, m)
    assert (ob["idx"], ob["disp_idx"], ob["top"], ob["bottom"]) == (12, 13, 10.5, 9.7) and ob["has_fvg"]
    assert (ob["touch_idx"], ob["mean_idx"], ob["invalid_idx"], ob["breaker_idx"], ob["dead_idx"]) == (15, 16, 17, 18, 19)
    assert ob["status"] == "dead" and not ob["live"]


def test_an_order_block_not_closed_through_stays_live():
    bars, m = _ob_case()
    [ob] = smc_marks.order_blocks(bars[:17], m)                      # up to the candle before the close below
    assert ob["status"] == "mean" and ob["live"]


def test_fvg_of_the_break_with_its_fill_states_and_davids_invalidation():
    bars, m = _ob_case()
    out = smc_marks.fvgs(bars, m, atr14(bars))
    [f] = out["fvgs"]
    assert (f["side"], f["bottom"], f["top"], f["idx"]) == ("bull", 10.5, 12.9, 13)
    assert (f["touched_idx"], f["ce_idx"], f["filled_idx"], f["inverted_idx"]) == (15, 15, 15, 17)
    assert f["status"] == "inverted" and f["invalid"].startswith("traded back into 1 candle") and not f["live"]
    assert len(out["fvg_clusters"]) == 1


def test_a_gap_outside_the_breaking_move_is_not_marked():
    bars, m = _ob_case()
    m = dict(m, events=[dict(m["events"][0], origin={"idx": 13, "price": 9.85})])   # move starts after the gap's middle
    assert smc_marks.fvgs(bars, m, atr14(bars))["fvgs"] == []


def _eq_case(sweep_close):
    """two equal highs 13.0 / 13.2 with a real pullback between, then a candle that wicks to 13.6"""
    hs = [10, 11, 12, 13, 12, 11, 10, 11, 12, 12.5, 13.2, 12, 11, 10, 11, 12, 13.0, 13.6, 12.5, 12, 11.5, 11, 10.5]
    bars = [_bar(i, h - 0.6, h, h - 1.0, h - 0.4) for i, h in enumerate(hs)]
    bars[17] = _bar(17, 12.9, 13.6, 12.6, sweep_close)
    if sweep_close > 13.2:                                           # the close stays above for the next candles
        for i in range(18, 23):
            bars[i] = _bar(i, 13.5, 13.9, 13.4, 13.7)
    return bars


def test_equal_highs_form_a_pool_and_a_wick_through_is_a_sweep():
    bars = _eq_case(sweep_close=12.9)
    pools = [p for p in smc_marks.liquidity(bars, {"points": []}, atr14(bars)) if p["kind"] == "EQH"]
    assert len(pools) == 1
    p = pools[0]
    assert (p["level"], p["touches"], p["first"], p["born"]) == (13.2, 2, 3, 13)
    assert p["status"] == "swept" and p["sweeps"][0]["kind"] == "wick" and p["sweeps"][0]["extreme"] == 13.6
    assert p["sweeps"][0]["start"] == p["sweeps"][0]["end"] == 17


def test_closes_that_stay_beyond_break_the_pool():
    bars = _eq_case(sweep_close=13.6)                                # 0.4 beyond: ≥ 0.25 ATR, a real close beyond
    [p] = [p for p in smc_marks.liquidity(bars, {"points": []}, atr14(bars)) if p["kind"] == "EQH"]
    assert p["status"] == "broken" and p["broken_idx"] == 20 and p["sweeps"] == []


def test_dealing_range_from_the_protected_swing_to_the_leg_high():
    bars = [_bar(i, 100, 101, 99, 100) for i in range(3)] + [_bar(3, 100, 110, 90, 105), _bar(4, 105, 106, 100, 102)]
    r = smc_marks.dealing_range(bars, {"trend": "up", "protected": {"idx": 3, "price": 90}})
    assert (r["low"], r["high"], r["eq"]) == (90, 110, 100)
    assert [round(v, 1) for v in r["ote"]] == [94.2, 97.6] and r["zone"] == "premium" and abs(r["pos"] - 0.6) < 1e-9
