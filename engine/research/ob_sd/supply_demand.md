# Supply & demand zones — the classic school's definition, made deterministic (research 2026-11-01)

Scope: what the Sam Seiden / Online Trading Academy (OTA) "core strategy", Alfonso Moreno (Set and Forget), the
S&D educator sites and the open-source indicators actually say, with the goal of a program that draws the zones a
professional S&D trader would draw. This extends the 2026-10-30 research (`~/forex/engine/research/supply_demand/
method_report.md`, `opensource_report.md`, `sources.md`, `validity_report.md`); everything there is taken as read
and only quoted where a new source changes or sharpens it. Every claim carries its URL. Sources that were only
reachable through search-engine excerpts (Forex Factory, babypips, the MoneyShow / justapricetrader odds-enhancer
write-ups) are marked **[excerpt]** and are second-hand. New primary material fetched today: Seiden's 2005 SFO article
(full text, `dl/seiden_sfo.txt`), the OTA Core Strategy curriculum PDFs (`dl/ota_core_2017.txt`, `dl/ota_core_2018.txt`),
seven OTA / FXStreet "Lessons from the Pros" articles (Seiden, Rick Wright, Brandon Wendell, Núria Foj Alvira), and
the Pine source of five more open-source scripts (`dl/*.json`, fetched from TradingView's pine-facade endpoint).

Why the current engine looks "fully wrong" to David (half the zones are a single candle, most are not at the move's
origin): `engine/supply_demand.py` starts from every displacement candle and takes the 1–3 base candles right before
it, with a fallback to "David's last opposite candle" when there is none. The classic school starts from the OTHER
end: find the big move first, walk back to the pause it left from, and that pause (the base) is the zone — a swing
origin, not any candle before any big body. §4 and the rule in §11 fix that order.

---------------------------------------------------------------------------------------------------------------------

## 1. Leg-in, base, leg-out — candle classification

### 1.1 What the originators say (no numbers)
- Seiden, SFO Jan 2005 (primary, full text): "Area A … represents a price level where supply and demand are in
  relative balance or equilibrium … On the close of the candle (B), the supply and demand relationship in area A is
  no longer in balance … Area A can now objectively be labeled demand (support)." And: "breakouts and breakdowns from
  areas of congestion show us exactly where the shift in supply and demand has taken place … it is the origin of the
  movement of price that serves as the demand (support) or supply (resistance)."
  https://c.mql5.com/forextsd/forum/65/sam_seiden_sfo_demand_amp_supply.pdf
- OTA vocabulary (Rick Wright, OTA, FXStreet 2019): "We call up moves rallies, down moves drops and sideways moves
  bases"; the four patterns differ in "the SPEED of the rallies, the DISTANCE of the rallies, the TIME of the base and
  the VOLATILITY (width) of the base". https://www.fxstreet.com/education/lessons-from-the-pros-forex-201504290000
- OTA Core Strategy curriculum (official PDF, 2017/2018): Day 1 "Formations: … Rally-Base-Drop, Drop-Base-Rally and
  how they are used as building blocks in the Zoning Process"; "Zoning Process: Using the concepts of Supply and
  Demand, Odds Enhancers and the Base Isolation Technique, you will become proficient at identifying Supply Zones and
  Demand Zones." No candle thresholds are published anywhere by OTA.
  https://www.sharekhan.com/MediaGalary/docs/CoreStrategyCourse-201805051400238399966.pdf ,
  https://www.sharekhan.com/Upload/General/CoreStrategy.pdf
- A single-candle base is normal in OTA material: an OTA-style lesson states "The base was formed only by one candle,
  and this happens frequently in the market" [excerpt]. https://www.scribd.com/document/1069306183/Lesson-2-The-Rally-Base-Drop-Pattern

### 1.2 The 50 % basing-candle rule — where it really comes from
- The 50 % rule is **Alfonso Moreno's** (Set and Forget), not Seiden's. Moreno, Forex Factory "Supply and demand in a
  nutshell" [excerpt]: a basing candle is one where "the candle body is 50% or lower than the whole candle range"; "a
  non-50% marubozu can serve as a basing candle"; "not all zones have to have a 50% candle on them"; on continuation
  patterns "marubozu candles are very common on CP patterns, and not every zone needs a 50% candle".
  https://www.forexfactory.com/thread/428204-supply-and-demand-in-a-nutshell-by-alfonso ,
  https://www.forexfactory.com/showthread.php?p=8150789
- Searching for the 50 % rule in Seiden's own articles finds nothing; every "50 %" hit is an indicator author
  (LuxAlgo library pages, DOSALGO "Indecisive Candles": `isIndecisive = bodyRange <= 0.5 * candleRange`, skbohler
  "Demand Zone Candles": `legCandle = body >= range*.5`, `baseCandle = body < range*.5`).
  https://www.tradingview.com/script/mFNpyFMe-Indecisive-Candles/ ,
  https://www.tradingview.com/script/vphHn1sk-Supply-Demand-Zone-Candles , https://www.luxalgo.com/library/indicator/KRlFYBWy-demand-and-supply-candles-open/
- eltraderfinanciado (OTA-style write-up): "A programmable version requires a base candle body of at most 50% of its
  range … a departure candle body of at least 50–60% of its range"; "find the departure first, then the base right
  before it". https://www.eltraderfinanciado.com/en/blog/supply-and-demand-zones
- MSH Demand & Supply Zones Pro (Pine, open source): `legInBodyPct 50`, `legOutBodyPct 50`, `baseBodyPct 50`,
  `maxBaseCandles 3`; `isBase = body/range <= 0.5`, `isBullLeg = body/range >= 0.5 and close > open`.
  https://www.tradingview.com/script/KXK4NQjc-MSH-Demand-Supply-Zones-Pro/
- Supply and Demand Based Pattern [RH] (Pine): "Candle Health %" default 60 — at least one candle in the leg must have
  body ≥ 60 % of range ("ensuring the presence of at least one candle with 60% health during the first rise/drop phase");
  "Base Max Retracement" 0.80 — the base may not retrace more than 80 % of the leg-in.
  https://www.tradingview.com/script/N1UG66qp-Supply-and-Demand-Based-Pattern-RH/
- ZikZak "Supply & Demand Zones" (Pine): base body < 40 % of range (`base_body_pct 40`), leg-out body > 0.5 × ATR(10)
  and beyond the base high/low, then a CONFIRMATION candle closing beyond the leg-out candle, and an FVG between the
  base and the confirmation candle (`fvg_bull = low[0] > high[2]`) — zones only when all three hold.
  https://www.tradingview.com/script/J56t02Ek-Advanced-S-D-Engine-ZikZak-Trader30
- LuxAlgo "Rally Base Drop Signals": rally = two consecutive green closes, drop = two red, base = neither (pure colour
  sequence, no body test). https://www.tradingview.com/script/laRupsVf-Rally-Base-Drop-Signals-LuxAlgo
- cmike444 (TypeScript): decisive body/range > 0.5, indecisive ≤ 0.5, explosive ≥ 0.7 AND range ≥ 1.5 ATR(14).
  https://unpkg.com/@cmike444/supply-and-demand-zones@1.3.1/README.md (code read on 2026-10-30)

### 1.3 Explosive / leg-out — the departure test
- Moreno, Forex Factory [excerpt]: measure "the distance in pips of the base you've drawn", the imbalance needs "twice
  that distance" with "a nice departure, plus at least one candle closing away from the base"; then "the price must
  consolidate away with at least one full OCHL candle that does not touch the basing area before it retests the area".
  https://www.forexfactory.com/showthread.php?p=8150789 (the same rule was quoted via energyexch in the 10-30 report).
  This is the only departure NUMBER an educator gives: **departure ≥ 2 × base height, plus one whole candle outside**.
- OTA (Brandon Wendell, FXStreet 2013/2014/2016): "Those strong levels identify themselves in the way that price
  leaves the level"; weak = price "move[s] sideways or slowly leave[s] the area", strong = price "barely enter[s]
  demand and move[s] quickly away". https://www.fxstreet.com/education/lesson-from-the-pros-stocks-201307090000
- OTA (Núria Foj Alvira, FXStreet 2015): strong supply = "a fast drop from the level, shown by large red candles, gaps
  down, and/or topping tails"; otherwise "a lower probability of success". https://www.fxstreet.com/education/lesson-from-the-pros-stocks-201504280000
- Seiden (FXStreet 2014): "The stronger the move in price away from an area, the more out of balance supply and
  demand is at the area." https://www.fxstreet.com/education/lessons-from-the-pros-201408120000
- Tool numbers (10-30 report + today): body ≥ 1.5 × ATR (Svopex), range ≥ 1.5 ATR + body ≥ 70 % (cmike), ≥ 1.5 ATR and
  ≥ 2 zone heights within 10 bars (AW), body > 0.5 ATR + confirmation + FVG (ZikZak), move high ≥ 0.8 × ATR(14) above
  the proximal (proea.app desk rule, https://proea.app/en/blog/supply-and-demand-zones), "exciting leg out" (stocknotify).

### 1.4 How many base candles
- Moreno: no stated maximum; the base is "the basing area" and its height is what the 2:1 rule is measured against
  [excerpt]. OTA: "the TIME of the base" is a quality dimension — fewer is better (odds enhancer "time at level", §5).
- stocknotify (Indian OTA-style school): "an exciting leg in, 1 to 6 base candles and a green exciting leg out";
  "Count them: 1 to 6 is valid"; 7 or more "is clutter, not information". https://www.stocknotify.in/learn/how-to-draw-supply-demand-zones
- crosstrade: "the 1-3 bars immediately before the impulsive move"; Dukascopy "three to five candles"; LuxAlgo "one to
  a handful"; MSH `maxBaseCandles 3` (1–6); Svopex 3 (1–6); cmike 6; AW 6; skbohler's patterns enumerate 1–4 base
  candles. (URLs in §12.)
- **Majority: 1–6 allowed, 1–3 preferred; no base candle at all → the last opposite-colour candle is the base**
  (Moreno "marubozu can serve as a basing candle"; norfolkfxtrader "mark the last bullish candle in the up move as
  your supply zone" https://www.norfolkfxtrader.com/basics-of-supply-and-demand-trading-a-helpful-illustrated-guide/ ;
  therighttrader "if the origin is a single candle, both names apply"
  https://therighttrader.com/learn/comparisons/order-block-vs-supply-and-demand-zone).

---------------------------------------------------------------------------------------------------------------------

## 2. Zone types

| pattern | leg-in | leg-out | side | role | source |
|---|---|---|---|---|---|
| RBR rally-base-rally | up | up | demand | continuation | OTA/Wright; LuxAlgo RBD Signals; eltrader |
| DBR drop-base-rally | down | up | demand | reversal | same |
| DBD drop-base-drop | down | down | supply | continuation | same |
| RBD rally-base-drop | up | down | supply | reversal | same |

- OTA (Wright 2019) names rally-base-drop and drop-base-rally as THE two formations of the article and says the other
  two are "beyond the scope" — the reversal pair is the headline pair. https://www.fxstreet.com/education/lessons-from-the-pros-forex-201504290000
- Where each lives: "Drop-Base-Drop is found in the middle of moves, unlike the Rally-Base-Drop that is found farther
  out at the extremes" [excerpt, OTA lesson]. https://www.fxstreet.com/education/lessons-from-the-pros-200805190000
- Which is stronger: LuxAlgo "reversal formations at range extremes are graded highest by many practitioners"
  (https://www.luxalgo.com/library/concept/supply-and-demand-zones.md); OTA's curve enhancer gives reversal zones at
  the extremes 2 points and mid-move zones 1 (§5); Moreno treats continuation patterns (CP) as valid but notes they
  often lack a 50 % candle [excerpt]. The TradingView "Odds Enhancers" idea posts: "Zones at the origin of a strong
  move are described as low risk, while zones in the middle are described as higher risk" [excerpt]
  https://pl.tradingview.com/chart/GBPUSD/GIurxWx9-GBPUSD-M15-Level-on-top-of-Level-Supply-Zone-1-34048-1-34370
- Majority position: **reversal (DBR/RBD) at the extreme of the curve > continuation (RBR/DBD) mid-move**; both are
  drawn, the continuation zone scores lower on "curve / location".

---------------------------------------------------------------------------------------------------------------------

## 3. Box edges — proximal and distal

### 3.1 Proximal (entry side)
- OTA/Seiden, FXStreet 2008 Q&A: draw "two lines so that the vast majority of trading is between your two lines";
  "Take a look at that area on two different time frames to determine where the majority of trading is"; drawing from
  candle highs and lows is acceptable "but often that makes for a very large stop which is not ideal"; buy "once price
  reaches the upper demand line", stop "just below the bottom demand line".
  https://www.fxstreet.com/education/lessons-from-the-pros-200805190000
- eltrader (OTA style): "Proximal: the bodies of the base candles. On demand, the highest body; on supply, the lowest."
  https://www.eltraderfinanciado.com/en/blog/supply-and-demand-zones
- stocknotify: "the highest point reached by any base candle's body becomes the proximal line" (demand); "only the
  base candles define the proximal and distal lines"; bodies "show where price was accepted, while wicks show brief
  rejected spikes, so orders cluster nearer the bodies"; wick-to-wick "can double the stop distance".
  https://www.stocknotify.in/learn/how-to-draw-supply-demand-zones
- LuxAlgo: proximal "at the near edge, commonly the candle bodies. Conventions vary; pick one and apply it
  consistently." https://www.luxalgo.com/library/concept/supply-and-demand-zones.md
- MSH (code): `prox = isDemand ? max(open[1], close[1]) : min(open[1], close[1])`, `dist = isDemand ? low[1] : high[1]`.
- Wick camp: maktradingschool / the TradingView HDFCBANK tutorial "Proximal line is plotted at the Highest Wick of the
  base candles" (demand) / "Lowest Wick of the base candles" (supply) https://www.tradingview.com/chart/HDFCBANK/EpzdjqTF-Proximal-and-Distal-Line-Plotting-For-Supply-and-Demand-Zones/ ;
  protradingschool for pin-bar bases "proximal line at the upper shadow and the distal line at the lower shadow"
  https://www.protradingschool.com/how-to-draw-supply-and-demand-zones/ ; Svopex, CienF, ZikZak, Moreno's eBook
  ("demand is drawn to cover the lowest lows in the basing area, and supply covers the highest highs" [excerpt] — this
  is the distal side; Moreno's proximal convention is not in the excerpt) use the base high/low.
- Moreno-school variant: norfolkfxtrader draws supply "from the last bullish candle open price to the high of the
  candle" (proximal = open of the last opposite candle, distal = its wick) — the ICT-style body edge.
- **Majority / most authoritative: proximal = extreme BODY of the base (highest open/close for demand, lowest for
  supply)** — OTA (Seiden's "majority of trading" rule and "highs and lows make a very large stop"), eltrader,
  stocknotify, LuxAlgo "commonly", MSH, cmike, ProRealCode. Wick proximal is the minority (Indian MAK school, several
  scripts).

### 3.2 Distal (stop side)
- All sources: the far WICK of the base (eltrader "the most extreme wick of the base"; stocknotify "the lowest point
  reached by any base candle's wick"; LuxAlgo "lowest wick of a demand base"; MSH `low[1]`).
- Including leg-in / leg-out wicks — three explicit rule sets:
  - TradingView HDFCBANK tutorial (MAK school): DBR "The distal line is plotted at the lowest point of the entire
    formation" (leg-in + base + leg-out); RBR "at the lowest point of either the Base candles or the Leg Out, whichever
    is lower" (leg-in ignored); RBD "highest point of the entire formation"; DBD "Highest point of either the Base
    candles or the Leg Out". Prices: HDFCBANK CMP 1668.3, demand proximal 1607.65 / distal 1588.75, supply proximal
    1688 / distal 1702.4. https://www.tradingview.com/chart/HDFCBANK/EpzdjqTF-Proximal-and-Distal-Line-Plotting-For-Supply-and-Demand-Zones/
  - stocknotify "exceptional marking": "extends only the distal line to a leg candle's wick; the proximal line never
    changes"; DBR and RBR: distal → leg-OUT candle's lowest wick; RBD: distal → leg-IN candle's highest wick; DBD:
    distal → leg-OUT candle's highest wick; "Always draw the normal zone first".
  - cmike444 (code): distal = extreme of the WHOLE formation always.
- **Majority: distal = extreme wick of the base, extended to the first leg-out candle's wick if that pokes beyond the
  base (the departure candle's wick is still "the origin"), and for REVERSAL patterns also to the adjacent leg-in
  candle's extreme if it is beyond.** Base-only is the LuxAlgo/eltrader minimal convention.

### 3.3 Width, and refining a wide zone
- OTA/Seiden: a zone drawn on highs/lows "makes for a very large stop which is not ideal"; "Take a look at that area on
  two different time frames to determine where the majority of trading is" (the OTA refinement rule, 2008).
- stocknotify: "There is no fixed width; it depends on the base candles and the stock's volatility"; "Skip the zone if
  the risk limit can't accommodate the stop distance."
- eltrader: three timeframes "separated by a factor of 4 to 6" (daily / 240 / 60; 240 / 60 / 15).
- LuxAlgo scoring: "a nested lower-timeframe zone fine-tunes the entry while the larger zone frames the trade";
  overlapping zones "merge into one wider area or the freshest, best-formed candidate is kept".
  https://www.luxalgo.com/library/concept/zone-scoring-and-refinement.md
- edgeful: "keep it narrow, because a wide zone dilutes its usefulness". https://www.edgeful.com/blog/posts/supply-and-demand-trading
- Tool caps: 1.5 ATR (cmike `MAX_ZONE_ATR_MULTIPLIER`), 1.0 ATR forced (Supply Demand Zones Pro), AW clips. Moreno's
  2:1 rule caps width implicitly: a base taller than half the departure is not a zone.
- **Deterministic refinement (majority of what is actually said): if the base is wider than the cap, drop to the next
  timeframe (factor 4) and take the base there whose leg-out is the same move; if that is still too wide, skip the
  zone.** On a single-timeframe engine the equivalent is: the sub-base = the shortest run of base candles ending at the
  leg-out that still contains ≥ 50 % of the base's closes ("majority of trading").

---------------------------------------------------------------------------------------------------------------------

## 4. WHERE the zone is — origin vs every pause

- Seiden: "it is the origin of the movement of price that serves as the demand (support) or supply (resistance). The
  origin is actually where the equation becomes out of balance" (SFO 2005); "that is where prices turn which is the
  origin of any market move" (FXStreet 2014). https://www.fxstreet.com/education/lessons-from-the-pros-201408120000
- Seiden, "Thinking Better Odds" (2016): the black line on the chart is "the origin of the rally"; reward is measured
  "from your supply/demand level to the nearest opposing supply/demand level". https://www.fxstreet.com/education/lessons-from-the-pros-201601190000
- Seiden, "Age of Supply and Demand" (2015): "Look back as far as you need to in order to find 'fresh' demand and
  supply … Sometimes, when price is far out on the curve, we look back months and years to find fresh levels"; "The
  fact that they were created long ago is not a bad thing". https://www.fxstreet.com/education/lessons-from-the-pros-201509150000
- Seiden, XLT odds enhancers (2011): on the 5-min S&P "several stacked areas that many traders would call demand do
  not qualify … the level at the bottom had enough Odds Enhancers to qualify it as strong demand" — the lowest base of
  the decline, not the pauses above it. https://www.fxstreet.com/education/lessons-from-the-pros-201109070000
- Seiden (2013): "supply and demand levels with very little activity between them"; levels are rejected when "too close
  to each other or there is too much trading activity between them". https://www.fxstreet.com/education/lessons-from-the-pros-201301290000
- therighttrader: "The base is the last pause before the move … Ignore bases that are huge relative to the move or sit
  in a messy range with no clear leave"; "Don't stretch the box to include bars that were already part of the prior
  trend." https://therighttrader.com/learn/price-action/supply-and-demand-zones
- edgeful: "the consolidation or pause that happened right before the impulsive move … The base of that rally is the zone".
- Moreno: trend rule "a higher high should remove the prior supply before a demand zone is considered validated"
  [excerpt]; "use only fresh supply or demand levels when the market is trending" [excerpt].
- **Majority position:** the zone is the base at the ORIGIN of the leg — the last pause from which the whole impulsive
  leg left, i.e. the base that contains or touches the swing low/high of that leg. Pauses inside the leg are
  continuation (RBR/DBD) zones: valid, drawn, but "in the middle of the move", scored lower on curve/location, and
  rejected by Seiden when they are "stacked" with "too much trading activity between them". A program draws ONE origin
  zone per impulsive leg plus at most the continuation bases whose own departure satisfies the 2:1 test; it never draws
  a zone for an isolated big candle without a pause before it.

---------------------------------------------------------------------------------------------------------------------

## 5. Validity / strength — the odds enhancers and their scoring

### 5.1 OTA's own words
- Seiden 2011: eight odds enhancers; four taught in the Professional Trader class, four in XLT; the four named:
  "How price left the level", "Time at the level", "Levels on top of the level", "Retracements"; "The Odds Enhancers
  have one purpose: To train your eye to identify a key demand or supply level (market turning point)."
  https://www.fxstreet.com/education/lessons-from-the-pros-201109070000
- Seiden 2014: departure strength; "the less time price spends at a level, the more out of balance supply and demand
  is at the level"; "We want to enter the position on the first retracement because it is at that point that supply or
  demand is strongest"; "With each successive retracement in price, the level is getting weaker, not stronger like the
  trading books suggest." https://www.fxstreet.com/education/lessons-from-the-pros-201408120000
- Seiden/Fulkerson 2014: a level "scored out as a 9 according to our rule based Odds Enhancers and one of the most
  important reasons was the 'profit zone'". https://www.fxstreet.com/education/lessons-from-the-pros-201406170000
- Seiden 2016 (R:R rule): "the '1' is the distance from entry to your protective stop … the '3' is the distance from
  your supply/demand level to the nearest opposing supply/demand level"; "If you are looking for 3:1, make sure the
  chart is offering you at least 4:1"; "No matter how many Odds Enhancers are present, the risk/reward must be there."
  https://www.fxstreet.com/education/lessons-from-the-pros-201601190000
- Seiden 2013: "at least 3:1 reward to risk to the first target … a safe minimum". https://www.fxstreet.com/education/lessons-from-the-pros-201301290000
- Rick Wright 2016: "one of our Odds Enhancers says to avoid levels with too many touches"; "Always go for at least a
  three to one reward to risk". https://www.fxstreet.com/education/lessons-from-the-pros-forex-201603150000
- OTA curriculum: "Decision Matrix … using Curve, Zone, Location and Trend"; "More Odds Enhancers and Scoring the
  Trade: … accumulate all the Odds Enhancers together to 'Score' the trading opportunity". (sharekhan PDFs above)
- Seiden 2005 (SFO): two strength factors — "the amount of trading activity in the level" (volume) and "how many
  times prices revisit … The highest-odds buying opportunity … is when prices revisit an objective demand area for the
  first time, not the second, third or fourth".

### 5.2 The point values (all second-hand, but consistent)
- babypips "Odd Enhancers – Sam Seiden" [excerpt]: six enhancers — strength of move, profit margin, big picture,
  retracement, time at level, return to level; "strength of the move: max 2 points"; total out of 10; "8 or more was
  a good probability trade". https://forums.babypips.com/t/odd-enhancers-sam-seiden/39321
- justapricetrader / TradingView "Odds Enhancers" write-ups of an OTA tutorial [excerpt]: "Strength of Move away from
  a price level … Strong departure (think of it like a NASA rocket taking off) i.e large ERC candles or a gap away from
  the level scored as a 2", gap = extra point; "Curve Location … demand zone low on the curve or a supply zone high on
  it = 2, mid-curve 1, opposite 0"; "Profit zone … 1 if the opposing zone is more than 1:1 away and 0 otherwise";
  freshness = "how many times price has returned to a zone since it formed"; "the less time price spends at a level,
  the stronger the imbalance". https://www.justapricetrader.com/p/odds-enhancers (site down today; wording from the
  search excerpt) , https://tr.tradingview.com/chart/USDCAD/pDLqtpxv-USDCAD-Set-Forget-Supply-Zone-1-28168-1-28213
- OTA Professional Futures Trader manual: zone-strength lesson scored "Best=2, Good=1, Poor=0" [excerpt].
  https://repubitdigital.com/futures-manual?i=482968&p=290&view=issueViewer
- eltrader: OTA's table "is not public"; the checklist = strength of departure, time at base (fewer candles better),
  freshness, profit margin, trend, curve; "if the chart offers 3:1, look for 4:1"; curve = thirds of the HTF range
  (low third longs only, middle nothing or reduced target, high third shorts only).
- Moreno's validity gates (not points): 50 % basing candle (or marubozu), departure ≥ 2 × base, ≥ 1 candle closing
  away, ≥ 1 full candle not touching the base before the retest, fresh, with the HTF trend, HTF zones "in control"
  [excerpts].

### 5.3 Is a break of structure required?
- Classic school: NO. Seiden's definition is the breakout from the congestion itself ("On the close of the candle (B)
  … Area A can now objectively be labeled demand"); Moreno's gate is 2 × base height; therighttrader: a zone "can
  exist without an ICT-style block if you never required a swing break", the OB needs the "ICT swing-break rule"
  https://therighttrader.com/learn/comparisons/order-block-vs-supply-and-demand-zone ; backtrex: OB needs BOS/CHoCH +
  displacement, "S&D needs none of these" https://backtrex.com/en/blog/order-block-vs-supply-demand-zone ; LuxAlgo:
  "departures that break a prior swing point carry more weight" (weight, not gate).
- Minority / hybrid: the Arabic Skillz Trading video "Before drawing, the recent high (demand) or low (supply) should
  be broken" https://videohighlight.com/v/mqTAtkSpgsU ; Moreno's trend rule "a higher high should remove the prior
  supply before a demand zone is considered validated" (a structure condition on the HTF, not on the leg-out) [excerpt];
  proea.app's desk: READY = "a later candle closes strictly above the move's high, within 20 candles of the pullback's
  start" https://proea.app/en/blog/supply-and-demand-zones ; David's rules §9–10 (BOS by close).
- **Majority: not required; a departure that also breaks the prior swing is the top "strength" grade.** For David's
  page the BOS gate stays as his filter, but it should be applied to the ORIGIN base of the leg (§4), not used to pick
  a candle.

### 5.4 Multi-timeframe
- OTA: analyse "on two different time frames"; eltrader: three timeframes ×4–6 apart, the HTF curve decides direction;
  Moreno: "higher-timeframe zones in control", the "realignment and sequence rules" pick the trading timeframe [excerpt];
  edgeful: "Find major zones on the 1-hour or 4-hour chart. Use the 15-minute or 5-minute chart for entry timing";
  Skillz video: "The four-hour timeframe is recommended".

---------------------------------------------------------------------------------------------------------------------

## 6. Lifecycle

| state | definition (majority) | sources |
|---|---|---|
| fresh | price has never come back to the proximal line since the departure | Seiden 2005/2014/2015; Moreno; stocknotify "The proximal line is the freshness test point" |
| tested | a candle trades into the zone; wick touch counts for most (Svopex, AW, cmike 0.5, NexusFi); stocknotify (body-to-wick zone) and Flux count only a BODY/close inside — "A wick alone does not count" | §12 |
| tested, still tradeable | Rick Wright: "If a new high is formed from a demand zone, you can consider entering a long trade on the next touch"; a touch that does not make a new extreme is not an entry | https://www.fxstreet.com/education/lessons-from-the-pros-forex-201603150000 |
| consumed / used up | "classic school: 3 or more tests → broken" (eltrader, crosstrade); edgeful "by the third or fourth test, the imbalance may be gone"; ZikZak `max_zone_touches 3`; Wendell: no more than 50 % penetration "a guideline, not a rule" (eltrader) | |
| broken | a CLOSE beyond the distal (therighttrader "a close through the distal edge is a failure"; eltrader; SDZ Pro default; AW default; MSH `close < distal`); wick-only = fake break (AW, NexusFi "wicks don't invalidate"); minority: wick (ZikZak `low < z_low`, cmike, Svopex), two closes (Flux) | |
| flip | broken demand acts as supply on the first return and vice-versa (Dukascopy, edgeful, SDZ Pro "flip levels", Flux, AW, dotnettutorials "A broken supply zone can become a demand zone"); eltrader "could not verify it in a primary OTA source"; therighttrader "a new idea, not a reason to keep the old long" | |
| aged out | Seiden: never by age ("eliminate time from the equation completely"); tools: 1000–2000 bars; proea desk 120 candles | |

---------------------------------------------------------------------------------------------------------------------

## 7. Entry / stop / target conventions

- OTA curriculum: "three entry types; Limit, Zone and Confirmation Entry"; S.E.T. = Stop, Entry, Target; "Bracket
  Order" with all three. (sharekhan PDFs)
- Seiden 2008: entry "once price reaches the upper demand line", stop "just below the bottom demand line", reduce size
  on wider stops. Seiden 2005: "enter a full position very close to his protective stop"; "Profits were taken into
  the area of supply, identified prior to entry"; "The profit zone … is the distance between the demand area and the
  supply area".
- eltrader: "first return to a fresh zone, as a limit order at the proximal"; stop "behind the distal"; target "before
  the opposing zone, not at it"; buying the initial departure is "the sucker bet".
- Moreno / Set and Forget: everything placed before price arrives — limit at the proximal, stop beyond the distal
  (LuxAlgo summary of the approach: "takes the best available price and a predefined stop but eats more outright
  failures" https://www.luxalgo.com/library/concept/supply-and-demand-zones.md).
- Stop buffer: TradingView HDFCBANK tutorial "slightly beyond the distal lines"; proea desk "one tick beyond the
  visit's deepest wick"; Seiden 2014 S&P example "protective buy stop of 3 points and a target about 15 points" (10-30
  report S3). therighttrader: "A stop inside the box is hit by an ordinary return."
- Target: Seiden ≥ 3:1 to the first target, chart must offer 4:1 (5:1 for a "stronger" 3:1); Rick Wright "at least a
  three to one"; Seiden 2014 "at least the high of that initial rally from demand" is the first profit zone
  https://www.fxstreet.com/education/lessons-from-the-pros-201409020000 ; proea desk 4R; therighttrader "part of the
  original leave" as first target.
- Confirmation entries (OTA "Confirmation Entry"; dotnettutorials: pin bar / engulfing / outside candle at the zone,
  "Look for acceptance or rejection on the trading timeframe" https://dotnettutorials.net/lesson/how-to-trade-with-supply-and-demand-zone ;
  therighttrader "a market entry after a hold and a close back through the proximal edge").

---------------------------------------------------------------------------------------------------------------------

## 8. How the open-source indicators compute zones (new code read today; the six ported on 10-30 are in opensource_report.md)

| script | base | leg-out | box | validity / life |
|---|---|---|---|---|
| MSH Demand & Supply Zones Pro (Pine v6) https://www.tradingview.com/script/KXK4NQjc-MSH-Demand-Supply-Zones-Pro/ | `isBase = body/range <= 0.5`, exactly ONE base candle at [1] (`maxBaseCandles` input exists but the code only checks `isBase[1]`) | `isBullLeg = body/range >= 0.5 and close>open` at [0]; leg-in = same test at [2]; RBR/DBR/RBD/DBD by the two colours | `prox = max(open[1],close[1])` (demand), `dist = low[1]` → body-to-wick | deleted on `close < distal`; keep 5 |
| Supply and Demand Based Pattern [RH] (Pine v5) https://www.tradingview.com/script/N1UG66qp-Supply-and-Demand-Based-Pattern-RH/ | the first bear candle after a rally = base start; base may retrace ≤ 80 % of the leg-in (`baseRetracement 0.80`) | leg-in: a bull close above the prior high with ≥ 1 candle of body ≥ 60 % ("Candle Health"); pattern confirmed when a bull candle closes above the leg-in high | box top = max(high, high[1]) at base start, bottom = low of base; a line at the leg-in's lowest open | RBR / DBD only (continuation) |
| ZikZak Supply & Demand Zones (Pine v6) https://www.tradingview.com/script/J56t02Ek-Advanced-S-D-Engine-ZikZak-Trader30 | body < 40 % range | body > 0.5 × ATR(10) and beyond the base high/low; next candle must CLOSE beyond the leg-out; FVG between base and confirmation | base candle high–low (wicks) | broken on a wick beyond the far edge; fades per touch; 3 touches → gone; 1000 bars |
| skbohler Demand Zone Candles (Pine v4) https://www.tradingview.com/script/vphHn1sk-Supply-Demand-Zone-Candles | base = body < 50 % | leg = body ≥ 50 % | pattern-matches literal L-B-L-B … L-BBBB-LLL-B strings (1–4 base, 1–3 leg candles) | colours bars only |
| LuxAlgo Rally Base Drop Signals (Pine v6) https://www.tradingview.com/script/laRupsVf-Rally-Base-Drop-Signals-LuxAlgo | base = not (2 same-colour closes) | rally/drop = 2 consecutive same-colour candles | no box; labels the R/B/D sequence | — |
| DOSALGO Indecisive with Gaps https://www.tradingview.com/script/mFNpyFMe-Indecisive-Candles/ | `bodyRange <= 0.5 * candleRange` | — | — | — |
| proea.app "Supply & Demand Desk" rule (documented, not code) https://proea.app/en/blog/supply-and-demand-zones | ONE base candle = "the last that closed against the move" | the next candle closes above the base high; move high ≥ 0.8 × ATR(14) above proximal; ≥ 2 pullback candles not touching; READY = close above the move high within 20 candles | proximal = base high (wick), distal = lower of the two lows | any touch before READY kills it; after READY confirm within 4 candles; 120-candle age; stop 1 tick below the visit wick; target 4R |
| MT4 "Supply and Demand Indicator 1.7" (MQL5 blog) https://www.mql5.com/en/blogs/post/773763 | starts from a 5-bar swing or an engulfing, not a base | — | StandartZones = extreme + nearby open/close; FullCandles; WicksOnly; fixed pips | removed when price exceeds the validating extreme |
| 10-30 ports: Shved (fractal S/R), BigBeluga (3 candles + volume, 2×ATR box), SDZ Pro (pivot, 1 ATR), Flux (pivot, wick-average box), cmike444, Svopex | see opensource_report.md §2 | | | |

Pattern across the code: every "RBR/DBD" script defines base by body/range ≤ 50 % (one uses 40 %), leg by body/range
≥ 50–70 % and/or an ATR multiple (0.5–1.5 ATR), boxes the base with the proximal at the body (MSH, cmike, PRC) or the
wick (Svopex, ZikZak, CienF, proea), and kills a zone on a close (MSH, SDZ Pro, AW, Flux) or a wick (ZikZak, cmike,
Svopex) beyond the distal. None of them locates the ORIGIN of a leg; all of them box every base-then-big-candle, which
is exactly the "every pause" error.

---------------------------------------------------------------------------------------------------------------------

## 9. Misconceptions and the majority position

1. **"A supply/demand zone is the ICT order block."** No. OB = "one opposing candle before a fast move, in the ICT
   vocabulary"; S&D zone = "the base, often several candles, that price left behind in a strong move"; "A block can
   sit inside a wider zone, but they are not the same box"; "Not every demand zone is an order block, and not every
   order block is a demand zone when there was no base" (therighttrader). backtrex: S&D box "3 to 8 times wider";
   OB requires BOS/CHoCH + displacement, FVG "often required"; S&D requires none. ICT himself (2016 talk, AI summary):
   supply and demand "do not give you the trade levels to trade at or a specific price level", "The bulk of the volume
   is … seen through the bodies of the candle not the Wicks" https://videohighlight.com/v/nBGsHuxNKbE . Majority: two
   different objects that coincide when the base is a single candle.
2. **"The 50 % basing-candle rule is Seiden's."** It is Moreno's (and the indicator authors'); Seiden never published
   a body threshold — OTA's zoning is "Base Isolation Technique" + odds enhancers, taught in class.
3. **"The zone needs a break of structure."** Classic school: no (§5.3); the departure itself defines the zone. A
   BOS is the highest "strength" grade and an ICT requirement.
4. **"Tested levels are stronger."** Classic S/R says yes; S&D says the opposite: "With each successive retracement in
   price, the level is getting weaker, not stronger like the trading books suggest" (Seiden). Academic evidence sides
   with S/R (validity_report.md), but the school's rule is fresh-first.
5. **"Draw the zone from the big candle."** The zone is the base BEFORE the big candle, never the impulse candle
   (edgeful; eltrader "find the departure first, then the base right before it").
6. **"Draw it at the swing high/low."** The pivot bar is where the zone IS (origin), but the box is the base's
   body-to-wick, not a fixed band around the pivot (SDZ Pro / Flux / Shved pivot boxes are S/R, not S&D —
   opensource_report.md).
7. **"Wick-to-wick is the correct box."** OTA: highs/lows "often … a very large stop which is not ideal"; neither is
   "objectively correct" (LuxAlgo). Majority: body proximal, wick distal.
8. **"A base must have ≥ 2 candles."** Single-candle bases are common and valid (OTA lesson; Moreno marubozu;
   therighttrader).
9. **"A zone dies when a wick pokes through."** Majority: a CLOSE beyond the distal; a wick is a fake break.
10. **"Old zones expire."** Seiden: "eliminate time from the equation completely"; fresh levels "months and years" old
    are fine.
11. **"Any pause inside a trend is a zone."** Seiden rejects stacked levels with "too much trading activity between
    them"; the origin is the zone, mid-move pauses are lower grade (§4).

---------------------------------------------------------------------------------------------------------------------

## 10. Worked examples from sources

1. **therighttrader demand** https://therighttrader.com/learn/price-action/supply-and-demand-zones : base 100–104,
   rally to 130, return to 104. Entry limit 104 (or after a close back above 104), stop below 100, first target inside
   the 26-point leave, next target the opposing zone / 130. Risk 4, leave 26 → 6.5:1 to 130. Supply mirror: base
   130–134, drop to 100, short 130, stop above 134.
2. **therighttrader OB vs zone** https://therighttrader.com/learn/comparisons/order-block-vs-supply-and-demand-zone :
   OB candle 100–105, swing high broken at 112, buy 103, stop 99 (risk 4); zone: base 50–53, drop to 40, short 51,
   stop 54 (risk 3).
3. **Dukascopy EUR/USD H4** (10-30 report S15): base 1.0850–1.0870, "150 pips in just a few candles to 1.1020"; first
   touch is the trade. https://www.dukascopy.com/swiss/english/marketwatch/articles/supply-and-demand-trading/
4. **Rick Wright CADJPY M30** https://www.fxstreet.com/education/lessons-from-the-pros-forex-201603150000 : demand
   zone 84.36–84.60; point 1 first touch long ("at least a two to one reward to risk was achieved"); point 2 valid
   re-entry because the 84.93 high "was easily broken by the move up from point 1"; points 3–5 touched the zone but
   made no new high → no trade.
5. **MAK / TradingView HDFCBANK** (above): demand proximal 1607.65 (highest base wick), distal 1588.75 (whole formation
   for DBR); supply 1688 / 1702.4; stop "slightly beyond the distal lines".
6. **stocknotify body-to-wick vs wick-to-wick** https://www.stocknotify.in/learn/how-to-draw-supply-demand-zones :
   proximal 500 (highest base body) vs 516 (base wick), entry 501 / 517, stop 485, risk 16 vs 32 per share, 1:2 target
   533 vs 581; exceptional DBR: leg-out wick to 478 → stop 477, risk 24.
7. **proea.app desk candles** (ATR 10): base o103 h104 l99 c100; departure o100 h110 l99.5 c108 → zone 99–104; move
   to 118 (14 above proximal ≥ 0.8 ATR = 8); pullback lows 112/110 (front liquidity 110 in the near half of 104–118);
   READY on a close at 120; visit wick 102 closes 105 below its open = visit, next candle 105→108 = entry 108, stop
   101.75, target 133 (4R).
8. **Seiden SFO 2005 Chart 1/4** (no prices): area A sideways, candle B closes above it → A = demand; decline C
   revisits A → long "very close to the protective stop", "profits were taken into the area of supply, identified
   prior to entry".

---------------------------------------------------------------------------------------------------------------------

## 11. Deterministic supply/demand rule (defaults; majority convention; David's settings where he defines a thing)

Inputs: closed OHLC bars of one timeframe; ATR14; `avg_body10`. All percentages are body / (high − low).

1. **Classify candles.** `base` = body ≤ 0.50 × range (Moreno; MSH/skbohler/cmike/AW/eltrader). `leg` = body ≥ 0.50 ×
   range, colour = direction. `explosive` = leg AND (body ≥ 1.5 × avg_body10 [David] OR range ≥ 1.5 × ATR14 [cmike/Svopex]).
   A doji (range 0) is base.
2. **Find the departures first** (eltrader "find the departure first"). A bullish departure starts at bar d when
   bars[d] is explosive-up and bars[d] closes above the high of every candle in the base that precedes it (ZikZak /
   proea "closes above the base high"). Continue the departure run while candles are up-legs or up-closes above the
   prior close; the run ends at the first candle that closes below the previous close (proea pullback rule).
3. **Isolate the base** (OTA "Base Isolation"): walk back from d over consecutive `base` candles, 1..6
   (stocknotify 1–6; cmike/AW 6; ≥ 7 = range, no zone). If there is NO base candle, the base is the single last
   opposite-colour candle before d (Moreno marubozu; norfolkfxtrader; therighttrader), provided it is adjacent to d.
   If the candle before d is a same-colour leg, there is no base → no zone from d (it is inside a leg).
4. **Leg-in and pattern.** Leg-in = the nearest leg candle (or the net close move over the 5 bars) before the base;
   up → RBR/RBD, down → DBR/DBD; none → treat as continuation. DBR/RBD = reversal, RBR/DBD = continuation.
5. **Box.** Demand: proximal = max(open, close) over the base (OTA "majority of trading", eltrader, stocknotify, MSH,
   cmike); distal = min(low) over the base ∪ the first departure candle; for REVERSAL (DBR) also ∪ the adjacent
   leg-in candle's low (MAK/TV tutorial; stocknotify exceptional; cmike). Supply mirrored. Record the wick proximal
   as well (minority convention) so the page can show both.
6. **Departure test (Moreno 2:1 + consolidate away).** Let H = distal→proximal height. The run must reach ≥ 2 × H
   beyond the proximal (and ≥ 1.5 × ATR14, AW) within 10 bars of d, and at least one candle after d must have its
   whole OHLC outside the box before any return (Moreno "one full OCHL candle"). Fail → not a zone.
7. **Width cap and refinement.** If H > 1.5 × ATR14 (cmike; SDZ Pro uses 1.0): refine to the sub-base = the shortest
   run of base candles ending at d that holds ≥ 50 % of the base closes (OTA "majority of trading" on a lower
   timeframe); still > cap → skip (stocknotify "skip the zone if the risk limit can't accommodate the stop").
8. **Origin vs pause (the fix for "not at the move's origin").** For each impulsive leg = from a confirmed swing
   low (N-bar pivot, David's major structure) to the next swing high: the ORIGIN zone is the first valid zone (steps
   2–7) whose base contains the pivot bar or whose base starts ≤ 2 bars after it. Later valid zones inside the same
   leg are CONTINUATION zones (RBR), kept only if their own departure passes step 6 and they do not overlap the origin
   box; overlapping boxes of the same leg merge into the earliest (LuxAlgo/AW merge). A departure with no pause before
   it produces no zone (Seiden: the origin is "the area of price stability", not a candle).
9. **Zone exists from the close of the departure candle** (Seiden "On the close of the candle (B)") — no look-ahead.
   Optional gate for David's page: the departure run closes beyond the previous confirmed swing (BOS); in the classic
   school this is a +2 "strength" grade, not a gate.
10. **Score 0–10 (OTA odds enhancers, second-hand points):** strength of departure 0–2 (run ≥ 2 H = 1, ≥ 4 H or body
    ≥ 2.5 × avg = 2; gap/FVG in the run +1 capped at 2 total with the BOS grade) ; time at level 0–2 (1–2 base candles
    = 2, 3–4 = 1, 5–6 = 0); freshness 0–2 (0 tests = 2, 1 test = 1, ≥ 2 = 0); profit zone 0–2 (distance to the nearest
    opposing live zone ≥ 4 H = 2 [Seiden "chart must offer 4:1"], ≥ 2 H = 1, else 0); curve / big picture 0–2
    (demand in the lower third of the HTF range = 2, middle third = 1, upper third = 0; supply mirrored; eltrader
    thirds). Trade ≥ 8 (babypips recollection); show every valid zone with its score.
11. **Lifecycle.** fresh → tested (a wick reaches the proximal; record depth: ≤ 50 % "shallow", > 50 % "deep"
    [Wendell guideline], 100 % = to the distal) → re-tradeable only if the move from the last touch made a new
    extreme (Rick Wright) → consumed after 3 separate visits (classic; a visit ends after 3 bars outside) → broken on
    one CLOSE beyond the distal (wick = fake break, counts as a touch) → flipped: after a break, the first return
    from the other side uses the same box as the opposite zone once → dead on a close back through it. No age expiry
    (Seiden). Superseded (page convention, David): a CHoCH against the side.
12. **Trade plan drawn on the box.** Entry = limit at the body proximal (or confirmation entry on a close back
    through it); stop = distal + buffer (max(spread, 0.1 × ATR14; proea 1 tick); target = just before the opposing
    live zone, required ≥ 3:1 with the chart offering ≥ 4:1 (Seiden); position size from the stop distance.

---------------------------------------------------------------------------------------------------------------------

## 12. Sources

Primary (originators)
- Sam Seiden, "Focus on True Supply and Demand", SFO Magazine Jan 2005 (PDF, full text read) — https://c.mql5.com/forextsd/forum/65/sam_seiden_sfo_demand_amp_supply.pdf
- Online Trading Academy, Core Strategy Course curriculum (2017, 2018 PDFs) — https://www.sharekhan.com/Upload/General/CoreStrategy.pdf , https://www.sharekhan.com/MediaGalary/docs/CoreStrategyCourse-201805051400238399966.pdf
- Seiden / OTA Q&A 2008 ("two lines … majority of trading", stop below the lower line) — https://www.fxstreet.com/education/lessons-from-the-pros-200805190000
- Seiden, "XLT odds enhancers" 2011 — https://www.fxstreet.com/education/lessons-from-the-pros-201109070000
- Seiden, 2013 (profit zone, 3:1 minimum, "very little activity between") — https://www.fxstreet.com/education/lessons-from-the-pros-201301290000
- Seiden/Fulkerson 2014 ("scored a 9", profit zone) — https://www.fxstreet.com/education/lessons-from-the-pros-201406170000
- Seiden, "Have Markets Really Changed?" 2014 (departure, time at level, first retracement, origin) — https://www.fxstreet.com/education/lessons-from-the-pros-201408120000
- Seiden, profit zones 2014 (Crude Oil 8/26/14, target ≥ the initial rally's high) — https://www.fxstreet.com/education/lessons-from-the-pros-201409020000
- Seiden, "The Age of Supply and Demand" 2015 — https://www.fxstreet.com/education/lessons-from-the-pros-201509150000
- Seiden, "Thinking Better Odds" 2016 (3:1 needs 4:1) — https://www.fxstreet.com/education/lessons-from-the-pros-201601190000
- Rick Wright (OTA), re-entry rule, CADJPY example 2016 — https://www.fxstreet.com/education/lessons-from-the-pros-forex-201603150000
- Rick Wright (OTA), rally/base/drop vocabulary 2019 — https://www.fxstreet.com/education/lessons-from-the-pros-forex-201504290000
- Brandon Wendell (OTA), how price leaves the level — https://www.fxstreet.com/education/lesson-from-the-pros-stocks-201307090000 , https://www.fxstreet.com/education/lesson-from-the-pros-stocks-201603150000 , https://www.fxstreet.com/education/lessons-from-the-pros-india-markets-201403180000
- Núria Foj Alvira (OTA), strong vs weak departure 2015 — https://www.fxstreet.com/education/lesson-from-the-pros-stocks-201504280000
- Alfonso Moreno, "Supply and demand in a nutshell" (Forex Factory, 403 — rules quoted from search excerpts) — https://www.forexfactory.com/thread/428204-supply-and-demand-in-a-nutshell-by-alfonso , https://www.forexfactory.com/showthread.php?p=8150789 , https://www.forexfactory.com/thread/post/8383937
- Moreno eBook mirrors (not fetchable today) — https://pdfcoffee.com/supply-and-demand-basic-alfonso-morenopdf-pdf-free.html , https://www.coursehero.com/file/44425233/OldNutshellRulespdf/
- babypips "Odd Enhancers – Sam Seiden" (403; excerpt) — https://forums.babypips.com/t/odd-enhancers-sam-seiden/39321
- OTA Professional Futures Trader manual (Best/Good/Poor; excerpt) — https://repubitdigital.com/futures-manual?i=482968&p=290&view=issueViewer
- OTA-style lesson "The Rally Base Drop Pattern" (Scribd; excerpt) — https://www.scribd.com/document/1069306183/Lesson-2-The-Rally-Base-Drop-Pattern
- ICT 2016 order-block talk (AI summary) — https://videohighlight.com/v/nBGsHuxNKbE

Educator / concept pages
- eltraderfinanciado — https://www.eltraderfinanciado.com/en/blog/supply-and-demand-zones
- stocknotify (1–6 base candles, body proximal, exceptional marking) — https://www.stocknotify.in/learn/how-to-draw-supply-demand-zones
- MAK Trading School / TradingView HDFCBANK tutorial (wick proximal, formation distal) — https://www.tradingview.com/chart/HDFCBANK/EpzdjqTF-Proximal-and-Distal-Line-Plotting-For-Supply-and-Demand-Zones/ , https://maktradingschool.com/how-to-draw-proximal-and-distal-lines/ (page is images)
- protradingschool (pin-bar bases) — https://www.protradingschool.com/how-to-draw-supply-and-demand-zones/
- norfolkfxtrader (last opposite candle, open-to-wick) — https://www.norfolkfxtrader.com/basics-of-supply-and-demand-trading-a-helpful-illustrated-guide/
- therighttrader S&D — https://therighttrader.com/learn/price-action/supply-and-demand-zones ; OB vs zone — https://therighttrader.com/learn/comparisons/order-block-vs-supply-and-demand-zone
- LuxAlgo concepts — https://www.luxalgo.com/library/concept/supply-and-demand-zones.md , https://www.luxalgo.com/library/concept/zone-scoring-and-refinement.md
- backtrex OB vs S&D — https://backtrex.com/en/blog/order-block-vs-supply-demand-zone
- crosstrade — https://crosstrade.io/learn/price-action/supply-and-demand-zones
- Dukascopy — https://www.dukascopy.com/swiss/english/marketwatch/articles/supply-and-demand-trading/
- edgeful — https://www.edgeful.com/blog/posts/supply-and-demand-trading
- dotnettutorials (OTA-style, India) — https://dotnettutorials.net/lesson/how-to-trade-with-supply-and-demand-zone
- proea.app desk rule — https://proea.app/en/blog/supply-and-demand-zones
- TradingView "Odds Enhancers" idea posts (OTA scoring write-ups; excerpt) — https://tr.tradingview.com/chart/USDCAD/pDLqtpxv-USDCAD-Set-Forget-Supply-Zone-1-28168-1-28213 , https://pl.tradingview.com/chart/GBPUSD/GIurxWx9-GBPUSD-M15-Level-on-top-of-Level-Supply-Zone-1-34048-1-34370 , https://www.justapricetrader.com/p/odds-enhancers (unreachable today)
- Skillz Trading video (Arabic; AI summary) — https://videohighlight.com/v/mqTAtkSpgsU

Open source (code read)
- MSH Demand & Supply Zones Pro — https://www.tradingview.com/script/KXK4NQjc-MSH-Demand-Supply-Zones-Pro/
- Supply and Demand Based Pattern [RH] — https://www.tradingview.com/script/N1UG66qp-Supply-and-Demand-Based-Pattern-RH/
- ZikZak Supply & Demand Zones — https://www.tradingview.com/script/J56t02Ek-Advanced-S-D-Engine-ZikZak-Trader30
- skbohler Demand Zone Candles — https://www.tradingview.com/script/vphHn1sk-Supply-Demand-Zone-Candles
- LuxAlgo Rally Base Drop Signals — https://www.tradingview.com/script/laRupsVf-Rally-Base-Drop-Signals-LuxAlgo
- DOSALGO Indecisive with Gaps — https://www.tradingview.com/script/mFNpyFMe-Indecisive-Candles/
- cmike444 supply-and-demand-zones — https://unpkg.com/@cmike444/supply-and-demand-zones@1.3.1/README.md
- MT4 Supply and Demand Indicator 1.7 manual — https://www.mql5.com/en/blogs/post/773763
- 10-30 ports (Shved, BigBeluga, LuxAlgo VR, SDZ Pro, Flux, Svopex, CienF, AW, PRC) — URLs in ~/forex/engine/research/supply_demand/opensource_report.md §1
