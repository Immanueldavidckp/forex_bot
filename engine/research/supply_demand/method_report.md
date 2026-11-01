# Supply & Demand — the method and what makes a zone VALID (research + prototype, 2026-10-30)

Files in this folder: `report.md` (this), `sd_proto.py` (prototype, python3 + numpy, imports
`~/forex/engine/major_structure.py` read-only), `verify.py` (toy reproductions + internal checks), `run_output.txt`,
`verify_output.txt`, `dl/seiden_sfo.txt` (text of Seiden's 2005 SFO article).

David's rules were read from `~/FOREXBOT/FOREXBOT/1 Strategy/Rules/Supply and Demand.md`, `new rules.md` §8–22 and
`V5 Strategy (original).md` §3–7. Where they define a thing they win; everything else below is a published rule with
≥ 2 independent sources, or is marked as single-source / second-hand.

Reachability note: forexfactory.com, forums.babypips.com, their mirrors (energyexch, metalsmine) and nexusfi threads
answer 403 to fetches, so Sam Seiden's point sheet quoted on babypips and Alfonso Moreno's Forex Factory rules are
quoted **second-hand** from search-engine excerpts of those threads. The OTA point table itself is not public
(eltraderfinanciado says so). Seiden's own 2005 SFO article was fetched as a PDF and is primary.

---------------------------------------------------------------------------------------------------------------------

## 1. Sources

Primary / educator
- S1 Sam Seiden, "Focus on True Supply and Demand", SFO Magazine Jan 2005 (PDF mirror): https://c.mql5.com/forextsd/forum/65/sam_seiden_sfo_demand_amp_supply.pdf — demand = "a price level where supply and demand are in relative balance" (a sideways area A) that price breaks out of; "it is the origin of the movement of price that serves as the demand"; strength = (1) trading activity / volume in the area, (2) "how many times prices revisit… The highest-odds buying opportunity is when prices revisit an objective demand area for the first time, not the second, third or fourth"; "profit zone… is the distance between the demand area and the supply area"; stop "very close to" the level; look back "as far as need be", no time limit.
- S2 OTA "XLT odds enhancers – the key to finding turning points" (fxstreet, 2011): https://www.fxstreet.com/education/lessons-from-the-pros-201109070000 — names four enhancers: "How did price leave the level", "Time at the level", "Levels on top of level", "Retracements"; no numbers (the rest is "in the XLT class").
- S3 OTA lesson (fxstreet 2014-02-18): https://www.fxstreet.com/education/lessons-from-the-pros-201402180000 — "fresh supply and demand levels… the lowest risk, highest reward, and highest probability entry"; worked S&P example: "protective buy stop of 3 points and a target about 15 points" (5:1).
- S4 babypips thread "Odd Enhancers – Sam Seiden" (403; via search excerpt): https://forums.babypips.com/t/odd-enhancers-sam-seiden/39321 — six enhancers: strength of move, profit margin, big picture, retracement, time at level, return to level; a 2008 sheet with "strength of the move: max 2 points", total out of 10, "8 or more was a good probability trade" (one poster's recollection).
- S5 Alfonso Moreno (Set and Forget) Forex Factory thread (403; via search excerpt): https://www.forexfactory.com/thread/post/8383937 and https://www.energyexch.com/thread/post/6690255 — "for an area to be valid, the move away needs a 2:1 imbalance and price must consolidate away from it for at least one full candle"; higher-timeframe zones in control; forward-test, don't backtest.
- S6 eltraderfinanciado "Supply and demand zones" (OTA-style write-up of the public parts of the OTA system): https://www.eltraderfinanciado.com/en/blog/supply-and-demand-zones — base candle "body at most 50 % of its range", departure body "at least 50–60 %"; proximal = base bodies, distal = extreme wick; OTA grading: departure strength, time at base (fewer candles better), freshness, profit margin, trend, curve; "if the chart offers 3:1, look for 4:1" (3:1 minimum); classic school: "3 or more tests → broken"; Brandon Wendell: no more than 50 % penetration "a guideline, not a rule"; curve = thirds of the HTF range; timeframes "separated by a factor of 4 to 6"; "best-rated public scripts limit themselves to about 5 per side".

Concept pages / comparisons
- S7 LuxAlgo concept "Supply & Demand Zones": https://www.luxalgo.com/library/concept/supply-and-demand-zones.md — RBR/DBR demand, DBD/RBD supply; base = "one to a handful of candles of overlapping range"; departure = "a run of strong, one-directional candles leaving an area quickly… a slow drift away does not qualify"; "departures that break a prior swing point carry more weight"; distal = far wick of the base, proximal = near edge "commonly the candle bodies… conventions vary"; freshness is behavioural, no expiry; "consumed once price trades decisively through it"; OB = "last opposing candle before a displacement rather than from a base".
- S8 LuxAlgo concept "Zone Scoring & Refinement": https://www.luxalgo.com/library/concept/zone-scoring-and-refinement.md — Seiden's checklist "departure strength, time spent at the level, freshness, room to the next opposing level"; proxies: candle count, range vs average range, retest counter; overlapping zones "merge into one wider area or the freshest, best-formed candidate is kept"; LTF zone nested in an HTF zone refines the entry; wick vs body: "neither is objectively correct; pick one convention".
- S9 LuxAlgo concept "Order Block Anatomy & Refinement": https://www.luxalgo.com/library/concept/order-block-anatomy-and-refinement.md — OB = last opposing candle before displacement; the leg "should break a swing point or leave an imbalance"; stricter models want a liquidity sweep just before; wick-to-wick "the widest honest zone"; 50 % mean threshold; invalid = close through the far side → re-labelled breaker.
- S10 LuxAlgo concept "Bullish/Bearish Order Block": https://www.luxalgo.com/library/concept/bullish-bearish-order-block.md — "No displacement means no order block, whatever the candle looks like"; FVG strengthens, sweep is a grading factor; S&D is "the older, looser framing… order blocks are the stricter, candle-level version".
- S11 backtrex "Order block vs supply and demand zones": https://backtrex.com/en/blog/order-block-vs-supply-demand-zone — OB needs BOS/CHoCH + displacement, FVG "often required", sweep = confluence; S&D needs none of these; S&D box "potentially 3 to 8 times wider"; OB invalid by full mitigation (close inside), S&D "until price closes cleanly outside it".
- S12 crosstrade "Order blocks": https://crosstrade.io/learn/price-action/order-blocks — valid OB "typically also requires" a BOS/CHoCH, a multi-bar impulsive move, elevated volume; OBs "a more precise version of supply/demand zones".
- S13 crosstrade "Supply and demand zones": https://crosstrade.io/learn/price-action/supply-and-demand-zones — base = "the 1-3 bars immediately before the impulsive move"; impulse "3-bar+ explosion"; fresh → 1-2 tests weaker → "3+ tests: treated as broken"; broken on "3+ tests or a decisive close through the zone".
- S14 therighttrader "Supply and demand zones": https://therighttrader.com/learn/price-action/supply-and-demand-zones — worked numbers: demand base 100–104, rally to 130, return to 104 (a "26-point leave"); "a close through the distal edge is a break"; teachers differ on whether a wick counts as a visit; OB vs zone: "if the origin is a single candle, both names apply".
- S15 Dukascopy "Supply and demand zones": https://www.dukascopy.com/swiss/english/marketwatch/articles/supply-and-demand-trading/ — "three to five candles moving sideways… followed by a sharp breakout"; worked EUR/USD H4: base 1.0850–1.0870 then "150 pips in just a few candles to 1.1020"; first touch highest probability; "if price moves through your entire zone and beyond, the zone has clearly failed"; broken supply "often transforms into a demand zone".
- S16 NexusFi "Supply/demand zones for futures": https://nexusfi.com/a/market-structure/supply-demand-zones-futures-trading — fresh = never returned to; "zones often fail by the third test"; invalidated when price "accepts beyond it… holds outside the zone for multiple bars", "wicks don't invalidate".
- S17 Trade Ideas "Supply and demand zones explained": https://www.trade-ideas.com/learning-center/chart-analysis/supply-and-demand-zones-explained/ — "last down candle(s) before a strong up move"; "draw zone covering bodies and wicks of base"; grade A/B/C by freshness, trend, departure; "five active zones beat fifty stale rectangles"; zones tested five times become "liquidity pools for stop runs".
- S18 maktradingschool "How to draw proximal and distal lines" (page is mostly images; rule from the search excerpt): https://maktradingschool.com/how-to-draw-proximal-and-distal-lines/ — proximal at the highest wick of the base (demand); distal: "for reversal patterns use the extreme of the entire formation (incl. leg-in); for continuation patterns ignore the leg-in".

Open-source / documented implementations (numbers)
- S19 `@cmike444/supply-and-demand-zones` (TypeScript, README): https://unpkg.com/@cmike444/supply-and-demand-zones@1.3.1/README.md — decisive body ≥ 0.5 × range, explosive ≥ 0.70 × range and optionally range ≥ 1.5 ATR; MIN_RALLY/DROP 2 candles; MIN_BASE 1, MAX_BASE 6; MAX_ZONE_ATR 1.5; MAX_BASE_GAP 0.5 ATR; proximal = bodies, distal = "entire formation (leg-in + base + leg-out) using full wicks"; freshness 1.0 / 0.5 (touched the proximal but not the distal); breached = wicked through the distal.
- S20 Svopex S&D Scan (TradingView, open source; description): https://www.tradingview.com/script/Jywsoivw-Svopex-S-D-Scan/ — "1 to N base candles with body ≤ 0.5 × ATR, followed by an explosive candle with body ≥ 1.5 × ATR"; max base candles 3 (1–6); box = high/low of the base candles; break by wick or body (option); v1.1: a touch = "a candle wick touches the zone".
- S21 Supply Demand Zones Pro (TradingView, open source; description): https://www.tradingview.com/script/h0jxhmgn-Supply-Demand-Zones-Pro/ — max zone height 1.0 ATR, min 1.0 ATR; invalidation "Close" (default) or "Wick"; broken → "Historic zone… flip levels"; score by age and retests, "7/10 or higher = fresh, less-tested".
- S22 AW Supply Demand (MQL5 blog, documented): https://www.mql5.com/en/blogs/post/775533 — base body ≤ 0.5 × range, up to 6 base candles; departure within 10 bars ≥ 1.5 ATR and ≥ 2 zone heights (presets 1.2/1.5 … 2.0/3.0); boundaries Classic = bodies→wicks; min 0.2 ATR, max clipped; fresh → tested (touch by wick or close, option) → weak → retired after N touches; visit ends after N bars outside; broken = close beyond the far boundary (1 close / 2 closes / wick option); fake break = wick only; flip with a retest window; state codes 1 Fresh 2 Tested 3 Weak 4 Broken 5 Flipped.
- S23 CienF-OTC "Supply & demand with qualifiers" (TradingView, open source; description): https://www.tradingview.com/script/lDD8Rnz0-Supply-demand-with-qualifieres-By-CienF-OTC/ — "Indecisive Base… body ≤ 50 % of its total range"; explosive candle body > 50 % (Elite: 60 %); "High Quality Ratio 2.0× larger than average"; the candle after the explosion cannot be indecisive (anti-stall, off by default); Elite: zone hidden "until price breaks that structure point"; box = base high/low incl. wicks; stop "just beyond the distal line".
- S24 Flux Charts Supply and Demand Zones (TradingView): https://www.tradingview.com/script/ZUAYemgd-Supply-and-Demand-Zones-Flux-Charts/ — retest = reaches into the zone and closes back; cooldown 3 bars; breakout = close through + a second close; a confirmed breakout flips the side; hold window 10 candles.
- S25 ProRealCode "Rally Base Drop SND": https://www.prorealcode.com/prorealtime-indicators/rally-base-drop-snd-indicator/ — rally = 2 consecutive bullish, drop = 2 bearish, base = neither; boxes from bodies (`max(close,open)`), pivots broken by a wick.
- S26 Proozac "Auto Supply & Demand Zones" (TradingView search page): base bodies < ATR, impulse ≥ 1.5 × ATR for forex.

---------------------------------------------------------------------------------------------------------------------

## 2. Findings per topic (agreement, disagreement, recommendation)

### 2.1 Formation
- Four formations, all sources agree (S6, S7, S15, S19): RBR, DBD = continuation; RBD, DBR = reversal. LuxAlgo: reversal formations at range extremes are graded highest by many practitioners.
- Base candle: body ≤ 50 % of range (S6, S19 "indecisive", S22, S23). Alternatives: body ≤ 0.5 × ATR (S20), body < ATR (S26). ProRealCode uses colour only. **Default: body ≤ 0.5 × range** (4 sources).
- Number of base candles: 1–3 (S13; S20 default 3), up to 5 (Dukascopy "three to five"), up to 6 (S19, S22). OTA: fewer = better ("time at the level"). **Default: 1–3 hard, +1 for David's opposite candle just before the run; 4–6 configurable.**
- Leg-out / explosive candle: David: body ≥ 1.5 × mean body of the previous 10 (wins). Published equivalents: body ≥ 1.5 × ATR (S20, S26), range ≥ 1.5 ATR (S19), ≥ 1.5 × the base candle (search excerpts), Moreno "2:1 imbalance" (S5, second-hand), body ≥ 50–70 % of range (S6, S19, S23). Departure distance: ≥ 1.5 ATR and ≥ 2 zone heights within 10 bars (S22). **Default: David's 1.5 × avg-body as the hard filter; body-% and run-in-box-heights as score.**
- Gap / FVG in the leg-out: LuxAlgo "frequently appear together" (S7); S10 "stronger blocks leave an FVG"; S11 "often required" for OBs; David §12: required for a trade setup, same displacement. **Default: flag + score point; `setup_ready` requires it (David).**
- Single-candle zone (no base): S14 "if the origin is a single candle both names apply"; S17 "last down candle(s)"; David V5 §3 = the last opposite candle. **Default: when the run of base candles is empty, the zone is David's candle (kind "single-candle" = the OB of smc_marks).**
- Leg-in: 2 consecutive same-colour candles (S19, S25) — brittle; the prototype uses the net close move over 5 bars ≥ 0.5 ATR (rally / drop / flat). Only the name depends on it.

### 2.2 Zone drawing
- Distal: far wick of the base — all sources. Reversal patterns incl. the leg-in extreme: S18, S19 (always). LuxAlgo, S6, S22: base only. **Default: base only** (David's candle wick; the leg-in extreme is already a structure level).
- Proximal: bodies (OTA/S6, S19, S25, LuxAlgo "commonly") vs wicks (S18, S20, S22 Full candle, S23, David's engine/OB boxes). LuxAlgo: neither is right. **Default: box = wick to wick (David's convention, consistent with the OB boxes), with the body edge drawn as a dashed ENTRY line** — the OTA proximal, where a limit order would sit.
- Maximum height: 1.5 ATR (S19), 1.0 ATR (S21), clipped (S22); huge bases rejected (S14, LuxAlgo). **Default: 1.5 ATR; a taller base is first REFINED to David's single candle (the LuxAlgo/S8 "nested zone refines the entry" idea without a lower timeframe), and dropped if still taller.**
- Refinement to a lower timeframe: S8, S6 (factor 4–6). Not needed on the page: the M15 zone already refines the H1 one; the single-candle refinement does the intra-TF part.

### 2.3 Validity / odds enhancers
- Seiden (S1, S2, S4): strength of the move out, time at the level, freshness ("return to level"), profit margin (reward to the opposing zone), big picture (trend), retracement / curve; "levels on top of levels". OTA point table: not public (S6); the babypips 10-point sheet with "8+ = good" is one poster's memory (S4).
- Thresholds that exist: 3:1 minimum reward to the opposing zone (S6; S3 example 5:1; Dukascopy "at least 1:2 or 1:3"); ≤ 50 % penetration guideline (S6 Wendell); base 1–3 candles (S13); departure ≥ 2 zone heights / 1.5 ATR in 10 bars (S22); explosive ≥ 2× average = "high quality" (S23).
- Scores vs hard filters: tools mix them — S21 score 0–10 by age/retests; S19 confidence = weighted mean of 7 factors; S22 "min score to show 6.0"; S17 grades A/B/C. LuxAlgo: "codified heuristics", not tested science. **Default: David's gates are hard; the enhancers are a displayed 0–10 score (table in §3).**

### 2.4 Life cycle
- Fresh = never revisited (S1, S7, S15, S16). First touch highest odds (S1, S15, S21, S22).
- Touch: a wick reaching the proximal line (S20 v1.1, S22 option, S19); some count only closes inside (S24). Depth: 50 % line = mean threshold (S9) / Wendell's guideline (S6). **Default: wick to the proximal = touch; record depth (50 % = "mean", distal = "full").**
- Spent: "3 or more tests → broken" (S6 classic school, S13), "often fail by the third" (S16), configurable (S22). **Default: 3 separate visits → spent (a visit ends after 3 bars outside: S22).**
- Invalidation: a CLOSE beyond the distal (S14, S21 default, S22 default, S9/S10 for OBs); wicks don't (S16, S22 "fake break"); S24 wants two closes. **Default: one close beyond the distal; a wick is a fake break and counts as a touch.**
- Flip: broken supply → demand on the first return (S15, S21, S22, S24; ICT "breaker" S9). S6: could not verify it in a primary OTA source. **Default: broken → flipped when price comes back to the box from the other side; a close back through the box ends it ("dead").**
- Nested / overlapping: merge or keep the best-formed (S8), keep newest/strongest/merge (S22), "no zone if it overlaps an existing one" (S24), ≈ 5 per side (S6, S17, S24). **Default: boxes of the SAME break that overlap are one zone (keep the earliest = the origin); different breaks keep both; the page shows ≤ 5 live per side nearest price.**
- Superseded: a CHoCH against the zone side after it (the page's existing OB/FVG convention) — keep for consistency.

### 2.5 S&D vs ICT order block vs SMC
Agree: both are "basing then leaving impulsively" (S10); the OB is the single-candle S&D zone (S14); both die on a close through the far edge (S9, S14, S21). Differ: S&D takes the whole base (3–8× wider, S11), needs no structure break in the classic school (S7, S11, S12), is prized fresh and degraded by tests (S7), targets the opposing zone (S1). The OB school requires displacement + BOS/CHoCH (S10 "no displacement, no order block"; S11, S12), likes an FVG in the leg (S10, S11) and a liquidity sweep / inducement just before the block (S9 stricter models, S10 grading factor, S11 confluence); invalid = close inside / through (S11). David's rule is the SMC gate applied to the S&D zone: the leg-out must be the displacement that produced a BOS by close (new rules §9–10) — LuxAlgo's "departures that break a prior swing point carry more weight" made into a gate. Sweep before the zone: all three OB sources treat it as a grade, not a gate → score only (not in the prototype; the page's liquidity layer already marks sweeps).

---------------------------------------------------------------------------------------------------------------------

## 3. Recommended spec for the /smc page — "Supply / Demand — only the valid ones"

Hard gates (a zone that fails any of them is not drawn):
| # | rule | default | source |
|---|------|---------|--------|
| G1 | leg-out candle = displacement: body ≥ `displacement_mult` × mean body of the previous `body_average_bars` | 1.5 × 10 | David V5 §4, new rules §11 (S20/S26 use 1.5 × ATR) |
| G2 | base = run of base candles (body ≤ 50 % range) right before the leg-out, 1..`max_base`; David's last opposite candle (≤ 5 bars before) is inside the box: extends the run by one if adjacent; no base → the zone IS that candle (single-candle) | 50 %, 3, 5 | S6/S19/S22/S23; S13/S20; David V5 §3 |
| G3 | box = base wicks; if taller than `max_height_atr` × ATR(14) → refine to David's candle; still taller → drop | 1.5 ATR | S19 (1.5), S21 (1.0), S22 (clip); refine: S8 |
| G4 | **BOS gate**: the leg-out candle lies inside a MAJOR BOS / CHoCH of its side (origin ≤ base, leg-out ≤ break candle, `major_structure.py`), i.e. the displacement closes beyond a confirmed swing | — | David new rules §9–10, §18 BOS #1; S7 "break a prior swing"; S10/S11/S12 |
| G5 | clean departure: between the leg-out and the break candle no wick comes back to the proximal line | — | David "move strongly away" (§9.1); S5 "consolidate away"; S19 freshness |
| G6 | one box per break: overlapping boxes of the same break merge into the earliest (the origin) | — | S1 "origin of the move"; S8/S22 merge |

Displayed score 0–10 (never hides a zone; the page sorts / dims by it):
| part | points | source |
|------|--------|--------|
| departure | body ≥ 1.5× avg = 1, ≥ 2.5× = 2; run from the proximal ≥ 2 box heights within 10 bars = +1 | S2 "how price left", S22, S23 (2× = high quality) |
| FVG in the leg-out | 1 | David §12 (required for `setup_ready`), S10, S11 |
| time at base | 1 candle 2, 2–3 → 1, more → 0 | S2 "time at the level", S6, S13 |
| freshness | fresh 2, 1 test 1, else 0 | S1, S4 "return to level" |
| trend | leg-out is a BOS (continues the major trend) 1, CHoCH 0 | S4 "big picture", S6 trend |
| curve | demand in the lower half / supply in the upper half of the last 200 bars | S6 curve thirds, S8 |
| profit margin | nearest opposing live zone ≥ 3 box heights away (or none) | S1 profit zone, S6 3:1 minimum |

Life cycle, known from the break candle on: fresh → tested (wick to the proximal; depth %, mean = 50 %, full = distal) → spent (3 visits; a visit ends after 3 bars outside) → broken (a CLOSE beyond the distal; a wick = fake break) → flipped (price returns to the box from the far side) → dead (a close back through it). Plus `superseded` (a CHoCH against the side) and `live` = fresh / tested and not superseded. Display: live zones in full colour with the entry (body) line dashed, spent / deep-tested dimmed, broken as a thin outline until flipped, nested (same break, non-overlapping, later) boxes on request; ≤ 5 per side nearest price (S6/S17).

How it differs from the page's OB (smc_marks): the OB is the last opposite candle before the LAST displacement of the break; the S&D zone is the base (1–4 candles, wicks) before the FIRST displacement whose departure ran cleanly to the break (the origin, S1). On our data the OB candle lies inside the "last" S&D box of the same break in 81 of 101 pairs (§5) — the S&D layer is the base-sized, origin-anchored, freshness-tracked version of the same idea, and the two coincide when the move has one displacement.

---------------------------------------------------------------------------------------------------------------------

## 4. Disagreements and what was chosen
1. Proximal line bodies (OTA) vs wicks (David, Svopex, CienF): box = wicks, bodies = entry line (both drawn).
2. Distal incl. the leg-in extreme for reversals (maktrading, cmike) vs base only (LuxAlgo, eltrader): base only — the leg-in extreme is already a structure level on the page.
3. Max base candles 3 vs 6: 3 (+1 for David's candle); 6 would admit ranges that David's "single candle" idea rejects.
4. Explosive candle by ATR (Svopex) vs by average body (David) vs body % (eltrader/cmike): David's; body % and run become score.
5. Invalidation by one close (most) vs two closes (Flux) vs wick (cmike): one close; a wick is a fake break / touch.
6. Spent after 3 tests (classic) vs never (freshness just decays, LuxAlgo/S21): 3 → "spent" status, still drawn dim.
7. BOS as a gate (David, OB school) vs as a weight (LuxAlgo, classic S&D): gate — David's rule and the clean-chart rule (§17).
8. Sweep / inducement before the zone: grade only (all three OB sources) → not a gate; left to the liquidity layer.
9. Flip zones: 4 tool sources + ICT breaker vs unverified in OTA primary material: implemented as a status, not a new zone.

---------------------------------------------------------------------------------------------------------------------

## 5. Prototype output (`python3 sd_proto.py`, last 3,000 bars per file; full text in run_output.txt)

*(`run_output.txt` and `verify_output.txt` were regenerated 2026-10-30 09:30 on newer bars, so the counts below differ a little from the files; every check still passes — see README.md.)*

| series | major events | displacement candidates /100 bars | VALID /100 bars | origin boxes | nested | with FVG | fresh now | live now | mean score |
|---|---|---|---|---|---|---|---|---|---|
| GOLD M15 (09-14 → 10-29 IST) | 47 (26 BOS / 21 CHoCH) | 24.0 | 2.37 (71) | 35 | 14 | 65 | 9 | 0 (all 9 fresh ones superseded by a CHoCH) | 7.2 |
| GOLD H1 (04-29 → 10-29) | 25 | 23.3 | 1.90 (57) | 21 | 21 | 50 | 11 | 10 | 7.6 |
| EURUSD M15 (09-15 → 10-29) | 29 | 25.2 | 1.90 (57) | 24 | 18 | 51 | 11 | 2 | 7.8 |
| EURUSD H1 (05-07 → 10-29) | 28 | 24.7 | 1.70 (51) | 26 | 10 | 49 | 14 | 2 | 7.8 |

Why candidates are dropped (GOLD M15 / GOLD H1 / EURUSD M15 / EURUSD H1): no major BOS/CHoCH from the leg-out 333 / 311 / 372 / 312; price came back to the box before the break 151 / 200 / 151 / 188; box taller than 1.5 ATR after refinement 126 / 101 / 132 / 167; overlapping box of the same break merged 24 / 16 / 22 / 15; no base and no opposite candle 11 / 6 / 17 / 8; base before the move's origin 4 / 9 / 4 / 0. Breaks that end with NO zone: 12 of 47, 4 of 25, 5 of 29, 2 of 28 — mostly because every candidate box was taller than 1.5 ATR (a wide base) or price re-entered it; a few because the move had no displacement candle at all. The BOS gate alone removes ~90 % of the displacement candidates — the "only the valid ones" effect.

OB vs the "last" S&D zone of the same break: GOLD M15 34 pairs, OB candle inside the base 28, boxes overlap 3, disjoint 3; GOLD H1 21: 17 / 1 / 3; EURUSD M15 20: 14 / 1 / 5; EURUSD H1 26: 22 / 3 / 1.

Timing: structure ~10 ms + zones ~60 ms per 3,000 bars (pure Python loops; fine for the page).

Dated examples (IST, origin boxes):
- GOLD M15 supply RBD, base 2026-10-22 18:45 ×1, box 4074.6–4081.5 (entry 4076.7, 0.67 ATR), leg-out ×2.45 body 82 %, run 4.4 boxes, FVG, major BOS supply 19:30; tested once, depth 100 %; score 8.
- GOLD M15 demand xBR, base 2026-10-27 15:45 ×1, box 3993.3–3997.4, leg-out ×5.26, run 7.6 boxes, FVG, major CHoCH demand 19:45; fresh; score 10.
- GOLD M15 demand DBR single-candle, base 2026-10-28 00:00, box 4054.4–4056.6, leg-out ×2.49 body 98 %, FVG, BOS 05:30 (the run David's sells were stopped by) → later broken, flipped, dead.
- GOLD H1 supply RBD, base 2026-10-12 08:30 ×1, box 4201.6–4208.2 (0.56 ATR), run 7.0 boxes, FVG, BOS supply 10-22 16:30; fresh; score 10.
- EURUSD M15 demand DBR, base 2026-10-28 12:30 ×1, box 1.1113–1.1116, leg-out ×4.4, run 4.9 boxes, FVG, CHoCH demand 17:30; fresh; score 10.
- EURUSD H1 supply DBD, base 2026-10-14 16:30 ×1, box 1.1188–1.1197, leg-out ×17.9 (news candle), run 8.1 boxes, BOS 17:30; tested, later dead.

---------------------------------------------------------------------------------------------------------------------

## 6. Verification (`python3 verify.py` → ALL OK, 19 checks; verify_output.txt)
1. therighttrader worked numbers (S14): toy series with a confirmed swing high at 112, a 3-candle base 100–104 (David's bearish candle inside), leg-out 103→113→122→130, return to 104. Result: one major BOS buy from the leg-out; exactly one valid demand zone; box 100–104 (distal 100, proximal 104), entry line 103.5 (highest base body), kind DBR, base 3, displacement ×9 with an FVG; status tested after the return (1 touch, depth 0 %), touch only after the break candle; score 9 (freshness 2 → 1). The BOS fires on bar 33 not 32 — the 0.25-ATR close margin of David's structure rule, not a prototype issue.
2. Same series with a leg-out that stops below 112: no major event → no valid zone; the candidates carry the "no major BOS / CHoCH from this leg-out (David §9-10)" reason.
3. Dukascopy worked numbers (S15): base 1.0850–1.0870, +150 pips to 1.1020 in 3 candles through the 1.0960 swing: one valid demand zone 1.0850–1.0870, DBR, fresh; run = 150 pips = 7.5 box heights.
4. Internal checks on GOLD M15: every valid zone hangs on a major event of its side with origin ≤ base < leg-out ≤ break; box geometry and entry line on the near side; David's candle inside every base when it exists; all boxes ≤ 1.5 ATR; base runs ≤ 4; clean departure holds; exactly one origin per break; status transitions monotone (broken only on a close beyond the distal, flipped after broken); **no look-ahead**: the 82 valid zones whose break is before a 400-bar cut are identical when computed on the truncated series.

Limits: the "spent after 3" and the score weights are educator conventions, not tested edges (LuxAlgo says so); the Seiden point sheet and Moreno's 2:1 rule are second-hand (forums 403); leg-in classification is a 5-bar / 0.5-ATR proxy; the curve uses a 200-bar window instead of the HTF range; the sweep-before-zone grade is not implemented (the page's liquidity layer has the sweeps).
