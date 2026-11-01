#!/usr/bin/env python3
"""verify.py — toy reproductions of published worked examples + internal checks for sd_proto.zones"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # sd_proto.py next to this file
sys.path.insert(0, "/home/david/forex/engine")                        # David's structure rule, read-only
import sd_proto as P
from major_structure import major_structure

T0 = 1_790_000_000_000
def bar(i, o, h, l, c):
    return {"t": T0 + i * 900_000, "o": o, "h": h, "l": l, "c": c}

def series(spec):
    """spec: list of (o,h,l,c)"""
    return [bar(i, *r) for i, r in enumerate(spec)]

def toy_demand():
    """therighttrader practice numbers: demand base 100-104, rally to 130, return to 104.
    Built so David's gate fires: a confirmed swing high at 112 (5 bars each side, 3-ATR pullback), the base, then the
    leg-out closes above 112 (= major BOS buy) on its way to 130."""
    s = []
    # 20 flat bars around 108 (ATR ~1), then a leg up to 112 (the swing high), pullback to the base at 100-104
    for i in range(20):                                                                               # ATR ~3 (a "26-point leave" instrument)
        s.append((108, 109.5, 106.5, 108.5) if i % 2 == 0 else (108.5, 110, 107, 108))
    s += [(108, 110.5, 107.5, 109.8), (109.8, 111.5, 109, 111), (111, 112, 110, 111.5)]            # up to 112 (idx 22)
    s += [(111.5, 111.8, 110, 110.5), (110.5, 111, 109, 109.5), (109.5, 110, 108, 108.5),
          (108.5, 109, 106.8, 107.2), (107.2, 107.8, 105.5, 106), (106, 106.5, 104.2, 104.7)]         # pullback (drop in)
    s += [(104.7, 104, 100, 102), (102, 104, 100.2, 101.5), (101.5, 103.5, 100, 103)]                 # base 100-104 (idx 29-31), small bodies
    s[-3] = (103.5, 104, 100, 102)                                                                     # bearish small-body candle = David's candle
    s += [(103, 113, 102.8, 112.8), (112.8, 122, 112.5, 121.5), (121.5, 130, 121, 129.5)]            # leg-out: closes above 112 = BOS (idx 32)
    s += [(129.5, 130, 125, 126), (126, 127, 120, 121), (121, 122, 114, 115), (115, 116, 108, 109), (109, 110, 104, 105)]  # return to 104 (idx 39)
    s += [(105, 109, 104.8, 108.5), (108.5, 112, 108, 111.5)]
    return series(s)

def check(name, cond, detail=""):
    print(f"  [{'ok' if cond else 'FAIL'}] {name} {detail}")
    return cond

ok = True
print("1. worked example (therighttrader practice numbers: base 100-104, rally to 130, return to 104)")
bars = toy_demand()
m = major_structure(bars, 5)
zs = P.zones(bars, m)
v = [z for z in zs if z["valid"]]
ok &= check("one major BOS buy fired by the leg-out (bar 32 or 33: the 0.25-ATR close margin of David's structure rule)",
            len(m["events"]) == 1 and m["events"][0]["side"] == "buy" and m["events"][0]["idx"] in (32, 33),
            str([(e["kind"], e["side"], e["idx"], e["level"]) for e in m["events"]]))
ok &= check("exactly one valid demand zone", len(v) == 1 and v[0]["side"] == "buy", f"{len(v)} valid of {len(zs)} candidates")
z = v[0]
ok &= check("box = base wicks 100..104 (distal 100, proximal 104)", z["bottom"] == 100 and z["top"] == 104, f"{z['bottom']}..{z['top']}")
ok &= check("entry line = highest base body 103.5", z["entry"] == 103.5, str(z["entry"]))
ok &= check("kind DBR (drop in, rally out), base 3 candles", z["kind"] == "DBR" and z["base_n"] == 3, z["kind"] + f" x{z['base_n']}")
ok &= check("leg-out = displacement >= 1.5x avg body with an FVG", z["disp_mult"] >= 1.5 and z["fvg"] is not None, f"x{z['disp_mult']} fvg {z['fvg']}")
ok &= check("status tested after the return to 104 (1 touch, shallow)", z["status"] == "tested" and z["touches"] == 1 and z["max_depth"] < 0.5,
            f"{z['status']} touches {z['touches']} depth {z['max_depth']:.2f} at bar {z['touch_idx']}")
ok &= check("zone is only known from the break candle (touch_idx > break_idx)", z["touch_idx"] > z["break_idx"])
ok &= check("score 10 before the touch would be 9 after (freshness 2 -> 1)", z["score_parts"]["freshness"] == 1 and z["score"] >= 8, str(z["score_parts"]))

print("2. same series, leg-out that breaks NO swing -> INVALID (David §9-10)")
s2 = [dict(b) for b in bars[:32]]
# a leg-out that stops at 111 (below the 112 swing high) and comes back
s2 += [bar(32, 103, 110.5, 102.8, 110.2), bar(33, 110.2, 111, 109, 109.5), bar(34, 109.5, 110, 106, 106.5), bar(35, 106.5, 107, 103, 103.5)]
s2 += [bar(36 + i, 103.5, 104.5, 102.5, 103.5) for i in range(8)]
m2 = major_structure(s2, 5)
zs2 = P.zones(s2, m2)
ok &= check("no major event, no valid zone, the candidate is filtered with the no-BOS reason",
            not m2["events"] and not any(z["valid"] for z in zs2) and any("no major BOS" in (z["why"] or "") for z in zs2),
            f"events {len(m2['events'])}, reasons {[z['why'] for z in zs2]}")

print("3. second worked example (Dukascopy: EURUSD H4 base 1.0850-1.0870, +150 pips to 1.1020 'in a few candles')")
s3 = []
for i in range(20):
    s3.append((1.0900, 1.0912, 1.0888, 1.0903) if i % 2 == 0 else (1.0903, 1.0915, 1.0890, 1.0900))
s3 += [(1.0900, 1.0930, 1.0895, 1.0928), (1.0928, 1.0950, 1.0920, 1.0948), (1.0948, 1.0960, 1.0940, 1.0955)]   # swing high 1.0960 (idx 22)
s3 += [(1.0955, 1.0958, 1.0935, 1.0938), (1.0938, 1.0940, 1.0915, 1.0918), (1.0918, 1.0920, 1.0895, 1.0898),
       (1.0898, 1.0900, 1.0878, 1.0880), (1.0880, 1.0882, 1.0862, 1.0865)]                                       # drop in
s3 += [(1.0865, 1.0870, 1.0850, 1.0858), (1.0858, 1.0869, 1.0851, 1.0862), (1.0862, 1.0870, 1.0850, 1.0856)]   # base 1.0850-1.0870 (idx 28-30)
s3 += [(1.0856, 1.0950, 1.0855, 1.0945), (1.0945, 1.1000, 1.0940, 1.0995), (1.0995, 1.1020, 1.0990, 1.1015)]   # +150 pips, closes above 1.0960 = BOS
s3 += [(1.1015, 1.1018, 1.0990, 1.0995)] * 6
b3 = series(s3)
m3 = major_structure(b3, 5)
z3 = [z for z in P.zones(b3, m3) if z["valid"]]
ok &= check("one valid demand zone 1.0850..1.0870, fresh, DBR", len(z3) == 1 and abs(z3[0]["bottom"] - 1.0850) < 1e-9 and abs(z3[0]["top"] - 1.0870) < 1e-9
            and z3[0]["status"] == "fresh" and z3[0]["kind"] == "DBR", str([(z["kind"], z["bottom"], z["top"], z["status"]) for z in z3]))
ok &= check("run from the proximal = 150 pips = 7.5 box heights (>= 2: departure point)", z3 and abs(z3[0]["run_zone_heights"] - 7.5) < 0.05,
            str(z3[0]["run_zone_heights"] if z3 else None))

print("4. internal checks on real bars (GOLD M15, last 3000)")
bars = P.load("GOLD", "M15")
m = major_structure(bars, 5)
zs = P.zones(bars, m)
v = [z for z in zs if z["valid"]]
ok &= check("every valid zone hangs on a major event of its side, base inside origin..break, leg-out <= break",
            all(m["events"][z["event"]]["side"] == z["side"] and z["origin_idx"] <= z["base"][0] < z["d"] <= z["break_idx"] for z in v))
ok &= check("box geometry: bottom < top, proximal/entry on the near side", all(z["bottom"] < z["top"] and
            ((z["proximal"] == z["top"] and z["bottom"] <= z["entry"] <= z["top"]) if z["side"] == "buy" else (z["proximal"] == z["bottom"] and z["bottom"] <= z["entry"] <= z["top"])) for z in v))
ok &= check("David's candle (last opposite candle within 5 before the leg-out) is inside the base of every valid zone, when it exists",
            all((lambda j: j is None or j in z["base"] or z["kind_note"].startswith("opposite candle further"))(
                next((i for i in range(z["d"] - 1, max(z["d"] - 1 - P.LOOKBACK, -1), -1) if P._opp(bars[i], z["side"])), None)) for z in v))
ok &= check("all boxes <= 1.5 ATR", all(z["height_atr"] <= P.MAX_HEIGHT_ATR for z in v))
ok &= check("all base runs <= MAX_BASE + 1 (base + David's candle)", all(z["base_n"] <= P.MAX_BASE + 1 for z in v))
ok &= check("clean departure: no bar between leg-out and break reaches the proximal line",
            all(not any((bars[i]["l"] <= z["proximal"]) if z["side"] == "buy" else (bars[i]["h"] >= z["proximal"]) for i in range(z["d"] + 1, z["break_idx"] + 1)) for z in v))
ok &= check("exactly one origin per event with a valid zone", all(sum(z["role"].startswith("origin") for z in v if z["event"] == k) == 1 for k in {z["event"] for z in v}))
ok &= check("status monotone: tested implies touch_idx; broken implies a close beyond the distal; flipped/dead after broken",
            all((z["status"] != "tested" or z["touch_idx"]) and (z["broken_idx"] is None or ((bars[z["broken_idx"]]["c"] < z["distal"]) if z["side"] == "buy" else (bars[z["broken_idx"]]["c"] > z["distal"])))
                and (z["flipped_idx"] is None or z["flipped_idx"] > z["broken_idx"]) for z in v))
# no look-ahead: zones whose break is before a cut must be identical (geometry + validity) when computed on the truncated series
cut = len(bars) - 400
zc = [z for z in P.zones(bars[:cut], major_structure(bars[:cut], 5)) if z["valid"]]
full_keys = {(z["d"], z["bottom"], z["top"], z["break_idx"]) for z in v if z["break_idx"] < cut - 20}
cut_keys = {(z["d"], z["bottom"], z["top"], z["break_idx"]) for z in zc if z["break_idx"] < cut - 20}
ok &= check("no look-ahead in zone creation (truncated series gives the same valid zones)", full_keys == cut_keys,
            f"{len(full_keys)} vs {len(cut_keys)}, diff {len(full_keys ^ cut_keys)}")
print("\nALL OK" if ok else "\nSOME CHECKS FAILED")
