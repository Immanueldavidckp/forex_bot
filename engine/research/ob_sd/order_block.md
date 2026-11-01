# Order Block (ICT / SMC) — the most complete deterministic definition the public sources support (2026-11-01)

Research only; nothing under `/home/david/forex` was touched. Pine sources of nine open-source TradingView order-block scripts were
downloaded from TradingView's own `pine-facade` endpoint into
`/tmp/claude-1000/-home-david-forex/e2318429-1be6-4027-b1f0-c6aeaaf52e54/scratchpad/obsd_research/dl/*.pine` (file names below); the
MQL5 article code and the joshyattridge Python library were read from their public repositories. ICT's own words are available only
as (a) AI-generated transcript summaries of the 2016 "Core Content Month 04" videos and the 2022/2023/2024 mentorship streams on
videohighlight.com / opentools.ai (both sites warn their summaries "may contain inaccuracies"), and (b) the way ICT-faithful scripts
restate them. Forum threads (forexfactory, babypips, metalsmine mirrors, rattibha/Twitter mirrors) answer 403; where they are quoted it
is from search-engine excerpts and marked **second-hand**. Every claim carries its URL; `[S#]` refers to the Sources list.

Credibility tags: **P** = ICT primary (his lecture, via summary) · **L** = LuxAlgo library concept page (editorial, no numbers) ·
**C** = code actually read · **E** = educator / vendor page · **F** = forum / social, second-hand.

---------------------------------------------------------------------------------------------------------------------

## 0. The short version

