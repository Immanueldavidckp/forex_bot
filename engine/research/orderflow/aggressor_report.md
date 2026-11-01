# Estimating buy vs sell ("aggressor") volume per price level from FxPro MT5 quotes — research + verification

Date 2026-10-29. Research only; nothing under ~/forex was touched. Files in this folder:
`classify_eval.py` (classifier evaluation, numpy only), `depth_eval.py` (depth-of-market analysis), `explore.py`
(tick facts), `results.json`, `depth_results.json`, `run2.log` (full output of classify_eval.py).

## 0. One-paragraph answer

FxPro's MT5 feed has no trades: BUY/SELL flags are never set, `last` == bid on 97 % of ticks, `volume` is a
constant quote size. The only information that exists is the direction of quote changes and their count. So a
footprint built from this feed is a **quote-change footprint**: "buy" = number of ticks on which the quote moved up
at that price, "sell" = number on which it moved down. The literature on trade classification (tick rule, Lee-Ready,
BVC, ...) all assumes real trades and reports 70-85 % accuracy *with* trades; with quotes only, no accuracy
figure exists and none can be measured on our data (there is no ground truth). On our 3 days of GOLD and EURUSD the
quote-only deltas agree with each other on sign 65-99 % of the time, agree with the bar's own return by
construction (Spearman 0.4-0.8 for the tick rule, 0.94-0.98 for BVC), and have **no** statistically significant
power to predict the next M1/M5/M15 bar's return (all permutation p > 0.05 except where plain return
autocorrelation explains it). **Recommendation: bid tick rule, changed-quotes only (unchanged ticks count 0),
unit weight per tick, binned at the chart's price step; label the chart "estimated from quote changes — not real
orders"; do not use FxPro's depth for a heatmap** (fixed aggregator tiers that slide with the price, totals constant
to the lot).

## 1. What the data contains (explore.py / classify_eval.py facts)

| fact | GOLD | EURUSD |
|---|---|---|
| ticks (71 h, 2026-10-26 14:37 → 10-29 13:37 UTC) | 2 822 368 | 1 297 581 |
| ticks per active second (mean / p99 / max) | 11.7 / 20 / 24 | 6.0 / 16 / 20 |
| ticks that change neither bid nor ask | **65.2 %** | **85.1 %** |
| ticks where bid changed | 34.6 % | 14.7 % |
| sign(Δbid) ≠ sign(Δask) | 0.46 % | 0.31 % |
| median spread (points) | 15 (0.15 $) | 2 (0.2 pip) |
| `last` == bid | 97.0 % | 97.7 % |
| mean abs Δbid when it changes (points) | 4.7 | 1.3 |
| flag combos seen | 24, 280, 1026, 1028, 1030 | + 6 |
| BUY / SELL flag ticks | 0 | 0 |

Flags: 24 = LAST|VOLUME, 280 = LAST|VOLUME|256, 1030 = BID|ASK|1024, 1026/1028 = one-sided (bits 256/1024 are not
documented in MqlTick). Flag-24 ticks never change bid or ask; flag-280 ticks change the quote only on 53 % (GOLD)
/ 17 % (EURUSD) of occurrences. The repeated no-change ticks are the aggregator re-sending the same top of book
(e.g. a different liquidity provider refreshing). Bid and ask move together on 99.4 % of changes: the broker quotes
a near-fixed spread around a mid, so the bid, mid and ask tick rules are the same classifier up to a few ticks.

**Up/down asymmetry (why a tick-count CVD drifts away from price).** GOLD: 483 385 up-ticks (mean step 4.75 pts)
vs 492 097 down-ticks (4.67 pts): net count −8 712 while the price rose +1 399 pts. A count-based CVD therefore
went *down* over 3 days while gold went *up* (Pearson of CVD vs close level −0.60 for GOLD, +0.56 EURUSD). This is
the known property of tick/count deltas: they count moves, not size, so a market that rises in few big steps and
falls in many small ones shows "selling" CVD into a rally. BVC's CVD tracks price almost by construction (+0.97 on
EURUSD).

## 2. Bid-ask flicker (c)

A "flicker" = a bid change that is undone by the next bid change back to the exact previous price.

| | GOLD | EURUSD |
|---|---|---|
| share of bid changes that are flicker | 10.9 % | **47.7 %** |
| sign reversal between consecutive bid changes | 47.5 % | 61.4 % |
| flicker undone within 1 s / 5 s | 85 % / 99.8 % | 44 % / 87 % |
| mean no-change ticks between move and its reversal | 3.2 | 6.8 |
| net delta per flicker pair, tick test (carry) | −0.03 | +0.01 |
| net delta per flicker pair, changed-only rule | 0 | 0 |

