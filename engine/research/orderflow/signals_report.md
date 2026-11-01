# Order-flow signals as deterministic rules — research + prototype on FxPro ticks (2026-10-29)

Research agent (Fable 5.1), read-only. Files in this folder: `signals_proto.py` (prototype + `--selftest`),
`proto_results.json` (default run), `proto_results_minvol5.json` (`--imb-minvol-frac 0`, vendor-style absolute
min-volume), `final_run.txt` / `final_run_minvol5.txt` (console summaries).

## 0. What this feed allows (read first)

FxPro MT5 ticks carry no traded volume and no aggressor flag (README: BUY/SELL flags never set). All signals are
computed on the aggressor agent's recommended estimate: **bid tick rule on CHANGED quotes only** — bid up = 1 buy
unit, bid down = 1 sell unit, unchanged = 0 (no carry-forward), binned at the new bid. Duplicate rows (a quote update
arrives as a LAST|VOLUME row and again as a BID|ASK row with the same ms/bid/ask) are collapsed: GOLD 2.82 M → 2.14 M
ticks, of which 45.5 % change the bid; EURUSD 1.30 M → 1.17 M, 16.3 % change the bid. Buy share of classified ticks
49.6 % / 49.9 %. `classify_ticks()` is swappable (`tick_rule_changed` default, `tick_rule_bid` = classic carry-forward,
`tick_rule_mid`, `quote_rule`).

Structural consequences (verified in `selftest()` and the diagnostics):
1. **Unfinished / finished auction is undefined.** The bid can only *rise* to a bar's high, so the top tick holds buy
   units only and the bottom tick sell units only — every bar is a "finished auction" at tick resolution (selftest 7).
   The footprint rule (bid AND ask traded at the extreme) needs real aggressor data; only the candle form (flat,
   repeated extremes, LuxAlgo) can be used.
2. **Quote-count "volume" is smooth.** GOLD M5 volume/SMA20 (all ticks): 90th pct 1.28×, 99th 1.74×, max 2.31×; the
   vendor 2×/4× spike thresholds almost never fire (real volume spikes 5–10×). With changed ticks only the counts are
   spikier (1.5× fires 9–24 / 100 bars).
3. **Delta % shrinks with tick count** (≈ 1/√N): GOLD M5 median |delta|/vol 4.6 %, 99th 18.5 %; EURUSD 8.5 %. A fixed
   "delta %" (NinjaTrader) or "20–30 %" (ATAS) is not portable; thresholds must be multiples of the bar's own mean
   |delta| (CVD Divergence Pro scores in multiples of the average bar delta).
4. **Diagonal 3:1 imbalances do not exist in dense rows.** Changed-tick sides in a dense row are ≈ 50/50, so 3:1 only
   appears where a row holds a handful of ticks. With the recommended min-row-volume filter (≥ 0.5 × the bar's mean
   row, as ATAS / LuxAlgo / JOAT advise) there are **0 stacked imbalances** in 2 228 bars; with an absolute minimum of
   5 ticks, 9 on gold and 0 on EURUSD. (The classic carry-forward tick rule manufactured 6–8 stacks / 100 bars — all
   artefacts of the carried runs; with them a "zone hold" of 65–77 % vs 47–53 % baseline appeared. It vanishes
   under the changed-only rule, so it was the carry-forward, not the market.)
5. Tick-rule accuracy itself: 90 % claimed (Lee & Ready 1991), 74–78 % in later equity tests, **~66 % on EUR/USD and
   ~60 % for zero-tick trades** (EFMA 2014). A single bar's delta sign is noisy on FX; CVD over many bars less so.

## 1. Sources (all read 2026-10-29; at least two per rule)

Vendor docs / blogs
- ATAS, how to find and trade imbalance (default 150 %, examples 300 %, 116/26 = 446 %, ≥ 3 levels stacked, stuck
  longs/shorts become S/R): https://atas.net/blog/how-to-find-and-trade-imbalance/
