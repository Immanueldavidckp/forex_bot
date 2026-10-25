"""
Tests of the market-agnostic tools on hand-built bars (no data, no network):

    python3 -m pytest engine/tools/test_tools.py -q
"""
from __future__ import annotations

import datetime as _dt

import pytest

from engine import tools as T

UTC = _dt.timezone.utc
IST = _dt.timezone(_dt.timedelta(hours=5, minutes=30))
T0 = int(_dt.datetime(2026, 10, 22, 9, 15, tzinfo=IST).timestamp() * 1000)


def bars_from(hl, minutes=5, v=100):
    """Bars from (high, low) pairs; open/close inside, close direction from the next bar's mid."""
    out = []
    for i, (h, l) in enumerate(hl):
        mid = (h + l) / 2
        nxt = (hl[i + 1][0] + hl[i + 1][1]) / 2 if i + 1 < len(hl) else mid
        o, c = (l + (h - l) * 0.25, h - (h - l) * 0.25) if nxt >= mid else (h - (h - l) * 0.25, l + (h - l) * 0.25)
        out.append({"t": T0 + i * minutes * 60_000, "o": o, "h": h, "l": l, "c": c, "v": v})
    return out


def bar(i, o, h, l, c, v=100, minutes=5):
    return {"t": T0 + i * minutes * 60_000, "o": o, "h": h, "l": l, "c": c, "v": v}


# ── bars ──

def test_resample_anchors_at_the_session_open_and_adds_volume():
    one = [bar(i, 100 + i, 101 + i, 99 + i, 100.5 + i, v=10, minutes=1) for i in range(12)]
    five = T.resample(one, 5, IST, _dt.time(9, 15))
    assert [T.to_dt(b["t"], IST).strftime("%H:%M") for b in five] == ["09:15", "09:20", "09:25"]
    assert five[0]["o"] == 100 and five[0]["h"] == 105 and five[0]["l"] == 99 and five[0]["c"] == 104.5 and five[0]["v"] == 50
    assert five[2]["v"] == 20                                      # the last bucket is partial
    clock = T.resample(one, 5, IST)                                # anchored at midnight: 09:15 is on the grid too
    assert [b["t"] for b in clock] == [b["t"] for b in five]


def test_sessions_follow_the_timezone():
    late = int(_dt.datetime(2026, 10, 22, 23, 30, tzinfo=UTC).timestamp() * 1000)
    assert T.session_key(late, UTC) == "2026-10-22" and T.session_key(late, IST) == "2026-10-23"


# ── indicators ──

def test_indicators_on_a_steady_rise():
    bs = [bar(i, 100 + i, 101 + i, 99.5 + i, 100.8 + i) for i in range(60)]
    closes = [b["c"] for b in bs]
    assert T.sma(closes, 3)[2] == pytest.approx(sum(closes[:3]) / 3) and T.sma(closes, 3)[1] is None
    assert T.rsi(closes) == 100.0                                  # never a down close
    assert T.atr(bs, 14) == pytest.approx(1.5)                     # high − low 1.5, gaps smaller
    line, sig, hist = T.macd(closes)
    assert line[-1] > 0 and hist[-1] is not None
    ax, pdi, mdi = T.adx(bs, 14)
    assert ax[-1] > 25 and pdi[-1] > mdi[-1]                       # a clean trend
    st, d = T.supertrend(bs, 10, 3.0)
    assert d[-1] == 1 and st[-1] < bs[-1]["c"]
    k, dd = T.stochastic(bs)
    assert k[-1] > 80
    mid, up, lo = T.bollinger(closes, 20)
    assert lo[-1] < mid[-1] < up[-1]
    assert T.obv(bs)[-1] == 100 * 59


def test_vwap_resets_each_session():
    day2 = T0 + 86_400_000
    bs = [bar(0, 10, 10, 10, 10, v=1), bar(1, 20, 20, 20, 20, v=1), {"t": day2, "o": 50, "h": 50, "l": 50, "c": 50, "v": 5}]
    assert T.vwap(bs, IST) == [10, 15, 50]
    m, u, lo = T.vwap_bands(bs, IST)
    assert m[1] == 15 and u[1] == pytest.approx(20) and lo[1] == pytest.approx(10)


# ── structure ──

UP_THEN_BREAK_DOWN = [(101, 99), (103, 100), (105, 102), (104, 101), (103, 100.5), (106, 103), (108, 105),
                      (107, 104), (105, 102), (104, 101.5), (103, 100), (101, 98), (100, 97)]