EURUSD is quoted in 1-point steps (81 % of changes are 1 point), so almost half of its quote changes are
oscillation between two adjacent prices — exactly Roll-1984 bid-ask bounce, which the trade-classification papers
identify as the tick rule's main error source. The changed-only rule nets each flicker pair to zero but still adds
2 ticks of "volume"; the carry-forward tick test (Lee-Ready's tick test applied to the quote) additionally gives all
the no-change ticks in between the sign of the move, so flicker runs get amplified. On average the carried sign
cancels (net ≈ 0 per pair), but per bar it is noise: 65 % (GOLD) / 85 % (EURUSD) of all ticks are carried signs
under the tick test.

## 3. Methods evaluated (classify_eval.py)

Per-tick sign s ∈ {−1, 0, +1}; bar delta = Σ s; CVD = cumulative delta; one tick = one unit of "volume" (the
broker's `volume` field is a constant and carries no information).

| key | rule |
|---|---|
| bid_tt / mid_tt / ask_tt | tick test on the bid / mid / ask: sign(Δp); unchanged tick carries the previous non-zero sign |
| bid_chg / mid_chg | sign(Δp), unchanged tick = 0 (count only quote updates on which the price changed) |
| bvc_n | Bulk Volume Classification on M1 bars: buy share = Φ(ΔP/σ), σ = trailing 120-bar std of close-to-close ΔP, normal CDF |
| bvc_t | same with Student-t CDF, ν = 0.25 (the setting ELO 2012 use); own numpy implementation, max error vs scipy 1e-14 |
| bvc_n5 | BVC directly on M5 bars (σ over 48 bars) |
| last_q | quote rule on `last` vs mid — degenerate: 99.7 % "sell" because last == bid |

### 3a. Agreement between methods — M5 bars (sign agreement below the diagonal, Pearson above)

GOLD (817 bars):

|  | bid_tt | mid_tt | ask_tt | bid_chg | mid_chg | bvc_n | bvc_t | bvc_n5 |
|---|---|---|---|---|---|---|---|---|
| bid_tt | – | 0.996 | 0.988 | 0.965 | 0.965 | 0.387 | 0.383 | 0.351 |
| mid_tt | 0.985 | – | 0.996 | 0.965 | 0.968 | 0.393 | 0.389 | 0.357 |
| ask_tt | 0.987 | 0.994 | – | 0.960 | 0.964 | 0.395 | 0.392 | 0.361 |
| bid_chg | 0.926 | 0.921 | 0.923 | – | 0.997 | 0.423 | 0.418 | 0.385 |
| mid_chg | 0.921 | 0.926 | 0.925 | 0.989 | – | 0.426 | 0.421 | 0.388 |
| bvc_n | 0.647 | 0.657 | 0.656 | 0.649 | 0.658 | – | 0.997 | 0.908 |
| bvc_t | 0.650 | 0.657 | 0.659 | 0.649 | 0.658 | 0.978 | – | 0.912 |
| bvc_n5 | 0.638 | 0.651 | 0.650 | 0.648 | 0.655 | 0.942 | 0.928 | – |

EURUSD (853 bars):

|  | bid_tt | mid_tt | ask_tt | bid_chg | mid_chg | bvc_n | bvc_t | bvc_n5 |
|---|---|---|---|---|---|---|---|---|
| bid_tt | – | 0.992 | 0.985 | 0.594 | 0.592 | 0.432 | 0.431 | 0.419 |
| mid_tt | 0.980 | – | 0.996 | 0.597 | 0.597 | 0.434 | 0.434 | 0.422 |
| ask_tt | 0.973 | 0.985 | – | 0.594 | 0.596 | 0.431 | 0.430 | 0.419 |
| bid_chg | 0.738 | 0.732 | 0.731 | – | 0.996 | 0.711 | 0.702 | 0.672 |
| mid_chg | 0.737 | 0.734 | 0.734 | 0.989 | – | 0.705 | 0.697 | 0.666 |
| bvc_n | 0.659 | 0.658 | 0.664 | 0.840 | 0.838 | – | 0.997 | 0.915 |
| bvc_t | 0.655 | 0.655 | 0.660 | 0.837 | 0.836 | 0.985 | – | 0.920 |
| bvc_n5 | 0.674 | 0.669 | 0.674 | 0.863 | 0.865 | 0.942 | 0.937 | – |

Reading: bid/mid/ask are interchangeable (≥ 0.97 sign agreement). Carry vs changed-only is the real fork: 93 % sign
agreement on GOLD but only 74 % on EURUSD, where 85 % of ticks are carried. Normal vs Student-t BVC are the same
(0.98-0.99). Tick-rule family vs BVC family agree on sign only ~65 % of the time (GOLD) — they measure different
things (count of moves vs size of the net move).

### 3b. Delta vs the bar's own return (contemporaneous) and the NEXT bar's return (predictive)

Spearman ρ with moving-block-bootstrap 95 % CI; "hit" = sign agreement; p = two-sided circular-shift permutation
p-value (1 000 shifts, keeps each series' autocorrelation). Only consecutive bars with ≥ 30 ticks.

GOLD M5 (813 pairs):

| method | ρ same-bar | hit | ρ next-bar [CI] | hit | p |
|---|---|---|---|---|---|
| bid_tt | 0.367 | 0.64 | −0.010 [−0.08, 0.05] | 0.50 | 0.74 |
| bid_chg | 0.406 | 0.65 | −0.013 [−0.08, 0.06] | 0.51 | 0.73 |
| bvc_n | 0.943 | 0.94 | 0.066 [0.00, 0.14] | 0.52 | 0.066 |
| bvc_t | 0.941 | 0.93 | 0.063 | 0.52 | 0.073 |
| bvc_n5 | 0.984 | 0.99 | 0.063 | 0.52 | 0.070 |
| *own return → next return* | | | 0.064 | 0.51 | 0.059 |
| *bvc_n residual after own return* | | | 0.048 | 0.50 | 0.20 |
| *bid_chg residual after own return* | | | −0.026 | 0.50 | 0.47 |

GOLD M15 (269 pairs): all next-bar ρ between −0.09 and +0.05, p ≥ 0.15. GOLD M1 (4 077 pairs): bvc_n ρ_next
−0.038 (p 0.017) — identical to own-return→next-return −0.038 (p 0.018), i.e. 1-minute mean reversion, not
order-flow information; bid_chg −0.025 (p 0.11).

EURUSD M5 (852 pairs):

| method | ρ same-bar | hit | ρ next-bar [CI] | hit | p |
|---|---|---|---|---|---|
| bid_tt | 0.466 | 0.67 | 0.020 [−0.03, 0.09] | 0.50 | 0.54 |
| bid_chg | 0.808 | 0.86 | 0.004 [−0.06, 0.07] | 0.53 | 0.91 |
| bvc_n | 0.951 | 0.94 | −0.010 [−0.07, 0.06] | 0.51 | 0.79 |
| bvc_t | 0.950 | 0.94 | −0.007 | 0.51 | 0.84 |
| bvc_n5 | 0.976 | 1.00 | 0.006 | 0.52 | 0.89 |
| *own return → next return* | | | 0.003 | 0.52 | 0.91 |

EURUSD M15 (269 pairs): bid_tt 0.046 (p 0.40), bid_chg 0.018 (p 0.72), bvc_n −0.092 (p 0.066), bvc_t −0.10
(p 0.064) — the only near-significant value is *negative* and matches own-return reversal (−0.077). EURUSD M1:
all |ρ| ≤ 0.005, p > 0.6.

Conclusions from (b):
- Contemporaneous: BVC is ~0.95 correlated with the bar's return because it *is* a function of the bar's return
  (ΔP/σ). The tick rule's 0.4 (GOLD) / 0.8 (EURUSD) is lower because it counts moves regardless of size; on GOLD,
  where steps vary from 1 to 50+ points, count and size diverge a lot.
- Predictive: nothing survives. No method, on either symbol, at M1/M5/M15, predicts the next bar's return beyond
  what the previous return itself predicts; normalising delta by tick count or taking the residual after the own
  return does not help. With ~800 M5 bars the test can detect abs(ρ) ≳ 0.07, so any real effect is below that.
  This matches the published view that quote-based "delta" on FX is a *description* of the bar's price action,
  not a forward-looking order-flow signal (Section 5).

### 3c. Timing (d)

| | GOLD | EURUSD |
|---|---|---|
| tick rate (mean active s / p99) | 11.7 / 20 ticks/s | 6.0 / 16 |
| tick rules on 3 days (all variants) | 0.29 s | 0.11 s |
| BVC (3 variants, 3 days) | 0.48 s | 0.22 s |
| one day of M5 footprints (276-288 bars, cells of 0.10 $ / 1 pip) | 0.07 s (970 k ticks, 9 692 cells) | 0.03 s (447 k ticks, 1 144 cells) |
| loading 3 days from csv.gz (np.fromstring) | 4.2 s | 2.3 s |

Footprints are a non-issue computationally: `np.unique` on (bar, price-bin) keys + `np.bincount`; a day of
M5 GOLD footprints costs 70 ms, so the server can rebuild on every refresh or keep a running one from the live tick
stream (12 ticks/s). Memory: 2.8 M ticks × 6 float64 columns ≈ 135 MB as raw arrays; keep only t/bid/ask (int64 +
2 float32 ≈ 45 MB) or store per-bar footprints (≈ 10 k cells/day).

## 4. Depth of market (depth_eval.py) — fixed aggregator tiers, not resting orders

| | GOLD | EURUSD |
|---|---|---|
| levels per side | 7-10 | 9-11 |
| distinct sizes (lots) | 100, 110, 200, 300, 400, 1 400, 25 000 | 100 k, 200 k, 2 M, 10 M |
| top-of-book size in every snapshot | 110 / 110 | 200 k / 200 k |
| total size per side over 60 s | **27 410 in all 60 snapshots, both sides** | 13.2-13.3 M, both sides |
| outer tier distance from best (pts) | 145 ± 12 (ask), 148 ± 12 (bid) | 54 ± 0.7 both sides |
| (bid−ask)/(bid+ask) imbalance | 0.000 ± 0.000 | −0.001 ± 0.002 (inner tiers ± 0.02) |
| snapshots where top of book moved | 59 / 59 | 45 / 59 |
| after a move: (price, size) pairs that survive | 3 % | 12 % |
| after a move: (distance-from-best, size) pairs that survive | 19 % | 51 % |

Interpretation: each side is the same small set of sizes (a few LP quotes of 100-200 lots inside, then 1 400 and
25 000-lot "catch-all" tiers at a fixed distance), the two sides have identical totals, and when the price moves the
levels move with it (offsets survive, prices do not). The inner GOLD prices do shift relative to each other between
seconds (so the inner tiers are probably real LP top-of-book quotes at different prices), but no level ever shows
size being consumed or replenished — the information content is "which LP is best right now", not where resting
orders sit. A Bookmap-style heatmap drawn from this would be a constant band of colour around the price: meaningless.
The research survey (Section 7) found the same from MetaQuotes' own description, FxPro's execution policy
and the one documented MQL5 attempt at a DOM heatmap (abandoned because broker DOMs are 1-10 synthetic levels).

## 5. Literature: trade-classification algorithms and their accuracy

All of these algorithms assume a **trade** stream (price, size) and usually a quote stream too. Their accuracy is
measured against exchange data that records the true aggressor. Nothing below was ever validated on a quote-only
feed; the numbers are an upper bound on what any rule can do when it at least sees trades.

| algorithm | rule | market / study | accuracy |
|---|---|---|---|
| tick rule (tick test) | up-tick = buy, down-tick = sell; zero tick inherits the last non-zero sign | Nasdaq 1996-97, Ellis-Michaely-O'Hara 2000 [L1] | 77.7 % |
| quote (midpoint) rule | above mid = buy, below = sell, at mid unclassified | same | 76.4 % |
| Lee & Ready 1991 [L2] | quote rule, tick rule for mid-point trades (orig. 5-s quote lag) | same; NYSE, Odders-White 2000 [L3] | 81.1 %; ~85 % |
| LR vs tick | | NYSE, Finucane 2000 [L4]; Frankfurt, Theissen 2001 [L5] | "about the same"; 72.8 vs 72.2 % |
| LR / tick / EMO / CLNV | | INET 2005, Chakrabarty-Li-Nguyen-Van Ness 2007 [L6] | 74.4 / 75.4 / 75.8 / 76.5 % |
| tick, all vs excl. zero ticks | | ASX, Aitken & Frino 1996 [L7] | 74 % vs > 90 % |
| LR 1 s / tick 1 s / LR ms stamps | | Nasdaq HFT era, Carrion & Kolay 2020 [L8] | 86.9 / 78.6 / 93.6 % |
| FI (order-book) / EMO / LR / BVC | | Nasdaq, Jurkatis 2022 [L9] | 95 / 90 / 89.5-96.5 / 62-88 % of volume |
| tick / quote rule / tick on zero ticks | | **EUR/USD ECN** 2005-06, Ben Omrane & Welch 2016 [L10] | 67 / 77 / 63 % |
| tick / LR / BVC | | Nasdaq ITCH 2011, Chakrabarty-Pascual-Shkilko 2015 [L11] | 90.8 / 92.6 / 64-80 % |
| tick / BVC 1-min | | E-mini S&P, Andersen & Bondarenko 2014 [L12] | 97.7 / 91.7 % (bucket level) |
| tick / BVC | | E-mini, Easley-López de Prado-O'Hara 2012 WP [L13] | 86.4 / 86.6-87.4 % |
| BVC / bulk tick-LR | | Euronext 2007-08 and LSE 2017, Panayides-Shohfi-Smith 2019 [L14] | 59-90 / 78-96 %; LSE: 53-87 / 40-84 % |
| tick / BVC | | B3 Brazil 2019, Carmo et al. 2023 [L15] | 80.8 / 56.9 % |

Bulk Volume Classification (ELO 2012 RFS eq. 7 [L13]; ELO 2016 JFE [L16]): V_buy = V · Z((P_close − P_open)/σ_ΔP),
V_sell = V − V_buy, Z = standard-normal CDF in 2012, Student-t with ν = 0.25 in 2016 and in every replication
(Jurkatis, Panayides); bars = 1-min time bars or volume bars; an unchanged price gives a 50/50 split.
Where the literature disagrees:
- *BVC vs tick rule.* ELO: BVC ≈ or > tick rule on futures and better linked to "informed trading" proxies; CPS 2015,
  Andersen-Bondarenko, Jurkatis 2022 and Carmo 2023: tick rule / LR are clearly better at the aggressor side (BVC
  misclassifies 2-4× more volume), and BVC's errors correlate with volatility so VPIN's forecasting power is partly
  mechanical [L12, L17]. Panayides 2019 splits it by venue speed: BVC wins only on very fast, fragmented 2017 LSE data.
  ELO 2016's own abstract concedes tick rules are "generally more accurate" for the aggressor side.
- *Fast markets.* Holden & Jacobsen 2014 [L18] propose interpolating same-second records; Jurkatis and Carrion-Kolay
  find that this *lowers* accuracy against the plain last-quote-before-trade rule.
- *Zero ticks are the weak spot everywhere*: Aitken-Frino > 90 % without them vs 74 % with; on EUR/USD ECN data half the
  trades are zero-tick and only 60-63 % of those are signed correctly [L10]. Roll 1984 [L19] bid-ask bounce (negative
  autocovariance of price changes) is the mechanism: alternating executions at bid/ask look like reversals.

**Quotes only (our case).** The academic route that uses only the best bid/ask is Cont-Kukanov-Stoikov 2014 order-flow
imbalance (OFI) [L20]: e_n = 1{Pb_n ≥ Pb_n−1}·qb_n − 1{Pb_n ≤ Pb_n−1}·qb_n−1 − 1{Pa_n ≤ Pa_n−1}·qa_n + 1{Pa_n ≥ Pa_n−1}·qa_n−1,
which explains ~65 % of the variance of price changes on NYSE TAQ — but it needs the **sizes** at the best quotes, and
FxPro's sizes are constants (110/130 lots on GOLD, 200 000 on EURUSD), so OFI degenerates to a tick rule on the bid and ask.
Evans & Lyons 2002 [L21] and Hasbrouck 1991 [L22] need signed trades. Suvorov 2021 (RUB/USD) [L23]: "when quote data is
not present, the tick rule yields a considerably lower accuracy" — and we have the opposite problem (quotes but no
trades). There is **no** published accuracy figure for a tick-count delta on a quote-only stream; every vendor that
offers one calls it a "rough proxy" (LuxAlgo, MQL5 blog [L24, L25]).

## 6. Literature: FX / CFD specifics — tick volume, MT5 tools, TradingView

**No consolidated tape.** OTC FX trades on > 75 venues; EBS and Refinitiv Matching are the primary interdealer venues
and now below a third of electronic spot (BIS QR Dec 2019 [F1]; BIS Triennial 2025: $9.6 tn/day [F2]). CME currency
futures (6E, 6B…) and GC are the exchange-traded instruments with real volume and aggressor flags [F3, F8].

**Tick volume as a proxy for real volume.**
- Marney 2011 [F4] (HotSpot + EBS real volume vs eSignal tick counts, EURUSD/USDJPY/GBPUSD/EURCHF): Pearson r 0.96-0.99 —
  but computed on *hour-of-day profiles*, i.e. it mostly shows shared intraday seasonality; the author says shorter horizons
  need more research.
- Danielsson & Payne 2002 [F5]: quote frequency "a fair proxy for volumes and liquidity supply" at 5-10 min aggregation,
  "a poor proxy" at 20-second sampling (indicative vs firm quotes). Bollerslev-Domowitz 1993 and Melvin-Yin 1996 used
  quote frequency as the volume proxy.
- Jones-Kaul-Lipson 1994 [F6] and Ané-Geman 2000 [F7]: the *number* of transactions, not their size, carries the
  volatility-volume relation — the academic basis for "count of events ≈ activity".
- Dissent: EarnForex [F9] reports tick volume "mostly uncorrelated" with CME 6E volume bar by bar (no statistic); a Babypips
  poster reports r ≈ 0.71; MQL5 blog "Why FX volume depends on your feed" [F10] and Sierra Chart docs [F11]: MT5 volume is
  the number of bid changes from one broker's LP mix, "not a true measure of actual trading volume", not comparable across
  brokers. TradingView help [F12]: many FX/CFD feeds carry no volume at all; where present it "indicates the amount of
  price updates".
  Net: tick count tracks real volume well as an *intraday activity profile* (r > 0.95 hourly), poorly bar by bar.

**How MT5 tools classify when there is no BUY/SELL flag.** MQL5 docs [F13]: TICK_FLAG_BUY/SELL mean "tick is the result of a
buy/sell deal"; MQL5 article 3708 (delta from flags) [F14]: real volumes are "not available for Forex, because this is the
over-the-counter market"; MQL5 book [F15]: flag mode "is suitable only for stock instruments"; MQL5 moderator Verleyen
[F16]: "there is NO WAY to get Buy/Sell information on Forex with MT4 or MT5 data … Bid/Ask are changing for different
reasons, one of them is there was a trade but that's not even the main one." The rules actually used:
- MQL5 book `IndDeltaVolume` [F15]: mid-price up = buy, down = sell, **size = points moved**
  (`d = ((ask+bid) − (prev.ask+prev.bid))/_Point; if d>0 buy += d else sell += −d`).
- MQL5 footprint blog [F17]: TICK_FLAG_BUY first; else last ≥ ask = buy, last ≤ bid = sell; else tick rule on the bid.
- Sierra Chart forex/CFD [F11]: bid/ask rose → "Ask Trade Volume" += 1, fell → "Bid Volume" += 1 (count, unchanged = nothing).
- CodeBase 17070: counts bid up-ticks vs down-ticks; MT5's own iVolume counts only bid changes [F16].
So every MT5 forex "delta" is a tick rule on bid or mid: up-move = buy, down-move = sell, unchanged = neither; the only
fork is count (Sierra, CodeBase) vs points moved (MQL5 book). Points-moved per bar equals close − open, i.e. BVC without
the CDF — our BVC rows show what that gives (a redrawing of the candle).

**Tools that refuse to estimate and use CME instead.** ClusterDelta [F18] maps MT tickers to 6E/6B/6J/GC/SI futures and
defines delta as volume at ask − volume at bid of the *futures*; ATAS uses 6E for EUR footprints "because forex does not
broadcast real volume" [F8]; Bookmap "does not support spot Forex … no centralized limit order book", use CME futures
[F19]. Caveat: futures and spot differ by basis/swap and the Globex 60-min break.

**TradingView.** Volume Delta / CVD / Volume Footprint [F20, F21, F22] "use intrabar volume and price fluctuations to
*estimate* the difference between buying and selling pressure": intrabar close > open → that intrabar's volume is buy,
close < open → sell, close = open → compare with the previous intrabar's close, still equal → inherit the previous
intrabar's sign. Intrabar TF: 1 s (seconds charts), 1 min (minute/hour charts), 5 min (daily); footprint ladder 1 tick →
1 S → 1 min → 60 min. On FX the "volume" being split is the provider's tick count, so the delta is a tick-count split by
intrabar direction — the same family as our bid_chg/BVC, one level coarser.

## 7. Literature: retail-broker depth of market and heatmaps

- MetaQuotes' own definition [D1]: on exchanges the DOM shows "real prices and order volumes from market participants";
  for OTC instruments "if the broker does not provide volumes, the DOM window functions as a scalping tool" showing
  "price levels calculated based on the Bid and Ask prices using the price change step"; MQL5 book [D2]: no history, not
  in the tester, a broker may build an OTC book from its own clients' orders. MetaQuotes CEO (2014) [D3]: "We use what
  came from the gateway" — MT5 passes through whatever the liquidity bridge sends; bridges "generate a combined Depth of
  Market" from several LPs [D4].
- FxPro [D5, D6]: available volume "is tiered" because "different LPs will have different prices and available
  liquidity"; market depth is "a breakdown of the available volumes … as received from its third party liquidity
  providers"; fills beyond top-of-book are VWAP across tiers. OANDA says the same operationally [D7]. So the retail DOM is
  the aggregator's executable price/size tiers, not resting client orders — exactly what Section 4 measures (fixed sizes,
  constant totals, levels sliding with the price).
- Practitioners: MQL5 moderators — forex DOM "not very usable if available at all … ONE broker only, not the FOREX market"
  [D8]; DOM-based EAs "are suited to exchanges only" [D9]. The one documented MT5 DOM heatmap attempt (Samuel Manoel De
  Souza, 2025) was abandoned because brokers "provide only 10, 4, or even 1 level" of inconsistent data [D10]; Daniel
  Santos's MQL5 article generates *simulated* book data because brokers often transmit none [D11].
- What a heatmap needs: Bookmap's connectivity list is exchange L2/MBO only (CME via BookmapData/Rithmic, dxFeed,
  TotalView; IB rejected for lacking full depth) [D12]. flowsurface [D13-D16] (Rust/iced; Binance, Bybit, Hyperliquid,
  OKX, MEXC): subscribes `depth@100ms` diffs + `aggTrade` + klines, REST snapshot then diff replay with update-id
  continuity; book = BTreeMap<price, qty>; heatmap = snapshots floored to an `aggr_time` bucket, prices rounded to
  `tick_size`, each level stored as runs {start, until, qty, is_bid}, colour = qty / max in view, trades per cell
  grouped by side. Other OSS: flowmap (badges its US-equity feed "SYNTH" because no depth exists) [D17],
  Elenchev/order-book-heatmap [D18], nssanta/quant-order-book [D19]. None of these can be fed from an MT5 DOM.