- ATAS learn, imbalances (≥ 200 % imbalance, ≥ 400 % strong): https://learn.atas.net/volume-basics/volume-analysis/imbalances
- ATAS marketplace Imbalance Levels (ratio default 5×, stack ≥ 3, level touched by the very next candle = noise,
  persists until price returns): https://marketplace.atas.net/product/imbalance-levels
- ATAS, what is delta (bearish candle with positive delta = absorption by a limit seller): https://atas.net/blog/what-is-delta/
- ATAS, study to read footprint (unfinished auction = volumes do not run out at the extreme; failed auction; low volume
  at the extreme; POC tracking): https://atas.net/blog/study-to-read-footprint-what-each-beginner-should-know/
- ATAS, footprint modes (exhaustion = footprint thins at the top/bottom; delta colour change = reversal):
  https://atas.net/blog/how-footprint-charts-work-footprint-modes-and-what-they-are-for/
- ATAS (es), delta patterns (absorption = large delta that does not move price; "large" = > 20–30 % of volume):
  https://atas.net/es/analisis-de-volumen/estrategias-y-patrones-de-analisis-de-volumen/como-operar-con-patrones-del-indicador-delta
- NinjaTrader Order Flow Volumetric Bars (imbalance ratio default 1.5, min diagonal difference 10, Max/Min delta,
  Delta SH / SL = delta since the last touch of the high / low, Delta %):
  https://static.ninjatrader.com/support/helpGuides/nt8/order_flow_volumetric_bars.htm
- Sierra Chart Numbers Bars (diagonal dominant side, POC, thresholds 100/200/300, 25/50/75 %):
  https://www.sierrachart.com/index.php?page=doc/NumbersBars.php ; Volume At Price Threshold Alert V2 (stacked =
  "Highlight Adjacent Alerts Minimum Group Size", walkthrough 3; diagonal ratio; min volume for ratio compares):
  https://www.sierrachart.com/index.php?page=doc/StudiesReference.php&ID=386
- Quantower, stacked imbalance (diagonal, 200–300 % typical; a stall against the stack = absorption):
  https://www.quantower.com/blog/imbalance-footprint-chart-and-rithmic-plugin
- LuxAlgo library: delta divergence (pivots 2–5 bars; bar form = up close on negative delta; "a condition, not a
  trigger") https://www.luxalgo.com/library/concept/delta-divergence.md ; bid/ask imbalance (300 %, range 250–400,
  ≥ 3 rows, min-volume filter, trade-through invalidates) https://www.luxalgo.com/library/concept/bid-ask-imbalance.md ;
  absorption & exhaustion https://www.luxalgo.com/library/concept/absorption-and-exhaustion.md ; footprint concepts
  https://www.luxalgo.com/library/concept/footprint-concepts.md ; unfinished auction (candle form)
  https://www.luxalgo.com/library/concept/unfinished-auction.md ; unfinished business (label drops on first revisit)
  https://www.luxalgo.com/library/concept/unfinished-business.md ; volume delta (delta flip, max/min delta)
  https://www.luxalgo.com/library/concept/volume-delta.md ; value migration (POC confirms)
  https://www.luxalgo.com/library/concept/value-migration.md ; responsive vs initiative (vs the prior session's
  VAH/VAL; inside value = noise) https://www.luxalgo.com/library/concept/responsive-vs-initiative-activity.md ;
  TPO profile (single prints, POC, 70 % two-row build) https://www.luxalgo.com/library/concept/tpo-profile.md
- Jigsaw / Peter Davies: absorption blog https://www.jigsawtrading.com/blog/order-flow-absorption-market-reversals/ ;
  slides "Introducing Order Flow Analysis" (icebergs = absorption; cumulative delta to stay onside; "flip")
  https://www.jigsawtrading.com/wp-content/uploads/2014/03/IntroducingOrderFlowToYourTrading.pdf
- Axia Futures, manage your trade with footprint (absorption; "delta reversal" = hard selling candle immediately
  reversed by a hard buying candle): https://axiafutures.com/blog/how-to-manage-your-trade-using-footprint/
- Bookmap learning center: https://bookmap.com/learning-center/en/order-flow-phenomena/order-flow-education/layering-and-absorption ,
  https://bookmap.com/learning-center/en/order-flow-phenomena/order-flow-education/anatomy-of-a-reversal
