# Which supply / demand validity criteria actually make a zone hold? (2026-10-30)

Research for David's /smc page: he wants the page to show "only the valid" supply / demand zones. This report tests,
on our own FxPro history, every validity criterion the S&D literature and David's rules propose, against matched
random levels, and collects what has actually been measured elsewhere. Files in this folder:

- `sd_test.py` — the test (python3 + numpy; reads `engine_data/history/<SYM>.json` and `engine/major_structure.py` read-only)
- `tables.md` — every table the script writes (overview, IS/OOS, freshness, strata, 45 criteria × {1 h, 1 ATR, 2 h}
  × {M15, H1} pooled, and per symbol / timeframe); `zones.json` — every zone, control and shuffled-series zone
- `sources.md` — the literature review with URLs and credibility grades (summarised in §1)
- `scan.txt` — the cross-cell consistency scan and the hard-stop expectancy (§4.5, §4.6)

## 0. The answer in one paragraph

Nothing tested makes a zone hold more often than a random level of the same size, at the same distance from price,
in the same market. Across 39,106 FX + GOLD zones (M15 + H1, 16 months, two zone definitions) the first return
"held" (price reacted one zone height before a candle closed beyond the distal line) 58.2 % of the time for David's
V5 zones and 57.5 % for classic base zones; matched random controls held 57.9 % / 57.3 % (lift +0.2 pp, 95 % CI
−0.6 … +1.0), and zones found on shuffled candles held 56.7 % / 55.5 %. In-sample and out-of-sample agree. David's
BOS gate (the leg-out closes through a confirmed swing of his major structure) changes the hold rate by −0.1 pp
(V5 M15), −1.2 pp (V5 H1), −3.1 pp (base M15, p = 0.03) and +1.1 pp (base H1): it does not select zones that hold.
Neither do freshness (second return 58.0 % vs first 57.7 %), the FVG, the displacement multiple, the base count,
departure strength, trend, premium / discount, a sweep, the session, a round number or the reward-to-risk to the
next zone. With a hard stop at the distal line the first-touch trade wins ≈ 30 % at RR 1 — for zones and for
controls alike. The published evidence says the same: the only measured S/R edges are a few points over a ~56 %
bounce base rate for professionally chosen horizontal levels and round numbers (Osler 2000/2003), and the three
independent order-block backtests with placebo controls find no effect. So "valid" on the page can only mean
"meets the method's definition and is still intact" — David's rule, applied honestly as a filter that cuts 6 zones
a day to under one — never "more likely to hold".

## 1. What is published (details and grades in sources.md)

Grades: A peer-reviewed / central bank, B preprint, C vendor or hobbyist backtest with a stated method, D assertion.

| source | what was measured | key numbers | grade |
|---|---|---|---|
| Osler 2000, *Support for Resistance*, FRBNY EPR — https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf | S/R levels published daily by 6 FX dealers, 1996-98, 1-min quotes; "bounce" = back on the near side 15 min after a hit; 10,000 sets of arbitrary levels as the null | arbitrary levels bounce **56.2 %**, published levels **60.8 %** (+4.6 pp, every firm × currency positive); 5 days later still better but 1.7 pp weaker; the firms' own "strength" ratings had **no** predictive value; 96 % of levels end in 0 or 5 | A |
| Osler 2003, *Currency Orders and Exchange Rate Dynamics*, J. Finance (FRBNY SR 125) — https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf | 9,667 stop-loss / take-profit orders at one bank | 8.7 % of all orders at rates ending **00**; take-profits cluster *at* 00, stop-losses just *beyond* it → reversal at round numbers, acceleration after they break | A |
| Chung & Bellotti 2021, arXiv:2101.07410 — https://arxiv.org/abs/2101.07410 | EURUSD / Lloyds / Brent 1-min, 2018; levels = rolling-window extremes; 1,000 shuffled series as null | bounce probability > 0.5 and **rises with the number of previous bounces**; EURUSD levels decay to chance after ~350 min (1 bounce) … ~900 min (4 bounces) | B |
| Garzarelli et al. 2014, Sci. Rep. 4:4487 — https://arxiv.org/abs/1110.5197 | 9 LSE stocks, tick data 2002 | shuffled 0.50 vs real **0.55–0.62**; p(bounce) rises with previous bounces | A |
| Brock, Lakonishok & LeBaron 1992, J. Finance — https://ideas.repec.org/a/bla/jfinan/v47y1992i5p1731-64.html; Curcio & Goodhart 1992 — https://eprints.lse.ac.uk/119184; Lo, Mamaysky & Wang 2000 — https://www.nber.org/papers/w7613; Zapranis & Tsinaslanidis 2012, doi 10.1080/09603107.2012.663469 | trading-range breaks, chartist S/R in FX, pattern recognition, rule-based horizontal S/R | small positive conditional effects (pre-1987 DJIA; 1992 FX); Zapranis: rule-based S/R does **not** beat buy-and-hold | A |
| TradingView *Order Block Statistics: Real Win Rate vs Random Levels* (open source) — https://www.tradingview.com/script/yFmy3VBi-Order-Block-OB-Statistics-Real-Win-Rate-vs-Random-Levels/ | OB = last opposite candle before a close-based BOS; placebo levels matched by height / direction / distance; BTC, EURUSD, ES, 4 TFs | control base rate 47–52 %; pooled OB effect **−2.1 pp** (CI −4.3 … +0.1); 2-ATR displacement filter −0.6 pp: "no reliable order-block effect" | C+ |
| StatOasis *I backtested ICT / SMC: what survives* — https://statoasis.com/overfit/research/ict-backtest-what-survives | SPY/QQQ/DIA/IWM daily, 648 variants vs random-entry baseline | OB edge +0.12 % (t 1.2); FVG retrace edge −0.005 % (t −0.08); 0 of 648 beat buy-and-hold | C |
| indicatoredge.io SMC page — https://indicatoredge.io/smart-money; Backtrex GBPUSD OB — https://backtrex.com/en/backtests/order-block-gbp-usd | vendor out-of-sample tallies | OB median win 40 %, alpha −6.5 %; GBPUSD H1 first-touch OB 2016-26: 38 % won, PF 0.83 | C− |
| Seiden / OTA "odds enhancers" (https://forums.babypips.com/t/odd-enhancers-sam-seiden/39321), Set & Forget / Alfonso Moreno, prop-firm journal (https://proptradingvibes.com/blog/supply-and-demand-trading), Trading Rush (https://tradingrush.net/why-you-should-never-sell-at-this-resistance-tested-200-times/) | the rule sets: departure strength, time at base (fewer candles), freshness, ≥ 3:1 profit margin, HTF trend, curve position, imbalance | **no measured result** for any rule; the one journal tally (fresh 62 %, 1st retest 48 %, 2nd 33 %, "200+ trades") is personal and unverifiable; Trading Rush: resistance shorts 50 % vs ~44 % random | D / C− |
| LuxAlgo *Order Blocks & Breaker Blocks*, *Supply and Demand Visible Range* — https://www.luxalgo.com/library/indicator/order-blocks-breaker-blocks/ , https://www.luxalgo.com/library/indicator/supply-and-demand-visible-range/ | definitions only | OB from a swing point, full range or body; mitigation = close *or* wick (user setting); "visible range S&D" is a volume profile, not a pattern | doc |

What the literature supports with data: horizontal levels that many traders watch (published levels, round numbers)
bounce a few points more often than chance; **tested** levels get *stronger* with each bounce (the opposite of the
"fresh zone" doctrine); the effect decays within hours intraday. What it does not support with any measurement:
freshness, base-candle count, departure strength, the FVG, the BOS as a zone qualifier, time at level. Three
independent OB/FVG backtests with placebo or random baselines find nothing. Where sources disagree (vendors: fresh
is best; academics: tested is stronger) our own data below sides with neither — the first and the second return
hold equally.

## 2. Method

**Data.** `engine_data/history/<SYM>.json` for GOLD, EURUSD, GBPUSD, USDJPY, AUDUSD (and BITCOIN for contrast), M15
(33,000 bars, ≈ Jun 2025 → Oct 2026) and H1 (8,500 bars, ≈ May 2025 → Oct 2026). In-sample = the first 70 % of
each file, out-of-sample = the last 30 %.

**Zones (two definitions, both run on everything).**
- *v5* — David's rule: a displacement candle (body ≥ 1.5 × the mean body of the previous 10, `config.py`
  `displacement_mult` / `body_average_bars`) and the last opposite candle ≤ 5 bars before it (`zone_lookback_bars`).
  Box = the candle's full wick, as `smc_marks.py` draws the OB. One zone per opposite candle (consecutive
  displacements do not duplicate it).