## 8. Recommendation

**Default classifier for the footprint: `bid_chg` — bid tick rule, changed quotes only.**

- sign = sign(bid_t − bid_{t−1}); ticks with no bid change are ignored (sign 0, not counted as volume);
- weight = 1 per tick (the `volume` field is a constant — never multiply by it);
- price bin = the footprint's row size (chart price step; 0.10 $ on GOLD M5, 1 pip EURUSD by default), assigned
  from the new bid (the price the move arrived at);
- bar delta = up-ticks − down-ticks; bar "volume" = up + down (= number of quote changes, not all ticks); CVD =
  running sum of delta, reset at the session (or shown per day) — long CVD drifts are artefacts (Section 1).
- Why not the carry-forward tick test: it assigns 65-85 % of ticks a sign they did not earn, and on EURUSD makes
  sign agreement with the changed-only rule fall to 74 %; the no-change ticks are LP refreshes, not activity.
- Why not BVC: its delta is a monotone function of the bar's close-to-close change, so the footprint/CVD would just
  be a redrawing of the candle (ρ ≈ 0.95-0.98); it adds nothing the candle does not already show, and the per-level
  split it needs (a σ per level) does not exist. Keep it only as an optional "bar delta" overlay for comparison.
- Why not mid/ask: identical to bid (≥ 97 % sign agreement) — use the bid because `last` is the bid and the
  sample-level price everywhere else in the engine is the bid.