- Orderflows (Valtos), rally on aggressive selling: https://www.orderflows.com/2023/01/25/order-flow-trading-strategy-how-a-market-can-rally-on-aggressive-selling/
- united-daytraders, absorptions & exhaustions: https://united-daytraders.com/blog/absorptions-and-exhaustions
- anomiq, absorption vs exhaustion with numbers (taker imbalance > ±60 %, volume z > 3, price impact → 0):
  https://anomiq.io/blog/absorption-exhaustion/
- MQL5 blog 774467, footprint from raw ticks (flags → last vs spread → tick rule; ratio "typically three", stacked
  ≥ 3): https://www.mql5.com/en/blogs/post/774467 ; MQL5 article 17518 (single-print code): https://www.mql5.com/en/articles/17518
- TradingView open-source scripts (descriptions; Pine is not served to a fetcher — logic reproduced in `selftest()`):
  Order Flow Footprint [JOAT] (buy[k] ≥ r·sell[k−1], sell[k] ≥ r·buy[k+1], r = 3.0, stack ≥ 4 / 3 on 1 m, delta flip
  after ≥ 5 same-sign bars) https://www.tradingview.com/script/3QFpGbCR-Order-Flow-Footprint-JOAT/ ; CVD Divergence &
  Absorption [UAlgo] https://br.tradingview.com/script/YeznJyfS-CVD-Divergence-Absorption-UAlgo/ ; CVD Divergence Pro
  https://www.tradingview.com/script/9KRT6CuB-CVD-Divergence-Pro/ ; Institutional Footprint Divergence Engine (pivot
  8–15, lookback 40–60) https://www.tradingview.com/script/2BbEtZFe-Institutional-Footprint-Divergence-Engine/ ;
  Orderflow Suite [martineye15] https://www.tradingview.com/script/eZnsyK2g-Orderflow-Suite-martineye15/ ; Bookmap
  Traps (buy imbalances at the top, close lower; strict wick 30 %) https://www.tradingview.com/script/AhH1CM72-Bookmap-Traps/ ;
  Big Volume Spikes (2× / 4× on SMA20) https://ar.tradingview.com/script/62AlXTph-Big-Volume-Spikes-Simplified/
- Market Profile / Dalton (secondary): LuxAlgo pages above; https://crosstrade.io/learn/technical-indicators/market-profile-tpo ;
  https://therighttrader.com/learn/volume-and-order-flow/market-profile

Academic
- Cont, Kukanov & Stoikov 2011, OFI = Σ e_n, e_n = 1{P^B_n ≥ P^B_{n−1}} q^B_n − 1{P^B_n ≤ P^B_{n−1}} q^B_{n−1}
  − 1{P^A_n ≤ P^A_{n−1}} q^A_n + 1{P^A_n ≥ P^A_{n−1}} q^A_{n−1}; ΔP = β·OFI, mean R² 65 % at 10 s (trade imbalance 32 %),
  β ∝ 1/depth: https://arxiv.org/abs/1011.6402
- Chordia & Subrahmanyam (JFE 2004; 2002 WP): Lee-Ready daily imbalances positively autocorrelated; lagged imbalance
  predicts next-day return (+), sign reverses conditional on the current imbalance; strategy profitable net of spread:
  https://www.cis.upenn.edu/~mkearns/finread/stock-misbalance.pdf
- Tick-rule accuracy: Ellis, Michaely & O'Hara 2000 https://ideas.repec.org/a/cup/jfinqa/v35y2000i04p529-551_00.html ;
  FX 66 % https://www.efmaefm.org/0efmameetings/efma%20annual%20meetings/2014-Rome/papers/EFMA2014_0302_fullpaper.pdf ;
  BVC https://papers.ssrn.com/abstract=1695596 and its critique https://repec.econ.au.dk/repec/creates/rp/13/rp13_43.pdf

Dead ends: guessed atas.net /volume-analysis/… 404; nexusfi concept pages 403; Trader Dale's rules only in his paid
book; Axia's course paywalled (blog used); TradingView serves descriptions, not Pine.

