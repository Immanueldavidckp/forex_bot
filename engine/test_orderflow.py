"""engine/test_orderflow.py — the order-flow chart (engine/orderflow.py) on the worked examples of the platforms'
own documentation (collected and checked by the research agent, 2026-10-29) and on made-up tick sequences."""
import datetime as dt

import numpy as np

from engine import orderflow as O


def table(rows):
    """{row: (sell, buy)} (row 0 = the lowest) → cells()."""
    n = max(rows) + 1
    sell = np.array([rows.get(r, (0, 0))[0] for r in range(n)], float)
    buy = np.array([rows.get(r, (0, 0))[1] for r in range(n)], float)
    return O.cells(sell, buy, np.cumsum(buy - sell))


def test_atas_blog_six_bid_imbalances_at_300_percent():
    """atas.net/blog/how-to-find-and-trade-imbalance: each bid vs the ask one level higher — 116/26, 86/8, 58/18,
    64/15, 218/67, 190/49 — all ≥ 300 % → six sell imbalances, one stacked sell zone."""
    f = table({7: (0, 26), 6: (116, 8), 5: (86, 18), 4: (58, 15), 3: (64, 67), 2: (218, 49), 1: (190, 30), 0: (40, 20)})
    assert f["is"] == [1, 2, 3, 4, 5, 6] and f["ib"] == [] and f["stack_sell"] == [(1, 6)]


def test_tradingview_help_buy_imbalance_is_diagonal():
    """TradingView footprint help: "506.37 ('buy') ≥ (300 / 100) × 166.433 ('sell')" one level below → buy imbalance."""
    assert table({2: (10, 506.37), 1: (166.433, 10), 0: (10, 10)})["ib"] == [2]
    assert table({2: (10, 499.0), 1: (166.433, 10), 0: (10, 10)})["ib"] == []


def test_zero_opposite_cell_and_the_edges_are_no_comparison():
    """Sierra / flowsurface: nothing to compare with a 0 cell; the top bid and the bottom ask are never compared."""
    f = table({2: (0, 50), 1: (0, 40), 0: (10, 0)})
    assert f["ib"] == [1] and f["is"] == []          # 40 ≥ 3 × 10 below; 50 vs a 0 sell below it is no comparison


def test_ticks_to_a_bar():
    # bid in points, row = 1 point: up, up, down, flat, up → +1 at 101, +1 at 102, −1 at 101, 0, +1 at 102
    t = np.arange(6, dtype=np.int64) * 1000
    bid = np.array([100, 101, 102, 101, 101, 102], dtype=np.int64)
    f = O.footprints(t, bid, [0], 300_000, 1)[0]
    assert f["r0"] == 101 and f["sell"] == [1, 0] and f["buy"] == [1, 2]
    assert f["vol"] == 4 and f["delta"] == 2 and f["dmax"] == 2 and f["dmin"] == 0
    assert f["poc"] == 0 and f["va"] == [0, 1]       # 2 = 2: the tie goes to the row nearest the middle, then the lower


def test_ticks_go_to_the_chart_bars_own_times():
    """FxPro's H4 bars open at 22:00 / 02:00 UTC, not on 4-hour multiples of UTC: the chart's times decide."""
    H, h4 = 3_600_000, 14_400_000
    bars = [22 * H, 26 * H]                          # 22:00 and 02:00 UTC
    t = np.array([22 * H + 1, 25 * H, 26 * H + 5, 29 * H], dtype=np.int64)
    bid = np.array([10, 11, 12, 13], dtype=np.int64)
    f = O.footprints(t, bid, bars, h4, 1)
    assert f[0]["vol"] == 1 and f[1]["vol"] == 2     # 25:00 = 01:00 belongs to the 22:00 bar, 26:00 starts the next


def test_cvd_resets_at_the_fxpro_server_day():
    # server = Cyprus time: 2026-10-29 21:55 UTC is 23:55 there, 22:00 UTC is midnight
    t0 = int(dt.datetime(2026, 10, 29, 21, 50, tzinfo=dt.timezone.utc).timestamp() * 1000)
    bar_t = [t0, t0 + 300_000, t0 + 600_000]
    fps = [{"delta": 5, "dmax": 6, "dmin": -1}, {"delta": 3, "dmax": 3, "dmin": 0}, {"delta": -2, "dmax": 1, "dmin": -4}]
    assert O.cvd(fps, bar_t) == [[0, 6, -1, 5], [5, 8, 5, 8], [0, 1, -4, -2]]


def test_stacked_zone_touched_by_a_wick_broken_by_a_close():
    rows = [[0, 10, 12, 9, 11], [1, 11, 13, 10.4, 12], [2, 12, 12.5, 9.5, 10], [3, 10, 10.5, 8, 8.5]]
    fps = [{"r0": 9, "stack_buy": [(0, 2)], "stack_sell": []}, None, None, None]   # rows 9..11 points → zone 9–12
    z = O.zones(fps, rows, 1, 1.0)[0]
    assert (z["lo"], z["hi"], z["status"]) == (9, 12, "broken") and z["t_touch"] == 1 and z["t_end"] == 3


def test_row_size_is_median_range_over_12_on_a_125_step():
    rows = [[0, 0, 4003.0, 4000.0, 0]] * 5            # 3 $ range → 0.25 → 0.2 $ on gold (point 0.01)
    assert O.row_points(rows, 0.01) == 20


def test_cvd_divergence_needs_a_higher_high_with_lower_cvd_on_the_same_day():
    t0 = int(dt.datetime(2026, 10, 29, 6, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
    highs = [10, 11, 12, 15, 12, 11, 10, 11, 12, 16, 12, 11, 10, 9, 17]          # pivot highs at 3 (15) and 9 (16)
    rows = [[t0 + i * 300_000, h - 1, h, h - 2, h - 0.5] for i, h in enumerate(highs)]
    cvd_close = [0, 5, 10, 40, 30, 20, 10, 15, 20, 25, 20, 15, 10, 5, 50]       # CVD 40 at the 1st, 25 at the 2nd
    cv = [[0, c, c, c] for c in cvd_close]
    d = O.divergences(rows, cv, [r[0] for r in rows])
    assert [(x["side"], x["p1"], x["p2"], x["c1"], x["c2"]) for x in d] == [("bear", 15, 16, 40, 25)]
    assert d[0]["t_known"] == rows[12][0] and d[0]["t_invalid"] == rows[14][0]   # the 17-high bar closes above 16


def test_spike_is_1_5_times_the_20_bars_before():
    fps = [{"vol": 100}] * 20 + [{"vol": 149}, {"vol": 160}]
    assert O.spikes(fps) == [21]