* **ICT's own definition (2016, Month 04 "Orderblocks", P):** a bullish order block is "the lowest candle or price bar with a down
  close that has the most range between open to close and is near a support level"; it becomes valid when "the high of the lowest
  down candle … is traded through by a later formed candle"; entry "at the open of the down candle … or five pips above it"; stop
  "below the bullish order block's low or below its close"; the **mean threshold is the midway point of the body** ("the best order
  blocks will not see price trade down below the midway point of the entire body of the candle"); consecutive down candles are
  "blended together to get one full bullish order block"; the move away should be "two to three times" the block's body height.
  [S1][S2]
* **ICT's 2022+ reformulation (P):** an order block "represents a change in the state of delivery"; the change happens "when the
  opening price of a candle is violated"; "not every down closed candle signifies a bullish order block"; "a bearish order block is
  identified by consecutive down candles" [sic, summary]. [S3] In 2024 he still draws it "from the opening price to the mean
  threshold (middle of the candlestick)" of "a down closed candle". [S4]
* **The educator / indicator formulation (L, E, C):** "the last opposing candle before a displacing move" — the final down candle
  before a rally that breaks structure or leaves an FVG; "No displacement means no order block, whatever the candle looks like".
  [S5][S6]
* **What the code actually does (C):** every swing-based implementation (LuxAlgo SMC, LuxAlgo OB & Breaker, LuxAlgo Propulsion,
  joshyattridge, ICT OB+ M1D, ICT OB Pro) marks **the candle at the extreme of the leg that broke structure** (lowest low / lowest
  down-close between the broken swing high and the breaking close), not literally "the last opposite candle before the big candle";
  the displacement-based ones (ICT Order Block HVcKIE8w, Order Block Finder, MQL5 article) walk back from a big candle / N-candle run
  to the first opposite-colour candle. The two coincide when the impulse starts at the leg extreme — which is exactly ICT's picture.

---------------------------------------------------------------------------------------------------------------------

## 1. Which candle IS the order block

### 1.1 ICT primary (2016 Core Content Month 04 "Orderblocks", via summaries)
* "the lowest candle or price bar with a down close that has the most range between open to close and is near a support level"
  (00:01 / 01:00). [S1][S2]
* Validation: "The high of the lowest down candle or price bar must be traded through by a later formed candle or price bar." [S1]
  ("Validation requires a new candle piercing the high of a down candle" — the same point in another summary. [S2])
* "Every time there is a new down candle, it becomes the new potential bullish order block" (28:30) — i.e. the candidate moves to
  each later down candle until one is validated. [S1]
* Consecutive down candles: "Blend down candles together to get one full bullish order block" (31:02); "you have to blend them
  together to get one full order block" (32:00). [S1][S2]
* A later 2023 stream talks of "bullish order blocks formed by two down closed candles". [S7]
* Bearish: "everything I say here you'll just reverse for a bearish order block". [S2]
* Location: "near a support level … an old low on long-term or higher time frame chart, or an old high price has moved above and
  retraced into"; "refine entries and levels from higher time frames to lower ones"; "identify blocks on higher time frames first
  (monthly, weekly, daily)". [S1][S2]

### 1.2 ICT 2022+ ("change in the state of delivery", CISD)
* 2022 Mentorship Ep. 3: an order block "represents a change in the state of delivery within the market" (24:06); the change occurs
  "when the opening price of a candle is violated" (24:28); "not every down closed candle signifies a bullish order block" (29:22);
  "a bearish order block is identified by consecutive down candles" (23:33, summary wording). [S3]
* "Order Blocks Simplified – ICT Concepts" (ICT-school video): "A valid order block is created when price displaces and closes below
  the opening price of a series of up-close candles" (bearish); buy side mirrored; "Validate an order block by closing over the down
  close candle"; mean threshold "50 % Fibonacci retracement from the body low to body high". [S8]
* LuxAlgo CISD page: the level is "the open of the first candle in the last unbroken run of down-closing candles into a low"; a
  "candle body must close fully beyond the level"; "some write-ups use the nearest candle's open rather than the first candle of the
  series". [S9]
* X/Twitter threads (second-hand, F): "An orderblock is defined as change in state of delivery"; "You mark orderblocks by marking up
  the last bullish/bearish candle or series of bullish/bearish candles before displacement"; "It is not simply every down-closed or
  up-closed candle." [S10]

### 1.3 Library / educator pages
* LuxAlgo "Bullish/Bearish Order Block": "An order block is the last candle that closed against a move before the move took off";
  "the final down-closing candle, or a consecutive group of them, before an impulsive move up"; "a run of consecutive opposite candles
  can be boxed as a single zone". [S6]
* LuxAlgo "Order Block Anatomy & Refinement": for stacked opposing candles "either take the one nearest the move's origin or merge the
  cluster into a single zone"; stricter refinements prefer "the one that ran a prior high or low, or the one with the largest range".
  Doji not addressed. [S5]
* penchan (ICT restatement): bullish OB = "the lowest candle, a bearish candle, the candle with the widest open-to-close body, located
  near a key support level"; simplified: "the last bearish candle before a move breaks a swing high". [S11]
* purple-trading: last opposite candle, "ideally the one that formed the lowest low"; "test both variants". [S12]
* TradingView idea (Anbat): "select the order block with the largest body and shortest wicks". [S13]
* alphaexcapital: "the single last candle that moved against the trend before that break … one candle, not a sequence". [S14]
* crosstrade: "the last bearish candle before a bullish push". [S15]
* atas.net: "the last opposing candle, or small group of candles, that appears before a strong price move". [S16]
* xs.com: "the very last candle" before the move. [S17]
* strike.money: "the exact candle or tight consolidation" before the move. [S18]
* The "decisional vs extreme" OB school (TradingHub / AlbaTherium, invite-only, F): "we have only 2 Order Blocks in each structure …
  Decisional Order Block and Extreme Order Block"; extreme = "the first and lowest OB between the Major Low and Major High",
  decisional = "the most recent OB lower than the current IDM [inducement]". [S19]

### 1.4 What the code does (all read, C)
| implementation | which candle | file |
|---|---|---|
| **Smart Money Concepts [LuxAlgo]** (most used SMC script) | on a BOS/CHoCH (`ta.crossover(close, pivot)`), the bar with the **lowest `parsedLow`** (bull) / highest `parsedHigh` (bear) between the broken pivot bar and the breaking bar — **candle colour is not checked**; bars whose range ≥ 2 × ATR(200) ("Order Block Filter") are excluded by swapping their high/low. Internal structure length 5, swing length 50. [S20] | `dl/smc_luxalgo.pine` lines 310-330, 507-525, 587, 612 |
| **Order Blocks & Breaker Blocks [LuxAlgo]** | on `close > top.y` of the last swing high (Swing Lookback 10): loop from the swing to the current bar, keep the bar with the minimum `min` (= low, or `min(open,close)` if Use Candle Body) — colour not checked. [S21] | `dl/ob_breaker_luxalgo_piIbWMpY.pine` |
| **Pure Price Action Order & Breaker Blocks [LuxAlgo]** | same loop, swings from a 3-bar fractal cascade ("Short/Intermediate/Long Term"), Use Candle Body **true** by default. [S22] | `dl/ppa_ob_breaker_luxalgo_5PB593yX.pine` |
| **ICT Propulsion Block [LuxAlgo]** | on `close > swingHigh` (length 3): among bars since the swing with `open > close` (**down candles only**) take the one with the lowest low. [S23] | `dl/propulsion_luxalgo.pine` lines 109-115 |
| **joshyattridge/smart-money-concepts `ob()`** (Python) | bullish OB when close exceeds the most recent uncrossed swing high; OB = the candle with the **lowest low** between that swing high and the break (ties → last); colour not checked. [S24] | GitHub |
| **ICT Order Blocks+ (M1D)** (claims Month-04 fidelity) | after `close > swHi` (pivot 2): among the **down-close** candles since the swing (≤ 40 bars) the one with the **lowest close**; tie → larger body; adjacent down candles blended ("ICT: two or more down candles in a row at the extreme are ONE bullish block, from the highest open to the extreme close"). [S25] | `dl/ict_ob_m1d_FvQ34DMp.pine` |
| **ICT OB Pro** | when a bullish FVG completes (`low > high[2]`): among bars 2..8 back the **down candle with the lowest low**. [S26] | `dl/ict_ob_pro_oObsuObl.pine` lines 519-528 |
| **ICT Order Block** (HVcKIE8w) | on a displacement bar (body > 1.5 × ATR14): the **first down candle within the 5 bars before it**; optional "Multi-Candle OB" merges up to 3 consecutive down candles. [S27] | `dl/ict_order_block_HVcKIE8w.pine` lines 161-196 |
| **Order Block Finder** (wugamlo lineage) | a down candle followed by **5 consecutive up candles** (Relevant Periods 5) with an optional minimum % move (default 0). [S28] | `dl/ob_finder_QqBOm57l.pine` |
| **ICT Order Blocks v2 (Debug)** | candle[2] is a down candle and candle[1]'s high exceeds its high; defaults require an FVG (`low[0] > high[2]`) and `close[1] > high[2]`. [S29] | `dl/ict_ob_v2_1M4FG5X2.pine` |
| **Order Block Detector [LuxAlgo]** | a **volume pivot** (pivothigh of volume, length 5) while the structure state is bearish; not a candle-colour rule at all. [S30] | `dl/obdetector_luxalgo.pine` |
| **MQL5 article 15899** (Developing Advanced ICT Trading Systems) | walk back ≤ 20 bars from a run of 4 same-colour candles to the first opposite candle; if that candle's body is > 1.3 × the next candle's body, move one bar forward. [S31] | mql5.com / forge |

### 1.5 Edge cases, answered
* **Several consecutive opposite candles**: blend them into one block (ICT P [S1][S2]; LuxAlgo L [S5][S6]; ICT OB+ M1D C [S25];
  ICT Order Block C [S27] max 3). Blended box = highest open (ICT body convention) or highest high (wick convention) down to the
  lowest low / lowest close. The alternative "take the one nearest the move's origin" (LuxAlgo [S5]) is the same candle when the
  origin candle is the extreme one.
* **No opposite candle** (the leg starts with a same-colour candle): the colour-blind implementations (LuxAlgo SMC, OB & Breaker,
  joshyattridge) still mark the extreme candle whatever its colour [S20][S21][S24]; Order Block Finder draws "Open→Low" of the
  candle, which for an up candle is its lower wick [S28]; the colour-strict ones (Propulsion, OB+ M1D, OB Pro, HVcKIE8w) mark
  nothing. No educator page addresses it; the search found none [S32]. ICT's 2022 CISD framing ("the open of the first candle of the
  series … violated") needs a series of down candles, so strictly: no series → no OB.
* **Doji**: no source defines it. In code, colour is `close < open` (strict), so an exact doji is not an opposite candle; ICT Order
  Block [S27] separately flags blocks as "weak" when ≥ 2 of the 3 following candles are dojis (body < 20 % of range) or inside bars.
* **Which of two overlapping candidates**: ICT tie-break = most open-to-close range [S1][S2]; OB+ M1D codes it as lowest close, then
  larger body [S25]; Anbat "largest body and shortest wicks" [S13]; LuxAlgo "largest range" or "the one that ran a prior high or
  low" [S5].

---------------------------------------------------------------------------------------------------------------------

## 2. Box edges — wick vs body vs refined; the 50 % mean threshold

| convention | who | notes |
|---|---|---|
| **Body (open → close)**, entry at the open, mean threshold = 50 % of the body | ICT P: "focus on the midway point of that down candle … the mean threshold"; entry "at the open of the down candle … or five pips above it"; 2024: "from the opening price to the mean threshold (middle of the candlestick)" [S1][S2][S4]; "50 % Fibonacci retracement from the body low to body high" [S8]; ICT OB+ M1D C: "The body is the block. Open to close, never the wicks. Its high is the level price returns to; its low is where the block fails" [S25]; penchan: "ICT definition: the zone is drawn from open to close, so wicks are excluded" [S11]; Notion ICT notes (F): "Ignore the wicks and look at the bodies" [S33] | the ICT-faithful position |
| **Full range (high → low)** | LuxAlgo L: "the most common approach" [S6]; LuxAlgo SMC, OB & Breaker (default), Propulsion, OB Pro, OB v2, ICT Order Block (default), joshyattridge — all code the box as high..low [S20][S21][S23][S24][S26][S27][S29]; crosstrade "the candle's high and low" [S15]; purple-trading "the full candle" [S12]; penchan "simplified method" [S11] | the indicator default |
| **Open → wick** (bullish: open..low; bearish: high..open) | Order Block Finder default [S28]; LuxAlgo L lists "open to the extreme" [S6]; MQL5 article: bullish = low..open [S31] | ICT's body top with the wick as the stop side |
| **Hybrid**: body for entry, wick extreme for invalidation | LuxAlgo L [S5]; ICT Order Block "Use Body Refinement" draws a dashed wick box around a filled body box and measures mitigation on the body [S27] | recommended by LuxAlgo |
| **50 % mean threshold** | ICT P: midpoint of the **body** [S1][S2][S8]; LuxAlgo L: "50 % mark of the Order Block" (of the chosen range), "prefer entries in the deeper half", refinement for large blocks [S5][S6]; OB Pro C: `(top+bot)/2` of the **high–low** box and, by default (`strict_mean = true`), a close beyond it invalidates [S26]; LuxAlgo Propulsion C: mean threshold line = `avg(open, close)` of the propulsion candle [S23]; penchan: "A clear retracement beyond 50 % makes the OB invalid" [S11] | body-based in ICT, range-based in most code |
| **Stop** | ICT P: "below the bullish order block's low or below its close", later "just below 50 % of the total range" [S1][S2]; OB Pro: "just outside the box (or at the Mean Threshold if using strict validation)" [S26] | |

LuxAlgo's verdict on the wick/body split: "Pick one convention, keep the invalidation beyond the far edge, and apply it
consistently" [S6]; "neither is objectively correct" (Zone Scoring page, earlier research).

---------------------------------------------------------------------------------------------------------------------

## 3. Validity requirements and how strict each school is

| requirement | ICT (P) | LuxAlgo library (L) | code defaults (C) | educators (E) |
|---|---|---|---|---|
| **Displacement** | the move away should be "two to three times" the block's body height (Month 04 28:00) [S1][S2]; 2022: "price displaces and closes below the opening price of a series of up-close candles" [S8] | **required**: "No displacement means no order block, whatever the candle looks like" [S6]; the leg "should break a swing point or leave an imbalance" [S5] | ICT Order Block: body > **1.5 × ATR(14)** [S27]; OB Pro: body > **0.8 × ATR(14)** and body/range ≥ **0.5** [S26]; OB+ M1D: rally-away multiple **2–3 × block height, off by default** [S25]; LuxAlgo swing scripts and joshyattridge: **none** (the BOS is the displacement) [S20][S21][S24]; Order Block Finder: 5 consecutive up candles, min % move 0 [S28]; MQL5: 4 same-colour candles with body/overlap ratios (40 % past the prior high, 25 %/50 % body rules) [S31]; David: body ≥ 1.5 × mean body of 10 | "strong impulsive move … multi-bar" [S15]; "wide candles (imbalance)" [S18] |
| **Break of structure / CHoCH by close** | minimal 2016 form: "the high of the lowest down candle … traded through by a later formed candle" [S1]; 2022 form: body close beyond the open of the down-candle series (CISD) [S3][S8][S9] | displacement "should ideally break structure or leave a fair value gap" [S5]; "must break a structural level or trade through a prior swing high or low" [S6] | **required and close-based** in LuxAlgo SMC (`ta.crossover(close, pivot)`), OB & Breaker (`close > top.y`), Propulsion, joshyattridge (`close_break=True`), OB+ M1D (`close > swHi`), OB Pro (`close > highest(high, 8)[3]`, "Require Market Structure Shift" on) [S20][S21][S23][S24][S25][S26]; optional in ICT Order Block ("Use Structural OB", off, 5-bar window) [S27]; not in Order Block Finder / MQL5 [S28][S31] | "must break a key structural level" [S17][S18]; "the break … is confirmed by the body of the candle" [S12] |
| **FVG / imbalance in the leg** | 2022: "A high probability ob takes liquidity & creates an FVG" (F) [S10]; Month 04 vacuum-block talk: an FVG "may form if price only retraces to a bullish order block" [S34] | **strengthens**: "a gap left in the leg away from the block raises its grade" [S6] | **required** by default in OB Pro (the FVG completion IS the trigger) and OB v2 (`require_fvg = true`) [S26][S29]; optional in ICT Order Block ("Use IMB Confirmation", off) [S27]; absent in the LuxAlgo swing scripts | "should create a Fair Value Gap immediately after it" [S17]; "advises against trading those OBs" without a gap [S12] |
| **Liquidity sweep / inducement before the block** | Breaker lesson: blocks after "runs on sell stops below old lows" [S35]; 2022 (F): high-probability OB "takes liquidity" [S10] | grading factor: "Many traders grade a block higher when its candle first ran a nearby low or high"; "Stricter models require a sweep of nearby liquidity just before the block forms" [S5][S6] | OB Pro: "Require Liquidity Sweep (Purge)" **off** by default (5-bar lookback), the sweep flag decides breaker vs mitigation block later [S26]; TradingFinder: a block is "more credible if liquidity sits between price and the block" [S36]; none of the others | "Strong OBs often form after stop-losses … are taken" [S17] |
| **Premium / discount** | "near a support level … a cheaper price" (Month 04) [S1]; sits inside ICT's PD-array logic | "bullish blocks in discount, bearish in premium, in agreement with higher-timeframe structure" [S6] | OB Pro: "Require PD Array Alignment" **on**: bullish OB low must be below the 4H high/low equilibrium [S26] | — |
| **Fresh / unmitigated** | first return is the trade; propulsion lesson: a block that is touched and holds the mean threshold is "highly sensitive" [S37] | "rank fresh, untested blocks above mitigated ones"; "used once and downgraded on later visits" [S5] | every tool removes or fades a block on first mitigation (§4) | "prefer untested OBs" [S12][S18] |
| **Timeframe / HTF alignment** | "identify blocks on higher time frames first" [S2] | HTF bias adds weight [S6][S14] | OB Pro overlays 240-min OBs and stars a chart-TF OB nested in a same-direction HTF OB [S26] | "1 hour or higher" structure [S13] |

Strictness ranking of the schools, from loosest to strictest: Order Block Finder / MQL5 (colour pattern only) → LuxAlgo swing scripts
and joshyattridge (BOS by close, any extreme candle) → ICT 2016 (down-close candle at the extreme + a later candle through its high
+ 2–3× rally) → David / ICT Order Block (last opposite candle + body ≥ 1.5× displacement + BOS by close [+ FVG for a setup]) → ICT OB
Pro "High Prob" (displacement + FVG + MSS + discount [+ sweep]) → the TradingHub school (inducement + extreme/decisional only).

---------------------------------------------------------------------------------------------------------------------

## 4. Lifecycle: mitigation, invalidation, breaker, mitigation block, rejection, propulsion, vacuum, reclaimed

### 4.1 Mitigation (first touch) and invalidation
* LuxAlgo L: "Mitigation occurs once price returns and trades into the zone. The block is used once and downgraded on later visits.
  Invalidation occurs when price closes through the far side … a close, not a wick." [S5] "A decisive close through the entire zone
  invalidates it." [S6]
* ICT P: no formal invalidation rule in the 2016 lesson; the quality rule is "the best order blocks will not see price trade down below
  the midway point of the entire body of the candle"; the stop sits "below the low or below its close" [S1][S2]. Propulsion lesson:
  a touched block "should not violate the mean threshold (half the body height)" [S37].
* Code (the word "mitigation" means different things):
  * **LuxAlgo SMC**: "Order Block Mitigation" = `High/Low` (**default**) or `Close`: a bullish OB is **deleted when `low < barLow`**
    (wick through the far edge) — with `Close`, when `close < barLow` [S20].
  * **LuxAlgo Order Block Detector**: `Wick` (default) / `Close` — removed when the lowest low (or lowest close) of the last N bars is
    below the box bottom [S30].
  * **LuxAlgo OB & Breaker / Pure Price Action**: a bullish OB becomes a **breaker when `min(close, open) < btm`** (a body close
    below the far edge); the breaker is **removed when `close > top`** (price closes back above the whole box) [S21][S22].
  * **LuxAlgo Propulsion**: `Closing Price` (default) / `Wick` below the OB low = mitigated [S23].
  * **joshyattridge**: `close_mitigation=False` (default) → mitigated when a later **low < Bottom** (wick); `True` → `min(open, close) <
    Bottom`; the mitigated block is "kept as breaker until price trades through the opposite side" [S24].
  * **ICT Order Block** (HVcKIE8w): "Break Detection Mode" `Bar Close` (default) / `Wick`; **mitigated = the close (or wick) lands
    inside the box** (first entry, "Fade" or "Hide"), **breaker = close below the box bottom**; blocks expire after 50 bars [S27].
  * **ICT OB Pro**: `tapped` when the low reaches the box top; after a tap, **mitigated when `close < mean threshold`** (`Strict Mean
    Threshold Invalidation` **on** by default; off → close below the box bottom) or when the target is hit [S26].
  * **ICT OB+ M1D**: "Failure erases. A close through the far side of the body removes the block"; `tested` flag on the first wick
    into it [S25].
  * **ICT OB v2**: `close < bull_ob_low` removes it [S29].
  * **Order Block Finder**: Mitigation `Off` (default) / `Touch` / `Close inside`; Invalidation `Off` / `Touch beyond` / `Close
    beyond` [S28].
  * **MQL5 article**: "price touched or exceeded the block levels" (touch-based despite comments saying "closed") [S31].
* Majority position: **touch = mitigated/used (wick into the box); invalid = a candle CLOSE beyond the far edge**; the stricter ICT
  purist rule: a close beyond the 50 % mean threshold already kills it (OB Pro default, penchan [S11], ICT's "best blocks" rule).

### 4.2 Breaker block vs mitigation block — the exact difference
* ICT Month 04 "Breaker Block" (P): price "runs buy stops above an old high", then "breaks below the low that created that new high";
  the breaker is "running stops to pull liquidity from the market"; bearish breaker candle = "a down close candle at the most recent
  swing low before an old high is violated" (summary wording). [S35]
* ICT Month 04 "Mitigation Blocks" (P): "An M pattern refers to a failure swing with confirmation break in market structure"; "a
  break below the previous low confirms a shift"; "Long positions taken from A to B can be liquidated or mitigated during the price
  move from B to C"; "Mitigation blocks are created when price breaks below previous lows"; hallmark: "The body of the candle is not
  violated". [S38]
* LuxAlgo L (breaker): "In the strict ICT definition the failing swing must first trade beyond a prior high or low. A mitigation block
  has the same role flip but no raid, so the swing fails short of the prior extreme. The looser retail reading treats any violated
  order block as a breaker." Formation (bullish): swing low → swing high → sell below the swing low (sweep) → displacement close back
  above the swing high → the breaker is "the down-closing candle or series inside that failed leg, usually from its high to its low";
  "Trade the retest, not the break"; "A clean trade back through the whole zone invalidates the idea." [S39]
* LuxAlgo L (mitigation block): "the last up-closing candle or group of candles before that failed swing" (bearish: a lower high that
  did not exceed the prior swing high, then a close below the prior low); "A breaker forms when the final swing sweeps beyond the
  prior extreme before reversing"; "Any sweep of that extreme reclassifies the setup as a potential breaker"; "Acceptance of price
  through the block's far side invalidates it." [S40]
* eltraderfinanciado: "In the bullish version, a breaker shows low, high, lower low, then break up. A mitigation block shows low, high,
  higher low, then break up"; "A bullish breaker is made of bullish candles, because it was originally a bearish order block"; "Mark
  the candles of the failed move using their full range, from high to low"; "The structure break needs displacement, meaning a close
  beyond the opposing swing, not just a wick." [S41]
* therighttrader (breaker): "If price never closed through the original block, you do not have a breaker"; wait for "a close through
  the order block. A wick does not count"; (mitigation block): "a failed order block that never ran the prior swing's stops"; "If you
  cannot tell whether the sweep happened … not force either label." [S42][S43]
* X thread (F): "A mitigation block occurs when there is a high, a low, and a higher high. (Inverse for bearish)". [S10]
* Code: OB Pro flags each OB with `swept_liq` (`low[ob] < lowest(low, 5)[1]`); when the OB is invalidated, `swept_liq → +BRK` else
  `→ +MB` [S26]; the LuxAlgo scripts and joshyattridge relabel **every** invalidated OB as a breaker (the "looser retail reading"
  LuxAlgo itself warns about) [S21][S24]; crosstrade uses "mitigation block" for a plain failed OB [S15].
* Note the terminological trap: ICT's "mitigation block" is a *formation* (failure swing without a stop run); the indicators' "OB
  mitigation" is the *event* of price returning to any block. Both are in use.

### 4.3 Rejection block
* ICT Month 04 (P): "Strong wicks on the high or highs indicate buy stops being run out before a price decline"; "The highest open or
  close within the swing high defines the rejection block" (bearish: from that body edge up to the highest high); "it can also be
  formed by multiple candles with high wicks"; bullish mirror: "The lowest wick low and lowest open or close define the zone"; stop
  "above the bearish block". [S44]
* LuxAlgo L: zone = "the top of the candle's body to the wick's extreme" at a swing high that ideally swept a prior high; "Treat body
  acceptance beyond the wick extreme as failure". [S45]
* therighttrader: "only the wick of a candle that swept a high or low and closed back"; "Do not include the body in the zone";
  worked numbers: spike to 130, body top 124 → zone 124–130, sell 127, stop 131, target 115 (4 : 12). [S46]
* Code: OB Pro requires wick ≥ 60 % of the candle range (`rb_ratio = 0.6`). [S26]

### 4.4 Propulsion block
* ICT Month 04 (P): "A propulsion block is defined as a down candle that trades back into a bullish order block"; it "should not
  violate the mean threshold (half the body height)"; "Propulsion candles rarely see mean threshold violations, so traders can set
  tight stop losses or exit if violated". [S37]
* LuxAlgo L: "a candle that trades back into a prior order block, respects it, and drives away"; "Every propulsion block is an order
  block, but only a subset qualifies"; draw "its full range, or … the open-to-extreme portion". [S47]
* LuxAlgo code: after a bullish OB exists, a bar whose `low` enters the OB (`low <= ob.high and low > ob.low`) while opening above
  it starts a "breach"; when a later `close` exceeds the breach high, the breach's low candle becomes a PB with its mean-threshold line
  at `avg(open, close)`; mitigation `Closing Price` below the low (default) [S23]. OB Pro: "a new OB forming inside an existing OB or
  an active HTF OB" [S26].

### 4.5 Vacuum block
* ICT Month 04 (P): "a gap in price action caused by a volatility event" (NFP, session open); "The absence of trades within the gap
  range defines it as a vacuum block"; "The two reference points are the opening of the gapped-up candle and the close of the previous
  up candle before the gap"; early-session gaps "more likely to close". [S34]
* OB Pro code: gap ≥ 0.5 × ATR(14) (`vb_min_atr`) [S26]. LuxAlgo: "in ICT vocabulary the vacuum block is not a synonym for a wick
  zone" [S45].

### 4.6 Reclaimed order block
* ICT Month 04 (P): "A bullish reclaimed block is defined as a candle previously used for buying that confirms minor displacement";
  bearish: "a prior sell point; minor displacement confirms the shift". [S48]
* LuxAlgo L: "an order block that has already served once and is later revisited and used again in its original direction"; "Some
  authors also apply the term to a zone that was briefly violated and then reclaimed … definitions vary". [S49] writofinance: "a
  previously invalidated zone that becomes valid after price action returns to it". [S50]

### 4.7 Status machine the sources support (union of ICT + LuxAlgo + code)
`fresh → tested (wick into the box) → mean (price past the 50 % line) → invalid (a CLOSE beyond the far edge; purist: beyond the
mean) → breaker (origin swing had swept liquidity) | mitigation block (no sweep) → dead (a close back through the flipped zone)`,
plus `propulsion` (an opposite candle that entered a live block, held its mean and launched) and `reclaimed` (a block re-used in its
own direction). David's current `smc_marks.py` already implements fresh/touched/mean/invalid/breaker/dead; what it lacks is the
sweep flag that separates breaker from mitigation block, and the blend of consecutive opposite candles.

---------------------------------------------------------------------------------------------------------------------

## 5. Where it sits in the swing, timeframe, how many per break

* **At the extreme of the leg, not inside it**: ICT "the lowest candle … with a down close … near a support level" [S1]; every
  swing-based implementation takes the min-low / lowest-close bar between the broken swing and the break [S20][S21][S23][S24][S25];
  the "decisional vs extreme" school allows exactly two (extreme + decisional) per structure [S19]; Anbat: "avoid entries at the
  highest or lowest order block … look for a fair value order block in the middle of the range" (minority, [S13]).
* **Inside the leg (last opposite candle before THE displacement candle)**: ICT Order Block [S27], MQL5 [S31], Order Block Finder
  [S28], David's rules (V5 §3, new rules §9-10). These mark a candle that may be mid-leg when the leg has a pullback before its
  biggest candle.
* **How many per break**: one per BOS/CHoCH in LuxAlgo SMC (`storeOrdeBlock` once per crossover; it keeps ≤ 100 and shows the last
  **5** per side, internal and swing separately) [S20]; one per swing break, show last **3** per side in OB & Breaker [S21]; OB+ M1D
  shows **1** per side and refuses a block that overlaps an already-drawn one [S25]; OB Pro skips an OB overlapping an active same-
  direction OB and labels nested ones PB [S26]; LuxAlgo L implies one per leg, with stacked candles chosen or merged [S5].
* **Timeframe**: ICT: find on monthly/weekly/daily, refine down [S2]; LuxAlgo: "Lower-timeframe refinement can locate a smaller block
  or imbalance inside the higher-timeframe block" [S5]; OB Pro: HTF 240-min overlay, chart OB nested in HTF OB = starred [S26];
  xs/strike: higher-TF alignment strengthens [S17][S18]. Expiry: ICT Order Block removes a block after 50 bars [S27]; LuxAlgo scripts
  never expire a block, only cap the count [S20][S21]; David's engine: stale after 600 bars.

---------------------------------------------------------------------------------------------------------------------

## 6. How the open-source indicators compute it (verbatim logic)

**Smart Money Concepts [LuxAlgo]** (`dl/smc_luxalgo.pine`, v7, 847 lines) [S20]
```
swingsLengthInput = 50 (min 10)      internal structure uses leg(5)
internalOrderBlocksSizeInput = 5, swingOrderBlocksSizeInput = 5 (swing OBs off by default, internal on)
orderBlockFilterInput  = 'Atr'  | 'Cumulative Mean Range'
orderBlockMitigationInput = 'High/Low' (default) | 'Close'
atrMeasure = ta.atr(200); highVolatilityBar = (high - low) >= 2 * volatilityMeasure
parsedHigh = highVolatilityBar ? low : high ; parsedLow = highVolatilityBar ? high : low   // a 2-ATR bar can never be the OB
on ta.crossover(close, pivot.currentLevel) [BOS or CHoCH]:
    a_rray = parsedLows.slice(pivot.barIndex, bar_index); parsedIndex = pivot.barIndex + a_rray.indexof(a_rray.min())
    orderBlock.new(parsedHighs[parsedIndex], parsedLows[parsedIndex], times[parsedIndex], BULLISH)       // box = that bar's high..low
deleteOrderBlocks: bullish removed when (close | low) < barLow ; bearish when (close | high) > barHigh
```
**Order Blocks & Breaker Blocks [LuxAlgo]** (`dl/ob_breaker_luxalgo_piIbWMpY.pine`) [S21]
```
length = 10 'Swing Lookback'; showBull = showBear = 3; useBody = false
swings: os flips when high[len] > highest(len) / low[len] < lowest(len)  → top/btm swing objects
max = useBody ? max(close,open) : high ; min = useBody ? min(close,open) : low
if close > top.y and not top.crossed:  for i = 1 .. (n - top.x)-1: minima = min(min[i]) ; maxima = max[i] at that bar ; loc = time[i]
    bullish_ob.unshift(ob.new(maxima, minima, loc))
breaker: if not breaker and min(close, open) < element.btm → breaker, break_loc = time
removal: if breaker and close > element.top → remove
```
**Pure Price Action Order & Breaker Blocks [LuxAlgo]**: identical OB/breaker loop; swings from a 3-bar fractal cascade (`'Short Term'
depth 1 / 'Intermediate Term' 2 (default) / 'Long Term' 3`); `useBody = true` by default; draws the 50 % average line. [S22]

**ICT Propulsion Block [LuxAlgo]** (`dl/propulsion_luxalgo.pine`) [S23]
```
obLength = 3 'Swing Detection Length'; obMitigationPrice = 'Closing Price' (| 'Wick'); Most Recent Blocks off (30 when on, else 125)
if bar.close > swingHigh.value and not swingHigh.cross:
    obBar = bar[1]; for index = 1 .. (bar.index - swingHigh.index)-1: if open[index] > close[index] and low[index] <= obBar.low → obBar = that bar
    (the lowest-low DOWN candle since the swing high; box = its open/high/low/close)
propulsion: a bar opening above the OB whose low dips into it (low <= ob.high and low > ob.low) starts a breach; a later close above the
    breach high confirms the breach-low candle as PB; PB mean threshold = avg(open, close)
mitigation: (close | low) < ob.low
```
**Order Block Detector [LuxAlgo]** (`dl/obdetector_luxalgo.pine`) [S30]: `length = 5 'Volume Pivot Length'`; `os` = structure state
from highest/lowest(length); `phv = ta.pivothigh(volume, length, length)`; bullish OB when `phv and os == 1`: box `hl2[length] ..
low[length]` (lower half of the volume-pivot bar); bearish `high[length] .. hl2[length]`; mitigation `'Wick'` (default: lowest low of
the last `length` bars below the box) or `'Close'`; show last 3.

**joshyattridge/smart-money-concepts `ob()`** [S24]: `swing_highs_lows(swing_length=50)` (centred rolling max/min, alternating);
bullish OB when `close` exceeds the most recent uncrossed swing high; OB = candle with the lowest low between that swing and the
break (ties → last); `Top/Bottom = high/low`; `close_mitigation=False` → mitigated when a later `low < Bottom`, `True` → `min(open,
close) < Bottom`; kept as a breaker until price trades through the other side; `OBVolume` = volume of the break candle + 2 before;
`Percentage = min(highVolume, lowVolume)/max(...)`; `bos_choch(close_break=True)`.

**ICT Order Blocks+ (M1D)** (`dl/ict_ob_m1d_FvQ34DMp.pine`) [S25]: `swingLen = 2`; `blendRun = true`; `rallyMult = 0` (ICT 2–3, off);
`keepN = 1`; on `close > swHi` (pivot high not yet broken): scan ≤ 40 bars back, among `close[k] < open[k]` take the lowest close
(tie → larger body); blend adjacent earlier down candles (≤ 4); block = `max(open of the run) .. close[kBest]` (**body only**);
optional: `legHi - grpTop >= rallyMult * bodyH`; removal `close < b.bot`; `tested` when `low <= top and high >= bot`.

**ICT OB Pro** (`dl/ict_ob_pro_oObsuObl.pine`) [S26]: `displace_mult = 0.8` (ATR14), `body_ratio_min = 0.5`; `req_mss = true`
(`mss_len = 8`: `close > highest(high, 8)[3]`); `req_sweep = false` (`swp_len = 5`); `use_pd_arr = true` (4H equilibrium);
`strict_mean = true`; `rb_ratio = 0.6`; `vb_min_atr = 0.5`; sessions 09:30–12:00 & 13:30–16:00 NY. Trigger = a bullish FVG
(`low > high[2]`); OB = the down candle with the lowest low among bars 2..8; box = high..low; `tapped` when `low <= top`; mitigated
after a tap when `close < mean` (strict) or `< bot`; invalidated OB → `+BRK` if `swept_liq` else `+MB`.

**ICT Order Block** (`dl/ict_order_block_HVcKIE8w.pine`) [S27]: `i_dispMultiplier = 1.5` × ATR(14) on the **body**; OB = first
`close[i] < open[i]` within 5 bars before the displacement (2..6 if "Use IMB Confirmation"); `i_obMultiCandle = false` (max 3);
`i_obBreakMode = "Bar Close"`; `i_obLookback = 50` bars; `i_obStructural = false` (BOS/CHoCH within 5 bars); `i_obRefinement = false`
(body box inside dashed wick box); indecision filter (doji < 20 % body, inside bars) off; mitigated = close inside the box; breaker =
close beyond the bottom.

**Order Block Finder** (`dl/ob_finder_QqBOm57l.pine`) [S28]: `periods = 5`, `threshold = 0 %`, zone `Open→Wick` (bull open..low),
`Body`, `Full Wick`; `bullishOB_conf = close[6] < open[6]` and closes 1..5 all up; `absmove = |close[6]-close[1]|/close[6]`;
mitigation/invalidation off by default.

**ICT Order Blocks v2 (Debug)** (`dl/ict_ob_v2_1M4FG5X2.pine`) [S29]: `close[2] < open[2]` and `high[1] > high[2]`; `require_fvg =
true` (`low[0] > high[2]`), `require_strong_close = true` (`close[1] > high[2]`); box `high[2]..low[2]`; removed on `close <
bull_ob_low`.

**MQL5 article 15899** [S31]: `Rango_universal_busqueda = 500`; normal case = 4 consecutive up closes with candle 2's low above
`open1 + 0.5·body1`, candle 2's body extending 40 % past high1, candle 3's low above `open2 + 0.25·body2`; alternatives: a 6-candle
run, an ATR(14) case, a volume-peak case with 60 % body conditions; anchor = first bearish candle ≤ 20 bars back (shift one forward if
its body > 1.3 × the next body); rectangle bullish `low..open`; mitigated on touch.

---------------------------------------------------------------------------------------------------------------------

## 7. Misconceptions and disagreements — and the majority / most authoritative position

| # | disagreement | positions | majority / authority |
|---|---|---|---|
| 1 | **Extreme candle vs "last opposite candle before the big candle"** | ICT 2016: the lowest down-close candle at the support of the leg, validated by a later candle through its high [S1][S2]; all swing-based code: the min-low/lowest-close bar of the leg [S20][S21][S23][S24][S25]; educators and displacement-based code: the last opposite candle immediately before the impulse [S5][S6][S27][S28][S31] | **The extreme candle** (ICT + 6 implementations). The educator wording describes the same candle when the impulse leaves from the extreme; when it does not, the professional marks the extreme ("bookmark … where the move launched"), not a mid-leg pullback candle. David's engine (last opposite before the LAST displacement) is the educator variant. |
| 2 | **Body vs wick** | ICT: body, entry at the open, mean = 50 % of the body [S1][S4][S8][S25]; LuxAlgo and most code: full range [S6][S20][S21][S26]; hybrid [S5][S27] | **Full range for the box, body (open) for the entry, mean threshold of the body for the quality test** — the hybrid LuxAlgo recommends and ICT's own entry/stop rules imply (open = entry, low = stop). No source calls either wrong. |
| 3 | **Invalidation by close vs wick vs 50 %** | close through the far edge [S5][S6][S14][S21][S25][S27][S29][S41][S42]; wick through the far edge [S20 default][S24 default][S30 default]; close beyond the mean threshold [S26 default][S11]; "best OBs never trade below the mean" [S1][S37] | **Close beyond the far edge invalidates; a close beyond the mean threshold downgrades** (ICT's quality rule, OB Pro's strict mode). The LuxAlgo wick default is a display choice, not a definition. |
| 4 | **Is displacement required?** | required: LuxAlgo L "no displacement, no order block" [S6], ICT OB Pro/HVcKIE8w, David; not coded: LuxAlgo swing scripts, joshyattridge, Order Block Finder, MQL5 [S20][S21][S24][S28][S31]; ICT: the move away 2–3× the body [S1] | **Required** in the definition (ICT + LuxAlgo library + ICT-faithful scripts); the swing scripts substitute the BOS itself for it. Measure: body ≥ 1.5 × average body (David) ≈ 0.8–1.5 × ATR (code) and/or a run ≥ 2 × block height (ICT). |
| 5 | **Is a BOS/CHoCH by close required?** | yes, close-based: LuxAlgo SMC/OB&Breaker/Propulsion, joshyattridge, OB+ M1D, OB Pro, purple-trading, alphaexcapital [S12][S14][S20]-[S26]; ICT 2016 needs only a later candle through the OB's high [S1]; ICT 2022 needs a body close beyond the open of the series (CISD) [S3][S8][S9]; optional in HVcKIE8w, absent in Finder/MQL5 | **Yes** — a close beyond a swing (SMC) or beyond the series' open (ICT CISD). Wick-only breaks do not count anywhere. |
| 6 | **Is an FVG required?** | required by default: OB Pro, OB v2, David §12 [S26][S29]; grade: LuxAlgo L, SMC code, xs.com, purple [S5][S6][S12][S17]; ICT: "high probability" needs it (F) [S10] | **Grade, not gate** for the block itself; **gate for a trade setup** (ICT "high probability", David §12). |
| 7 | **Sweep / inducement before the block** | stricter models require it [S5][S19]; OB Pro optional, off [S26]; LuxAlgo & educators: grading [S6][S17] | **Grade**; it decides breaker vs mitigation block later, not whether the OB exists. |
| 8 | **Breaker = any failed OB?** | retail/looser (LuxAlgo scripts, joshyattridge, atas, xs) [S16][S17][S21][S24]; strict ICT: failed OB whose swing ran liquidity, otherwise a mitigation block [S35][S38][S39][S40][S41][S42][S43] | **Strict ICT**: breaker needs the stop run; "mitigation block" is the no-run version. The scripts simply do not track the sweep. |
| 9 | **Consecutive opposite candles** | blend into one (ICT, LuxAlgo, OB+ M1D, HVcKIE8w option) [S1][S5][S6][S25][S27]; "one candle, not a sequence" (alphaexcapital) [S14]; nearest the origin (LuxAlgo alt) [S5] | **Blend** (ICT's explicit instruction). |
| 10 | **Where the 50 % line is measured** | body (ICT, Propulsion code, "Order Blocks Simplified") [S1][S8][S23]; full box (LuxAlgo L, OB Pro, PPA code) [S5][S22][S26] | **Body** is ICT's; code mostly uses the box. Store both. |
| 11 | **Does a tested block stay valid?** | ICT/LuxAlgo: used once, downgraded; propulsion if it holds the mean [S5][S37]; Svopex-style S&D: delete on first touch; academic S/R: tested levels are stronger (earlier research, sources.md) | **Downgrade, keep until invalid** (ICT propulsion logic). |
| 12 | **Does any of it work?** | three independent OB backtests find no edge vs placebo levels (TradingView OB-statistics script: pooled −2.1 pp; StatOasis t = 1.22; Backtrex GBPUSD H1 38 % win, PF 0.83) — see the earlier `sources.md` | LuxAlgo itself: "no reliable universal hit rate exists" [S6]; therighttrader: "no reliable published win rate" [S42][S43][S46]. The definition is a convention, not a measured edge. |

Other misconceptions the sources name explicitly: "it is not simply every down-closed or up-closed candle" [S10]; the institutional-
order narrative "is untested" [S14]; the vacuum block is not a wick zone [S45]; a rejection block must not include the body or "it
turns the idea into … an order block" [S46]; a breaker needs a close through the original block, "a wick does not count" [S42].

---------------------------------------------------------------------------------------------------------------------

## 8. Worked examples from the sources

1. **ICT Month 04 (P)** — bullish OB: find the lowest down-close candle near support; wait for a later candle to trade through its
   high and for a rally of "two to three times" the body height; when price returns, "identify the entry at the open of the down
   candle … or five pips above it"; stop "below the bullish order block's low or below its close"; the best blocks "will not see price
   trade down below the midway point of the entire body". Later the stop can be moved "just below 50 % of the total range". [S1][S2]
2. **ICT Month 04 (P), propulsion**: a new down candle trades into an existing bullish OB and holds above its mean threshold; that
   candle is the propulsion block, traded with a tight stop below its own low ("exit if violated"). [S37]
3. **therighttrader breaker (E, hypothetical numbers)**: bullish OB 110–114; price closes below 110 after the swing that formed it took
   a prior low → 110–114 is a bearish breaker; sell the return at 112, stop 115, target 100 (risk 3 : reward 12); invalid on a close
   back above 114. [S42]
4. **therighttrader mitigation block (E, hypothetical)**: prior high 120 never traded; lower high 116; close through the swing low 108;
   block = last up candle 110–114; short on a return that stalls (close back under 112), stop 117, target 100 (5 : 12). [S43]
5. **therighttrader rejection block (E, hypothetical)**: spike to 130, body top 124 → zone 124–130; sell 127, stop 131, target 115. [S46]
6. **atas.net AAPL daily, summer 2024 (E)**: bearish OB after the break above $200 and the rise to ~$230; the Aug-29 test of the zone
   gave the short entry (no stop/target given). [S16]
7. **purple-trading Gold D1 (E)**: bearish OB after a break of the lower low; entering at the first touch before the gap filled is
   "risky"; waiting for the gap to fill "would have offered almost 6R versus about 3R". [S12]
8. **David's own data (engine, 2026-10-28 00:00 IST GOLD M15)**: single-candle demand 4054.4–4056.6 (the last down candle before a
   ×2.49-body displacement with an FVG that broke structure 05:30) — later broken, flipped and dead (method_report §5). Under rule §9
   below the same candle is the OB if it is the lowest down-close candle of the leg; if a lower same-colour candle exists the box moves
   to it.

---------------------------------------------------------------------------------------------------------------------

## 9. Deterministic OB rule (numbered, with defaults) — what a program should mark

Defaults in **bold**; sources in brackets. Bullish case; bearish mirrored.

1. **Structure.** Swings = David's major structure (`major_structure.py`); a break = a candle **close** beyond the protected swing
   (BOS/CHoCH by close). [S20][S21][S24][S25]; ICT CISD [S3][S9]; David new rules §4-5. Wick-only breaks never create an OB.
2. **Leg.** `origin` = the bar with the lowest low after the previous swing high and before the break bar `x`; the leg is `[origin ..
   x]`. (LuxAlgo SMC/OB & Breaker scan `[pivot .. x]` for the min low — same bar.) [S20][S21]
3. **Displacement gate.** The leg must contain ≥ 1 candle with body ≥ **1.5 × mean body of the previous 10** (David; code equivalents
   0.8–1.5 × ATR14 with body/range ≥ 0.5 [S26][S27]) **and** the run from the OB's top to the break must be ≥ **2 × the OB's body
   height** (ICT "two to three times" [S1][S2]; OB+ M1D `rallyMult` [S25]). No displacement → no OB ("whatever the candle looks like"
   [S6]).
4. **Candidate candle.** `kind = extreme` (**default**): among the down-close candles (`close < open`, strict) in `[origin − 5 .. x−1]`
   take the one with the **lowest low** (ICT "lowest candle with a down close" [S1]; Propulsion/OB Pro code [S23][S26]); tie → the
   larger open-to-close body [S1][S25]. `kind = last` (David's current variant, switchable): the last down-close candle ≤ 5 bars before
   the first displacement candle of the leg (ICT Order Block [S27], David V5 §3).
5. **No down candle at the extreme.** If the leg's lowest-low candle is an up candle and no down-close candle exists within 5 bars
   before it: **mark nothing** (colour-strict code [S23][S25][S26]; ICT CISD needs a series [S9]). Configurable fallback (LuxAlgo SMC /
   joshyattridge behaviour): the extreme candle itself, box `open → low` [S20][S24][S28]. An exact doji (`close == open`) is not a
   down candle; a candle whose body < 20 % of its range may be flagged "doji" for display [S27] but still counts by its close.
6. **Blend.** Extend the candidate backwards over adjacent down-close candles (≤ **4** in a row, OB+ M1D `GROUP_MAX`; HVcKIE8w max 3)
   — ICT: "blend them together to get one full order block" [S1][S2][S25]. The block is one object.
7. **Box.** `top = max(high)` of the blended run, `bottom = min(low)` (**full range**, the indicator majority [S6][S20][S21][S26]);
   also store `body_top = max(open)` (ICT's entry level, "the open of the down candle" [S1][S4][S25]), `body_bottom = min(close)`,
   `mean = (body_top + body_bottom) / 2` (ICT mean threshold of the body [S1][S8]) and `mid = (top + bottom) / 2` (LuxAlgo/OB Pro 50 %
   of the box [S5][S26]). Entry reference = `body_top`; stop reference = `bottom` [S1][S2].
8. **Filters that do not change the candle but grade it** (0–10 score, never hide): FVG left inside the leg after the OB (+2; required
   for a *setup* per David §12 and ICT "high probability" [S10][S26]); the OB's low swept a prior low / EQL within 5 bars (+2, marks
   `swept = true` [S5][S26]); OB low below the dealing-range equilibrium (discount) (+2 [S6][S26]); HTF OB of the same side contains it
   (+1 [S26]); body ≥ 50 % of range (+1); OB candle is the leg extreme (+2 when `kind = last` differs from the extreme). Hard gates stay
   1–3 only.
9. **One block per break.** Store one OB per BOS/CHoCH event (the blended run); a candidate whose box overlaps a live same-side OB of
   an earlier break is not drawn separately (OB+ M1D, OB Pro) [S25][S26]; show the nearest **5** live per side [S20].
10. **Lifecycle from `x+1` on** (closed candles): `fresh` → `tested` when `low ≤ top` (wick into the box) [S25][S26]; `mean` when
    `low ≤ mean` (ICT: a block whose mean holds is "highly sensitive"; past the mean = downgraded [S1][S37]); `invalid` when a candle
    **closes** `< bottom` (majority [S5][S6][S21][S25][S27][S42]); optional `strict_mean`: `close < mean` already invalidates (OB Pro
    default, penchan [S11][S26]). A wick below `bottom` without a close is a sweep of the block, not an invalidation (LuxAlgo's wick
    default is display only).
11. **After invalidation.** If `swept = true` → `breaker` (ICT: the origin swing ran liquidity [S35][S39][S41]); else → `mitigation
    block` (failure swing, "the body of the candle is not violated" [S38][S40][S43]). Both are traded on the return from the other
    side; `dead` when a candle closes back through the far (original top) edge [S21][S39].
12. **Propulsion.** A down-close candle that trades into a live bullish OB (`low ≤ top`, `low > bottom`, open above `top`), does not
    close below the OB's `mean`, and is followed by a close above its own high → it is a `propulsion` block with its own box and mean
    = avg(open, close) [S23][S37][S47].
13. **Stale.** A fresh block older than **600** bars (David) is `stale`; the public scripts either never expire (LuxAlgo) or drop after
    50 bars (HVcKIE8w) [S27] — keep David's.
14. **Rejection block** (separate mark, optional): at a major swing high that swept a prior high, zone = highest open/close of the swing
    .. highest high, wick ≥ 60 % of range [S26][S44][S46]. **Vacuum block**: a gap (next open vs prior close) ≥ 0.5 ATR at a session
    open / news bar [S26][S34]. Neither is an OB.

### David's rule text vs the sources
David's "Supply = the final bullish candle before strong bearish displacement" (new rules §9, V5 §3) is **exactly the educator order
block** [S5][S6][S27], not a supply zone: Seiden/OTA supply & demand is a *base* of 1–6 small-bodied candles before the departure (the
earlier `method_report.md`, S6/S19/S22/S23 there), "potentially 3 to 8 times wider" than an OB (backtrex, earlier research) and needs
no structure break. LuxAlgo states the relationship directly: supply/demand "covers the whole base"; "order blocks are the stricter,
candle-level version, usually requiring displacement, a structure break, or a sweep" [S6]. So the engine's `OB` layer is the right
name for his rule, and the difference between his rule and ICT's is only step 4 (`last` vs `extreme`) and step 6 (blending).

---------------------------------------------------------------------------------------------------------------------

## Sources

ICT primary (lecture summaries; the pages warn they are AI-generated)
- [S1] ICT Mentorship Core Content – Month 04 – Orderblocks (videohighlight summary): https://videohighlight.com/v/PIYh0CxoY9c
- [S2] same lecture, opentools.ai transcript summary: https://opentools.ai/youtube-summary/ict-mentorship-core-content-month-04-orderblocks
- [S3] 2022 ICT Mentorship Episode 3 (summary): https://videohighlight.com/v/nQfHZ2DEJ8c
- [S4] ICT 2024 Mentorship – Tape Reading – Sept 25, 2024 (summary): https://videohighlight.com/v/NDwNIqUkASc
- [S7] ICT 2023 Mentorship Analysis – Jan 25, 2023 (summary): https://videohighlight.com/v/HkiPAi1Mdu8
- [S8] "Order Blocks Simplified – ICT Concepts" (summary): https://videohighlight.com/v/DMUiDBnTYc8
- [S34] Month 04 – ICT Vacuum Block: https://videohighlight.com/v/shPGUz9pU-A
- [S35] Month 04 – ICT Breaker Block: https://videohighlight.com/v/UrS-mtGHtAA
- [S37] Month 04 – ICT Propulsion Block: https://videohighlight.com/v/glu98jAH8vE
- [S38] Month 04 – Mitigation Blocks: https://videohighlight.com/v/FOUzW0QmsfI
- [S44] Month 04 – ICT Rejection Block: https://videohighlight.com/v/oALYX0HCSYw
- [S48] Month 04 – Reclaimed ICT Orderblock: https://videohighlight.com/v/X5pQjfkAUCI
- Month 04 playlist index: https://videohighlight.com/playlist/PLVgHx4Z63pabb9rl1nyG58TG8PG8yzuao ; 2022 mentorship index: https://videohighlight.com/playlist/PLVgHx4Z63paYiFGQ56PjTF1PGePL3r69s
- [S10] X/Twitter threads on ICT order blocks (threadreaderapp mirror; rattibha mirror 403): https://threadreaderapp.com/thread/1819402201665622455 , https://en.rattibha.com/thread/1782835104248709494

LuxAlgo library (concept pages)
- [S5] Order Block Anatomy & Refinement: https://www.luxalgo.com/library/concept/order-block-anatomy-and-refinement.md
- [S6] Bullish/Bearish Order Block: https://www.luxalgo.com/library/concept/bullish-bearish-order-block.md
- [S9] Change in State of Delivery: https://www.luxalgo.com/library/concept/change-in-state-of-delivery.md
- [S39] Breaker Block: https://www.luxalgo.com/library/concept/breaker-block.md
- [S40] Mitigation Block: https://www.luxalgo.com/library/concept/mitigation-block.md
- [S45] Rejection Block: https://www.luxalgo.com/library/concept/rejection-block.md
- [S47] Propulsion Block: https://www.luxalgo.com/library/concept/propulsion-block.md
- [S49] Reclaimed Order Block: https://www.luxalgo.com/library/concept/reclaimed-order-block.md
- LuxAlgo indicator pages: Order Blocks & Breaker Blocks https://www.luxalgo.com/library/indicator/order-blocks-breaker-blocks/ ; Smart Money Concepts https://www.luxalgo.com/library/indicator/SRsr9SLs-smart-money-concepts ; ICT Propulsion Block https://www.luxalgo.com/library/indicator/ict-propulsion-block.md

Open-source code (read)
- [S20] Smart Money Concepts [LuxAlgo], Pine v7 (PUB;6daafb2cabe6419d98ae25229d2327f8): https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-LuxAlgo/ — local `dl/smc_luxalgo.pine`
- [S21] Order Blocks & Breaker Blocks [LuxAlgo] (PUB;2c9c3913a94e4a2ba3ffaa624d76c115): https://www.tradingview.com/script/piIbWMpY-Order-Blocks-Breaker-Blocks-LuxAlgo/ — `dl/ob_breaker_luxalgo_piIbWMpY.pine`
- [S22] Pure Price Action Order & Breaker Blocks [LuxAlgo] (PUB;b216cce6412c4b45a2650c5accf8b3a6): https://www.tradingview.com/script/5PB593yX-Pure-Price-Action-Order-Breaker-Blocks-LuxAlgo/ — `dl/ppa_ob_breaker_luxalgo_5PB593yX.pine`
- [S23] ICT Propulsion Block [LuxAlgo] (PUB;a5100ba791cb49f688245ed2abe49837): https://www.tradingview.com/script/bXiYDei9-ICT-Propulsion-Block-LuxAlgo/ — `dl/propulsion_luxalgo.pine`
- [S30] Order Block Detector [LuxAlgo] (PUB;7c893384ebc34d83b9f1ec3275e2f002): https://www.tradingview.com/script/KvGhxGxY-Order-Block-Detector-LuxAlgo/ — `dl/obdetector_luxalgo.pine`
- [S24] joshyattridge/smart-money-concepts (Python): https://raw.githubusercontent.com/joshyattridge/smart-money-concepts/master/smartmoneyconcepts/smc.py , README https://raw.githubusercontent.com/joshyattridge/smart-money-concepts/master/README.md
- [S25] ICT Order Blocks+ (M1D) (PUB;68483d62e0b349059efd5b84bbff8eb8): https://www.tradingview.com/script/FvQ34DMp-ICT-Order-Blocks-M1D/ — `dl/ict_ob_m1d_FvQ34DMp.pine`
- [S26] ICT Order Block Pro / "ICT OB Pro – Quantitative System" (PUB;8aff8b93b6d7449f9c592e1c99274bfc): https://www.tradingview.com/script/oObsuObl-ICT-Order-Block-Pro/ — `dl/ict_ob_pro_oObsuObl.pine`
- [S27] ICT Order Block (PUB;3a0701dcdf8247eda7724e88f0ea3e0a): https://www.tradingview.com/script/HVcKIE8w-ICT-Order-Block/ — `dl/ict_order_block_HVcKIE8w.pine`
- [S28] Order Block Finder (Xcelerate, wugamlo lineage; PUB;4ef22bb516274cf5bfb90a5ca25d2c9a): https://www.tradingview.com/script/QqBOm57l-Order-Block-Finder/ — `dl/ob_finder_QqBOm57l.pine` ; original "Order Block Finder (Experimental)" description: https://www.luxalgo.com/library/indicator/R8g2YHdg-order-block-finder-experimental/
- [S29] ICT Order Blocks v2 (Debug) (PUB;99f223f396b247dda52b87d60dc007cf): https://www.tradingview.com/script/1M4FG5X2-ICT-Order-Blocks-v2-Debug — `dl/ict_ob_v2_1M4FG5X2.pine`
- [S31] MQL5 article "Developing Advanced ICT Trading Systems: Implementing Order Blocks in an Indicator": https://www.mql5.com/en/articles/15899 ; repo https://forge.mql5.io/nique_372/MQLArticles/src/branch/main/Ob/README.md ; discussion https://www.mql5.com/en/forum/489668/57258884
- [S36] ICT Concept [TradingFinder] Order Block | FVG | Liquidity Sweeps: https://www.tradingview.com/script/5n6Lawvs-ICT-Concept-TradingFinder-Order-Block-FVG-Liquidity-Sweeps/
- Pine sources were fetched from `https://pine-facade.tradingview.com/pine-facade/get/PUB%3B<id>/last?no_4xx=true`.

Educators / vendors / forums
- [S11] penchan "ICT order block": https://penchan.co/en/market/ict-order-block/
- [S12] Purple Trading "Smart money strategy: order blocks": https://www.purple-trading.com/trading-trends-2023-smart-money-strategy-order-blocks/
- [S13] TradingView idea (Anbat) "Order Blocks – How To Use Them In Trading": https://www.tradingview.com/chart/GBPAUD/3nqRgyvN-Order-Blocks-How-To-Use-Them-In-Trading/
- [S14] alphaexcapital "Order blocks explained": https://www.alphaexcapital.com/smart-money-concepts/order-blocks-explained
- [S15] crosstrade "Order blocks": https://crosstrade.io/learn/price-action/order-blocks
- [S16] atas.net "What are ICT order blocks and breaker blocks": https://atas.net/blog/what-are-ict-order-blocks-and-breaker-blocks-in-trading/
- [S17] xs.com "What is an order block": https://www.xs.com/en/courses/smart-money-concept-strategy/what-is-an-order-block
- [S18] strike.money "Order block": https://www.strike.money/technical-analysis/order-block
- [S19] "extreme vs decisional" OB (invite-only AlbaTherium / TradingHub, via search excerpts, second-hand): https://www.tradingview.com/script/AmNw9twO-AlbaTherium-Structure-Mapping-Order-Blocks-Advanced-Beta , https://cn.tradingview.com/script/zSkad1tv-OrderBlock-TradingHub
- [S32] search for the no-opposite-candle case (no source addresses it): https://www.luxalgo.com/library/concept/bullish-bearish-order-block.md , https://crosstrade.io/learn/price-action/order-blocks
- [S33] ICT core-content notes (Notion, JS-rendered — search excerpt only): https://arjoio.notion.site/Institutional-Order-Flow-f56c5b3c64024b55b8d0b5b1a55a9d94 , https://arjoio.notion.site/Orderblocks-fe4c506b65d94805991e19aee99f449e
- [S41] eltraderfinanciado "Breaker block": https://www.eltraderfinanciado.com/en/blog/breaker-block
- [S42] therighttrader "Breaker block": https://therighttrader.com/learn/smart-money-concepts/breaker-block
- [S43] therighttrader "Mitigation block": https://therighttrader.com/learn/smart-money-concepts/mitigation-block
- [S46] therighttrader "Rejection block": https://therighttrader.com/learn/smart-money-concepts/rejection-block
- [S50] writofinance "ICT reclaimed order block": https://www.writofinance.com/ict-reclaimed-order-block-in-forex
- MQL5 blog "Master Smart Money Concepts … Order Block & FVG indicator": https://www.mql5.com/en/blogs/post/771981
- dotnettutorials "Order Block Trading Strategy": https://dotnettutorials.net/?p=35367
- Unreachable (403/404) and therefore not quoted beyond search excerpts: metalsmine threads 15263773 / 15274595 / 15304155, babypips 700783, rattibha threads, innercircletrader.net CISD page (ad-only render), shortform ICT-2022 summary (paywall), arjoio / mirandatr8 Notion notes.

Earlier research reused: `/home/david/forex/engine/research/supply_demand/method_report.md`, `opensource_report.md`, `sources.md`
(backtests: TradingView "Order Block (OB) Statistics" https://www.tradingview.com/script/yFmy3VBi-Order-Block-OB-Statistics-Real-Win-Rate-vs-Random-Levels/ , StatOasis https://statoasis.com/overfit/research/ict-backtest-what-survives , Backtrex https://backtrex.com/en/backtests/order-block-gbp-usd).