## 2. Rule table (recommended rule + defaults = `P` in signals_proto.py)

Rows R: GOLD 0.10 $ (≈ 32 rows per M5 bar), EURUSD 0.00002 (≈ 13); buy[k], sell[k] per row; delta = Σbuy − Σsell;
mean|Δ| = SMA20 |delta|; ATR = ATR14 (engine/major_structure.atr14); "new extreme" = beyond the previous new_n = 5 bars.

| # | Signal | Rule | Defaults | Invalidation | Drawn | Tick-rule OK? | Sources: agree / disagree |
|---|---|---|---|---|---|---|---|
| 1 | Bar delta divergence | close > open and delta ≤ −k·mean\|Δ\| → bull (sellers absorbed); close < open and delta ≥ +k·mean\|Δ\| → bear | k = 1.5 | next bar closes beyond the bar's extreme in the delta's direction | arrow + "Δ −1.9×" | partly (single-bar sign ~66 % right on FX) | form: LuxAlgo, ATAS, MQL5 agree; magnitude: none gives one, NT delta % / ATAS 20–30 % do not scale — multiples of mean\|Δ\| recommended |
| 2 | CVD divergence at swings | pivots n each side; bear: later pivot high higher, CVD at it lower; bull mirrored; pivots ≤ L bars apart; known n bars after the 2nd pivot | n = 3, L = 60 | a close beyond the 2nd pivot's extreme; CVD anchor reset | line joining the two price pivots and the two CVD pivots | yes (CVD averages the noise) | LuxAlgo 2–5, Engine 8–15, Pro ATR zig-zag; regular form everywhere, hidden only in UAlgo |
| 3 | Absorption | vol ≥ a·SMA20 and \|delta\| ≥ k·mean\|Δ\| and body·sign(delta) ≤ b·ATR → fade the aggressors; best at a level | a 1.3, k 1.5, b 0.10 | a close ≥ 0.25 ATR beyond the absorbed extreme | box on the bar | weak (needs size) | Jigsaw, Bookmap, LuxAlgo, ATAS, united-daytraders qualitative; only anomiq numeric (crypto taker data) |
| 4 | Exhaustion | new high and the top r rows each ≤ f·mean row and delta > 0 → bear; mirrored | r 2, f 0.25 | next bar higher high on vol ≥ SMA | marker at the tip | partly (every spike has a thin tip) | LuxAlgo, ATAS, crowstack "N×0", united-daytraders; none numeric |
| 5 | Stacked imbalances | diagonal buy[k] ≥ r·sell[k−1], sell[k] ≥ r·buy[k+1], row vol ≥ max(5, 0.5·mean row); ≥ s consecutive same-side rows = zone | r 3.0, s 3 | ATAS: taken out by the next candle = noise; else a close through the far edge | shaded band to the right | **no** (§0.4) | ratio ATAS 150/300, learn.atas 200/400, NT 1.5, JOAT 3.0, LuxAlgo 300, ATAS Levels 5×; stack 3 (ATAS, Sierra, LuxAlgo, MQL5) vs 4 (JOAT) → 3.0 / 3 |
| 6 | Unfinished auction | footprint form undefined (§0.1); candle proxy: two consecutive bars share the high (low) within 1 tick at a new extreme | new_n 5 | first revisit (LuxAlgo) | line from the extreme until touched | proxy only | ATAS / LuxAlgo / Trader Dale agree on form and "revisit, no timetable"; no statistic published |
| 7 | Delta flip | sign(delta) changes after ≥ m same-sign bars | m 5 | flips back next bar | marker | yes | LuxAlgo plain sign change; JOAT run ≥ 5; Axia "delta reversal" = hard sell candle then hard buy candle |
| 8 | Trapped traders | ≥ 1 buy-imbalance row in the top p of the range, close below it and in the lower half → bear; mirrored | p 0.30 | next bar closes above the high | marker at the rows | weak (needs 5) | Bookmap Traps, ATAS "stuck longs", Trader Dale |
| 9 | Volume spike | vol ≥ x·SMA20 (undirected) | x 1.5 (vendors 2 / 4) | — | bar highlight | weak (§0.2) | Big Volume Spikes 2/4×, intrabar 4×, NT tool 1.5× median |
| 10 | Large print (row) | one row ≥ y × the mean row of the last 20 bars | y 4 | traded through | dot at the row | weak | as 9; LuxAlgo block trades |
| 11 | Initiative / responsive | prior server day's VA (70 % of ticks, two-row build as engine/volume_profile.py); delta > 0 and close > VAH = initiative buy; delta > 0 and close < VAL = responsive buy; mirrored; inside VA = nothing | 70 % | value migrates against | tag | yes | LuxAlgo, NexusFi agree (one poster counts inside-value as initiative) |
| 12 | POC migration | bar POC higher than the previous bar's m bars running → up; mirrored | m 3 | a POC against the run | step line | yes (POC of counts ≈ time at price) | ATAS, LuxAlgo; no numeric rule anywhere |
| 13 | Single print / LVN in a bar | an inner row (not the outer 2) ≤ f·mean row with both neighbours ≥ g·mean row | f 0.15, g 0.5 | traded through | thin line | partly | MQL5 17518, LuxAlgo |
| 14 | Delta at the high / low | new high and top-row delta ≤ 0 (top-row vol ≥ 5) → bear; mirrored; NT Delta SH/SL also computed | — | next bar higher high | marker | **mostly no** (§0.1) | NinjaTrader Delta SH/SL; Orderflows / ATAS narrative |
| 15 | Sweep + flow | wick ≥ w·ATR beyond the previous n-bar swing, close back inside, previous bar not beyond; "confirmed" if the bar delta leans INTO the sweep (chasers trapped) | w 0.10 (engine SWEEP_ATR), n 5 | close beyond the level by 0.25 ATR (engine BOS margin) | engine sweep mark + "Δ +7 %" tag | partly | LuxAlgo, sweep-absorption-reclaim scripts: structure first, flow as confirmation |
| 16 | BOS with strong delta | engine major_structure event whose break bar has delta·side ≥ k·mean\|Δ\| and vol ≥ 1.2·SMA20 | k 1.5 | the engine's | tag on the BOS | partly | Wyckoff SOS-on-volume (engine), LuxAlgo |
| 17 | OB / FVG retest with delta flip | (not prototyped: smc_marks needs the engine config) first bar whose wick enters a live OB / FVG with delta on the zone's side ≥ k·mean\|Δ\| | k 1.5 | per smc_marks | tag on the zone | partly | SMC-flow scripts: zone first, delta confirms |
| 18 | OFI (academic) | Σ e_n over the bar from L1 quotes; on FxPro the size terms are fixed tiers, so OFI collapses to Σ(bid up − bid down) = rule 0's delta | 10 s–1 min | — | oscillator | sizes meaningless here | Cont et al. (contemporaneous R² 65 %); Chordia-Subrahmanyam (daily lagged → next day) |