- *base* — the classic rally-base-rally family: a directional leg-in candle, 1–6 base candles with body ≤ 50 % of
  their range, and a leg-out that is a displacement by the same rule **and closes beyond the whole base**. Distal
  edge = the base's extreme wick (the stop goes behind the last price traded there), proximal edge = the base's
  extreme body (entries trigger where the base actually traded, not at a wick) — the Seiden / OTA and Set-and-Forget
  convention; LuxAlgo offers both as a setting.
- Both: the leg-out must close beyond the proximal line, price must leave by ≥ 1 zone height before the first
  return, zone height ≥ 0.05 ATR (drops dojis). Everything is known at the close of the leg-out candle.

**Outcome at the first return** (closed bars only). r = the first bar after the leg-out whose wick reaches the
proximal line. From r: *fail* = a bar (r included) **closes** beyond the distal line; *hold 1 h* = before that, a
later bar trades ≥ 1 zone height beyond the proximal line; *hold 2 h* = ≥ 2 heights (an RR-2 trade with the stop at
the distal line); *hold 1 ATR* = ≥ 1 ATR(14) at r. A bar that reaches the target and closes through the stop counts
as a fail (the path inside the bar is unknown). Unresolved after 200 bars = not held. Also recorded: bars to return,
MAE and MFE in zone heights, and the outcome at the **second** return of zones that held the first one (freshness).

**Criteria recorded per zone** (all computable before r): David's BOS gate — a `major_structure` BOS / CHoCH of the
zone's side whose move contains the zone candle and whose breaking close comes with the leg-out (≤ 10 bars after it)
and before r; the same with any delay; the zone merely inside a major break's move; the break being a CHoCH; a
fractal version (the leg-out's 3 closes beat the nearest unbroken 3-bar swing); displacement multiple (≥ 2, ≥ 3);
FVG of the leg-out, its size, and David's FVG rule (untouched for 2 candles and a 0.5 ATR run before the first
trade back into it); base count (≤ 2 / ≥ 3); departure (≥ 3 heights, ≥ 2 ATR); leg-out range ≥ 2 heights; height
(≤ 0.5 ATR, > 1 ATR); with / against the major trend at the leg-out; demand in discount / supply in premium of the
major range (protected swing ↔ running extreme) and of the last 100 bars; a liquidity sweep (the base's wick took
the last fractal swing and the leg-out closed back); a round-number level in or at the zone (00/50 pips, $10 gold,
¥0.50, $1,000 BTC); RR ≥ 2 to the nearest live opposing zone; no opposing zone; bars to return (≤ 50, > 200);
session of formation (UTC); and the sensible combinations (gate + FVG, + FVG kept, + trend, + P/D, + sweep, …).

**Baselines.** (i) *Matched controls*: 3 per zone, same side, same height and same distance from the close in ATR
units, at a random bar, run through the same return / departure / outcome rules (139,632 controls). (ii) *Shuffled
candles*: the whole pipeline on a series whose bars were shuffled (each bar keeps its own shape, closes chained):
what the detection mechanics alone produce without any market memory. **Significance**: 95 % bootstrap CI for
zone − control; two-sided permutation test (4,000 draws) for every criterion's lift within the zones; IS and OOS
lifts side by side; and a scan of all 24 symbol × timeframe × method cells per criterion (`scan.txt`) — at 5 %
one expects ≈ 1.2 false positives per criterion.

## 3. Results — do zones hold better than random levels?

### 3.1 V5 zones (David's rule), per symbol / timeframe

| set | zones | hold 1h % | ctrl 1h % | lift pp [95 % CI] | shuf 1h % | hold 1 ATR % | ctrl 1 ATR % | hold 2h % | ctrl 2h % | median wait | MAE h | closed thru % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL FX+GOLD v5 | 20399 | 58.2 | 57.9 | +0.2 [-0.6, +1.0] | 56.7 | 54.5 | 54.8 | 44.9 | 44.6 | 5 | 1.43 | 55.5 |
| FX+GOLD v5 M15 | 16280 | 57.7 | 57.9 | -0.2 [-1.0, +0.7] | 56.3 | 54.2 | 54.8 | 44.6 | 44.6 | 5 | 1.43 | 55.9 |
| FX+GOLD v5 H1 | 4119 | 59.9 | 58.1 | +1.8 [+0.1, +3.5] | 58.2 | 56.0 | 54.9 | 46.3 | 44.7 | 5 | 1.44 | 54.1 |
| GOLD M15 v5 | 3223 | 57.1 | 57.2 | -0.1 [-2.1, +1.9] | 55.9 | 53.7 | 54.2 | 44.8 | 44.5 | 6 | 1.43 | 55.8 |
| GOLD H1 v5 | 827 | 56.5 | 55.6 | +0.8 [-3.0, +4.8] | 58.3 | 50.4 | 51.6 | 43.4 | 42.2 | 6 | 1.46 | 57.3 |
| EURUSD M15 v5 | 3270 | 58.0 | 57.5 | +0.5 [-1.4, +2.5] | 56.3 | 54.1 | 54.7 | 44.2 | 43.7 | 5 | 1.41 | 56.6 |
| EURUSD H1 v5 | 828 | 57.6 | 57.3 | +0.3 [-3.7, +4.1] | 57.2 | 54.6 | 55.3 | 43.7 | 44.9 | 6 | 1.47 | 56.6 |
| GBPUSD M15 v5 | 3313 | 58.2 | 58.3 | -0.1 [-2.1, +1.7] | 57.2 | 54.7 | 55.3 | 45.4 | 45.2 | 5 | 1.40 | 55.1 |
| GBPUSD H1 v5 | 825 | 62.1 | 58.7 | +3.4 [-0.4, +7.2] | 56.8 | 60.6 | 56.7 | 50.3 | 44.7 | 5 | 1.38 | 49.8 |
| USDJPY M15 v5 | 3284 | 58.5 | 57.1 | +1.4 [-0.5, +3.5] | 56.1 | 55.1 | 53.7 | 45.1 | 43.6 | 5 | 1.47 | 55.4 |
| USDJPY H1 v5 | 829 | 62.4 | 57.2 | +5.2 [+1.4, +9.0] | 58.0 | 58.0 | 52.5 | 47.2 | 44.2 | 4 | 1.46 | 53.0 |
| AUDUSD M15 v5 | 3190 | 56.7 | 59.5 | -2.7 [-4.7, -0.8] | 56.1 | 53.2 | 56.0 | 43.4 | 46.1 | 5 | 1.45 | 56.8 |
| AUDUSD H1 v5 | 810 | 61.0 | 61.7 | -0.7 [-4.6, +3.3] | 60.5 | 56.4 | 58.3 | 47.0 | 47.6 | 5 | 1.39 | 53.6 |
| BITCOIN M15 v5 | 3324 | 58.0 | 58.2 | -0.1 [-2.1, +1.8] | 56.5 | 53.4 | 54.8 | 44.0 | 45.1 | 6 | 1.49 | 56.6 |

