"""verify_examples.py — reproduce worked examples from the platforms' documentation with footprint_proto."""
import sys
sys.path.insert(0, "/tmp/claude-1000/-home-david-forex/6f79950b-2f79-4743-8184-d36a070b7e52/scratchpad/of_research/footprint")
from footprint_proto import analyze_table

results = []

# 1. Sierra Chart Numbers Bars, "Diagonal Dominant Side" example (https://www.sierrachart.com/index.php?page=doc/NumbersBars.php)
#    bar listed top → bottom as Bid | Ask: A (0|56) B (293|359) C (48|532) D (1008|830) E (682|452) F (16|0)
#    Documented: bid dominant at B, D; ask dominant at B, D, E; A bid and F ask: no comparison.
tbl = {6: (0, 56), 5: (293, 359), 4: (48, 532), 3: (1008, 830), 2: (682, 452), 1: (16, 0)}
b = analyze_table(tbl, row=1, ratio=1.0, strict=True, zero_rule="skip")    # dominance = strictly larger
name = {6: "A", 5: "B", 4: "C", 3: "D", 2: "E", 1: "F"}
got_bid = sorted(name[int(p)] for p in b["imb_sell"]); got_ask = sorted(name[int(p)] for p in b["imb_buy"])
results.append(("Sierra diagonal dominant side", got_bid == ["B", "D"] and got_ask == ["B", "D", "E"],
                f"bid-dominant {got_bid} (doc: B, D); ask-dominant {got_ask} (doc: B, D, E)"))
# the same table with zero_rule = "count" (Sierra 'Zeros as Ones' = 1 → 56 > 1 and 16 > 1 would NOT be compared
# at the extremes unless 'Compare with No Data at High/Low' is on) — our "count" compares only existing rows:
b2 = analyze_table(tbl, row=1, ratio=1.0, strict=True, zero_rule="count")
results.append(("Sierra table, zero_rule=count (extremes still uncompared)",
                sorted(name[int(p)] for p in b2["imb_buy"]) == ["B", "D", "E"] and
                sorted(name[int(p)] for p in b2["imb_sell"]) == ["B", "D"], "same result: no zero opposite inside the bar"))

# 2. Sierra "Ask Volume Bid Volume Difference Per Tick": Ask 1000, Bid 1500, 2600.50–2602.00, tick 0.25 → -83.33
val = (1000 - 1500) / ((2602.00 - 2600.5) / 0.25)
results.append(("Sierra delta per tick", abs(val + 83.33) < 0.01, f"{val:.2f} (doc: -83.33)"))

# 3. Sierra Volume At Price Threshold Alert V2: Ask 100 vs Bid 50 → ratio 200 % (https://www.sierrachart.com/index.php?page=doc/StudiesReference.php&ID=386)
b = analyze_table({2: (0, 100), 1: (50, 0)}, row=1, ratio=2.0)
results.append(("Sierra VAP alert ratio 200 %", b["imb_buy"] == [2.0], f"buy imbalance rows {b['imb_buy']} (doc: ask 100 / bid 50 = 200 % triggers at threshold 200)"))
b = analyze_table({2: (0, 100), 1: (50, 0)}, row=1, ratio=2.01)
results.append(("Sierra VAP alert ratio just above 200 %", b["imb_buy"] == [], f"{b['imb_buy']} (no trigger at 201 %)"))

# 4. TradingView Volume Footprint help (https://www.tradingview.com/support/solutions/43000726164-volume-footprint-chart):
#    "506.37 ('buy') ≥ (300 / 100) * 166.433 ('sell') ... a 'buy' imbalance", buy level 3 vs sell level 2.
b = analyze_table({3: (10, 506.37), 2: (166.433, 10), 1: (10, 10)}, row=1, ratio=3.0)
results.append(("TradingView 300 % example", b["imb_buy"] == [3.0] and b["imb_sell"] == [], f"buy imbalance rows {b['imb_buy']} (doc: level 3)"))
b = analyze_table({3: (10, 499.0), 2: (166.433, 10), 1: (10, 10)}, row=1, ratio=3.0)
results.append(("TradingView 300 % counter-example", b["imb_buy"] == [], f"499 < 3 × 166.433 = 499.3 → {b['imb_buy']}"))