## 3. Prototype results (default run: changed-tick rule; 2000 within-day circular-shift permutations; forward
return in ATR units signed by the signal; "(/100)" = fires per 100 bars = false-positive load)

GOLD M5 817 bars / M15 273; EURUSD M5 853 / M15 285; 2026-10-26 20:07 → 10-29 19:07 IST (4 server days).

| signal | GOLD M5 n (/100): h3 / h6 / h12 ATR (p) | GOLD M15 | EURUSD M5 | EURUSD M15 |
|---|---|---|---|---|
| bar_div | 39 (4.8) −0.07/−0.08/−0.33 (.73/.81/.49) | 23 (8.4) +0.11/+0.20/+1.24 (.65/.62/.09) | 8 (0.9) −0.19/−0.44/−1.03 | 4 (1.4) −0.47/−0.39/−1.44 |
| cvd_div | 32 (3.9) −0.33/−0.52/−0.81 (.14/.09/.09) | 14 (5.1) −0.11/+0.15/−0.23 | 23 (2.7) +0.09/+0.15/+0.13 | 6 (2.1) +0.06/−0.06/−0.39 |
| absorb | 16 (2.0) −0.15/−0.07/−0.01 | 9 (3.3) +0.59/+1.09/+2.47 (.16/.13/.10) | 6 (0.7) +0.28/−0.73/−1.20 | 3 |
| exhaust | 97 (11.9) +0.01/+0.07/+0.10 | 48 (17.6) −0.01/−0.15/+0.30 | 24 (2.8) +0.51/+1.08/+0.80 (.12/.04/.24) | 21 (7.4) +0.26/−0.06/−0.15 |
| stack (relative min vol) | 0 | 0 | 0 | 0 |
| stack (abs min 5) | 5 (0.6) zone held 1/4 vs 0.54 | 4 (1.5) held 3/4 vs 0.46 | 0 | 0 |
| unfin (candle proxy) revisit | 3: 2/3 vs 0.76 | 1 | 38 (4.5): 0.97 vs 0.88, p .08 | 3: 3/3 vs 0.90 |
| finished control (sharp spike) revisit | 249: 0.94 vs 0.89, p .005 | 72: 0.88 vs 0.90 | 273: 0.89 vs 0.89 | 88: 0.88 vs 0.90 |
| dflip | 50 (6.1) +0.27/+0.34/+0.68 (.14/.17/.04) | 16 (5.9) +0.32/−0.04/+0.55 | 25 (2.9) −0.09/+0.27/+0.37 | 10 (3.5) −1.03/−1.37/−2.12 (.01/.01/.03) |
| trap | 104 (12.7) +0.06/+0.10/+0.24 | 20 (7.3) +0.46/+0.60/+0.48 (.11/.14/.44) | 58 (6.8) −0.14/+0.05/+0.03 | 25 (8.8) −0.16/−0.25/+0.36 |
| spike 1.5× (\|r\| vs all bars) | 74 (9.1) 1.13/1.59/2.21 vs 0.93/1.32/1.86 | 32 (11.7) 1.03/1.56/2.04 vs 0.87/1.25/1.90 | 138 (16.2) 1.41/1.92/2.63 vs 1.03/1.46/2.03 | 68 (23.9) 1.17/1.49/1.80 vs 0.95/1.26/1.61 |
| bigrow revisit | 128: 0.95 vs 0.94 | 53: 0.93 vs 0.95 | 107: 0.95 vs 0.92 | 49: 0.92 vs 0.92 |
| init | 322 (39) −0.05/−0.21/−0.30 | 65 (24) −0.27/−0.07/−0.55 (.06/.77/.24) | 260 (31) −0.03/0.00/+0.05 | 34 (12) −0.40/−0.56/−0.63 |
| resp | 301 (37) +0.02/−0.10/−0.11 | 66 (24) −0.09/−0.01/−0.07 | 233 (27) −0.05/−0.10/−0.41 | 40 (14) +0.19/+0.18/+0.48 |
| pocmig | 223 (27) −0.20/−0.32/−0.47 (.12/.12/.13) | 65 (24) −0.05/+0.42/+0.38 | 195 (23) −0.11/−0.18/−0.43 | 60 (21) −0.49/−0.18/−0.34 (.06/.57/.50) |
| lvn revisit | 60: 0.93 vs 0.87, p .12 | 11: 0.91 vs 0.91 | 77: 0.91 vs 0.88 | 17: 0.94 vs 0.87 |
| dhl | 15 (1.8) +0.26/+0.16/−0.66 | 5 | 1 | 0 |
| sweep (all) | 14 (1.7) +0.12/0.00/−0.35 | 11 (4.0) +0.42/−0.47/−0.20 | 13 (1.5) +0.02/−0.18/+1.73 (.94/.69/.01) | 10 (3.5) −0.17/−0.30/−1.00 |
| sweep confirmed by delta | 10: −0.06/+0.16/+0.10 | 6: +0.93/+0.34/+1.86 (.05/.60/.11) | 7: −0.41/−0.95/+1.66 | 6: +0.13/+0.11/−0.32 |
| sweep unconfirmed | 4: +0.72/−0.56/−1.84 | 5: −0.18/−1.44/−2.25 | 6: +0.52/+0.71/+1.81 | 4: −0.61/−0.91/−1.84 |
| BOS strong / weak delta | 2 / 10 (weak +0.28/+0.15/+0.03) | 2 / 7 | 5 / 12 (strong +0.44/−0.74/−0.80, p > .38) | 2 / 4 |