### 3.2 Classic base zones, per symbol / timeframe

| set | zones | hold 1h % | ctrl 1h % | lift pp [95 % CI] | shuf 1h % | hold 1 ATR % | ctrl 1 ATR % | hold 2h % | ctrl 2h % | median wait | MAE h | closed thru % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL FX+GOLD base | 18707 | 57.5 | 57.3 | +0.2 [-0.5, +1.1] | 55.5 | 51.6 | 52.2 | 46.2 | 46.1 | 5 | 1.54 | 55.8 |
| FX+GOLD base M15 | 14881 | 57.0 | 57.2 | -0.2 [-1.1, +0.8] | 55.2 | 50.8 | 52.0 | 45.5 | 45.9 | 5 | 1.55 | 56.5 |
| FX+GOLD base H1 | 3826 | 59.6 | 57.8 | +1.8 [+0.1, +3.6] | 56.6 | 54.9 | 53.3 | 48.6 | 46.6 | 6 | 1.54 | 52.8 |
| GOLD M15 base | 3007 | 55.6 | 57.2 | -1.6 [-3.6, +0.4] | 53.5 | 50.1 | 52.7 | 45.2 | 46.1 | 6 | 1.53 | 56.6 |
| GOLD H1 base | 746 | 58.7 | 53.3 | +5.4 [+1.3, +9.5] | 54.6 | 54.6 | 48.6 | 49.1 | 43.5 | 6 | 1.53 | 52.0 |
| EURUSD M15 base | 3047 | 57.0 | 56.8 | +0.1 [-1.9, +2.2] | 55.4 | 51.0 | 51.5 | 45.5 | 45.4 | 5 | 1.51 | 56.5 |
| EURUSD H1 base | 773 | 58.1 | 57.4 | +0.7 [-3.5, +4.7] | 58.1 | 53.7 | 53.9 | 45.8 | 46.1 | 6 | 1.58 | 55.5 |
| GBPUSD M15 base | 3034 | 57.1 | 56.8 | +0.2 [-1.8, +2.2] | 55.5 | 50.6 | 52.0 | 45.0 | 45.6 | 5 | 1.56 | 57.2 |
| GBPUSD H1 base | 785 | 60.5 | 58.7 | +1.8 [-2.1, +5.8] | 55.8 | 56.8 | 54.8 | 49.4 | 46.6 | 5 | 1.56 | 52.0 |
| USDJPY M15 base | 2848 | 58.0 | 56.9 | +1.1 [-1.0, +3.2] | 55.3 | 51.6 | 51.4 | 45.8 | 45.8 | 5 | 1.57 | 56.2 |
| USDJPY H1 base | 762 | 58.3 | 58.1 | +0.2 [-3.8, +4.3] | 56.4 | 53.0 | 52.6 | 48.0 | 47.6 | 5 | 1.57 | 53.5 |
| AUDUSD M15 base | 2945 | 57.5 | 58.0 | -0.6 [-2.5, +1.5] | 56.1 | 50.6 | 52.3 | 46.1 | 46.6 | 5 | 1.55 | 56.1 |
| AUDUSD H1 base | 760 | 62.4 | 61.3 | +1.1 [-2.9, +5.1] | 58.3 | 56.4 | 56.4 | 50.8 | 49.4 | 6 | 1.45 | 51.2 |
| BITCOIN M15 base | 2927 | 56.6 | 57.5 | -0.9 [-3.0, +1.2] | 55.2 | 49.8 | 51.9 | 44.7 | 46.5 | 6 | 1.62 | 57.6 |

Reading: hold 1 h ≈ 58 % for zones, ≈ 58 % for matched random levels, ≈ 56 % for zones on shuffled candles. The
≈ 58 % is not an edge — it is what the definition gives a random level (a wick to +1 height is easier than a close
beyond −1 height; median MAE is 1.4–1.5 heights, i.e. the typical return pokes through the distal line before it
resolves). Only 3 of the 24 symbol cells differ from their controls at 5 %, with mixed sign (GOLD H1 base +5.4,
USDJPY H1 V5 +5.2, AUDUSD M15 V5 −2.7) — the expected number of false positives. H1 pooled shows +1.8 pp
[+0.1, +3.5] for both methods; the shuffled-series baseline on H1 (56.6–58.2 %) is within that, so at most a
1–2 pp H1 effect may be real. BITCOIN behaves like FX.

### 3.3 In-sample / out-of-sample

| set | zones | hold 1h % | ctrl 1h % | lift pp [95 % CI] | shuf 1h % | hold 1 ATR % | ctrl 1 ATR % | hold 2h % | ctrl 2h % | median wait | MAE h | closed thru % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FX+GOLD v5 IS | 14396 | 58.2 | 58.1 | +0.2 [-0.7, +1.1] | 56.5 | 54.6 | 54.8 | 45.1 | 44.6 | 5 | 1.43 | 55.4 |
| FX+GOLD v5 M15 IS | 11480 | 57.8 | 58.0 | -0.3 [-1.3, +0.8] | 56.0 | 54.2 | 54.8 | 44.7 | 44.5 | 5 | 1.43 | 55.8 |
| FX+GOLD v5 H1 IS | 2916 | 60.2 | 58.3 | +1.9 [-0.1, +4.0] | 58.5 | 56.4 | 54.8 | 46.7 | 44.8 | 6 | 1.44 | 53.9 |
| FX+GOLD v5 OOS | 6003 | 58.0 | 57.6 | +0.4 [-1.1, +1.8] | 57.2 | 54.4 | 54.8 | 44.6 | 44.7 | 5 | 1.44 | 55.8 |
| FX+GOLD v5 M15 OOS | 4800 | 57.6 | 57.6 | +0.0 [-1.6, +1.6] | 57.1 | 54.2 | 54.8 | 44.4 | 44.8 | 5 | 1.44 | 56.1 |
| FX+GOLD v5 H1 OOS | 1203 | 59.3 | 57.5 | +1.8 [-1.5, +4.9] | 57.5 | 55.1 | 55.0 | 45.4 | 44.4 | 5 | 1.44 | 54.4 |

