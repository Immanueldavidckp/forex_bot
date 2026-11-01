"""engine/test_supply_demand.py — supply / demand, only the valid zones (engine/supply_demand.py), on toy series built
from published worked examples (therighttrader's practice numbers, Dukascopy's EUR/USD example — reproduced by the
research agent 2026-10-30) and David's gate: no major BOS / CHoCH from the move out → not valid."""
from engine import supply_demand as S
from engine.major_structure import major_structure

T0 = 1_790_000_000_000


def series(spec):
    return [{"t": T0 + i * 900_000, "o": o, "h": h, "l": l, "c": c} for i, (o, h, l, c) in enumerate(spec)]


def toy_demand(breaks=True):
    """Base 100–104 after a drop from a confirmed 112 swing high; the move out closes above 112 (BOS) on its way to 130,
    then price returns to 104 (therighttrader). breaks=False: the move out stops at 111 and comes back."""
    s = [(108, 109.5, 106.5, 108.5) if i % 2 == 0 else (108.5, 110, 107, 108) for i in range(20)]
    s += [(108, 110.5, 107.5, 109.8), (109.8, 111.5, 109, 111), (111, 112, 110, 111.5)]
    s += [(111.5, 111.8, 110, 110.5), (110.5, 111, 109, 109.5), (109.5, 110, 108, 108.5),
          (108.5, 109, 106.8, 107.2), (107.2, 107.8, 105.5, 106), (106, 106.5, 104.2, 104.7)]
    s += [(103.5, 104, 100, 102), (102, 104, 100.2, 101.5), (101.5, 103.5, 100, 103)]
    if breaks:
        s += [(103, 113, 102.8, 112.8), (112.8, 122, 112.5, 121.5), (121.5, 130, 121, 129.5)]
        s += [(129.5, 130, 125, 126), (126, 127, 120, 121), (121, 122, 114, 115), (115, 116, 108, 109), (109, 110, 104, 105)]
        s += [(105, 109, 104.8, 108.5), (108.5, 112, 108, 111.5)]
    else:
        s += [(103, 110.5, 102.8, 110.2), (110.2, 111, 109, 109.5), (109.5, 110, 106, 106.5), (106.5, 107, 103, 103.5)]
        s += [(103.5, 104.5, 102.5, 103.5)] * 8
    return series(s)


def test_the_worked_demand_zone():
    bars = toy_demand()
    m = major_structure(bars, 5)
    v = [z for z in S.zones(bars, m) if z["valid"]]
    assert len(v) == 1
    z = v[0]
    assert (z["side"], z["bottom"], z["top"], z["entry"], z["kind"], z["base_n"]) == ("buy", 100, 104, 103.5, "DBR", 3)
    assert z["disp_mult"] >= 1.5 and z["fvg"] is not None
    assert z["status"] == "tested" and z["touches"] == 1 and z["touch_idx"] > z["break_idx"]    # known from the break on


def test_no_bos_from_the_move_out_means_not_valid():
    bars = toy_demand(breaks=False)
    m = major_structure(bars, 5)
    zs = S.zones(bars, m)
    assert not m["events"] and not any(z["valid"] for z in zs)
    assert any("no major BOS" in (z["why"] or "") for z in zs)
    assert S.page(bars, m)["zones"] == []


def test_dukascopy_eurusd_demand_is_fresh_and_ran_7_5_box_heights():
    s = [(1.0900, 1.0912, 1.0888, 1.0903) if i % 2 == 0 else (1.0903, 1.0915, 1.0890, 1.0900) for i in range(20)]
    s += [(1.0900, 1.0930, 1.0895, 1.0928), (1.0928, 1.0950, 1.0920, 1.0948), (1.0948, 1.0960, 1.0940, 1.0955)]
    s += [(1.0955, 1.0958, 1.0935, 1.0938), (1.0938, 1.0940, 1.0915, 1.0918), (1.0918, 1.0920, 1.0895, 1.0898),
          (1.0898, 1.0900, 1.0878, 1.0880), (1.0880, 1.0882, 1.0862, 1.0865)]
    s += [(1.0865, 1.0870, 1.0850, 1.0858), (1.0858, 1.0869, 1.0851, 1.0862), (1.0862, 1.0870, 1.0850, 1.0856)]
    s += [(1.0856, 1.0950, 1.0855, 1.0945), (1.0945, 1.1000, 1.0940, 1.0995), (1.0995, 1.1020, 1.0990, 1.1015)]
    s += [(1.1015, 1.1018, 1.0990, 1.0995)] * 6
    bars = series(s)
    m = major_structure(bars, 5)
    v = [z for z in S.zones(bars, m) if z["valid"]]
    assert len(v) == 1 and abs(v[0]["bottom"] - 1.0850) < 1e-9 and abs(v[0]["top"] - 1.0870) < 1e-9
    assert v[0]["status"] == "fresh" and v[0]["kind"] == "DBR" and abs(v[0]["run_zone_heights"] - 7.5) < 0.05
    p = S.page(bars, m)["zones"][0]
    assert p["side"] == "demand" and p["live"] and p["t_break"] > p["t0"]
