"""sd_david: the class rule (video 6), on the bars of the picture class6_demand.png"""
from engine import sd_david

PIC = [(100, 102, 98, 101), (101, 106, 100, 105), (105, 110, 104, 109), (109, 111, 105, 106),
       (106, 107, 101, 102), (102, 103, 97, 98), (98, 99, 95, 96), (96, 107, 95.5, 106), (106, 110, 102, 109),
       (109, 115, 108, 114), (114, 117, 112, 116), (116, 117, 108, 109), (109, 110, 103, 104), (104, 105, 99, 100),
       (100, 108, 99.5, 107)]


def bars(rows, flip=False):
    f = (lambda p: 220 - p) if flip else (lambda p: p)
    return [{"t": i, "o": f(o), "h": f(l) if flip else h, "l": f(h) if flip else l, "c": f(c)} for i, (o, h, l, c) in enumerate(rows)]


def events(flip=False, kind="BOS"):
    side = "sell" if flip else "buy"
    return {"events": [{"kind": kind, "side": side, "origin": {"idx": 6}, "idx": 9, "level": 220 - 111 if flip else 111, "level_idx": 3}]}


def test_demand_is_candle_a_below_the_gap():
    zs = sd_david.zones(bars(PIC), events())
    assert len(zs) == 1 and zs[0]["valid"]                # one zone per BOS: the first gap from the leg's start
    z = zs[0]
    assert [g["a"] for g in z["others"]] == [7]           # the leg's second gap (107 → 108) is kept, not drawn
    assert (z["side"], z["a"], z["top"], z["bottom"], z["proximal"], z["distal"], z["mid"]) == ("demand", 6, 99, 95, 99, 95, 97)
    assert (z["fvg"]["bottom"], z["fvg"]["top"]) == (99, 102)
    assert z["touch_idx"] == 13 and z["status"] == "tested" and z["live"]


def test_supply_is_candle_a_above_the_gap():
    z = [z for z in sd_david.zones(bars(PIC, True), events(True)) if z["valid"]][0]
    assert (z["side"], z["a"], z["bottom"], z["top"], z["proximal"], z["distal"]) == ("supply", 6, 121, 125, 121, 125)
    assert z["touch_idx"] == 13


def test_choch_gives_no_zone():
    assert sd_david.zones(bars(PIC), events(kind="CHoCH")) == []


def test_no_gap_no_zone():
    rows = list(PIC)
    rows[8] = (106, 110, 98.5, 109)                       # C's wick now touches A's high → no gap
    rows[9] = (109, 115, 106, 114)                        # and the second gap (A=7) closed too
    z = sd_david.zones(bars(rows), events())
    assert len(z) == 1 and not z[0]["valid"] and z[0]["why"].startswith("no gap")


def test_4th_candle_fills_the_gap():
    rows = list(PIC)
    rows[9] = (109, 115, 98.8, 114)                       # the candle after C reaches A's high
    z = sd_david.zones(bars(rows), events())
    assert len(z) == 1 and not z[0]["valid"] and "4th" in z[0]["why"]   # both gaps die: 98.8 fills 99 and 107


def test_broken_on_close_through_the_far_edge():
    rows = list(PIC) + [(100, 101, 93, 94)]
    z = [x for x in sd_david.zones(bars(rows), events()) if x["valid"]][0]
    assert z["status"] == "broken" and not z["live"]


def test_fib_targets_from_entry_to_the_recent_high():
    z = sd_david.zones(bars(PIC), events())[0]
    assert z["fib_ext"] == 117                            # leg high before price came back (bar 10/11)
    assert [round(t["price"], 3) for t in z["targets"]] == [round(117 + f * (99 - 117), 3) for f in (0.618, 0.5, 0.382)]
    assert z["targets"][2]["price"] > z["targets"][0]["price"] > 99   # T3 is the farthest, all above the entry


def test_supply_targets_go_down():
    z = sd_david.zones(bars(PIC, True), events(True))[0]
    assert z["fib_ext"] == 103 and all(t["price"] < 121 for t in z["targets"])