# 5. TradingView Volume Profile value area algorithm (https://www.tradingview.com/support/solutions/43000502040-volume-profile/):
#    one row at a time, larger neighbour, stop BEFORE exceeding the target; tie → closer to POC, equal → above.
tot = {1: 10, 2: 30, 3: 100, 4: 25, 5: 20, 6: 5}          # total 190, target 133
b = analyze_table({p: (v, 0) for p, v in tot.items()}, row=1, va_step=1, va_stop="never_exceed")
# POC 3 (100); candidates 2 (30) vs 4 (25) → add 2 (130); next 1 (10) vs 4 (25) → 25 would make 155 > 133 → stop → VA 2..3
results.append(("TradingView VA never_exceed", (b["val"], b["vah"]) == (2.0, 3.0), f"VA {b['val']}–{b['vah']} (expected 2–3, 130/190 = 68 %)"))
b = analyze_table({p: (v, 0) for p, v in tot.items()}, row=1, va_step=1, va_stop="reach")
results.append(("Sierra/ATAS VA reach ≥ 70 %", (b["val"], b["vah"]) == (2.0, 4.0), f"VA {b['val']}–{b['vah']} (expected 2–4, 155/190 = 82 %)"))
# tie: equal neighbours → the row above
b = analyze_table({1: (40, 0), 2: (100, 0), 3: (40, 0), 4: (1, 0)}, row=1, va_step=1, va_stop="reach")
results.append(("VA tie → row above POC first", (b["val"], b["vah"]) == (2.0, 3.0), f"VA {b['val']}–{b['vah']} (expected 2–3: 140/181 = 77 %)"))

# 6. Unfinished auction (learn.atas.net footprint-patterns; Trader Dale): both non-zero at the extreme = unfinished
b = analyze_table({3: (5, 7), 2: (50, 60), 1: (0, 12)}, row=1)
results.append(("unfinished high / finished low", b["unfinished_high"] and not b["unfinished_low"], f"high {b['unfinished_high']} low {b['unfinished_low']}"))

# 7. Stacked imbalance (3 consecutive buy imbalances → one zone)
b = analyze_table({5: (1, 2), 4: (2, 40), 3: (10, 30), 2: (9, 33), 1: (10, 1)}, row=1, ratio=3.0, stack=3)
results.append(("stacked buy 3 rows", b["stacked_buy"] == [(2.0, 4.0)], f"stacked buy {b['stacked_buy']} imb rows {b['imb_buy']}"))

# 8. NinjaTrader Volumetric bars doc (https://static.ninjatrader.com/support/helpGuides/nt8/order_flow_volumetric_bars.htm):
#    level delta 740 − 220 = 520; "Buy volume of 518 is compared to the diagonal below sell volume of 989 … 989 / 518 = 1.9092"
#    > 1.5 → sell imbalance (difference 471 ≥ min delta 10); bar buy 3463, sell 4535 → delta −1072.
b = analyze_table({2: (0, 518), 1: (989, 0)}, row=1, ratio=1.5, min_vol=10)
results.append(("NinjaTrader 989/518 = 1.909 > 1.5 sell imbalance", b["imb_sell"] == [1.0] and b["imb_buy"] == [], f"sell rows {b['imb_sell']}"))
b = analyze_table({1: (220, 740)}, row=1)
results.append(("NinjaTrader level delta 740 − 220", b["delta"] == 520, f"delta {b['delta']}"))
results.append(("NinjaTrader bar delta 3463 − 4535", 3463 - 4535 == -1072, "-1072"))

# 9. ATAS blog (https://atas.net/blog/how-to-find-and-trade-imbalance/) 300 % setting: bid vs ask one level higher:
#    116/26 = 446 %, 86/8 = 1075 %, 58/18 = 322 %, 64/15 = 426 %, 218/67 = 325 %, 190/49 = 387 % → all bid (sell) imbalances
tbl = {7: (0, 26), 6: (116, 8), 5: (86, 18), 4: (58, 15), 3: (64, 67), 2: (218, 49), 1: (190, 30), 0: (40, 20)}
b = analyze_table(tbl, row=1, ratio=3.0, stack=3)
results.append(("ATAS blog six bid imbalances at 300 %", sorted(b["imb_sell"]) == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0] and b["imb_buy"] == [],
                f"sell rows {sorted(b['imb_sell'])}, stacked sell {b['stacked_sell']}"))
#    ATAS cluster-settings example: "if the ask volume equals 30 and the imbalance threshold is set to 350% then the corresponding bid volume must exceed 105"
b = analyze_table({2: (0, 30), 1: (105, 0)}, row=1, ratio=3.5, strict=True)
b2 = analyze_table({2: (0, 30), 1: (106, 0)}, row=1, ratio=3.5, strict=True)
results.append(("ATAS 350 %: bid must EXCEED 105 vs ask 30", b["imb_sell"] == [] and b2["imb_sell"] == [1.0], f"105 → {b['imb_sell']}, 106 → {b2['imb_sell']}"))

# 10. flowsurface (Rust) exceeds_diagonal_threshold: qty > diag × (100 + 200) / 100, ignore_zeros → 3× strict
b = analyze_table({2: (0, 300), 1: (100, 0)}, row=1, ratio=3.0, strict=True)
b2 = analyze_table({2: (0, 301), 1: (100, 0)}, row=1, ratio=3.0, strict=True)
results.append(("flowsurface strict > at 200 % threshold", b["imb_buy"] == [] and b2["imb_buy"] == [2.0], f"300 → {b['imb_buy']}, 301 → {b2['imb_buy']}"))

for n, ok, msg in results:
    print(f"[{'OK' if ok else 'FAIL'}] {n}: {msg}")
print("all OK" if all(r[1] for r in results) else "SOME FAILED")