Dated examples (IST). GOLD M5: 10-28 04:10 sweep of the swing high 4064.2 with delta +7 % (the run into David's
4065.67 EQH / PDH; the engine's failed-break sweep at 05:30–06:20 is the larger structure); 10-28 05:30 BOS buy on
vol 2.5× but delta only +6 %; 10-27 06:20 absorption bear (vol 1.5×, delta +6 %, body −0.16 ATR); 10-26 22:55 CVD
divergence bear (HH 4021 → 4029.8, CVD +195 → −13). EURUSD M5: 10-27 06:30 BOS sell delta −12 % vol 2.8× (strong);
10-28 02:20 bar divergence bear (down close on delta +16 % = 3.6× mean). Per-day counts and three examples per signal
and dataset: `proto_results.json` → `per_day`, `examples`.

### Verification of the detectors
`python3 -I signals_proto.py --selftest` reproduces on toy inputs: ATAS' published ratios (116/26 = 446 %, 86/8 =
1075 %); JOAT's diagonal rule and ≥ 3 stacking on a hand-made 6-row footprint; LuxAlgo's bearish divergence on a toy
price/CVD series with 2-bar pivots; the Cont-Kukanov-Stoikov e_n for the four L1 event types; the changed-quote tick
rule ([0,0,1,0,−1,0,1]) and the classic carry-forward variant; NinjaTrader Delta SH/SL; and the property that the
tick rule leaves only buy units at the exact high. All pass.