def test_swings_need_confirmation_and_are_labelled():
    bs = bars_from(UP_THEN_BREAK_DOWN)
    sw = T.label_swings(T.swing_points(bs, 2, 2))
    highs = [(s["idx"], s["price"], s["label"]) for s in sw if s["kind"] == "high"]
    assert highs == [(2, 105, "H"), (6, 108, "HH")]
    assert all(s["confirmed"] == s["idx"] + 2 for s in sw)
    assert not any(s["idx"] >= len(bs) - 2 for s in sw)         # the last 2 bars cannot be swings yet


def test_structure_bos_and_choch_without_look_ahead():
    bs = bars_from(UP_THEN_BREAK_DOWN)
    sw = T.swing_points(bs, 2, 2)
    st = T.market_structure(bs, sw)
    kinds = [(e["kind"], e["dir"], e["level"]) for e in st["events"]]
    assert kinds[0] == ("CHoCH", "up", 105)                        # first break sets the bias
    assert ("CHoCH", "down", 100.5) in kinds                       # the higher low at bar 4 gives way
    assert st["bias"] == "down"
    # the swing high at bar 2 is only known at bar 4: a close above 105 before that is not a break
    early = T.market_structure(bs[:5], T.swing_points(bs[:5], 2, 2))
    assert early["events"] == []


def test_trend_from_swings():
    assert T.trend([{"kind": "high", "price": 10}, {"kind": "low", "price": 5}, {"kind": "high", "price": 12},
                    {"kind": "low", "price": 6}]) == "up"
    assert T.trend([{"kind": "high", "price": 10}, {"kind": "low", "price": 5}, {"kind": "high", "price": 9},
                    {"kind": "low", "price": 4}]) == "down"
    assert T.trend([{"kind": "high", "price": 10}]) is None


def test_sweep_and_equal_highs():
    # two equal highs at 110, then a bar wicks to 111 and closes at 108: a sweep, the pool is taken
    hl = [(105, 100), (108, 103), (110, 106), (107, 103), (106, 102), (108, 104), (110, 106), (107, 103), (105, 101)]
    bs = bars_from(hl)
    sw = T.swing_points(bs, 2, 2)
    assert [p["price"] for p in T.equal_levels(bs, sw, 0.5)] == [110]
    bs.append(bar(len(bs), 106, 111, 105, 108))
    ev = T.sweeps(bs, sw)
    assert ev and ev[-1]["side"] == "high" and ev[-1]["level"] == 110
    assert T.equal_levels(bs, sw, 0.5) == []


def test_dealing_range_zones():
    bs = bars_from([(110, 100)] * 3)
    st = {"last_high": {"price": 110}, "last_low": {"price": 100}}
    bs[-1]["c"] = 108
    r = T.dealing_range(bs, st)
    assert r["zone"] == "premium" and r["eq"] == 105 and r["ote_long"] == pytest.approx((102.1, 103.8))


# ── smc ──

def test_fair_value_gap_fill_and_inversion():
    bs = [bar(0, 100, 101, 99, 100.5), bar(1, 101, 105, 100.8, 104.5), bar(2, 104.5, 106, 103, 105.5)]
    g = T.fair_value_gaps(bs)
    assert g == [{"kind": "bull", "top": 103, "bottom": 101, "idx": 1, "t": bs[1]["t"], "fill": 0.0, "state": "open"}]
    bs.append(bar(3, 105, 105.5, 102, 104))                         # trades halfway into the gap
    assert T.fair_value_gaps(bs)[0]["state"] == "partial" and T.fair_value_gaps(bs)[0]["fill"] == 0.5
    bs.append(bar(4, 104, 104, 100.5, 100.8))                       # closes below the gap: it flips
    assert T.fair_value_gaps(bs)[0]["state"] == "inverted"
    assert T.fair_value_gaps(bs[:3], min_size=3) == []