- Bars: compute at M1 and sum up (M1 → M5 → M15 → H1 → H4), so a single tick pass serves all timeframes.
- Show "flicker" honestly: on EURUSD, 48 % of quote changes are 1-point oscillations, so cells near the current
  price will always show balanced buy/sell counts; an optional filter "ignore a move that is undone within N
  ticks" (N = 1) removes most of it, at the cost of hiding genuine two-way activity. Offer it as a toggle, off by
  default.

**What the numbers mean (plain words for the chart legend):** "Buy/Sell here = number of times the FxPro quote
ticked up / down at this price. Estimated from price changes, not real orders: FxPro is an OTC CFD broker with no
trade tape, so no true volume or aggressor side exists. Delta and CVD describe how the price got where it is; in
our 3-day test they did not predict the next bar. Treat imbalance as a description of the move (how many steps up
vs down), not as 'big buyers'."

**Depth:** do not use FxPro's depth for a heatmap or for "liquidity" levels. It is a sliding set of fixed
aggregator tiers (totals constant to the lot, imbalance zero). If a heatmap is ever wanted for gold, it needs CME
GC (or MGC) L2 data; for EURUSD, CME 6E or a crypto exchange's depth stream for the method — the flowsurface
repo shows the data model (time × price grid, resting size runs, from a depth diff stream + aggTrades).