| set | zones | hold 1h % | ctrl 1h % | lift pp [95 % CI] | shuf 1h % | hold 1 ATR % | ctrl 1 ATR % | hold 2h % | ctrl 2h % | median wait | MAE h | closed thru % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FX+GOLD base IS | 13229 | 57.5 | 57.5 | +0.0 [-1.0, +1.0] | 55.6 | 51.4 | 52.4 | 46.1 | 46.1 | 5 | 1.54 | 55.9 |
| FX+GOLD base M15 IS | 10486 | 57.0 | 57.5 | -0.5 [-1.6, +0.6] | 55.4 | 50.6 | 52.2 | 45.5 | 46.1 | 5 | 1.53 | 56.6 |
| FX+GOLD base H1 IS | 2743 | 59.6 | 57.7 | +1.9 [-0.1, +4.0] | 56.3 | 54.7 | 53.1 | 48.3 | 46.3 | 6 | 1.55 | 53.3 |
| FX+GOLD base OOS | 5478 | 57.6 | 56.7 | +0.8 [-0.7, +2.4] | 55.1 | 52.0 | 52.0 | 46.4 | 45.9 | 5 | 1.56 | 55.4 |
| FX+GOLD base M15 OOS | 4395 | 57.1 | 56.4 | +0.7 [-1.0, +2.4] | 54.6 | 51.2 | 51.5 | 45.7 | 45.5 | 5 | 1.57 | 56.3 |
| FX+GOLD base H1 OOS | 1083 | 59.6 | 58.0 | +1.6 [-1.8, +4.8] | 57.3 | 55.5 | 54.0 | 49.4 | 47.4 | 5 | 1.50 | 51.8 |

### 3.4 Freshness: first vs second return (FX + GOLD)

| set | first return hold % | zones that held then returned | second return hold % |
|---|---|---|---|
| v5 M15 | 57.7 | 9,191 | 58.0 |
| v5 H1 | 59.9 | 2,405 | 59.4 |
| base M15 | 57.0 | 8,336 | 56.7 |
| base H1 | 59.6 | 2,229 | 59.5 |

A zone that already held once holds the second time just as often (per symbol in `tables.md`: −3.1 … +3.9 pp,
no sign pattern). Neither the vendor claim (fresh is best) nor the academic finding (tested is stronger) shows up
at this resolution.

### 3.5 Age, height, departure — zones vs controls in the same bucket (V5, FX + GOLD)

| bars to return | zones n | zones hold % | ctrl n | ctrl hold % | lift pp |
|---|---|---|---|---|---|
| 1-10 | 12804 | 57.8 | 36345 | 58.2 | -0.4 |
| 10-30 | 3461 | 59.5 | 11128 | 59.1 | +0.5 |
| 30-100 | 2111 | 59.8 | 6853 | 57.9 | +1.9 |
| 100-300 | 1087 | 56.2 | 3279 | 55.1 | +1.1 |
| 300-3001 | 936 | 56.8 | 2826 | 53.6 | +3.2 |

| height / ATR | zones n | zones hold % | ctrl n | ctrl hold % | lift pp |
|---|---|---|---|---|---|
| 0-0.5 | 2497 | 55.3 | 7489 | 55.8 | -0.5 |
| 0.5-1 | 12753 | 58.5 | 38084 | 58.4 | +0.2 |
| 1-2 | 5054 | 58.4 | 14610 | 58.0 | +0.5 |
| 2-100 | 95 | 66.3 | 248 | 55.2 | +11.1 |

| departure / height | zones n | zones hold % | ctrl n | ctrl hold % | lift pp |
|---|---|---|---|---|---|
| 1-2 | 7459 | 57.8 | 20292 | 58.0 | -0.1 |
| 2-3 | 3959 | 59.1 | 12496 | 59.0 | +0.1 |
| 3-5 | 3617 | 58.7 | 11626 | 58.3 | +0.3 |
| 5-10 | 2865 | 58.2 | 8771 | 58.5 | -0.3 |
| 10-1000 | 2499 | 56.9 | 7246 | 54.7 | +2.3 |

(Base zones: `tables.md` lines 1027–1050, same picture.) Within every bucket the zone and its control agree to
≈ 2 pp; thin zones (< 0.5 ATR) hold less in absolute terms (55 %) **for zones and controls alike**, old zones
(> 300 bars) a little less, and a huge departure (> 10 heights) is where the only +2–3 pp over control appears.

## 4. Results — which criteria move the hold rate within the zones?

Pooled FX + GOLD, hold = 1 zone height. (1 ATR and 2-height versions and every symbol separately: `tables.md`.)

### 4.1 V5 zones, M15

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 1611 | 57.7 | 57.7 | -0.1 | 0.981 | +0.3 | -1.2 |
| major BOS before the return (any delay) | 2552 | 57.2 | 57.8 | -0.6 | 0.611 | -0.4 | -0.9 |
| zone inside any major break's move | 2590 | 57.4 | 57.8 | -0.4 | 0.749 | -0.1 | -1.2 |
| the break is a CHoCH | 561 | 59.0 | 57.7 | +1.3 | 0.538 | +1.4 | +1.1 |
| BOS gate (3-bar fractal swing) | 7697 | 57.2 | 58.2 | -1.0 | 0.205 | -0.6 | -1.8 |
| displacement >= 2 x avg body | 11417 | 57.5 | 58.2 | -0.6 | 0.474 | -0.8 | -0.2 |
| displacement >= 3 x avg body | 5377 | 56.9 | 58.1 | -1.2 | 0.152 | -1.1 | -1.5 |
| FVG in the leg-out | 12639 | 58.0 | 56.7 | +1.3 | 0.161 | +2.8 | -2.1 |
| FVG >= 0.3 ATR | 8431 | 58.0 | 57.4 | +0.7 | 0.385 | +1.3 | -0.8 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 5790 | 57.9 | 57.6 | +0.3 | 0.729 | +1.0 | -1.4 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 12777 | 57.9 | 57.1 | +0.8 | 0.421 | +0.8 | +0.7 |
| base >= 3 candles | 3503 | 57.1 | 57.9 | -0.8 | 0.433 | -0.8 | -0.7 |
| departure >= 3 zone heights before the return | 7121 | 57.6 | 57.8 | -0.2 | 0.847 | -0.5 | +0.5 |
| departure >= 2 ATR before the return | 8484 | 58.2 | 57.2 | +1.1 | 0.170 | +1.7 | -0.5 |
| leg-out candle range >= 2 zone heights | 7403 | 56.9 | 58.4 | -1.6 | 0.044 | -2.2 | -0.1 |
| zone height <= 0.5 ATR | 1882 | 54.4 | 58.2 | -3.8 | 0.002 | -5.2 | -0.8 |
| zone height > 1 ATR | 4109 | 59.0 | 57.3 | +1.7 | 0.062 | +2.6 | -0.5 |
| with the major trend | 8165 | 57.7 | 57.8 | -0.1 | 0.936 | -0.3 | +0.5 |
| against the major trend | 8101 | 57.8 | 57.7 | +0.1 | 0.899 | +0.3 | -0.5 |
| demand in discount / supply in premium (major range) | 8217 | 58.3 | 57.1 | +1.2 | 0.119 | +1.2 | +1.1 |
| ... of the last 100 bars' range | 8319 | 58.6 | 56.8 | +1.8 | 0.017 | +1.6 | +2.3 |
| liquidity sweep just before the leg-out | 3616 | 59.6 | 57.2 | +2.4 | 0.008 | +2.5 | +2.2 |
| round-number level in / at the zone | 3294 | 59.0 | 57.4 | +1.6 | 0.097 | +1.7 | +1.3 |
| RR >= 2 to the nearest live opposing zone | 9683 | 58.0 | 57.3 | +0.7 | 0.365 | +1.4 | -1.0 |
| no live opposing zone above / below | 387 | 56.3 | 57.8 | -1.4 | 0.604 | -2.4 | +3.7 |
| returned within 50 bars | 13867 | 57.9 | 56.6 | +1.4 | 0.211 | +0.5 | +3.4 |
| returned after > 200 bars | 987 | 55.9 | 57.8 | -1.9 | 0.252 | -2.0 | -1.8 |
| formed in Asia (00-07 UTC) | 5101 | 58.0 | 57.6 | +0.4 | 0.680 | -0.7 | +2.8 |
| formed in London (07-12 UTC) | 3362 | 59.0 | 57.4 | +1.7 | 0.085 | +1.6 | +1.9 |
| formed in London/NY overlap (12-16 UTC) | 2781 | 58.2 | 57.6 | +0.6 | 0.550 | +1.2 | -1.0 |
| BOS gate + FVG | 1465 | 57.7 | 57.7 | -0.0 | 0.979 | +0.1 | -0.4 |
| BOS gate + FVG kept | 960 | 57.6 | 57.7 | -0.1 | 0.948 | -0.7 | +1.4 |
| BOS gate + with trend | 1046 | 57.1 | 57.8 | -0.7 | 0.662 | -0.1 | -2.3 |
| BOS gate + discount/premium | 179 | 57.5 | 57.7 | -0.2 | 1.000 | -1.4 | +3.3 |
| BOS gate + sweep | 238 | 60.9 | 57.7 | +3.3 | 0.316 | +2.2 | +6.7 |
| BOS gate + FVG + with trend | 949 | 56.6 | 57.8 | -1.2 | 0.468 | -0.7 | -2.8 |
| BOS gate + FVG + discount/premium | 175 | 57.1 | 57.7 | -0.6 | 0.879 | -2.1 | +3.8 |
| BOS gate + departure >= 3 h | 1227 | 57.7 | 57.7 | -0.0 | 1.000 | -0.2 | +0.4 |
| fractal BOS + FVG | 6463 | 57.3 | 58.0 | -0.7 | 0.393 | +0.3 | -2.9 |
| FVG + departure >= 3 h | 6531 | 57.7 | 57.7 | -0.0 | 0.987 | -0.1 | +0.1 |
| sweep + FVG | 2899 | 59.2 | 57.4 | +1.8 | 0.076 | +2.7 | -0.5 |
| sweep + major BOS before return | 496 | 57.7 | 57.7 | -0.1 | 1.000 | -0.4 | +0.8 |
| with trend + discount/premium | 2466 | 58.7 | 57.5 | +1.2 | 0.274 | +0.5 | +2.5 |
| NO major BOS (David: invalid) | 14669 | 57.7 | 57.7 | +0.1 | 0.978 | -0.3 | +1.2 |

