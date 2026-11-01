"""engine/test_major_structure.py — David's structure rule (his TradingView sketch, 2026-10-28)."""
from engine.major_structure import major_structure


def _events(s):
    """(kind, side, level) with the level at the turning point (the candles' wicks reach 0.5 beyond it)"""
    return [(e["kind"], e["side"], round(e["level"] + (0.5 if e["side"] == "sell" else -0.5))) for e in s["events"]]


def _path(prices, per_leg=8):
    """Candles walking straight from each turning point to the next (per_leg candles a leg)."""
    bars, t = [], 0
    for a, b in zip(prices, prices[1:]):
        for k in range(per_leg):
            o, c = a + (b - a) * k / per_leg, a + (b - a) * (k + 1) / per_leg
            bars.append({"t": t, "o": o, "h": max(o, c) + 0.5, "l": min(o, c) - 0.5, "c": c})
            t += 1
    return bars


# the sketch, bottom to top: three higher highs (each one a BOS), the higher low 425, the top 720, a fall through
# 425 (CHoCH) to 285, then a rally with three higher internal highs 480 / 595 / 660 — not marked — through the top
SKETCH = [95, 310, 180, 450, 285, 570, 425, 720, 285, 480, 385, 595, 460, 660, 535, 785]


def test_the_sketch_gives_three_bos_and_two_choch_and_no_internal_breaks():
    s = major_structure(_path(SKETCH), n=3)
    got = _events(s)
    assert got == [("BOS", "buy", 310), ("BOS", "buy", 450), ("BOS", "buy", 570),
                   ("CHoCH", "sell", 425), ("CHoCH", "buy", 720)]
    # the first CHoCH's move came from the top; the second from the low after it
    assert s["events"][3]["origin"]["price"] == 720.5 and s["events"][4]["origin"]["price"] == 284.5
    assert s["trend"] == "up" and s["protected"]["price"] == 284.5


def test_after_a_choch_a_new_low_is_a_bos_and_its_lower_high_becomes_protected():
    # … top 720, CHoCH down through 425 to 285, lower high 400, lower low 200 (BOS through 285), rally to 390:
    # below the protected lower high 400, so nothing; through it = CHoCH
    s = major_structure(_path([95, 310, 180, 450, 285, 570, 425, 720, 285, 400, 200, 390, 300, 520]), n=3)
    got = _events(s)
    assert got[3:] == [("CHoCH", "sell", 425), ("BOS", "sell", 285), ("CHoCH", "buy", 400)]


def test_a_break_needs_a_close_not_a_wick():
    bars = _path([100, 300, 200, 420, 330])
    at300 = lambda s: [e for e in s["events"] if abs(e["level"] - 300.5) < 1e-9]
    assert at300(major_structure(bars, n=3))                         # the rally closes through 300: BOS
    wick = [dict(b) for b in bars]
    for b in wick[16:]:                                               # the same rally, every close kept under 300
        b["o"], b["c"] = min(b["o"], 299.0), min(b["c"], 299.0)
        b["l"] = min(b["l"], b["o"], b["c"])
    assert not at300(major_structure(wick, n=3))                     # only wicks above it: no break


def test_zigzag_points_alternate():
    pts = major_structure(_path(SKETCH), n=3)["points"]
    assert all(a["kind"] != b["kind"] for a, b in zip(pts, pts[1:]))
    assert [q["kind"] for q in pts[-2:]] == ["low", "high"] and pts[-1]["price"] == 785.5   # ends at the last leg's top


def test_a_small_bounce_is_internal_not_a_level():
    # down: 400 broken (BOS), a 30-point bounce 300 → 330 (under 3 ATR), lower low 250, rally to 380 — above the
    # bounce's high 330 but under the protected high 550 — then 200. The bounce is internal: no BOS at 300 and
    # no CHoCH at 330 (EURUSD M15 10-12 → 10-14, where David kept the trend down)
    path = [700, 400, 550, 300, 330, 250, 380, 200]
    assert _events(major_structure(_path(path), n=3)) == [("BOS", "sell", 400), ("BOS", "sell", 250)]
    without = _events(major_structure(_path(path), n=3, pullback_atr=0, margin_atr=0))   # the old rule:
    assert ("BOS", "sell", 300) in without and any(k == "CHoCH" and s == "buy" for k, s, _ in without)   # false CHoCH