**Labelling rule:** every panel built from this estimate carries the text "estimated from quote changes (tick
count), not real volume"; never show lot/contract sizes.

## 9. Sources

Literature (L):
[L1] Ellis, Michaely, O'Hara 2000, JFQA — https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/accuracy-of-trade-classification-rules-evidence-from-nasdaq/A2CAD2206B562784527548F5283A9ECB
[L2] Lee & Ready 1991 — https://ideas.repec.org/a/bla/jfinan/v46y1991i2p733-46.html
[L3] Odders-White 2000 — https://ideas.repec.org/a/eee/finmar/v3y2000i3p259-286.html
[L4] Finucane 2000 — https://ideas.repec.org/a/cup/jfinqa/v35y2000i04p553-576_00.html
[L5] Theissen 2001 — https://ideas.repec.org/a/eee/intfin/v11y2001i2p147-165.html (figures via Perlin-Brooks-Dufour https://www.efmaefm.org/0efmameetings/EFMA%20ANNUAL%20MEETINGS/2012-Barcelona/papers/EFMA2012_0020_fullpaper.pdf)
[L6] Chakrabarty, Li, Nguyen, Van Ness 2007 — https://ideas.repec.org/a/eee/jbfina/v31y2007i12p3806-3821.html ; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=958178
[L7] Aitken & Frino 1996 — https://researchers.mq.edu.au/en/publications/the-accuracy-of-the-tick-test-evidence-from-the-australian-stock-/
[L8] Carrion & Kolay 2020 — https://ideas.repec.org/a/bla/finrev/v55y2020i3p385-404.html
[L9] Jurkatis 2022, BoE WP 896 — https://www.bankofengland.co.uk/-/media/boe/files/working-paper/2020/inferring-trade-directions-in-fast-markets.pdf
[L10] Ben Omrane & Welch 2016 — https://ideas.repec.org/a/eee/riibaf/v37y2016icp135-152.html ; WP https://www.efmaefm.org/0efmameetings/efma%20annual%20meetings/2014-Rome/papers/EFMA2014_0302_fullpaper.pdf
[L11] Chakrabarty, Pascual, Shkilko 2015, JFM — https://ideas.repec.org/a/eee/finmar/v25y2015icp52-79.html ; https://www.sciencedirect.com/science/article/abs/pii/S1386418115000415
[L12] Andersen & Bondarenko 2014 "VPIN and the flash crash" — https://www.kellogg.northwestern.edu/academics-research/research/detail/2014/vpin-and-the-flash-crash/ ; "Reflecting on the VPIN dispute" https://repec.econ.au.dk/repec/creates/rp/13/rp13_42.pdf
[L13] Easley, López de Prado, O'Hara 2012 RFS (WP PDF, eq. 7) — https://www.stern.nyu.edu/sites/default/files/assets/documents/con_035928.pdf ; https://ideas.repec.org/a/oup/rfinst/v25y2012i5p1457-1493.html ; "Bulk classification of trading activity" https://www.academia.edu/20057247/Bulk_Classification_of_Trading_Activity
[L14] Panayides, Shohfi, Smith 2019, JBF — https://tom.shohfi.com/don/pubs/01-Don-BVC.pdf ; WP https://www.quantresearch.org/Panayides_Shohfi_Smith.pdf
[L15] Carmo et al. 2023 (B3) — https://www.redalyc.org/journal/1230/123075331006/html/
[L16] Easley, López de Prado, O'Hara 2016, JFE — https://ideas.repec.org/a/eee/jfinec/v120y2016i2p269-285.html ; https://papers.ssrn.com/abstract=1989555
[L17] Pöppe, Moos, Schiereck 2016, JBF — https://ideas.repec.org/a/eee/jbfina/v73y2016icp165-181.html ; ELO rejoinder 2014 https://ideas.repec.org/a/eee/finmar/v17y2014icp47-52.html
[L18] Holden & Jacobsen 2014 — https://scholar.smu.edu/business_finance_research/128
[L19] Roll 1984 — https://authors.library.caltech.edu/records/afwsc-6bb61
[L20] Cont, Kukanov, Stoikov 2014 — https://ar5iv.labs.arxiv.org/html/1011.6402 ; https://ideas.repec.org/a/oup/jfinec/v12y2014i1p47-88..html
[L21] Evans & Lyons 2002 — https://www.nber.org/papers/w7317.pdf
[L22] Hasbrouck 1991 — https://ideas.repec.org/a/bla/jfinan/v46y1991i1p179-207.html
[L23] Suvorov 2021 — https://ideas.repec.org/a/eee/finlet/v42y2021ics1544612320317062.html
[L24] LuxAlgo tick delta — https://www.luxalgo.com/library/indicator/Rnkr88ze-tick-delta-volume/ ; https://www.luxalgo.com/library/indicator/L91nPcl5-intrabar-volume-delta-realtime-history-stocks-crypto-forex/
[L25] MQL5 blog on tick data — https://www.mql5.com/en/blogs/post/777201 ; algorithm definitions table: Olbryś & Mursztyn https://publikationen.bibliothek.kit.edu/1000100804/50975462 ; https://hftradingbook.com/data/trade-sign-inference

