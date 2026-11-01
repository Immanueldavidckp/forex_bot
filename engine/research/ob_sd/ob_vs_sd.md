# Order block (ICT / SMC) vs supply & demand zone (Seiden / OTA) — settling the confusion

Research 2026-11-01 (Fable 5.1 agent). Every claim carries its URL; `[S#]` points to the Sources list at the end.
Read-only context: `~/forex/engine/research/supply_demand/method_report.md` (§2.5), `opensource_report.md`,
`engine/smc_marks.py`, `engine/supply_demand.py`, `~/FOREXBOT/FOREXBOT/1 Strategy/Rules/new rules.md` §8–12.

Reachability: reddit.com refuses the crawler entirely (search and fetch) [S60]; forums.babypips.com, forexfactory.com and
its mirror metalsmine.com answer 403 [S61][S62]; Scribd ICT transcripts are truncated [S63]; the LuxAlgo Pine endpoint
returns 404, so the LuxAlgo SMC source was read from a public gist mirror of the script [S20]. Forum positions below are
therefore quoted from search-engine excerpts (marked "excerpt") or from forums that do answer (EarnForex).

---------------------------------------------------------------------------------------------------------------------

## 0. The one-paragraph answer

They are two different objects that very often sit on the same candles. The **supply/demand zone** (Seiden/OTA lineage)
is the *base* — "a price level where supply and demand are in relative balance", "the origin of the movement of price"
— boxed from the base's wicks/bodies, graded by how price *left* it, how long it *sat* there, and whether it is *fresh*;
it needs no structure break [S1][S2][S7]. The **order block** (ICT) is *one candle*: in ICT's own 2016 lesson "the lowest
candle or price bar with a down close that has the most range between open to close" near support, traded from the
*open* with the 50 % *mean threshold* of the body, validated when a later candle "trades through" its high [S10]; in
ICT's later and in most SMC teaching it is "the last opposing candle before the displacement that breaks structure"
[S11][S12][S14]. Where the base is a single candle the two boxes are the same box ("if the origin is a single candle,
both names apply" [S8]); where the base is several candles the OB is the last (or the lowest) of them, inside the zone
[S13][S14][S15]; and where the OB school takes the last opposite candle *inside the leg* before a second displacement,
the zone school still marks the *origin* [S1][S7][S16]. Neither box can show "where the banks' orders rest": "Neither
drawing shows what a bank ordered" [S8]; "cannot verify from a chart that specific institutional orders rest in one
particular candle" [S13].

---------------------------------------------------------------------------------------------------------------------

## 1. Side-by-side

| | **Supply / demand zone** (Seiden, OTA, classic S&D) | **Order block** (ICT 2016 "Month 04") | **Order block** (ICT 2022-style / SMC mainstream / David's rule) |
|---|---|---|---|
| **What it IS (candles)** | The **base**: "one to a handful of candles of overlapping range" before a strong departure [S7]; "the 1-3 bars immediately before the impulsive move" [S17]; Dukascopy "three to five candles moving sideways… followed by a sharp breakout" [S18]; base candle body ≤ 50 % of its range [S6][S19]. Seiden: "a price level where supply and demand are in relative balance", "the origin of the movement of price" [S1]. | **One candle**: "the lowest candle or price bar with a down close that has the most range between open to close… and is near a support level" (bullish); "everything I say here you'll just reverse for a bearish order block" [S10]. Bodies only: "do not use the wicks, don't use the very high or the very low" [S10]. | "The last opposing candle before a Break of Structure with displacement" [S14]; "the last opposite-colour candle before a strong displacement move that breaks structure" [S13]; "A valid order block is created when price displaces and closes below the opening price of a series of up-close candles" (bearish) [S11]. A run of consecutive opposite candles may be boxed as one [S12]. David: "Final bullish candle before strong bearish displacement" that "Break[s] a valid previous confirmed Swing Low" by close [S64]. |
| **Where it sits** | At the **origin** of the move (Seiden) [S1]; formations RBR/DBD (continuation, mid-leg) and RBD/DBR (reversal, at the extreme) [S7][S6]; reversal zones at range extremes "graded highest by many practitioners" [S7]. | At the **swing low/high** itself (the *lowest* down-close candle "near a support level") [S10]. LuxAlgo SMC code implements exactly this: after a BOS/CHoCH it loops from the pivot to the current bar and keeps the bar with the minimum low (`min := math.min(low[i], min)`) [S20]; joshyattridge's Python port takes "the candle with the lowest low in the range from after the swing high up to the break candle" [S21]. | **Inside the leg**, immediately before the displacement that breaks structure — may be mid-leg: "A valid order block must form within the same price leg" as the BOS/CHoCH [S22]; MQL5 CodeBase detector searches "10 bars back from the break candle" for "the last down-closing candle before an impulsive close above a recent swing high" [S23]. "Within or at the edge of that zone" [S13][S16]. |
| **Box size / width** | Whole base, wick (distal) to body or wick (proximal) [S6][S7][S19]; "potentially 3 to 8 times wider" than the OB [S24]; "typically 20-50 pips" vs OB "5-15 pips" [S25]; a 50-pip daily zone containing a ~10-pip H1 OB [S26]. Tools cap height at 1.0–1.5 ATR [S19][S27]. | One candle **body** (open→close); entry "at the open of the down candle… or five pips above it"; "50 level or halfway point is the mean threshold" [S10]. | One candle: full range "or from the candle's open to its close for a more refined zone" [S25]; LuxAlgo: wick-to-wick "the widest honest zone", 50 % mean threshold [S12]; MQL5 default full high-low, option body-only [S23]. On our bars the OB candle lies inside the S&D base of the same break in 81 of 101 pairs [S65 §5]. |
| **What validates it** | **Departure strength** ("how did price leave the level"), **time at level** (less is better), **freshness**, **profit margin** to the opposing zone, big picture, retracement/curve [S2][S3][S4]; "departures that break a prior swing point carry more weight" — a *weight*, not a gate [S7]; "any sharp move qualifies", no BOS [S25]; "S&D needs none of these [BOS/CHoCH, displacement, FVG, sweep]" [S24]. Moreno (second-hand): 2:1 imbalance + consolidate away one full candle [S5]. | A later candle **trades through the OB's high** ("the high of the lowest down candle… is traded through by a later formed candle") [S10]; displacement as evidence of "someone with a whole lot of money" [S10]; no BOS, no FVG, no sweep named in the lesson [S10]. | **Displacement + BOS/CHoCH**: "No displacement means no order block, whatever the candle looks like" [S28]; "without this, many SMC traders would not call it a valid order block" [S13]; FVG "often required" [S24] / "strengthens" [S28]; liquidity sweep: "sweep any stops before considering it as a valid buy-side order block" [S11], "stricter models want a liquidity sweep just before" [S12], TradingFinder: OB "carries more weight when there is liquidity… before reaching the order block" [S29]. David: displacement body ≥ 1.5× avg body of 10, BOS by close, FVG from the same displacement [S64]. |
| **Used up / invalid** | Fresh → tested → "3 or more tests → broken" (classic school) [S6][S17]; a **close** through the distal edge is a break [S8][S27]; wicks don't invalidate [S30]; broken supply "often transforms into a demand zone" (flip) [S18][S31]. | "Ideally the best order blocks will not see price trade down below the midway point of the entire body" [S10]; stop below the OB low [S10]. | First touch "spends" it: "An order block is only valid the first time price reaches it. Even a slight wick… counts as mitigation" [S22]; "valid only on its first test" (strict) vs "until price closes fully through" (loose) [S25]; close through the far side → re-labelled **breaker** [S12][S32]. Tools: MQL5 default "any wick touching the zone" mitigates [S23]; LuxAlgo SMC: low crossing the box top = mitigated, `close < ob_btm` = removed [S20]; joshyattridge `close_mitigation` option (low vs min(open,close) below the bottom) [S21]. |
| **Entry / stop / target** | Limit at the proximal line, stop "very close to" the level beyond the distal [S1]; stop "just beyond the distal line" [S19]; target = the opposing zone ("profit zone… the distance between the demand area and the supply area") [S1], 3:1 minimum, "if the chart offers 3:1, look for 4:1" [S6]; OTA example 3-point stop / 15-point target [S3]. "No confirmation is required in supply-demand trading" [S33]. | Buy at the open of the down candle (+5 pips), stop "below the bullish order block's low or below the close", raise to "just below the 50 percent"; target "external range liquidity" [S10]. | Limit at the OB edge / open / 50 % ("refine the entry to the open or the 50% mean threshold of the candle's body") [S26]; stop beyond the OB far edge (+ ATR buffer in some rule sets) [S34]; often LTF confirmation (CHoCH / sweep / engulfing) before entry [S26][S22]; target = liquidity / opposing array; "there is no universal 2:1 or 3:1 target" [S34]. David: M5 BOS after the retrace, one normal entry [S64]. |

Width ratio in practice: backtrex 3–8× [S24]; quantum-algo 20–50 pips vs 5–15 pips (≈ 3–4×) [S25]; fxnx 50 vs 10 pips (5×)
[S26]; on GOLD/EURUSD M15–H1 the measured base is 1–4 candles and the prototype's boxes average ~1 ATR [S65 §5] while the
OB candle is ~0.6 ATR, i.e. ≈ 1.5–2× here because the base is usually short.

---------------------------------------------------------------------------------------------------------------------

## 2. The misunderstandings that circulate — who says it, who disagrees, what the authoritative sources say

### M1 — "An order block is just a supply/demand zone renamed"
- **Who says it**: EarnForex thread opener dompips: order blocks are "another form of supply & demand", a bullish OB "is a
  demand zone" [S35]; Price Action Ninja: "order blocks are supply and demand zones – just a different type" [S36]; a
  YouTube summary defines "Demand candle: Last bearish candle before a bullish expansion" word-for-word as the OB [S37];
  the TradingView script "Order Blocks Finder + Supply and Demand Zones" literally "plots the resulting Order Blocks as
  refined Supply and Demand zones" [S38]; DMITRY ORDERBLOCKS: order blocks "also known as supply and demand zones" [S39];
  Vantage reports the critics' line "basically support/resistance or supply/demand with a new name" [S40]; AlgoStorm
  explains the OB as "bases preceding breakouts — a concept from supply/demand zones (Sam Seiden) and Wyckoff" [S41].
- **Who disagrees**: therighttrader: "They are not two words for the same box… Do not call every demand zone an order
  block" [S8]; ForexBee: "The order block is not the same as the supply demand" [S33]; LuxAlgo: S&D is "the older, looser
  framing… order blocks are the stricter, candle-level version" [S28]; dailypriceaction: "They're related, but not the
  same" [S22]; keenbase: "Order blocks differ from conventional supply and demand zones, typically from a base formed over
  two or three candles. In contrast, order blocks arise out of narrow-range consolidations" [S42]; tradingstrategyguides:
  "ICT focuses more on order blocks and de-emphasizes the broader zone concept" [S16].
- **What the primary sources say**: Seiden defines the zone as a *balance area* / *origin* and grades it by departure,
  time, freshness, profit margin [S1][S2]; ICT defines a *specific candle* with an open-price entry and a body
  mean-threshold, validated by a trade-through of its high, and his lesson "never uses" the words supply and demand
  [S10]. Different definitions, different grading, same neighbourhood. The honest statement is the FAQ answer "Not
  quite, but they are close" / "layers of one concept rather than competitors" [S13]. No Seiden statement on order
  blocks was found anywhere [S43].

### M2 — "The last opposite candle is the demand zone"
- **Who says it**: Trade Ideas: demand = "last down candle(s) before a strong up move" [S44]; the BigBeluga S&D indicator
  (11k boosts) finds three same-colour candles and boxes "the last bull candle" before them with a fixed 2×ATR height
  [S66 §2.5]; the YouTube summary above [S37]; **David's current `supply_demand.py`** anchors every box on "David's
  zone candle (the LAST OPPOSITE-colour candle ≤ 5 bars before the leg-out)" [S67] — which is the OB definition.
- **Who disagrees**: Seiden — demand is the sideways *area* price broke out of, "the origin of the movement" [S1];
  LuxAlgo's S&D page explicitly contrasts: the OB is "the last opposing candle before a displacement rather than from a
  base" [S7]; crosstrade: base = "the 1-3 bars immediately before the impulsive move" [S17]; Dukascopy 3–5 candles [S18];
  cmike444 library: base = run of 1–6 indecisive candles, box = base bodies to pattern wick [S19]; keenbase [S42].
- **Verdict**: the last opposite candle is the *order block*; the S&D zone is the *base* containing it. The two
  coincide only when the base is one candle [S8].

### M3 — "Every base inside a leg is a zone"
- **Who says it (partly)**: the classic school does list RBR / DBD continuation formations as valid zones [S6][S7][S19];
  Flux / Shved / SDZ-Pro style tools draw a box at every pivot [S66 §2].
- **Who disagrees**: Seiden — the zone is the *origin* [S1]; LuxAlgo — reversal zones "at range extremes are graded
  highest" [S7]; maktradingschool — for continuation patterns "ignore the leg-in" [S45]; SMC "extreme vs decisional":
  "The Extreme POI (at the far end/corner) has the highest validity… A Decisional POI can be used if all validity
  checks apply and the first corner (IDM) has already been taken out"; "the first swing or corner after a BOS is often
  a trap" [S46]; dailypriceaction: the OB must be "within the same price leg" as the break [S22]; Trade Ideas: "five
  active zones beat fifty stale rectangles" [S44].
- **Verdict**: a mid-leg base is at most a *continuation* (S&D: RBR/DBD) or *decisional* (SMC) zone; the origin /
  extreme is the primary one in both schools.

### M4 — "The order block must be at the swing high / low"
- **Who says it**: ICT himself in 2016 — "the lowest candle… with a down close… near a support level" [S10]; the LuxAlgo
  SMC indicator (the most-used SMC script) codes it: the bar with the minimum low between the pivot and the break
  [S20]; joshyattridge's Python port does the same [S21]; LuxAlgo's "Order Blocks" tools "identify Order Blocks by
  locating specific swing high and swing low points (fractals)" [S47].
- **Who disagrees**: ICT's later framing and nearly all SMC articles — the last opposing candle *before the displacement*
  that breaks structure, wherever it is in the leg [S11][S13][S14][S22]; the MQL5 CodeBase detector searches only 10
  bars back from the break candle [S23]; David's rule [S64]; `smc_marks.py` (last opposite candle before the LAST
  displacement of the break) [S68].
- **Verdict**: two legitimate, *named* conventions — the **swing / extreme OB** (ICT 2016, LuxAlgo, Trading Hub
  "Extreme") and the **decisional / last-before-displacement OB** (ICT 2022-style, MQL5, David). A chart must say which
  one it draws; the confusion comes from calling both "the OB".

### M5 — "A supply/demand zone needs a BOS"
- **Who says it**: David's rules ("If no valid Bearish BOS: Supply = INVALID") [S64]; CienF-OTC "Elite" mode hides the zone
  "until price breaks that structure point" [S48]; SMC-flavoured S&D writers [S16].
- **Who disagrees**: Seiden / OTA never mention a structure break — the enhancers are departure, time, freshness,
  profit margin, big picture, retracement [S1][S2][S4]; LuxAlgo: a departure that breaks a swing "carr[ies] more weight"
  (grade) [S7]; backtrex: "S&D needs none of these" [S24]; crosstrade [S17]; quantum-algo: "any sharp move qualifies" [S25].
- **Verdict**: classic S&D does *not* require a BOS; requiring one is the OB school's gate applied to the zone — a
  legitimate hybrid (it is literally what David's "valid supply" rule is) but it should be called "BOS-confirmed zone",
  not "supply and demand". Measured on 39k zones it changed the hold rate by ±2 points, no consistent sign [S67 header].

### M6 — "No FVG, no order block"
- **Who says it**: gist.ly summary "Always ensure your order blocks and structure zones include a fair value gap" [S49];
  backtrex "often required" [S24]; fxnx "often seen as a Fair Value Gap" [S26]; David §12 "FVG REQUIRED" for the *setup*
  (not for the zone) [S64].
- **Who disagrees**: ICT 2016 — the validation is a trade-through of the OB's high, FVG not mentioned [S10]; LuxAlgo:
  "stronger blocks leave an FVG" — a grade [S28]; algokings: FVG is "confirmation… not stated as a requirement" [S13].
- **Verdict**: FVG is a grade (or a setup requirement, as in David's rules), not part of the OB definition.

### M7 — "No liquidity sweep, no order block"
- **Who says it**: ICT 2022-style content — "sweep any stops before considering it as a valid buy-side order block"
  [S11]; Two Side Traders — "The POI's validity increases significantly if it formed after removing people's stop
  losses" [S46]; TradingFinder script weights OBs by liquidity before the block [S29].
- **Who disagrees**: ICT 2016 lesson — no sweep requirement [S10]; LuxAlgo: sweep is "a grading factor" / "stricter
  models" [S12][S28]; dailypriceaction's three rules are structure, displacement, unmitigated — no sweep [S22].
- **Verdict**: a sweep is a grade; the "breaker" is the block type whose definition *does* require it [S32].

### M8 — "More tests make a zone stronger" (support/resistance thinking)
- **Who says it**: Shved "Supply and Demand" (the most-copied MT4/MT5 S&D indicator): untested → verified → "proven" after
  > 3 tests [S66 §2.1]; Flux ranks by retest count [S66 §2.4].
- **Who disagrees**: Seiden: "The highest-odds buying opportunity is when prices revisit an objective demand area for
  the first time, not the second, third or fourth" [S1]; OB school: first touch spends it [S22][S25]; SDZ-Pro scores
  *fewer* retests higher [S27]; measured: SDZ-Pro strength > 5 zones broken within 200 bars 33–57 % vs 74–85 % — the
  only built-in score that predicted survival [S66 §3].
- **Verdict**: both schools agree — fresh is best; the "proven" vocabulary is S/R, not S&D or OB.

### M9 — "Bodies vs wicks" and "wick touch vs close"
- ICT: bodies only, entry at the open, mean threshold = 50 % of the body [S10]. LuxAlgo: wick-to-wick is "the widest
  honest zone" [S12]; S&D proximal "commonly the candle bodies… conventions vary" [S7]; "neither is objectively correct;
  pick one convention" [S50]. Mitigation: MQL5 default "any wick touching the zone" [S23]; LuxAlgo SMC: a wick in = mitigated,
  a close beyond the far side = removed [S20]; S&D: a close through the distal is the break, "wicks don't invalidate" [S30].
- **Verdict**: not a disagreement about the object, only about drawing; state the convention.

### M10 — "The box shows where institutional orders rest"
- Said by most SMC/ICT marketing [S14][S36]; rejected by therighttrader ("Neither drawing shows what a bank ordered")
  [S8], algokings ("cannot verify from a chart that specific institutional orders rest in one particular candle") [S13],
  AlgoStorm ("Unprovable and likely oversimplified"; 82 % vs 78 % control on ES, 47 % vs 51 % on EUR/USD) [S41],
  Price Action Ninja on Seiden's bank-orders explanation [S51]; our own measurement: zones held 58.2 % vs 57.9 % for
  random levels [S67 header].

### M11 — a stray definition that conflicts with all of the above
- "a bullish order block is a bearish candle followed by an engulfing candle" circulates in some guides [S52]; the
  original Order Block Finder lineage (wugamlo → LuxAlgo) defines a bullish OB as "a downward candle followed by a
  specified number of consecutive upward candles" with a minimum % move [S53] — a pattern filter, not ICT's candle.

---------------------------------------------------------------------------------------------------------------------

## 3. When they coincide, when they differ, and how traders who use both combine them

**Coincide**
- Single-candle base at the origin: "if the origin is a single candle, both names apply" [S8]; prototype data: of the
  valid S&D zones on GOLD/EURUSD M15–H1, 1-candle bases dominate (Svopex: 20–25 of 27–46) [S66 §3] and the OB candle is
  inside the S&D base in 81 of 101 pairs [S65 §5].
- Both die the same way: "A close through the far side of the box is the usual invalidation for either mark" [S8].
- Both are graded by the same things under different names: departure strength ≈ displacement; freshness ≈ unmitigated
  [S2][S7][S22].

**Differ**
- Multi-candle base: the zone takes the whole base, the OB the last (SMC) or the lowest (ICT 2016 / LuxAlgo code) candle
  [S7][S10][S20]. Tools cap the base at 3–6 candles and 1–1.5 ATR [S19][S27]; the OB has no such cap because it is one
  candle (LuxAlgo filters bars whose range ≥ 2× ATR/cumulative mean range [S20]).
- OB inside the leg vs zone at the origin: a leg with two displacements has an origin base (S&D zone; ICT-2016 / "extreme"
  OB) and a mid-leg last-opposite candle before the breaking displacement (the "decisional" OB; David's OB) [S10][S46][S68].
- Continuation bases (RBR/DBD): the S&D school keeps them as zones (lower grade) [S6][S7]; the OB school marks the
  opposite candle in them only if the departure broke structure [S22][S28].
- Validation gate: S&D none / grade; OB displacement + BOS [S24][S28].
- Life after the first touch: S&D degrades over 3 tests [S6][S17]; OB is spent on the first touch (strict) [S22].
- Target: S&D targets the opposing zone with ≥ 3:1 [S1][S6]; OB targets liquidity / the next array, "no universal 2:1 or
  3:1" [S10][S34].

**How practitioners combine them**
- "S&D for the map, OB for the GPS": "The S&D zone tells you where to look on the chart. The order block inside it tells
  you exactly where to enter and where to place your stop" [S16]; "Use the broad zone for context and the order block for
  the entry once price arrives" [S25]; "mark the higher-timeframe zone for context, then find the order block inside it
  for the entry" [S13]; "A 50-pip daily supply zone → H1 bearish OB inside it spans about 10 pips → risk falls from 50+ to
  just 15 pips" [S26]; "Traders may enter the zone and tighten the stop to the candle, or wait for price to reach the
  candle inside it" [S8].
- Multi-timeframe: S&D timeframes "separated by a factor of 4 to 6" [S6]; LTF zone nested in an HTF zone refines the entry
  [S50]; SMC: HTF POI → LTF CHoCH/sweep/engulfing confirmation [S26][S46]; David: H1 bias → M15 zone → M5 BOS entry [S64].
- Counting confluence honestly: "If two rule sets produce the same rectangles on the same bars, they should not be counted
  as independent confluences" [S34].
- Journal discipline: "Write 'candle' or 'base' in your journal. If the note could be either, the level is not ready" [S8].

---------------------------------------------------------------------------------------------------------------------

## 4. Related blocks that get mixed in (one line each)

- **Breaker block** — "an order block that failed and flipped roles"; strict ICT reading: "the failing swing must first
  trade beyond a prior high or low" (liquidity run), looser retail reading: "any violated order block"; "the Smart Money
  Concepts version of the classic support-resistance flip" [S32]. tradingstrategyguides: "price must have swept liquidity"
  [S54]. ictkillzone's variant test: body close through the OB's far boundary = breaker, wick only = mitigation [S55].
- **Mitigation block** — "the same role-flip without that raid: the swing fails short of the prior extreme" [S32]; "The
  defining detail that separates a mitigation block from its near twin, the breaker block, is the failed swing"; "Any sweep
  of the extreme reclassifies the setup as a potential breaker" [S56]. (Some sites misuse it as "an OB retested as
  continuation" [S57] — not the ICT meaning.)
- **Rejection block** — "the ICT array built from a wick rather than a candle body": at a swing high "the span from the top
  of the candle's body to the extreme of the wick"; "the order block uses the body of the last opposite candle at a move's
  origin" [S58].
- **Propulsion block** — "a candle that trades back into an earlier order block" and then "propels price away"; "an order
  block that forms on top of an earlier order block"; its 50 % body mean threshold should hold; ICT 2016 Core Content Month 04
  [S59]; LuxAlgo: "Every propulsion block is an order block; very few order blocks earn the propulsion label" [S69].
- **Flip zone** (S&D vocabulary) — a broken zone that takes the opposite role: "a broken supply zone becomes a demand zone,
  and a broken demand zone becomes a supply zone" [S31]; Dukascopy "often transforms" [S18]; implemented as a side flip
  after a confirmed close in Flux / AW / SDZ-Pro [S66 §2.4][S27]. The same candles the ICT school calls a breaker (with
  sweep) or mitigation block (without) [S32][S56].
- **Extreme vs decisional (POI / OB)** — "The Extreme POI (at the far end/corner) has the highest validity… A Decisional
  POI can be used if all validity checks apply and the first corner (IDM) has already been taken out" [S46]; a YouTube
  summary: extreme blocks "located at the extremes of a price range, specifically in the bottom and top quarters", "Fair
  price blocks… within the intermediate price ranges" [S37]; Trading Hub-based script: "Main Order Blocks (Extreme,
  Decisional, and SMT)… Check that the candle is not inside bar" [S70]. Not standardised — position labels, not new objects.
- **Decision point (DP)** — the same idea in S&D vocabulary: the swing/OB "that caused the Break of Structure" [S71].
- **POI (point of interest)** — "a price zone where large orders are likely to sit, so price often reacts there… not a
  signal on its own" [S72]; "not all Order Blocks or Order Flows can be considered POIs" [S46]; glossary: "Key price level
  where traders anticipate significant market reactions" [S73].
- **Inducement (IDM)** — "The first swing after a BOS/CHoCH… often acts as a trap" [S46]; glossary: smart money
  "deliberately moves prices in a specific direction to trap retail traders" [S73].
- **Order flow (ICT)** — "corrective candles that form before a Break of Structure" [S74] — i.e. the pullback series the OB
  belongs to.
- **Mean threshold** — "the halfway point of the candle body, measured open to close… do not use the wicks" [S10].

---------------------------------------------------------------------------------------------------------------------

## 5. Chart situations to show the definitions on a real chart

Each: the candles → what the S&D school marks → what the ICT/SMC school marks → notes.

1. **One bearish candle at the swing low, then a displacement candle that closes above the prior swing high (DBR, 1-candle
   base).** S&D: a demand zone = that candle, wick distal, body proximal, fresh, departure strong [S1][S7]. ICT 2016: the
   bullish OB = that candle (lowest down-close, trade-through of its high confirms) [S10]. SMC/David: valid demand / OB
   (last opposite candle + displacement + BOS by close) [S14][S64]. **Same box, every school** — the "coincide" case [S8].

2. **Three small-bodied candles at the low (bodies ≤ 50 % of range), the last one bearish, then the displacement.** S&D:
   the zone is all three (base), distal = lowest wick, proximal = highest body [S6][S19]. SMC: the OB is the last bearish
   candle only [S14]; LuxAlgo-anatomy allows boxing the run of opposite candles [S12]. LuxAlgo SMC *code*: the bar with the
   lowest low of the three [S20]. The OB sits inside the zone — the nesting case [S13][S16].

3. **Rally, a 2-candle pause, then a second rally that breaks the high (RBR, continuation base).** S&D: a continuation
   demand zone at the pause, lower grade, leg-in ignored [S6][S45]. SMC: the last down-close in the pause is the
   *decisional* OB; the origin candle of the whole leg is the *extreme* OB [S46]. ICT 2016 picks the extreme (the lowest
   down-close near support) [S10]; LuxAlgo SMC code picks the lowest-low bar, i.e. the origin [S20]; David's `smc_marks`
   picks the pause candle (last opposite before the *last* displacement) [S68]. **Two different OBs on one leg** — M4.

4. **A leg with an origin base, a mid-leg opposite candle, and the breaking displacement only after the second candle.**
   Seiden: the zone is the origin [S1]; `supply_demand.py` currently keeps the *earliest clean* box as "origin" and
   labels the one nearest the break "last" (= the OB) [S67]; this is the correct split (origin = S&D, last = decisional OB).

5. **A huge bearish candle (range > 2 ATR, news) followed by a rally that breaks structure.** LuxAlgo SMC excludes it as an
   OB candidate (`(high[i] - low[i]) < ob_threshold[i] * 2`) [S20]; S&D tools reject the base as too tall (cmike 1.5 ATR,
   SDZ-Pro 1 ATR) [S19][S27]; ICT would use the *body* and the 50 % mean threshold rather than the range [S10]. Shows why
   "the OB is the candle" needs a size convention.

6. **A rally that stalls below the prior swing high, then drops hard from a 2-candle base (RBD without a BOS).** S&D
   (classic): a valid supply zone — strong departure, fresh, no structure break needed [S2][S24][S25]. SMC: "No
   displacement means no order block" is satisfied, but no BOS → "many SMC traders would not call it a valid order block"
   [S13][S28]; David: INVALID supply, do not mark [S64]. **The M5 case** — the schools disagree by definition.

7. **A hammer at the swing low (long lower wick, small body), then the rally.** ICT: a *rejection block* from the body
   bottom to the wick low [S58]; if the hammer closed down it is also the OB candle, but ICT trades its *body* (open,
   mean threshold), not the wick [S10]. S&D: the wick is the distal line, the body the proximal — the zone *includes* the
   wick [S6][S7]. Same candle, two different boxes.

8. **A demand zone / bullish OB that is closed through, then price returns to it from below.** S&D: a *flip zone* — the
   broken demand is now supply [S31][S18]. ICT: a *breaker* if the swing that failed had first swept a prior high, a
   *mitigation block* if it had not [S32][S56]; ictkillzone's variant: breaker only if a *body* closed through [S55]. One
   more candle: price returns to a still-valid OB, prints a new bearish candle inside it and rallies → that new candle is
   a *propulsion block* [S59].

---------------------------------------------------------------------------------------------------------------------

## 6. What this means for the /smc page (no code written; for David's decision)

- `supply_demand.py` anchors on "the LAST OPPOSITE-colour candle ≤ 5 bars before the leg-out" [S67] — that is the OB
  (M2). A classic S&D layer anchors on the **base at the origin** (Seiden [S1], LuxAlgo [S7], crosstrade [S17]) and does
  not need the BOS gate (M5); the base run should be allowed to sit *before* the opposite candle, not only to extend it.
- David's "valid supply = final bullish candle before strong bearish displacement that breaks a swing low by close" [S64]
  is, word for word, the SMC order-block definition ("the last opposing candle before a Break of Structure with
  displacement" [S14]). Calling the layer "BOS-confirmed supply/demand" or "SMC supply (order block + base)" would end
  the confusion on the page; the classic S&D zone is the origin base without the gate (gate → score, as LuxAlgo [S7]).
- Two OB conventions exist (M4). The page could label `smc_marks` boxes "decisional OB (last opposite before the breaking
  displacement)" and optionally draw the "extreme OB" = the lowest down-close / highest up-close candle of the leg (ICT
  2016 [S10], LuxAlgo SMC [S20]) — on single-displacement legs they coincide.
- Keep wick-to-wick boxes with the body/open line drawn (ICT entry = open, mean threshold = 50 % of the body [S10]).

---------------------------------------------------------------------------------------------------------------------

## Sources

Primary / educators
- [S1] Sam Seiden, "Focus on True Supply and Demand", SFO Magazine 2005 (PDF): https://c.mql5.com/forextsd/forum/65/sam_seiden_sfo_demand_amp_supply.pdf
- [S2] OTA / fxstreet 2011, "XLT odds enhancers": https://www.fxstreet.com/education/lessons-from-the-pros-201109070000
- [S3] OTA / fxstreet 2014, fresh levels, 3-pt stop / 15-pt target: https://www.fxstreet.com/education/lessons-from-the-pros-201402180000
- [S4] babypips "Odd Enhancers – Sam Seiden" (403; search excerpt): https://forums.babypips.com/t/odd-enhancers-sam-seiden/39321
- [S5] Alfonso Moreno, Forex Factory (403; search excerpt): https://www.forexfactory.com/thread/post/8383937
- [S6] eltraderfinanciado, OTA-style write-up: https://www.eltraderfinanciado.com/en/blog/supply-and-demand-zones
- [S7] LuxAlgo concept "Supply & Demand Zones": https://www.luxalgo.com/library/concept/supply-and-demand-zones.md
- [S8] therighttrader, "Order block vs supply and demand zone": https://therighttrader.com/learn/comparisons/order-block-vs-supply-and-demand-zone ; and "Supply and demand zones" ("if the origin is a single candle, both names apply"): https://therighttrader.com/learn/price-action/supply-and-demand-zones
- [S10] ICT Mentorship Core Content Month 04 "Orderblocks" — verbatim auto-captions via OpenTools: https://opentools.ai/youtube-summary/ict-mentorship-core-content-month-04-orderblocks
- [S11] "Order Blocks Simplified – ICT Concepts" (third-party video, channel not identified; transcript summary): https://videohighlight.com/v/DMUiDBnTYc8
- [S12] LuxAlgo concept "Order Block Anatomy & Refinement": https://www.luxalgo.com/library/concept/order-block-anatomy-and-refinement.md
- [S13] AlgoKings, "Order Blocks vs Supply and Demand Zones: The Real Difference": https://www.algokings.net/learn/order-blocks-vs-supply-and-demand/
- [S14] Quantum Algo, "Supply & Demand Zones vs Order Blocks": https://www.quantum-algo.com/blog/supply-demand-zones-vs-order-blocks/
- [S15] crosstrade "Order blocks": https://crosstrade.io/learn/price-action/order-blocks
- [S16] tradingstrategyguides, "Day 11: Supply & Demand Zones vs Order Blocks": https://tradingstrategyguides.com/day-11-supply-demand-zones-vs-order-blocks-ict-smc-compared/
- [S17] crosstrade "Supply and demand zones": https://crosstrade.io/learn/price-action/supply-and-demand-zones
- [S18] Dukascopy "Supply and demand trading": https://www.dukascopy.com/swiss/english/marketwatch/articles/supply-and-demand-trading/
- [S19] @cmike444/supply-and-demand-zones README: https://unpkg.com/@cmike444/supply-and-demand-zones@1.3.1/README.md
- [S20] LuxAlgo "Smart Money Concepts" Pine source (gist mirror, `ob_coord`): https://gist.github.com/niquedegraaff/8c2f45dc73519458afeae14b0096d719 (original script: https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/)
- [S21] joshyattridge/smart-money-concepts `smc.py` (`ob`): https://raw.githubusercontent.com/joshyattridge/smart-money-concepts/master/smartmoneyconcepts/smc.py
- [S22] dailypriceaction, "Order Blocks Will Fail You Without These 3 Simple Rules": https://dailypriceaction.com/blog/order-blocks/
- [S23] MQL5 CodeBase "Order Block Detector" (ID 76878): https://www.mql5.com/en/code/76878 ; "Order Block Mitigation Tracker" (76068): https://www.mql5.com/en/code/76068
- [S24] backtrex, "Order block vs supply and demand zones": https://backtrex.com/en/blog/order-block-vs-supply-demand-zone
- [S25] Quantum Algo (same as S14; pip sizes, win-rate claims without methodology)
- [S26] FXNX, "Order Block vs S/D: 1 real difference": https://fxnx.com/en/blog/order-block-vs-s-d-1-real-diff-sharper-entries
- [S27] Supply Demand Zones Pro (TradingView): https://www.tradingview.com/script/h0jxhmgn-Supply-Demand-Zones-Pro/
- [S28] LuxAlgo concept "Bullish/Bearish Order Block": https://www.luxalgo.com/library/concept/bullish-bearish-order-block.md
- [S29] TradingFinder "ICT Concept" script (OB weighted by liquidity): https://www.tradingview.com/script/5n6Lawvs-ICT-Concept-TradingFinder-Order-Block-FVG-Liquidity-Sweeps
- [S30] NexusFi "Supply/demand zones for futures": https://nexusfi.com/a/market-structure/supply-demand-zones-futures-trading
- [S31] Flip zones (search excerpt set; Flux Charts S&D, Supply Demand Flip Planner, scanz): https://www.tradingview.com/script/ZUAYemgd-Supply-and-Demand-Zones-Flux-Charts/ , https://www.tradingview.com/script/1Ic0EhON-Supply-Demand-Flip-Planner-AGPro-Series/ , https://scanz.com/supply-and-demand-trading/
- [S32] LuxAlgo concept "Breaker Block": https://www.luxalgo.com/library/concept/breaker-block/
- [S33] ForexBee, "Order Block vs Supply and Demand": https://forexbee.co/order-block-vs-supply-and-demand-in-trading/
- [S34] chartmini, "Order Block Trading: Definition, Rules, Retests & Testing": https://chartmini.com/blog/order-block-trading-supply-demand-zones-2026
- [S35] EarnForex forum, dompips "3 Simple Smart Money Concepts To Trading Order Blocks" (2022): https://www.earnforex.com/forum/threads/3-simple-smart-money-concepts-to-trading-order-blocks.46908/latest
- [S36] Price Action Ninja, "How To Find And Use ICT Order Blocks": https://priceactionninja.com/trading-ict-order-blocks/
- [S37] gist.ly YouTube summary "Mastering Order Blocks: Understanding Supply and Demand in Trading": https://gist.ly/youtube-summarizer/mastering-order-blocks-understanding-supply-and-demand-in-trading
- [S38] TradingView "Order Blocks Finder + Supply and Demand Zones (2027 Update)": https://www.tradingview.com/script/UGuTPjYC-Order-Blocks-Finder-Supply-and-Demand-Zones-2027-Update/
- [S39] TradingView "[DMITRY ORDERBLOCKS]" (invite-only; description): https://www.tradingview.com/script/HRq9e3vt-DMITRY-ORDERBLOCKS
- [S40] Vantage Markets, "Order Blocks in Forex": https://www.vantagemarkets.com/en-za/academy/order-blocks/
- [S41] AlgoStorm, "Order Blocks and Fair Value Gaps: What Holds Up": https://algostorm.com/ict-smc-key-concepts/
- [S42] Keenbase, "ICT Order Blocks": https://www.keenbase-trading.com/ict-order-blocks/
- [S43] Search for Seiden on order blocks (no primary statement found): https://www.forexfactory.com/thread/419697-sam-seidens-supply-and-demand-does-it?page=4
- [S44] Trade Ideas, "Supply and demand zones explained": https://www.trade-ideas.com/learning-center/chart-analysis/supply-and-demand-zones-explained/
- [S45] maktradingschool, proximal / distal lines: https://maktradingschool.com/how-to-draw-proximal-and-distal-lines/
- [S46] Two Side Traders video "Order Block & POI Advanced Trading Strategy" (AI notes, Hindi video, 2024): https://readray.ai/en/notes/get-your-first-users-20260207/advanced-order-block-poi-strategy ; related notes: https://lilys.ai/de/notes/openai-agent-builder-20260208/high-probability-poi-order-block
- [S47] LuxAlgo "Order Blocks" indicator family page ("locating specific swing high and swing low points (fractals)"): https://www.luxalgo.com/library/indicator/FWIFn7mK-order-blocks-only/ ; concept text: https://www.luxalgo.com/library/indicator/q93FtpwL-order-blocks/ ; Order Block Detector (volume pivots): https://www.luxalgo.com/library/indicator/order-block-detector/
- [S48] CienF-OTC "Supply & demand with qualifiers": https://www.tradingview.com/script/lDD8Rnz0-Supply-demand-with-qualifieres-By-CienF-OTC/
- [S49] gist.ly YouTube summary "Master Supply & Demand Zones: Order Blocks & Market Structure" (video Qxuyp3PfuXU): https://gist.ly/youtube-summarizer/master-supply-demand-zones-order-blocks-market-structure
- [S50] LuxAlgo concept "Zone Scoring & Refinement": https://www.luxalgo.com/library/concept/zone-scoring-and-refinement.md
- [S51] Price Action Ninja, "3 Key Facts Sam Seiden Gets Wrong": https://priceactionninja.com/sam-seiden-supply-and-demand/
- [S52] tradingstrategyguides OB guides (engulfing variant noted in search summary): https://tradingstrategyguides.com/what-is-an-ict-order-block-how-to-identify-and-trade-it/
- [S53] LuxAlgo "MTF Order Block Finder" / "Order Block Finder" (wugamlo lineage): https://www.luxalgo.com/library/indicator/zyYceJYb-mtf-order-block-finder/ , https://www.luxalgo.com/library/indicator/rvHVaisA-order-block-finder/ , https://www.tradingview.com/script/QqBOm57l-Order-Block-Finder/
- [S54] tradingstrategyguides, "Day 12: Breaker Blocks & Mitigation Blocks": https://tradingstrategyguides.com/day-12-breaker-blocks-mitigation-blocks-explained-ict-smc-deep-dive/
- [S55] ictkillzone, "Breaker vs Mitigation": https://www.ictkillzone.com/ict-breaker-vs-mitigation
- [S56] LuxAlgo concept "Mitigation Block": https://www.luxalgo.com/library/concept/mitigation-block/
- [S57] innercircletrader.net (unaffiliated), "Mitigation block explained": https://innercircletrader.net/tutorials/ict-mitigation-block-explained/
- [S58] LuxAlgo concept "Rejection Block": https://www.luxalgo.com/library/concept/rejection-block/
- [S59] ictkillzone, "Propulsion Block" (ICT 2016 Month 04): https://www.ictkillzone.com/ict-propulsion-block
- [S60] reddit.com — blocked to the crawler (search error + fetch refused).
- [S61] babypips threads (403): https://forums.babypips.com/t/ict-and-order-blocks-anybody-use-this-for-trading/700783 , https://forums.babypips.com/t/has-anybody-heard-of-the-order-block-strategy/491121
- [S62] Forex Factory "Order Block Theory – Institutional Trading Method" (403; search excerpt: ICT framing adds manipulation/liquidity logic, overlaps RBD/DBD): https://www.forexfactory.com/thread/post/13453386 ; metalsmine POI post (403): https://www.metalsmine.com/thread/post/15353797
- [S63] Scribd ICT core-content notes (truncated): https://www.scribd.com/document/747453712/ICT-Core-Content-Months-1-to-12-by-GatieTrades-Notes
- [S64] David, "new rules.md" §8–12, §18: /home/david/FOREXBOT/FOREXBOT/1 Strategy/Rules/new rules.md
- [S65] method_report.md (§2.5, §5): /home/david/forex/engine/research/supply_demand/method_report.md
- [S66] opensource_report.md (§2, §3): /home/david/forex/engine/research/supply_demand/opensource_report.md
- [S67] engine/supply_demand.py (docstring, `_candidate`): /home/david/forex/engine/supply_demand.py
- [S68] engine/smc_marks.py (OB docstring, `_ob_candle`): /home/david/forex/engine/smc_marks.py
- [S69] LuxAlgo concept "Propulsion Block": https://www.luxalgo.com/library/concept/propulsion-block/
- [S70] TradingView "OrderBlock_TradingHub" (TradingHUB-3; Extreme / Decisional / SMT, inside-bar rule): https://www.tradingview.com/script/zSkad1tv-OrderBlock-TradingHub
- [S71] "You're Using the Wrong Decisional Order Block — True SMC" (YouTube; search excerpt "the swing or Order Block that caused the Break of Structure"): https://www.youtube.com/watch?v=fkl4NTz5-GI
- [S72] POI definitions (search excerpts): https://www.altrady.com/crypto-trading/smart-money-concept/points-of-interest-poi-fibonacci-smart-money-trading
- [S73] TradingFinder SMC glossary: https://tradingfinder.com/education/forex/smc-abbreviation/
- [S74] TradingFinder "ICT Institutional Order Flow": https://tradingfinder.com/education/forex/ict-market-order-flow/
- Also read: kenmacro "Order block meaning": https://kenmacro.com/order-block-meaning/ ; FXNX "Stop getting swept": https://fxnx.com/en/blog/smc-order-blocks-vs-supply-demand-stop-getting-swept ; EBC beginner's guide: https://www.ebc.com/forex/what-is-an-order-block-in-trading-beginner-s-guide ; LuxAlgo SMC library page: https://www.luxalgo.com/library/indicator/smart-money-concepts-smc ; LuxAlgo "Order Blocks & Breaker Blocks": https://www.luxalgo.com/library/indicator/2w1Acc8Q-order-blocks-breaker-blocks-signals-alerts/