def test_order_block_is_the_last_down_candle_before_the_breaking_leg():
    bs = [bar(0, 100, 101, 99, 100.5), bar(1, 100.5, 103, 100, 102.5), bar(2, 102.5, 104, 101.5, 103.5),
          bar(3, 103.5, 103.8, 101, 101.5), bar(4, 101.5, 102, 100, 100.6),
          bar(5, 100.5, 101, 99.5, 100.2),                           # the last down candle: the OB
          bar(6, 100.2, 103, 100.1, 102.8), bar(7, 102.8, 106, 102.5, 105.8), bar(8, 105.8, 107, 105, 106.5)]
    sw = T.swing_points(bs, 2, 2)
    st = T.market_structure(bs, sw)
    up = [e for e in st["events"] if e["dir"] == "up"]
    assert up and up[0]["level"] == 104
    obs = T.order_blocks(bs, st["events"])
    ob = next(o for o in obs if o["kind"] == "bull")
    assert ob["idx"] == 5 and (ob["bottom"], ob["top"]) == (99.5, 101) and ob["state"] == "fresh"
    bs.append(bar(9, 106, 106, 100.5, 101.5))                       # back into the block
    assert next(o for o in T.order_blocks(bs, st["events"]) if o["kind"] == "bull")["state"] == "tested"
    bs.append(bar(10, 101.5, 101.6, 98, 98.5))                      # closes through it: a breaker
    ob = next(o for o in T.order_blocks(bs, st["events"]) if o["kind"] == "bull")
    assert ob["state"] == "broken" and ob["breaker"]


# ── levels, candles, volume ──

def test_levels():
    p = T.pivots(110, 100, 105)
    assert p["P"] == 105 and p["R1"] == 110 and p["S1"] == 100
    assert T.pivots(110, 100, 105, "camarilla")["R3"] == pytest.approx(105 + 2.75)
    assert T.fib_levels(100, 200)["0.5"] == 150 and T.fib_levels(100, 200, up=False)["0.618"] == pytest.approx(161.8)
    zones = T.sr_zones([{"price": 100, "t": 1}, {"price": 100.2, "t": 2}, {"price": 105, "t": 3}, {"price": 100.1, "t": 4}], 0.5)
    assert zones == [{"price": pytest.approx(100.1), "low": 100, "high": 100.2, "touches": 3, "last_t": 4}]
    assert T.nearest([("PDH", 110), ("VWAP", 104), ("PDL", 95), ("X", None)], 105) == (("PDH", 110.0), ("VWAP", 104.0))
    sess = [bar(i, 100, 100 + i, 99 - i, 100) for i in range(6)]
    assert T.opening_range(sess, 15) == (102, 97) and T.opening_range(sess[:3], 15) is None
    day = 86_400_000
    daily = [{"t": T0 - k * day, "o": 1, "h": 10 + k, "l": 1, "c": 5, "v": 1} for k in range(10, 0, -1)]
    assert T.prior_session(daily, "2026-10-22", IST)["high"] == 11


def test_candle_patterns():
    assert "hammer" in T.patterns([bar(0, 100, 100.2, 97, 100.1)])
    assert "shooting_star" in T.patterns([bar(0, 100, 103, 99.9, 99.95)])
    assert "bull_engulfing" in T.patterns([bar(0, 101, 101.2, 99.8, 100), bar(1, 99.9, 101.6, 99.7, 101.5)])
    assert "inside_bar" in T.patterns([bar(0, 100, 105, 95, 102), bar(1, 101, 104, 96, 103)])
    assert "doji" in T.patterns([bar(0, 100, 101, 99, 100.05)])


def test_volume_profile_and_curve():
    bs = [bar(0, 100, 101, 100, 101, v=10), bar(1, 101, 102, 101, 102, v=1000), bar(2, 102, 103, 102, 103, v=10)]
    vp = T.volume_profile(bs, bins=3)
    assert 101 <= vp["poc"] <= 102 and vp["val"] <= vp["poc"] <= vp["vah"]
    day2 = [{**b, "t": b["t"] + 86_400_000} for b in bs]
    curve = T.volume_curve(bs + day2, IST, 5)
    assert curve[9 * 60 + 20] == 10 and curve[9 * 60 + 25] == 1010 and curve[9 * 60 + 30] == 1020
    assert T.relative_volume(2020, curve, 9 * 60 + 25) == 2.0


# ── summary ──

def test_read_and_brief():
    bs = bars_from(UP_THEN_BREAK_DOWN * 3)
    r = T.read(bs, tz=IST)
    assert set(r) >= {"trend", "bias", "last_break", "fvgs", "order_blocks", "liquidity", "sweep", "range", "patterns"}
    assert isinstance(T.brief(r, bs[-1]["c"]), str) and T.read(bs[:4]) == {} and T.brief({}, 1) == "-"