FX / CFD (F):
[F1] BIS QR Dec 2019, Schrimpf & Sushko — https://www.bis.org/publ/qtrpdf/r_qt1912g.pdf
[F2] BIS Triennial 2025 — https://www.bis.org/statistics/rpfx25_fx.htm
[F3] ClusterDelta 6E — https://clusterdelta.com/ticker/6e
[F4] Marney 2011, FX Trader Magazine — https://c.mql5.com/forextsd/forum/145/fxvolume_tick_volume_vs_real_volume_study_1.pdf
[F5] Danielsson & Payne 2002 — https://www.riskresearch.org/files/DanielssonPayne2002.pdf
[F6] Jones, Kaul, Lipson 1994 — https://ideas.repec.org/a/oup/rfinst/v7y1994i4p631-51.html
[F7] Ané & Geman 2000 — https://ideas.repec.org/a/bla/jfinan/v55y2000i5p2259-2284.html
[F8] ATAS footprint — https://atas.net/blog/strategy-of-using-the-footprint/
[F9] EarnForex tick volume — https://www.earnforex.com/guides/tick-volume-in-forex ; Babypips r≈0.71 (not opened) https://forums.babypips.com/t/inquiries-regarding-volume-for-spot-forex-intraday/67574
[F10] MQL5 blog "Why FX volume depends on your feed" — https://www.mql5.com/en/blogs/post/778035
[F11] Sierra Chart forex volume — https://www.sierrachart.com/index.php?page=doc/SCRealTimeFOREX.php#VolumeData
[F12] TradingView volume by provider — https://www.tradingview.com/support/solutions/43000481397 ; Trade Nation https://support.tradenation.com/understanding-volume-in-tradingview
[F13] MQL5 docs MqlTick / CopyTicks — https://www.mql5.com/en/docs/constants/structures/mqltick ; https://www.mql5.com/en/docs/series/copyticks
[F14] MQL5 article 3708 (delta from flags) — https://www.mql5.com/en/articles/3708
[F15] MQL5 book, ticks & delta volume — https://www.mql5.com/en/book/applications/timeseries/timeseries_ticks_mqltick
[F16] MQL5 forum 293921 (Verleyen) — https://www.mql5.com/en/forum/293921
[F17] MQL5 blog footprint from raw ticks — https://www.mql5.com/en/blogs/post/774467
[F18] ClusterDelta — https://clusterdelta.com/en/ ; https://clusterdelta.com/delta ; MQL5 job https://mql5.com/en/job/140586
[F19] Bookmap forum on spot forex (not opened, snippet) — https://bookmap.com/forum/viewtopic.php?p=8475
[F20] TradingView Volume Delta — https://www.tradingview.com/support/solutions/43000725057/
[F21] TradingView CVD — https://www.tradingview.com/support/solutions/43000725058
[F22] TradingView Volume Footprint — https://www.tradingview.com/support/solutions/43000726164 ; Pine lower-TF docs https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/ ; ta library https://www.tradingview.com/script/Ey482J07-ta-m/

