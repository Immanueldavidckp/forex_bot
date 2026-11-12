"""fib_trend: the class's two Fib rules (video 5), on his own example (gold 2 h, 26–28 Aug 2025) and on small series"""
import json
import os

from engine import fib_book, fib_trend as F

HERE = os.path.dirname(os.path.abspath(__file__))


def gold():
    with open(os.path.join(HERE, "testdata", "fib_gold_h2_2025-08.json")) as f:
        return [{"t": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4]} for r in json.load(f)["rows"]]


def test_his_class_trade_28_aug_2025():
    """his chart (video ~1:09:00): 0 = 3373.77, 1 = 3393.69, stop 3377.47, target 1.618 = 3406.06 (OANDA prices);
    on FxPro's bars the same swing: 1 = 3394.11, 0 = 3373.81, stop 3377.47 to the cent, a win"""
    bars = gold()
    s = [s for s in F.setups(bars) if s["status"] == "won" and abs(s["H"] - 3394.11) < 0.01][0]
    assert (s["side"], s["swing"]) == ("buy", 2)
    assert abs(s["L"] - 3373.81) < 0.01
    assert abs(s["levels"]["0.618"] - 3386.36) < 0.01
    assert abs(s["sl"] - 3377.47) < 0.01                       # 0.236 − 0.1 ATR
    assert abs(s["tp"] - (3373.81 + 1.618 * (3394.11 - 3373.81))) < 1e-6
    assert s["entry"] == bars[s["touch_idx"]]["h"]            # the 0.618 candle's high, hit by the next candle
    assert s["entry_idx"] == s["touch_idx"] + 1 and s["rr"] >= 1


def test_ema_cross_back_means_no_trade():
    for s in F.setups(gold()):
        if s["cross_back_idx"] is not None and s["entry_idx"] is not None:
            assert s["cross_back_idx"] > s["entry_idx"]           # rule 5: never an entry after the EMAs crossed back


def test_only_the_second_swing():
    assert {s["swing"] for s in F.setups(gold())} == {2}


def _series(points, step=1.0):
    """a zigzag through the given prices, one candle per `step` of price, wicks ±0.2"""
    out, t = [], 0
    for a, b in zip(points, points[1:]):
        n = max(1, int(abs(b - a) / step))
        for k in range(n):
            o, c = a + (b - a) * k / n, a + (b - a) * (k + 1) / n
            out.append({"t": t, "o": o, "h": max(o, c) + 0.2, "l": min(o, c) - 0.2, "c": c})
            t += 1
    return out


def test_retracement_limit_at_0618_stop_0236_target_1():
    # down, CHoCH up, BOS up (swing 2), pullback to 0.618 then up through the high
    bars = _series([130, 100, 112, 106, 125, 118, 140, 132, 150, 128, 160])
    rs = F.retrace_setups(bars, n=3, mode="every")
    assert rs, "no BOS leg found"
    for s in rs:
        assert abs(s["entry_level"] - F.fib(s["H"], s["L"], 0.618)) < 1e-9
        assert abs(s["sl"] - F.fib(s["H"], s["L"], 0.236)) < 1e-9 and s["tp"] == s["H"]
    done = [s for s in rs if s["status"] in ("won", "lost")]
    assert done and all(s["entry_idx"] > s["h_idx"] for s in done)


def test_retrace_safety_swings():
    bars = _series([130, 100, 112, 106, 125, 118, 140, 132, 150, 140, 165, 155, 180, 170, 195, 185, 210])
    assert {s["swing"] for s in F.retrace_setups(bars, n=3)} <= {2, 3, 6}


def test_book_levels_buy_stop_and_market():
    s = {"side": "buy", "mark": 100.0, "entry_level": 99.0, "sl": 97.0, "tp": 106.0}
    info = {"digits": 2, "point": 0.01, "trade_stops_level": 0}
    lv = fib_book.levels("trend", s, {"bid": 99.0, "ask": 99.1}, info)
    assert (lv["price"], lv["sl"], lv["tp"], lv["market"]) == (100.1, 97.0, 106.0, False)   # a stop at the mark + spread
    lv = fib_book.levels("trend", s, {"bid": 100.5, "ask": 100.6}, info)
    assert lv["market"] and lv["price"] == 100.6                                            # already through: at once
    assert "why" in fib_book.levels("retrace", s, {"bid": 98.5, "ask": 98.6}, info)         # past the limit: no chase


# ── the live versions + the reject checklist (fib_reject.py) ──
def test_live_versions_are_2r_with_the_stop_beyond_the_swing_low():
    from engine import fib_reject as FR
    bars = gold()
    for rule in ("trend", "retrace"):
        done = [s for s in FR.setups(rule, bars) if s["status"] in ("won", "lost")]
        assert done
        for s in done:
            sg = 1 if s["side"] == "buy" else -1
            assert (s["L"] - s["sl"]) * sg > 0                                   # the stop is beyond the swing low (Fib 0)
            assert abs(abs(s["tp"] - s["entry"]) / abs(s["entry"] - s["sl"]) - 2) < 1e-6
    r = [s for s in FR.setups("retrace", bars) if s["entry_idx"] is not None][0]
    assert abs(r["entry_level"] - F.fib(r["H"], r["L"], 0.382)) < 1e-9


def test_reject_checklist_counts_warnings():
    from engine import fib_reject as FR
    bars = gold()
    ctx = FR.context(bars)
    s = {"side": "buy", "sl": 3370.0, "H": 3394.0, "L": 3373.8, "h_idx": 300, "swing": 2}
    j = next(i for i, b in enumerate(bars) if i > 310 and FR.session(b["t"]) == "London" and (b["t"] // 86400_000 + 3) % 7 == 2)
    assert FR.warnings("trend", "GOLD", s, bars, ctx, j, 3390.0, spread=0.3) == []            # 0.3 / 20 = 1.5 % of the stop
    w = FR.warnings("trend", "CADCHF", s, bars, ctx, j, 3390.0, spread=5.0)                   # bad market + spread 25 %
    assert len(w) == 2 and w[0] == "market CADCHF" and "spread" in w[1]
    asia = next(i for i, b in enumerate(bars) if i > 310 and FR.session(b["t"]) == "Asia")
    assert any("Asia" in x for x in FR.warnings("trend", "GOLD", s, bars, ctx, asia, 3390.0, spread=0.3))
    assert FR.REJECT["trend"]["need"] == 1 and FR.REJECT["retrace"]["need"] == 2


def test_judged_marks_rejected():
    from engine import fib_reject as FR
    for s in FR.judged("retrace", "CADCHF", gold()):
        assert s["rejected"] == (len(s["warnings"]) >= 2)