### 4.2 V5 zones, H1

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 466 | 58.8 | 60.0 | -1.2 | 0.609 | -0.4 | -4.1 |
| major BOS before the return (any delay) | 714 | 59.7 | 59.9 | -0.3 | 0.898 | +1.1 | -4.8 |
| zone inside any major break's move | 719 | 59.7 | 59.9 | -0.3 | 0.900 | +1.1 | -4.8 |
| the break is a CHoCH | 171 | 61.4 | 59.8 | +1.6 | 0.691 | +2.8 | -4.5 |
| BOS gate (3-bar fractal swing) | 1957 | 60.2 | 59.6 | +0.6 | 0.732 | +0.3 | +1.3 |
| displacement >= 2 x avg body | 3056 | 60.3 | 58.7 | +1.6 | 0.359 | +4.0 | -4.1 |
| displacement >= 3 x avg body | 1599 | 60.0 | 59.8 | +0.2 | 0.891 | +1.9 | -3.7 |
| FVG in the leg-out | 3055 | 59.9 | 59.9 | +0.0 | 1.000 | -0.2 | +0.4 |
| FVG >= 0.3 ATR | 2024 | 60.0 | 59.8 | +0.3 | 0.869 | +0.2 | +0.4 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 1448 | 59.8 | 59.9 | -0.1 | 0.948 | +0.9 | -2.5 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 3308 | 60.9 | 55.9 | +5.0 | 0.010 | +4.8 | +5.6 |
| base >= 3 candles | 811 | 55.9 | 60.9 | -5.0 | 0.011 | -4.8 | -5.6 |
| departure >= 3 zone heights before the return | 1860 | 59.5 | 60.2 | -0.7 | 0.654 | +0.3 | -3.0 |
| departure >= 2 ATR before the return | 2138 | 59.4 | 60.4 | -1.0 | 0.502 | -0.9 | -1.4 |
| leg-out candle range >= 2 zone heights | 2150 | 60.6 | 59.2 | +1.4 | 0.361 | +3.7 | -4.1 |
| zone height <= 0.5 ATR | 617 | 58.3 | 60.2 | -1.8 | 0.401 | -0.8 | -4.4 |
| zone height > 1 ATR | 1035 | 57.1 | 60.8 | -3.7 | 0.032 | -5.5 | +0.6 |
| with the major trend | 2071 | 59.7 | 60.1 | -0.3 | 0.853 | -2.3 | +4.5 |
| against the major trend | 2039 | 60.2 | 59.6 | +0.6 | 0.733 | +2.6 | -4.5 |
| demand in discount / supply in premium (major range) | 2125 | 59.6 | 60.2 | -0.6 | 0.732 | +0.1 | -2.2 |
| ... of the last 100 bars' range | 2119 | 60.1 | 59.7 | +0.5 | 0.788 | +0.7 | +0.1 |
| liquidity sweep just before the leg-out | 848 | 57.9 | 60.4 | -2.5 | 0.182 | -1.2 | -5.9 |
| round-number level in / at the zone | 1439 | 57.5 | 61.2 | -3.7 | 0.021 | -3.3 | -4.8 |
| RR >= 2 to the nearest live opposing zone | 2458 | 60.0 | 59.7 | +0.4 | 0.822 | +1.0 | -1.1 |
| no live opposing zone above / below | 177 | 58.2 | 60.0 | -1.8 | 0.635 | -2.1 | -1.0 |
| returned within 50 bars | 3496 | 59.6 | 61.3 | -1.7 | 0.447 | -4.1 | +5.9 |
| returned after > 200 bars | 249 | 59.8 | 59.9 | -0.1 | 1.000 | +3.2 | -9.8 |
| formed in Asia (00-07 UTC) | 1400 | 61.2 | 59.2 | +2.0 | 0.219 | +0.4 | +5.9 |
| formed in London (07-12 UTC) | 1005 | 58.6 | 60.3 | -1.7 | 0.354 | -0.4 | -4.5 |
| formed in London/NY overlap (12-16 UTC) | 677 | 62.5 | 59.4 | +3.1 | 0.133 | +1.1 | +8.4 |
| BOS gate + FVG | 421 | 58.7 | 60.0 | -1.4 | 0.604 | -0.8 | -3.4 |
| BOS gate + FVG kept | 279 | 60.6 | 59.8 | +0.7 | 0.840 | +0.7 | +0.8 |
| BOS gate + with trend | 289 | 57.8 | 60.1 | -2.3 | 0.460 | -1.8 | -3.7 |
| BOS gate + discount/premium | 59 | 55.9 | 60.0 | -4.0 | 0.593 | -1.5 | -13.3 |
| BOS gate + sweep | 60 | 63.3 | 59.8 | +3.5 | 0.602 | +5.3 | -9.3 |
| BOS gate + FVG + with trend | 258 | 58.1 | 60.0 | -1.9 | 0.557 | -1.9 | -2.0 |
| BOS gate + FVG + discount/premium | 58 | 56.9 | 59.9 | -3.0 | 0.686 | -0.2 | -13.3 |
| BOS gate + departure >= 3 h | 368 | 57.1 | 60.2 | -3.1 | 0.256 | -3.2 | -3.2 |
| fractal BOS + FVG | 1610 | 60.4 | 59.5 | +0.9 | 0.582 | +0.5 | +1.9 |
| FVG + departure >= 3 h | 1668 | 59.7 | 60.1 | -0.4 | 0.798 | +0.6 | -2.9 |
| sweep + FVG | 651 | 58.1 | 60.2 | -2.2 | 0.319 | -1.3 | -4.4 |
| sweep + major BOS before return | 128 | 55.5 | 60.0 | -4.6 | 0.317 | -2.5 | -13.7 |
| with trend + discount/premium | 645 | 58.9 | 60.1 | -1.2 | 0.590 | -3.1 | +2.9 |
| NO major BOS (David: invalid) | 3653 | 60.0 | 58.8 | +1.2 | 0.626 | +0.4 | +4.1 |