Depth (D):
[D1] MT5 user guide, Depth of Market — https://www.metatrader5.com/en/terminal/help/trading/depth_of_market
[D2] MQL5 book, MarketBook — https://www.mql5.com/en/book/automation/marketbook ; https://www.mql5.com/en/book/automation/marketbook/marketbook_application ; docs https://www.mql5.com/en/docs/marketinformation/marketbookget ; https://www.mql5.com/en/docs/constants/structures/mqlbookinfo
[D3] MQL5 forum, Fatkhullin on DOM — https://www.mql5.com/en/forum/396280/30841439
[D4] Brokeree bridge — https://brokeree.com/solutions/mt4-mt5-bridge/ ; Fortex https://directory.financemagnates.com/mt4-mt5-bridge-providers/fortex/fortex-inc-announces-today-the-release-of-its-mt5-product-suite-that-joins-its-flagship-mt5-bridge-omx-to-institutional-fx-and-cfd-liquidity/
[D5] FxPro order execution (403; via snippets) — https://www.fxpro.com/fxpro-platform-order-execution
[D6] FxPro UK order execution policy — https://www.slideshare.net/slideshow/order-execution-policy/190080652
[D7] OANDA depth of market — https://www.oanda.com/bvi-en/cfds/platforms/depth-market/
[D8] MQL5 forum 10986 — https://www.mql5.com/en/forum/10986/442386
[D9] MQL5 forum 512668 — https://www.mql5.com/en/forum/512668
[D10] MQL5 blog 771305 (DOM heatmap abandoned) — https://www.mql5.com/en/blogs/post/771305
[D11] MQL5 article 15748 (simulated book) — https://www.mql5.com/en/articles/15748
[D12] Bookmap connectivity — https://bookmap.com/knowledgebase/docs/KB-IntroductionToBookmap-Connectivity
[D13] flowsurface — https://github.com/flowsurface-rs/flowsurface
[D14] flowsurface Binance stream — https://github.com/flowsurface-rs/flowsurface/blob/main/exchange/src/adapter/hub/binance/stream.rs
[D15] flowsurface depth model — https://github.com/flowsurface-rs/flowsurface/blob/main/exchange/src/depth.rs
[D16] flowsurface heatmap — https://github.com/flowsurface-rs/flowsurface/blob/main/data/src/chart/heatmap.rs
[D17] flowmap — https://github.com/nazmiefearmutcu/flowmap
[D18] order-book-heatmap — https://github.com/Elenchev/order-book-heatmap
[D19] quant-order-book — https://github.com/nssanta/quant-order-book
Also: IC Markets DOM claims https://www.icmarkets.com/trading-accounts/standard-account ; FxPro MT5 launch https://www.fxpro.com/press-release/fxpro-mt5-now-live ; cTrader DoM https://help.ctrader.com/trading-with-ctrader/depth-of-market/ ; Finance Magnates https://www.financemagnates.com/forex/analysis/metatrader-5-is-more-than-just-an-mt4-upgrade/

Note on verification: the three literature threads were run by web research agents that opened the pages (a few marked
"not opened" were search snippets only); the data results in Sections 1-4 are from the scripts in this folder.