### Honest verdict per signal
Sample: 4 days, ~800 M5 bars per symbol — low power. 17 directional signals × 4 datasets × 3 horizons ≈ 200 tests →
~10 expected at p < 0.05 by chance; 8 observed, none with the same sign in all four datasets, and the aggressor
agent found no classification method predicts the next bar at all. So:
- **CVD divergence at pivots**: right sign in 3 of 4 datasets at h6/h12 on gold (−0.5 to −0.8 ATR against the move,
  p 0.09) but ~0 on EURUSD. Not significant; the one rule worth re-testing on weeks of data. Draws cleanly.
- **Delta flip**: p 0.01–0.04 in two datasets *with opposite signs* (gold M5 continuation, EURUSD M15 reversal) —
  noise.
- **Stacked imbalances / trapped traders / delta at the high-low**: do not exist or are artefacts on tick-rule data
  (§0.4). The earlier "zones hold 72 %" came from the carry-forward rule; gone under changed-only ticks.
- **Bar delta divergence, absorption, exhaustion, initiative / responsive, POC migration, BOS-with-delta, sweep
  confirmed vs unconfirmed**: within noise; signs flip between symbols / timeframes. Exhaustion fires 12–18 / 100
  bars on gold — useless as a filter.
- **Volume (quote-count) spike**: the only robust information, and it is *undirected*: after a 1.5× spike the next
  3–12 bars move 15–40 % more than average in all four datasets (activity clusters; a volatility, not a direction
  signal).
- **Revisit rules (unfinished auction, LVN, big print)**: any level at that distance is revisited ~87–94 % within
  24 bars, so the claims are untestable at this window; the sharp-spike control was revisited *more* on gold M5
  (0.94 vs 0.89, p .005) — the opposite of the lore. No usable rule on this feed.

### Recommendation for the /smc page
Show as a concept layer labelled "estimated (bid tick rule, changed quotes)": per-bar delta in multiples of mean |Δ|,
the session-anchored CVD line with pivot-divergence marks (rule 2), delta tags on the engine's own sweep / BOS /
OB-retest marks (rules 15–17) as *annotations, never filters*, and the 1.5× activity spike. Do not draw stacked
imbalances, unfinished auctions, delta-at-the-extreme or trapped-trader marks from tick-rule data; revisit them only
if a feed with real aggressor flags (CME GC / 6E futures) is added, and re-run `signals_proto.py --method …` then.