### 4.3 Base zones, M15

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 1432 | 54.2 | 57.3 | -3.1 | 0.025 | -2.3 | -5.4 |
| major BOS before the return (any delay) | 2264 | 55.4 | 57.3 | -1.9 | 0.090 | -1.7 | -2.6 |
| zone inside any major break's move | 2321 | 55.4 | 57.3 | -1.9 | 0.093 | -1.7 | -2.5 |
| the break is a CHoCH | 506 | 57.3 | 57.0 | +0.3 | 0.897 | +0.7 | -0.8 |
| BOS gate (3-bar fractal swing) | 6363 | 56.0 | 57.8 | -1.7 | 0.029 | -1.6 | -2.1 |
| displacement >= 2 x avg body | 9934 | 56.4 | 58.2 | -1.8 | 0.035 | -1.8 | -1.9 |
| displacement >= 3 x avg body | 4391 | 55.8 | 57.5 | -1.7 | 0.069 | -2.1 | -0.6 |
| FVG in the leg-out | 9808 | 57.8 | 55.5 | +2.3 | 0.007 | +2.2 | +2.4 |
| FVG >= 0.3 ATR | 6420 | 57.4 | 56.7 | +0.7 | 0.416 | +0.6 | +0.9 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 4226 | 58.0 | 56.6 | +1.3 | 0.134 | +1.4 | +1.1 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 11605 | 56.5 | 58.9 | -2.4 | 0.019 | -1.8 | -3.8 |
| base >= 3 candles | 3276 | 58.9 | 56.5 | +2.4 | 0.016 | +1.8 | +3.8 |
| departure >= 3 zone heights before the return | 8401 | 56.3 | 57.9 | -1.6 | 0.045 | -1.1 | -2.8 |
| departure >= 2 ATR before the return | 7817 | 57.2 | 56.9 | +0.3 | 0.721 | +0.7 | -0.6 |
| leg-out candle range >= 2 zone heights | 8820 | 56.0 | 58.5 | -2.6 | 0.003 | -2.3 | -3.3 |
| zone height <= 0.5 ATR | 4866 | 54.4 | 58.3 | -3.9 | <0.001 | -2.7 | -6.7 |
| zone height > 1 ATR | 2698 | 57.9 | 56.8 | +1.1 | 0.283 | +0.9 | +1.5 |
| with the major trend | 7483 | 56.4 | 57.7 | -1.3 | 0.106 | -1.5 | -0.8 |
| against the major trend | 7387 | 57.7 | 56.3 | +1.4 | 0.093 | +1.6 | +0.8 |
| demand in discount / supply in premium (major range) | 7514 | 57.8 | 56.2 | +1.6 | 0.047 | +0.8 | +3.5 |
| ... of the last 100 bars' range | 7601 | 57.7 | 56.3 | +1.4 | 0.084 | +1.1 | +2.1 |
| liquidity sweep just before the leg-out | 3010 | 58.2 | 56.7 | +1.5 | 0.161 | +0.7 | +3.3 |
| round-number level in / at the zone | 2712 | 57.1 | 57.0 | +0.1 | 0.946 | +1.3 | -3.2 |
| RR >= 2 to the nearest live opposing zone | 10796 | 57.1 | 56.7 | +0.4 | 0.650 | +1.9 | -3.1 |
| no live opposing zone above / below | 454 | 54.4 | 57.1 | -2.7 | 0.274 | -2.9 | -1.4 |
| returned within 50 bars | 12618 | 57.0 | 56.9 | +0.2 | 0.888 | -0.6 | +2.2 |
| returned after > 200 bars | 907 | 53.6 | 57.2 | -3.7 | 0.029 | -2.4 | -7.7 |
| formed in Asia (00-07 UTC) | 4811 | 57.2 | 56.9 | +0.3 | 0.695 | +0.1 | +0.8 |
| formed in London (07-12 UTC) | 3195 | 58.2 | 56.7 | +1.5 | 0.142 | +1.5 | +1.6 |
| formed in London/NY overlap (12-16 UTC) | 2727 | 57.3 | 57.0 | +0.3 | 0.759 | -0.2 | +1.8 |
| BOS gate + FVG | 1162 | 53.7 | 57.3 | -3.6 | 0.018 | -2.7 | -6.4 |
| BOS gate + FVG kept | 735 | 53.6 | 57.2 | -3.6 | 0.053 | -2.9 | -5.6 |
| BOS gate + with trend | 923 | 52.7 | 57.3 | -4.6 | 0.004 | -3.6 | -7.7 |
| BOS gate + discount/premium | 165 | 56.4 | 57.0 | -0.7 | 0.881 | -3.5 | +8.8 |
| BOS gate + sweep | 168 | 57.1 | 57.0 | +0.1 | 1.000 | +0.8 | -1.5 |
| BOS gate + FVG + with trend | 741 | 51.1 | 57.3 | -6.2 | 0.002 | -4.8 | -10.3 |
| BOS gate + FVG + discount/premium | 141 | 57.4 | 57.0 | +0.4 | 0.927 | -1.1 | +6.3 |
| BOS gate + departure >= 3 h | 1182 | 53.6 | 57.3 | -3.8 | 0.010 | -2.9 | -6.4 |
| fractal BOS + FVG | 4815 | 56.8 | 57.1 | -0.3 | 0.718 | -0.4 | -0.1 |
| FVG + departure >= 3 h | 6518 | 57.2 | 56.9 | +0.3 | 0.724 | +0.3 | +0.3 |
| sweep + FVG | 2048 | 58.5 | 56.8 | +1.8 | 0.135 | +1.2 | +3.4 |
| sweep + major BOS before return | 359 | 55.7 | 57.0 | -1.3 | 0.623 | -1.6 | -0.6 |
| with trend + discount/premium | 2241 | 57.3 | 57.0 | +0.4 | 0.749 | -0.8 | +2.9 |
| NO major BOS (David: invalid) | 13449 | 57.3 | 54.2 | +3.1 | 0.029 | +2.3 | +5.4 |

