"""engine/test_concepts.py — rows 2–8 of the /smc concept table on hand-made candles: sessions, trend lines, chart
patterns, indicators, volume profile, Wyckoff, Elliott (candles: test_candles.py)."""
import datetime as dt

from engine import chart_patterns, elliott, indicators, levels, trendlines, volume_profile, wyckoff
from engine.major_structure import atr14

M15 = 900_000


def _path(pts, t0=0, step=M15, wick=0.1):
    """bars along a piecewise-linear close path [(bar, price), ...]: open = the previous close"""
    closes = []
    for (i0, p0), (i1, p1) in zip(pts, pts[1:]):
        closes += [p0 + (p1 - p0) * (k / (i1 - i0)) for k in range(i1 - i0)]
    closes.append(pts[-1][1])
    bars = []
    for i, c in enumerate(closes):
        o = closes[i - 1] if i else c
        bars.append({"t": t0 + i * step, "o": o, "h": max(o, c) + wick, "l": min(o, c) - wick, "c": c, "v": 0.0})
    return bars


# ── row 2: sessions follow their own summer time ──

def _day_bars(day):
    t0 = int(dt.datetime(*day, 0, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
    return [{"t": t0 + i * M15, "o": 1.0, "h": 1.0 + (i % 7) * 0.01, "l": 1.0 - (i % 5) * 0.01, "c": 1.0, "v": 1.0} for i in range(96 * 2)]


def test_sessions_move_with_summer_time():
    for day, london_utc, ny_utc, asia_utc in (((2026, 7, 14), 7, 12, 0), ((2026, 12, 14), 8, 13, 1)):
        bars = _day_bars(day)
        s = levels.sessions(bars, atr14(bars))["sessions"]
        first = lambda key: next(x for x in s if x["key"] == key and x["date"] == f"{day[0]}-{day[1]:02d}-{day[2]:02d}")
        hour = lambda x: dt.datetime.fromtimestamp(bars[x["first"]]["t"] / 1000, dt.timezone.utc).hour
        assert hour(first("london")) == london_utc and hour(first("ny")) == ny_utc
        asia = first("asia")                                         # 20:00 New York, the evening before UTC's next day
        assert hour(asia) == asia_utc and asia["last"] - asia["first"] == 15 and asia["final"]


def test_pullback_depth_and_its_class():
    bars = _path([(0, 100), (20, 110), (30, 105)])
    m = {"trend": "up", "protected": {"idx": 0, "price": 99.9}, "events": []}
    pb = levels.pullback(bars, m)
    assert pb["extreme"] == 110.1 and abs(pb["deepest"] - (110.1 - 104.9) / (110.1 - 99.9)) < 1e-4 and pb["class"] == "normal"


# ── row 4: a rising support line, touched a third time, then broken ──

def test_support_trend_line_touches_and_break():
    bars = _path([(0, 104), (20, 100), (30, 106), (40, 102), (50, 108), (60, 104), (70, 110), (90, 95)])
    A = atr14(bars)
    out = trendlines.trendlines(bars, {"protected": None}, A)
    ln = next(x for x in out["lines"] if x["side"] == "support" and (x["b1"], x["b2"]) == (20, 40))
    assert 60 in ln["touches"] and ln["confirmed"]
    assert ln["status"] == "broken" and ln["held"] and 75 <= ln["break_idx"] <= 79


# ── row 5: a double top confirmed through its valley; the mirror is a double bottom ──

def _double_top():
    return _path([(0, 100), (30, 110), (50, 120), (65, 110), (80, 120.2), (100, 105)])


def test_double_top_confirms_through_the_valley():
    bars = _double_top()
    P = [p for p in chart_patterns.patterns(bars, atr14(bars), "M15") if p["pattern"] == "double top"]
    assert len(P) == 1
    p = P[0]
    assert [q["idx"] for q in p["points"]] == [50, 65, 80] and p["known_idx"] == 85
    assert p["status"] == "running" and 85 < p["confirm_idx"] < 95 and p["confirm_price"] < 109.9
    assert abs(p["target"] - (p["confirm_price"] - (120.3 - 109.9))) < 1e-9


def test_mirrored_double_top_is_a_double_bottom():
    bars = [{"t": b["t"], "o": 200 - b["o"], "h": 200 - b["l"], "l": 200 - b["h"], "c": 200 - b["c"]} for b in _double_top()]
    P = [p for p in chart_patterns.patterns(bars, atr14(bars), "M15") if p["pattern"] == "double bottom"]
    assert len(P) == 1 and P[0]["side"] == "bull" and P[0]["status"] == "running" and P[0]["confirm_price"] > 90.1


# ── row 6: RSI / MACD / ATR edge cases, divergence, VWAP ──

def test_rsi_macd_atr_on_simple_series():
    up = [100.0 + i for i in range(40)]
    assert indicators.rsi(up)[-1] == 100.0 and indicators.rsi([5.0] * 40)[-1] == 50.0 and indicators.rsi(up)[13] is None
    assert indicators.macd([7.0] * 60)["macd"][-1] == 0.0
    assert indicators.rma([2.0] * 30, 14)[-1] == 2.0 and indicators.sma([1.0, 2.0, 3.0], 2) == [None, 1.5, 2.5]


def test_regular_bullish_divergence_on_oscillator_pivots():
    osc = [50.0] * 50
    for p, v in ((10, 30.0), (30, 40.0)):
        for k in range(-4, 5):
            osc[p + k] = min(osc[p + k], v + abs(k) * 2)
    bars = [{"t": i, "o": 110, "h": 111, "l": 110 - (10 if i == 10 else 15 if i == 30 else 0), "c": 110} for i in range(50)]
    [d] = indicators.divergences(bars, osc, "RSI")
    assert (d["kind"], d["idx"], d["prev_idx"], d["known"], d["invalid_idx"]) == ("regular bull", 30, 10, 35, None)


def test_vwap_resets_on_the_server_day():
    t0 = int(dt.datetime(2026, 10, 27, 21, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)   # 23:00 server; its day ends at 22:00 UTC
    bars = [{"t": t0 + i * 3_600_000, "o": p, "h": p, "l": p, "c": p, "v": v} for i, (p, v) in enumerate(((10, 1), (20, 3), (30, 1)))]
    v = indicators.vwap(bars, {"protected": None})
    assert v["session"]["vwap"] == [10, 20, 22.5] and v["starts"] == [1]                  # (20·3 + 30·1) / 4


# ── row 7: POC, value area by the two-row step ──

def test_volume_profile_poc_and_value_area():
    bars = [{"t": 0, "o": 10, "h": 18, "l": 10, "c": 18, "v": 320.0},       # 10 per 0.25 row
            {"t": 1, "o": 12, "h": 12.5, "l": 12, "c": 12.5, "v": 200.0},     # +100 in 12.00–12.25 and 12.25–12.50
            {"t": 2, "o": 12.25, "h": 12.5, "l": 12.25, "c": 12.5, "v": 50.0}]
    p = volume_profile._profile(bars, 0, 2, 0.25, True)
    assert p["poc"] == 12.375 and p["val"] == 11.75 and p["vah"] == 15.5 and p["hvn"] == []


def test_row_size_is_a_fixed_price_unit():
    assert volume_profile.row_size([{"c": 4050.0}], "M15") == 0.5 and volume_profile.row_size([{"c": 1.115}], "M5") == 0.0001
    assert volume_profile.row_size([{"c": 157.4}], "H1") == 0.04


# ── row 8: a Wyckoff accumulation SC → AR → ST → Spring → SOS → LPS → markup ──

def test_wyckoff_accumulation_runs_through_its_phases():
    bars = _path([(0, 130), (40, 100), (50, 105), (60, 100.2), (70, 105), (79, 100.6), (80, 100.5), (95, 107), (100, 106.2), (115, 110)])
    bars[80] = dict(bars[80], l=99.0, c=100.5)                        # the spring: a wick under the support, closed back in
    m = {"points": [{"idx": 0, "price": 130.1, "kind": "high", "t": 0}, {"idx": 40, "price": bars[40]["l"], "kind": "low", "t": 0}]}
    out = wyckoff.wyckoff(bars, m, atr14(bars), "M15")
    [r] = [x for x in out["ranges"] if x["kind"] == "accumulation"]
    assert [e["label"] for e in r["events"]] == ["SC", "AR", "ST", "Spring", "SOS", "LPS", "markup"]
    assert r["phase"] == "E" and r["status"] == "markup" and r["schematic"] == 1 and not out["volume"]
    assert [e["idx"] for e in r["events"]][:4] == [40, 50, 60, 80]


# ── row 8: Elliott hard rules ──

def _pts(prices, first="low"):
    kinds = ("low", "high") if first == "low" else ("high", "low")
    return [{"idx": i * 10, "t": i, "price": p, "kind": kinds[i % 2]} for i, p in enumerate(prices)]


def test_elliott_impulse_rules():
    A = [1.0] * 100
    c = elliott.impulse(_pts([100, 110, 104, 120, 113, 125]), A)
    assert c["pattern"] == "impulse" and c["side"] == "bull" and c["ratios"]["w2/w1"] == 0.6 and c["invalidation"] == 110
    assert elliott.impulse(_pts([100, 110, 99, 120, 113, 125]), A) is None              # R1: wave 2 beyond the start
    assert elliott.impulse(_pts([100, 110, 104, 112, 111, 125]), A) is None             # R2: wave 3 the shortest
    assert elliott.impulse(_pts([100, 110, 104, 120, 109, 125]), A) is None             # R3: wave 4 in wave 1, no diagonal
    assert elliott.impulse(_pts([100, 110, 104, 120, 109, 127]), A)["pattern"] == "diagonal"   # expanding
    assert elliott.impulse(_pts([125, 113, 120, 104, 110, 100], "high"), A)["side"] == "bear"


def test_elliott_corrections():
    z = elliott.correction(_pts([125, 112, 120, 108], "high"))
    assert z["pattern"] == "zigzag" and z["b_retrace"] == 0.615 and z["c_vs_a"] == 0.923
    f = elliott.correction(_pts([125, 112, 124.5, 111], "high"))
    assert f["pattern"] == "flat" and f["b_retrace"] == 0.962
    assert elliott.correction(_pts([125, 112, 120, 113], "high")) is None               # a zigzag's C must pass A's end