### 4.4 Base zones, H1

| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |
|---|---|---|---|---|---|---|---|
| BOS gate (David's major structure, break within 10 bars) | 413 | 60.5 | 59.5 | +1.1 | 0.709 | +1.2 | +0.5 |
| major BOS before the return (any delay) | 641 | 60.4 | 59.4 | +0.9 | 0.658 | +1.6 | -1.5 |
| zone inside any major break's move | 655 | 60.5 | 59.4 | +1.0 | 0.640 | +1.6 | -1.0 |
| the break is a CHoCH | 155 | 63.9 | 59.4 | +4.5 | 0.268 | +4.0 | +6.3 |
| BOS gate (3-bar fractal swing) | 1723 | 60.0 | 59.2 | +0.8 | 0.642 | +1.4 | -0.9 |
| displacement >= 2 x avg body | 2726 | 60.1 | 58.3 | +1.9 | 0.294 | +3.1 | -1.2 |
| displacement >= 3 x avg body | 1285 | 61.3 | 58.7 | +2.6 | 0.119 | +3.6 | +0.2 |
| FVG in the leg-out | 2444 | 60.1 | 58.7 | +1.4 | 0.391 | +1.4 | +1.6 |
| FVG >= 0.3 ATR | 1592 | 60.5 | 59.0 | +1.5 | 0.347 | +2.8 | -1.6 |
| FVG kept (David: untouched 2 candles, 0.5 ATR run) | 1093 | 59.9 | 59.5 | +0.5 | 0.794 | +1.8 | -2.9 |
| base <= 2 candles (V5: opposite candle <= 2 bars before) | 3015 | 58.8 | 62.5 | -3.7 | 0.053 | -4.2 | -2.4 |
| base >= 3 candles | 811 | 62.5 | 58.8 | +3.7 | 0.059 | +4.2 | +2.4 |
| departure >= 3 zone heights before the return | 2163 | 58.6 | 60.9 | -2.2 | 0.169 | -2.2 | -2.2 |
| departure >= 2 ATR before the return | 2034 | 59.7 | 59.5 | +0.2 | 0.924 | +0.9 | -1.5 |
| leg-out candle range >= 2 zone heights | 2354 | 58.8 | 60.8 | -2.0 | 0.231 | -1.7 | -2.5 |
| zone height <= 0.5 ATR | 1243 | 57.2 | 60.7 | -3.5 | 0.034 | -3.9 | -2.6 |
| zone height > 1 ATR | 747 | 60.6 | 59.3 | +1.3 | 0.542 | +1.0 | +2.0 |
| with the major trend | 1905 | 59.7 | 59.5 | +0.2 | 0.919 | -1.8 | +5.3 |
| against the major trend | 1917 | 59.5 | 59.7 | -0.1 | 0.952 | +1.9 | -5.3 |
| demand in discount / supply in premium (major range) | 1933 | 59.3 | 59.9 | -0.5 | 0.766 | -0.0 | -1.7 |
| ... of the last 100 bars' range | 1910 | 59.1 | 60.1 | -1.1 | 0.519 | -1.0 | -1.2 |
| liquidity sweep just before the leg-out | 724 | 58.6 | 59.8 | -1.3 | 0.550 | -0.4 | -3.8 |
| round-number level in / at the zone | 1236 | 59.5 | 59.6 | -0.1 | 0.976 | +1.2 | -3.5 |
| RR >= 2 to the nearest live opposing zone | 2665 | 59.5 | 59.8 | -0.3 | 0.883 | -0.1 | -0.6 |
| no live opposing zone above / below | 176 | 57.4 | 59.7 | -2.3 | 0.578 | -1.4 | -7.7 |
| returned within 50 bars | 3253 | 59.9 | 58.1 | +1.7 | 0.456 | +0.4 | +6.0 |
| returned after > 200 bars | 225 | 56.0 | 59.8 | -3.8 | 0.268 | -2.1 | -9.1 |
| formed in Asia (00-07 UTC) | 1403 | 58.4 | 60.3 | -1.9 | 0.246 | -1.6 | -2.8 |
| formed in London (07-12 UTC) | 984 | 62.1 | 58.7 | +3.4 | 0.065 | +3.2 | +3.9 |
| formed in London/NY overlap (12-16 UTC) | 716 | 59.1 | 59.7 | -0.6 | 0.776 | -1.4 | +1.4 |
| BOS gate + FVG | 341 | 58.7 | 59.7 | -1.0 | 0.730 | -1.0 | -1.2 |
| BOS gate + FVG kept | 223 | 60.1 | 59.6 | +0.5 | 0.898 | +1.9 | -4.0 |
| BOS gate + with trend | 257 | 58.8 | 59.7 | -0.9 | 0.783 | -0.3 | -2.8 |
| BOS gate + discount/premium | 46 | 58.7 | 59.6 | -0.9 | 1.000 | +0.4 | -5.1 |
| BOS gate + sweep | 50 | 64.0 | 59.5 | +4.5 | 0.558 | +2.9 | +10.5 |
| BOS gate + FVG + with trend | 213 | 58.2 | 59.7 | -1.5 | 0.706 | -0.5 | -4.7 |
| BOS gate + FVG + discount/premium | 40 | 60.0 | 59.6 | +0.4 | 1.000 | +0.4 | +0.4 |
| BOS gate + departure >= 3 h | 335 | 57.9 | 59.8 | -1.8 | 0.527 | -2.7 | +1.1 |
| fractal BOS + FVG | 1278 | 60.7 | 59.0 | +1.7 | 0.318 | +2.5 | -0.4 |
| FVG + departure >= 3 h | 1653 | 58.4 | 60.5 | -2.1 | 0.187 | -1.7 | -3.2 |
| sweep + FVG | 494 | 60.5 | 59.5 | +1.1 | 0.661 | +1.5 | -0.2 |
| sweep + major BOS before return | 110 | 60.9 | 59.6 | +1.4 | 0.849 | +0.6 | +4.2 |
| with trend + discount/premium | 538 | 60.0 | 59.5 | +0.5 | 0.857 | -1.2 | +4.8 |
| NO major BOS (David: invalid) | 3413 | 59.5 | 60.5 | -1.1 | 0.697 | -1.2 | -0.5 |

### 4.5 Consistency across all 24 symbol × timeframe × method cells (`scan.txt`)

| criterion | cells p < 0.05 (+ / −) | cells with lift > 0 (of 24) | IS and OOS same sign (of 24) | pooled lift M15 v5 / base, H1 v5 / base |
|---|---|---|---|---|
| BOS gate (David's major structure) | 0 / 1 | 13 | 13 | −0.1 / −3.1 / −1.2 / +1.1 |
| major BOS before the return (any delay) | 0 / 0 | 13 | 9 | −0.6 / −1.9 / −0.3 / +0.9 |
| the break is a CHoCH | 0 / 0 | 14 | 10 | +1.3 / +0.3 / +1.6 / +4.5 |
| BOS gate (3-bar fractal) | 0 / 1 | 8 | 12 | −1.0 / −1.7 / +0.6 / +0.8 |
| displacement ≥ 2× / ≥ 3× | 0 / 0, 0 / 1 | 12, 10 | 9, 8 | −0.6 / −1.8 / +1.6 / +1.9 |
| FVG in the leg-out | 3 / 0 | 17 | 10 | +1.3 / +2.3 / +0.0 / +1.4 |
| FVG kept (David's rule) | 3 / 0 | 13 | 13 | +0.3 / +1.3 / −0.1 / +0.5 |
| base ≤ 2 candles | 1 / 2 | 11 | 11 | +0.8 / −2.4 / +5.0 / −3.7 |
| departure ≥ 3 h | 1 / 3 | 9 | 11 | −0.2 / −1.6 / −0.7 / −2.2 |
| departure ≥ 2 ATR | 2 / 0 | 12 | 14 | +1.1 / +0.3 / −1.0 / +0.2 |
| zone height ≤ 0.5 ATR | 0 / 6 | 5 | 12 | −3.8 / −3.9 / −1.8 / −3.5 |
| with the major trend | 0 / 0 | 14 | 8 | −0.1 / −1.3 / −0.3 / +0.2 |
| discount / premium (major range) | 0 / 0 | 14 | 10 | +1.2 / +1.6 / −0.6 / −0.5 |
| discount / premium (100 bars) | 1 / 0 | 17 | 8 | +1.8 / +1.4 / +0.5 / −1.1 |
| liquidity sweep | 1 / 0 | 11 | 12 | +2.4 / +1.5 / −2.5 / −1.3 |
| round number | 0 / 0 | 13 | 9 | +1.6 / +0.1 / −3.7 / −0.1 |
| RR ≥ 2 to the opposing zone | 0 / 1 | 14 | 10 | +0.7 / +0.4 / +0.4 / −0.3 |
| returned after > 200 bars | 0 / 0 | 9 | 13 | −1.9 / −3.7 / −0.1 / −3.8 |
| London session | 2 / 1 | 14 | 9 | +1.7 / +1.5 / −1.7 / +3.4 |
| BOS gate + FVG | 0 / 0 | 11 | 10 | −0.0 / −3.6 / −1.4 / −1.0 |
| BOS gate + FVG kept | 0 / 0 | 11 | 16 | −0.1 / −3.6 / +0.7 / +0.5 |
| BOS gate + FVG + trend | 0 / 0 | 7 | 14 | −1.2 / −6.2 / −1.9 / −1.5 |
| BOS gate + sweep | 0 / 0 | 10 | 8 | +3.3 / +0.1 / +3.5 / +4.5 |
| NO major BOS (David: "invalid") | 1 / 0 | 11 | 13 | +0.1 / +3.1 / +1.2 / −1.1 |

Only one row beats the false-positive rate in the same direction: **zone height ≤ 0.5 ATR is worse** (6 of 24
cells, −2 … −4 pp, IS and OOS both negative) — and §3.5 shows the matched controls are equally worse, so it is
geometry (a thin box resolves on noise), not zone quality. The FVG is the only "positive" criterion with any
consistency (3 cells, 17 of 24 positive, +1–2 pp on M15, 0 on H1). The base count flips sign between the two zone
definitions; the sweep, premium / discount, session and round number are +1–2 pp on one timeframe and −1–4 pp on
the other; the BOS gate, trend, displacement multiple, departure and RR do nothing anywhere. BOS-gated zones
compared with the random controls directly: V5 M15 57.7 % vs 57.9 %, V5 H1 58.8 % vs 58.1 %, base M15 54.2 % vs
57.2 % (CI −5.7 … −0.4), base H1 60.5 % vs 57.8 % (CI −2.2 … +7.6).

### 4.6 As a trade

With the stop at the distal line as a *close* (the hold definition), hold 2 h ≈ 45–49 % for zones and controls, so
an RR-2 first-touch trade looks positive — but the median MAE of 1.4–1.5 heights says the stop is really 1.5 heights
deep. With a **hard stop** at the distal line (any wick), the target at 1 height is reached first in only
30.5 % (V5 M15), 32.1 % (V5 H1), 28.8 % (base M15), 30.2 % (base H1) of zones — controls 30.7 / 30.6 / 28.7 /
28.9 % (break-even 50 %). Measured conservatively (MAE counted until the 2-height resolution), but the comparison
is the point: the first touch of a zone is not a better entry than the first touch of a random level, and both
lose at RR 1 with a tight stop. (The TradingView placebo study, Backtrex's 38 % win and indicatoredge's 40 % median
say the same for order blocks.)

## 5. Recommendation for the /smc page

**What "valid" can honestly mean.** Not "more likely to hold" — nothing in 39,106 zones or in the literature
supports a reliability claim for any S&D qualifier. It can mean *meets the method's definition and is still
intact*, and that is a legitimate reason to show few zones instead of six a day:

Define **valid** (gate — a zone without these is not drawn) as:
1. **David's rule, as the method's definition**: the last opposite candle before a displacement (body ≥ 1.5 × the
   previous 10) whose move **closes through a confirmed swing** of the major structure — his BOS gate. It is the
   rule he trades by and the standard SMC definition (ICT, LuxAlgo, the TradingView OB-statistics script all seed
   the block from a close-based structure break); state on the page that it is a *structure* filter. On GOLD M15 it
   leaves 0.8 zones a day of 6.3 (the fractal-swing version leaves 3.0).
2. **Still intact**: no close beyond the distal line since the leg-out (David's V5 §33 and the LuxAlgo "close"
   mitigation setting); after a close through it the box becomes a breaker candidate, not a zone.
3. **Geometry**: height ≥ 0.5 ATR(14) (thin boxes resolve on noise, −4 pp in absolute terms, 6 of 24 cells), the
   leg-out closed beyond the proximal line and price left by ≥ 1 height (otherwise there is no zone to return to).
4. **Age**: expire after ~300 bars without a return (−2 … −4 pp absolute, 13 of 24 cells same sign; `smc_marks`
   uses 600 for a stale OB — 300 is closer to the data).

Everything else is **display only** — label it, never filter by it or imply odds: fresh / tested (the second return
holds as often as the first), base candle count, departure strength and displacement multiple, FVG present / kept
(keep it as David's *setup* trigger, it is worth at most +1–2 pp on M15 as a zone qualifier), with / against the
trend, premium / discount, sweep, session, round number, RR to the next zone. If the page shows a "quality" score
built from these, it is folklore; the honest alternative is to show the measured number next to the zone
("zones like this held 58 % of first returns on GOLD M15 — the same as a random level"), which the script can
produce per symbol / timeframe.

**How S&D differs from the OB layer on this data.** The classic base zone and David's V5 candle select different
boxes (the base needs small-bodied candles and a leg-in; the V5 candle may be a large opposite candle, and
`smc_marks` takes the *last* displacement before the break) but behave identically: 57.5 % vs 58.2 % hold, same
controls, same criterion pattern. Showing both as separate "valid" layers would double the clutter for no
information; show one box per structure break (the V5 candle, which the engine already draws) and, if a base
exists, extend the box to the base's extreme wick as the distal line.

**Caveats.** 16 months of one broker's data, two timeframes; "hold" is a price-action definition (no spread, no
slippage); the BOS-gated subsets are small on H1 (≈ 400–470 zones); 45 criteria × 24 cells invites false
positives, which is why only sign-consistent, IS/OOS-stable effects are reported as real. Nothing here says the
zones are useless as *locations* for David's entry logic (M5 BOS after the retrace, FVG trigger) — that is a
different test; it says the zone's own validity criteria do not predict whether the first return holds.
