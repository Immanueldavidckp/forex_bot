# Open-source supply & demand tools — exact algorithms, ports, comparison (2026-10-30)

Research only. Files in this folder: `ports.py` (six faithful numpy ports), `toy_tests.py` (behaviour checks, all pass),
`compare.py` → `compare_output.txt` / `compare_results.json`, `dl/` (the downloaded originals: `dl/shved29395/*.mq5`,
`dl/shved14545/*.mq4`, `dl/tv/*.pine`, `dl/cmike/*.js`, `dl/tv_luxalgo_vr.pine`, `dl/wraquant_sr.py`, `dl/prorealcode_rbd.html`).
Nothing under /home/david/forex was touched; `major_structure.py` was imported read-only via `sys.path`.

## 1. Sources (code actually read, with popularity)

| # | Tool | Where the code is | Popularity | Method family |
|---|------|-------------------|-----------|---------------|
| 1 | **Shved Supply and Demand** (MT4 original "Shved" 2016; MT5 port by Behzad.mvr v1.7, 2023) | https://www.mql5.com/en/code/14545 (mq4), https://www.mql5.com/en/code/29395 (mq5, ~70k views) | the most copied MT4/MT5 S&D indicator | **fractal (swing) S/R zones** with weak / untested / verified / proven / turncoat |
| 2 | **Supply and Demand Zones [BigBeluga]** (Pine v6, CC BY-NC-SA) | https://www.tradingview.com/script/I0o8N7VW-Supply-and-Demand-Zones-BigBeluga/ | 11,359 boosts | 3 same-colour candles + volume → last opposite candle, fixed 2×ATR(200) box |
| 3 | **Supply and Demand Visible Range [LuxAlgo]** / **Supply and Demand Daily [LuxAlgo]** (Pine v5) | https://www.tradingview.com/script/UpWXXsbC-Supply-and-Demand-Visible-Range-LuxAlgo/ , https://www.tradingview.com/script/rc0kPSGU-Supply-and-Demand-Daily-LuxAlgo/ | 26,404 / 9,585 boosts | **volume profile of the range** (volume accumulated from the top / bottom until 10 % of the range volume) — NOT a price-action zone method |
| 4 | **Supply Demand Zones PRO** (ProjectSyndicate, Pine v6) | https://www.tradingview.com/script/h0jxhmgn-Supply-Demand-Zones-Pro/ | 5,819 boosts | pivot(12) candle box forced to 1 ATR; retests; strength 0–10 |
| 5 | **Supply and Demand Zones \| Flux Charts** (Pine v6) | https://www.tradingview.com/script/ZUAYemgd-Supply-and-Demand-Zones-Flux-Charts/ | 4,305 boosts | pivot(30) + average-wick box; retest / breakout / flip / "held %" statistics |
| 6 | **@cmike444/supply-and-demand-zones 1.3.1** (TypeScript, MIT, github.com/cmike444/SupplyAndDemand) | https://unpkg.com/@cmike444/supply-and-demand-zones@1.3.1/dist/lib/identifyZones.js (+ rallyBaseDrop.js, isValidBase.js, calculateConfidence.js, filterFreshZones.js, constants/candles.js) | npm; the only full RBD/DBD/DBR/RBR library with readable code | **Sam-Seiden style leg–base–leg** with decisive / indecisive / explosive candles, ATR base limits, confidence score |
| 7 | **Svopex S&D Scan** (Pine v6) | https://www.tradingview.com/script/Jywsoivw-Svopex-S-D-Scan/ | 51 boosts (small, but the cleanest "base candles + explosive candle in ATR" code) | 1–3 base candles (body < 0.5 ATR) then an explosive body > 1.5 ATR |
| – | Supply and Demand Zones [Clean v6] (CaseInTheMoney) | https://www.tradingview.com/script/VDv1AnDA-supply-and-demand-zones/ (575 boosts) | read, not ported | pivot(10) + 0.25×ATR(50) box, broken by a close through the near edge |
| – | Supply/Demand Zone Candles (skbohler) | https://www.tradingview.com/script/vphHn1sk-Supply-Demand-Zone-Candles (273) | read, not ported | pure L-B-L-B candle patterns (leg = body ≥ 50 % of range, base = body < 50 %) |
| – | wraquant `supply_demand_zones` (Python) | https://wraquant.readthedocs.io/en/stable/_modules/wraquant/ta/support_resistance.html | read, not ported | 3 small-body bars (body < median body) then a bar with body/range ≥ 0.6; zone = the 3 bars' high/low |
| – | PRC Rally Base Drop SND (ProRealCode, Iván González 2025) | https://www.prorealcode.com/prorealtime-indicators/rally-base-drop-snd-indicator/ | read, not ported | rally = 2 green closes, drop = 2 red closes, base = neither; zone = highest/lowest BODY of the 2 base bars |
| – | "Advanced Supply and Demand Indicator" (CR-JE, 199), "AMG" (58) | tradingview.com/script/uMuNx4rk…, KJ3bRTUs… | read, rejected | trivial / broken (AMG pushes every bar whose range > 0.4 ATR; CR-JE never draws a box because its arrays are rebuilt each bar) |

The Pine sources were fetched from `https://pine-facade.tradingview.com/pine-facade/get/<PUB;id>/last` (TradingView's own
open-source endpoint); MQL5 CodeBase zips from `mql5.com/en/code/download/<id>`. The sandbox refused nothing: the Shved MQL and the
npm JS were read directly; nothing from the downloads was executed (Python ran with `-I`).

GitHub copies of Shved exist only as forum attachments (metalsmine.com thread 14425051, fxcodebase "shved_supply_and_demand_mod_v1.mq4");
the MQL5 CodeBase originals above are the canonical code. The `SRRR` object prefix in Shved shows its lineage: it is the old
"SupportResistance zones" MT4 indicator renamed — Shved's **zones are swing-high/low S/R, not base-before-displacement S&D**.

## 2. Each algorithm exactly

### 2.1 Shved Supply and Demand (mq4 14545 == mq5 29395, same FindZones)
Inputs (defaults): `BackLimit 1000`, `zone_show_weak false` (mq4: true), `zone_show_untested true`, `zone_show_turncoat true`
(mq4: false), `zone_fuzzfactor 0.75`, `zone_merge true`, `zone_extend true`, `fractal_fast_factor 3.0`, `fractal_slow_factor 6.0`,
ATR = `iATR(7)`.

Zone finding (`FindZones()`, lines 301-479 of v1_7):
- Swing points: `Fractal(M,P,shift)` with `P = timeframe*factor; if timeframe>P P=timeframe; P = P/timeframe*2 + ceil(P/timeframe/2)`
  (integer MQL arithmetic) → **fast = 7 bars each side, slow = 15 bars each side on every timeframe** (the timeframe cancels).
  A high is a fractal when the 7 older highs are `<=` it and the 7 newer highs are `<` it (`High[shift+i]>High[shift]` / `High[shift-i]>=High[shift]` → false).
  Fractals are known 7 (15) bars after the bar; the loop ignores the 5 newest bars (`for ii=shift; ii>cnt+5`).
- Box of an up-fractal (lines 314-317): `fu = ATR7/2 * fuzz`; `hival = High + fu` (extend); `loval = max(min(Close, High-fu), High-2fu)`
  → the fractal high plus 0.375 ATR above, down to the close (bounded between 0.375 and 0.75 ATR below the high).
  Down-fractal mirrored. **Height ≈ 0.75–1.1 ATR7**, anchored on the wick extreme.
- Walking forward from the fractal (lines 323-367): a **touch** = a later FAST fractal of the same kind inside [loval,hival]
  (`FastUpPts[i]>=loval && FastUpPts[i]<=hival`), only if no such fractal in the 10 older bars; a touch sets `bustcount=0; testcount++`.
  A **bust** = a WICK through the far side (`High[i]>hival`): `bustcount++`; if `bustcount>1 || isWeak` → the zone is dropped
  (`isBust=true; break`); else the zone **turns** (`turned=!turned; hasturned=true; testcount=0`) — a resistance becomes support and
  touches are now down-fractals inside the box. `isWeak` = no SLOW fractal at the same bar (lines 311-313).
- Strength (lines 377-389): `testcount>3 → PROVEN; testcount>0 → VERIFIED; hasturned → TURNCOAT; !isWeak → UNTESTED; else WEAK`.
- Merge (lines 481-537, ≤ 3 passes): any two overlapping boxes become their union; `hits` summed; `strength = max`; `hits>3 → PROVEN`;
  **two untested overlapping boxes become VERIFIED with hits=1** (lines 524-529); turn survives only if both turned.
- Type (lines 550-574): support if `zone_hi < Close[0]`, resistance if `zone_lo > Close[0]`, otherwise the first older close outside decides.
- Display: a rectangle from the fractal bar to now, colour by strength; label "Sup/Res i Strength=Verified, Test Count=n".
- There is **no displacement / impulse test, no volume, no close-based invalidation** (busts are wicks), and a zone busted twice
  simply disappears (nothing is drawn for it).

### 2.2 cmike444 supply-and-demand-zones (identifyZones.js + rallyBaseDrop.js …)
Constants (`constants/candles.js`): `DEFAULT_EXPLOSIVE_THRESHOLD 0.7`, `DEFAULT_DECISIVE_THRESHOLD 0.5`, `MIN_RALLY_CANDLES 2`,
`MIN_DROP_CANDLES 2` (declared, **not enforced** — rallyBaseDrop only checks `rallyEndIndex === 0`), `MIN_BASE_CANDLES 1`,
`MAX_BASE_CANDLES 6`, `MIN_ZONE_CANDLES 5`, `ATR 14`, `MAX_ZONE_ATR_MULTIPLIER 1.5`, `MAX_BASE_GAP_ATR_MULTIPLIER 0.5`,
`MIN_EXPLOSIVE_ATR_MULTIPLIER 1.5`.
- Candle classes: decisive = body/range > 0.5; indecisive = body/range ≤ 0.5 (or body 0); explosive = body/range ≥ 0.7 **and** range ≥ 1.5 × ATR.
- `localATR` at bar i = mean TR of the 14 candles **before** i.
- At every bar i try RBD, DBD, DBR, RBR in that order (`identifyZones` lines 92-137): leg-in = run of decisive candles of the leg
  colour from i (`findPatternEnd`); base = run of ≤ 6 indecisive candles (≥ 1); leg-out = run of explosive candles of the exit colour
  (≥ 1); `isValidBase`: gaps between base candles ≤ 0.5 ATR and base high–low ≤ 1.5 ATR; the first leg-out candle must not be the
  opposite colour. On a match the scan jumps past the pattern (`i += endIdx`).
- Edges (rallyBaseDrop.js lines 42-45): supply **proximal = lowest BODY of the base** (`min(open,close)`), **distal = highest HIGH of the
  whole formation** (leg-in + base + leg-out), demand mirrored. So the box is base-body-to-pattern-wick, often taller than the base.
- Confidence 0–1 = mean of seven factors: departure (share of strong candles, mean range/ATR, departure volume / base volume as
  ratio/(ratio+1), base length ≤3 → 1, ≤6 → 0.5) ×3, position in the chart's price range, **freshness (1.0 never entered, 0.5 entered
  at the proximal)**, timeframe (log-scaled), RR (`min(departureExtent/zoneWidth/5, 1)` — as coded it uses ALL candles ≤ end, a bug).
- `filterFreshZones`: a demand whose proximal is above a supply's proximal is in conflict; the older one is dropped.
- Invalidation: none beyond the freshness flag and that conflict rule.

### 2.3 Svopex S&D Scan (f_detect / f_track / f_break)
Inputs: `baseMax 3`, `baseBodyPct 0.5` (base body ≤ ATR×0.5), `explMult 1.5` (explosive body ≥ ATR×1.5), `atrLen 14`,
`maxZonesPerSide 20`, `useWicks true`, `breakPct 0`, `nearMult 1`.
- `isBase = |c-o| < 0.5*ATR`; `isExplUp = (c-o) > 1.5*ATR`. Consecutive base candles accumulate `baseH/baseL` (wicks). On an explosive
  candle with `1 ≤ baseCount ≤ 3` the zone = `[baseL, baseH]` (wick-to-wick of the base), anchored at the first base bar; a base longer than
  3 is discarded (`else baseCount := 0`). The zone is handed on one bar late (`sig[1]`).
- `f_break` (lines 426-450): on each confirmed bar `thr = bot + hgt*pct`; with the **default `breakPct 0` a supply zone is deleted the
  first time a bar's HIGH reaches its BOTTOM edge** — default = "fresh zones only, gone on the first touch"; `breakPct 100` = gone when
  the far edge is exceeded by a wick (or a body if `useWicks` false).
- Status: price inside / "NEAR" (within 1 ATR of the near edge) / "WAS IN" (touched in the last 10 bars). No touch count, no strength.

### 2.4 Flux Charts Supply and Demand Zones
Inputs: `Swing Period 30`, `Lookback 2000`, `Show 5` per side, `Min Zone Spacing 0.1 %`, `Retest Cooldown 3`, `Hold Window 10`,
`Min Held % 0`, `rankBy Strongest`, constants `WICK_AVG_BARS 5`, `HOLD_PRIOR 1/2`, `DIST_SENS 25`, `INCUMBENT_BONUS 0.15`.
- Zone = `ta.pivothigh(30,30)`; box (`getZoneBounds`): `top = pivot high`, `bottom = top − mean upper wick of the pivot bar and the 4 bars
  before it` → **tiny boxes, ~0.3 ATR**. A new zone is skipped if it overlaps any active zone of either side (`hasOverlap`).
- Per confirmed bar (`updateZones`): `brokeThrough` = close beyond the far edge, `brokeBack` = close beyond the near edge.
  First close through → `pendingFlip`. Next bar: still through → **breakout counted and the zone FLIPS side** (`isSupply := not isSupply`,
  a new "segment"); closed back through the near edge → counted as a **retest** ("failed breakout"). Otherwise a retest = wick into the box
  and close back outside (`high >= bottom and close < bottom`), at most one per 3 bars.
- `computeHoldStats`: a retest "held" if no breakout within the next 10 bars; `quality = (held+1)/(resolved+2)`;
  `score = quality × (1+ln(1+retests)) × 1/(1+relDist×25)`, incumbents ×1.15; the 5 best per side are drawn, with Retests · Breakouts · Held %.
- A zone never dies (only ages out at 2000 bars); the only "validity" is the held statistic and the side flip.

### 2.5 Supply and Demand Zones [BigBeluga]
- `extra_vol = volume > avg(last 1000 volumes)`, `atr = ta.atr(200)*2`.
- Supply: `bear and bear[1] and bear[2] and extra_vol[1] and count_bear == 0` → look back ≤ 6 bars for the last **bull** candle i:
  box `[low[i], low[i] + 2*ATR200]` (bottom = that candle's low, fixed 2-ATR height going UP from it — not the candle's range);
  cooldown 15 bars; demand mirrored (`[high[i] − 2 ATR, high[i]]`). The label shows the signed volume delta of the 3-candle move.
- Deleted on `close > top` (far edge). Dashed ("mitigated") when a bar straddles the near edge — the age gate
  `(right − left − 15) > 20` is always true because `set_right(bar_index+100)` runs just before it. A box whose range contains another
  box's near edge is removed; only the last 5 per side are kept.

### 2.6 Supply Demand Zones PRO (ProjectSyndicate)
Inputs: `swingLen 12`, `maxZones 10`, `maxZoneHeightATR 1.0`, `minZoneHeightATR 1.0`, `forceZoneHeightATR 1.0`, `minZoneDistance 44`,
`invalidation Close`, ATR(20), session filter (hour 22-23 exchange time = "Other" → no zone).
- Zone = the pivot(12) candle's `high..low`, expanded to ≥ 1 ATR around its mid, then clamped to ≤ 1 ATR → **every zone is exactly
  1 ATR(20) tall centred on the pivot candle**; a new zone of the same side needs 44 bars since the last; an overlapping unbroken zone of
  the same side is merged (union, among the last 10 zones).
- Retest = a bar entering the box (edge-triggered); broken = `close > top` (supply) / `close < bottom` (demand) → grey "historic".
- `strength = int(clamp(8 − 0.8×retests − min(age/500, 2), 0, 10))` — **fewer retests and younger = stronger**; label shows pips,
  session, age, distance.

### 2.7 LuxAlgo Supply and Demand Visible Range / Daily (for completeness)
`per 10 %`, `div 50`: split the visible (or previous day's) high–low range into 50 bins; walk down from the high adding the intrabar
volume of each bin until it exceeds 10 % of the range's total volume → that band is "supply"; up from the low → "demand"; average and
volume-weighted average lines; equilibrium = mid. A volume-profile value-area edge recalculated when the view changes — a context
overlay, not a zone-validity method. Not ported (needs intrabar volume; nothing to validate against David's rule).

## 3. Comparison on our bars (last 3,000 bars, `compare.py`)

*(`compare_output.txt` / `compare_results.json` were regenerated 2026-10-30 09:29 on newer bars; `toy_tests.py` was rewritten the same morning after the original was lost with the research scratchpad — 31 checks, all pass.)*

Generic life after the bar the tool first draws the zone: touch = a bar enters the box, broken = a **close** beyond the far edge
(the same test for every tool, David-style), evaluated on zones with ≥ 200 bars of life left. `h/ATR` = box height / ATR14 at the
anchor. `gate` = David's validity: the anchor bar lies inside the leg of a major BOS/CHoCH of the matching side (origin ≤ idx ≤ break,
`major_structure.py` defaults); `strict` = additionally within 10 bars of the leg origin (the zone is the START of the breaking move).

| data | tool | zones/100 bars | h/ATR mean | touched ≤50 | broken ≤50 | broken ≤200 | fresh at end | David gate | strict |
|---|---|---|---|---|---|---|---|---|---|
| GOLD M15 | shved (all fractal zones) | 2.90 | 1.10 | 83 % | 60 % | 79 % | 8 % | 35 % | 16 % |
| | cmike | 1.83 | 1.10 | 84 % | 68 % | 78 % | 9 % | 47 % | 15 % |
| | svopex | 1.37 | 1.27 | 92 % | 64 % | 87 % | 2 % | 59 % | 20 % |
| | flux | 1.63 | 0.31 | 44 % | 31 % | 64 % | 20 % | 67 % | 51 % |
| | bigbeluga | 5.90 | 2.14 | 89 % | 45 % | 75 % | 2 % | 43 % | 12 % |
| | sdzpro | 2.63 | 1.16 | 77 % | 51 % | 82 % | 4 % | 41 % | 24 % |
| GOLD H1 | shved | 2.43 | 1.13 | 86 % | 65 % | 82 % | 7 % | 27 % | 4 % |
| | cmike | 1.47 | 0.98 | 80 % | 62 % | 82 % | 5 % | 50 % | 5 % |
| | svopex | 0.90 | 1.00 | 60 % | 52 % | 84 % | 15 % | 82 % | 19 % |
| | flux | 1.63 | 0.32 | 42 % | 31 % | 58 % | 18 % | 51 % | 35 % |
| | bigbeluga | 6.03 | 2.13 | 86 % | 50 % | 75 % | 3 % | 39 % | 5 % |
| | sdzpro | 2.63 | 0.99 | 75 % | 53 % | 73 % | 4 % | 39 % | 14 % |
| EURUSD M15 | shved | 2.63 | 1.07 | 71 % | 47 % | 87 % | 6 % | 37 % | 9 % |
| | cmike | 1.93 | 1.25 | 73 % | 50 % | 82 % | 7 % | 45 % | 5 % |
| | svopex | 1.53 | 1.17 | 88 % | 68 % | 93 % | 4 % | 37 % | 7 % |
| | flux | 1.43 | 0.27 | 26 % | 24 % | 50 % | 30 % | 58 % | 40 % |
| | bigbeluga | 4.67 | 1.96 | 82 % | 46 % | 77 % | 4 % | 36 % | 9 % |
| | sdzpro | 2.43 | 1.12 | 73 % | 54 % | 73 % | 8 % | 43 % | 22 % |
| EURUSD H1 | shved | 2.37 | 1.19 | 80 % | 57 % | 78 % | 11 % | 44 % | 9 % |
| | cmike | 1.60 | 1.15 | 78 % | 61 % | 76 % | 6 % | 52 % | 8 % |
| | svopex | 1.33 | 1.42 | 81 % | 60 % | 73 % | 8 % | 55 % | 5 % |
| | flux | 1.60 | 0.31 | 46 % | 39 % | 64 % | 17 % | 54 % | 25 % |
| | bigbeluga | 5.00 | 2.33 | 85 % | 53 % | 71 % | 6 % | 42 % | 7 % |
| | sdzpro | 2.70 | 1.06 | 80 % | 51 % | 74 % | 6 % | 44 % | 16 % |

Major events in the windows: GOLD M15 47 (26 BOS / 21 CHoCH), GOLD H1 25, EURUSD M15 29, EURUSD H1 28.

Tool-specific status counts (GOLD M15 / GOLD H1 / EURUSD M15 / EURUSD H1):
- Shved: of 87 / 73 / 79 / 71 fractal zones only **9 / 12 / 8 / 13 survive** to the last bar (untested 2/2/2/4, verified 4/8/5/6,
  proven 0/1/0/0, turncoat 0/1/0/2, weak 3/0/1/1); 78 / 61 / 71 / 58 are busted (two wicks through). Surviving verified/untested zones
  pass David's gate 50–100 % of the time; busted ones 18–33 %. The strength classes are informative only after the fact (a zone is
  "verified" because a later swing stopped in it).
- cmike: pattern mix roughly even (RBD 8–15, DBD 13–19, DBR 11–13, RBR 9–15); only **5–9 % still fresh**; 58–77 % removed as "stale" by
  the demand-above-supply rule; confidence ≥ 0.6 for almost all zones (mean 0.72), and the score does not separate broken from unbroken
  (broken ≤200: 78 % vs 80 %).
- Svopex: **89–98 % of zones are removed at the first touch** (default breakPct 0); a base of 1 candle dominates (20–25 of 27–46).
- Flux: mean 10–13 "retests" per zone over 3,000 bars, 60–79 % flip side at least once, held % 53–57 %; quality ≥ 0.5 raises the gate
  pass from 40–62 % to 54–68 %.
- BigBeluga: 46–58 % deleted by a close through the far edge, 31–47 % removed by its overlap rule, 77–85 % "mitigated" (dashed) at some point.
- SDZ PRO: 79–90 % broken by the end; strength histogram sits at 3–6; **strength > 5 zones pass David's gate 58–75 % vs 36–42 % for ≤ 5,
  and are broken within 200 bars 33–57 % vs 74–85 %** — the only built-in score that separates both.

Agreement (% of the row tool's zones that the column tool also has: same side, overlapping price, anchor within ±40 bars):

| GOLD M15 | shved | cmike | svopex | flux | bigbeluga | sdzpro |
|---|---|---|---|---|---|---|
| shved | – | 28 | 16 | 23 | 82 | 59 |
| cmike | 26 | – | 35 | 4 | 80 | 42 |
| svopex | 20 | 46 | – | 7 | 83 | 42 |
| flux | 27 | 4 | 6 | – | 65 | 29 |
| bigbeluga | 27 | 32 | 29 | 23 | – | 57 |
| sdzpro | 33 | 25 | 22 | 18 | 81 | – |

The other three data sets look the same (full matrices in `compare_output.txt`): BigBeluga "agrees" with everybody only because it
draws 5–6 two-ATR boxes per 100 bars; the two base-candle methods agree with each other (cmike↔svopex 35–74 %); the pivot methods
(shved, flux, sdzpro) agree with each other 18–59 %; **base-candle zones and pivot zones are almost disjoint (flux↔cmike/svopex 0–10 %)**
— they are different objects (the base of a move vs the extreme of a move).

How many major BOS/CHoCH legs carry a zone of the tool at their origin (origin..origin+10 bars): flux 43–68 %, sdzpro 40–55 %,
bigbeluga 36–47 %, shved 12–30 %, svopex 7–17 %, cmike 8–15 %. Pivot tools sit at leg origins by construction (a major leg starts at a
swing); the base-candle tools find far fewer of David's legs because his displacement (body ≥ 1.5 × avg body of 10) is rarely preceded
by 1–3 "indecisive" candles on M15/H1 gold.

## 4. What is worth copying, and why

1. **The validity gate must stay David's (BOS by close).** No public tool has it. The closest are SDZ PRO (close beyond the far edge
   = historic) and Flux (close through, confirmed by a second close = breakout / flip). All tools draw 1.4–6 zones per 100 bars; David's
   gate keeps 35–60 % of them and the strict "zone is the start of the breaking leg" keeps 5–25 % (flux 25–51 %). That matches David's
   instruction "do NOT mark every supply / demand".
2. **Freshness as the first class — copy from Svopex / cmike / BigBeluga.** Every base-candle tool treats the first touch as the end of
   the zone's prime (Svopex deletes it; cmike halves the confidence; BigBeluga dashes it). On our bars 70–92 % of zones are touched within
   50 bars, so "fresh" is the scarce, valuable state: `fresh → tested (wick in) → mitigated (close through) → broken`.
3. **Touch count with a cooldown — copy from Shved (10-bar) / Flux (3-bar) / SDZ PRO (edge-triggered).** Shved's classes
   untested → verified (1–3 tests) → proven (>3) are the best-known vocabulary; but Shved tests are *later swing points inside the box*,
   not any wick, which is the sharper definition (a swing that formed in the zone = the zone held). Recommend: a test = a swing (3-bar
   pivot) inside the box, ≥ 3 bars apart. The data: retest-rich classes do NOT predict survival (Flux held % ≈ 55 % everywhere; SDZ PRO's
   formula rewards FEW retests, and that one does predict: strength > 5 → broken 33–57 % vs 74–85 %). Seiden's rule ("fresh is best,
   each test weakens") is what the numbers support, not Shved's "proven".
4. **Turncoat / flip — copy from Shved + Flux**, but with a close: Shved flips on a wick through (the zone keeps living with the other
   role), Flux flips only after two consecutive closes beyond the far edge. On gold M15 wicks through a 1-ATR box are routine (78 of 87
   Shved zones busted), so the Flux rule (confirmed close) is the right one and is the same object as David's "mitigation block" / the OB
   "breaker" already in smc_marks.py.
5. **Box edges — base-body proximal (cmike / ProRealCode) and the base-wick distal (Svopex).** cmike's distal = whole-pattern wick makes
   boxes too tall; Svopex's wick-to-wick of the base (1.0–1.4 ATR here) is the common definition; the proximal at the base's body edge
   (cmike, PRC) is where the entry sits in Seiden's method. For David the zone candle is already fixed (the last opposite candle before
   the displacement = the OB in smc_marks.py); S&D adds the **base** = all consecutive small-body candles (body < 0.5 ATR, ≤ 3, Svopex)
   ending with that candle, box = base wicks, proximal = base body edge.
6. **Do not copy**: BigBeluga's fixed 2×ATR(200) box (height unrelated to the base; 5–6 zones/100 bars, 31–47 % removed by its own overlap
   rule), the LuxAlgo volume-range method (a value area, not a zone), SDZ PRO's forced 1-ATR height (every zone identical), Flux's
   wick-average box (0.3 ATR — spreads and gold wicks eat it; 26–46 % touched vs 70–90 % for the others, i.e. it misses the reaction),
   Shved's merge rule (two untested boxes → "verified").

Difference from the OB already on /smc: the OB is one candle (the last opposite candle before the LAST displacement of a major break).
The S&D method as implemented by every public tool is (a) a **base** of 1–3(6) small-range candles, (b) an **impulse out** measured in
ATR or body/range, (c) **freshness / touch classes** and (d) in Flux/Shved a **flip** rule. With David's rules the S&D layer = base
around his zone candle + his displacement + his BOS gate + fresh/tested/mitigated/flipped status — the genuinely new information versus
the OB is the base extent and the test count, and the comparison says to display *fresh, gated* zones first.

## 5. Port notes / ambiguities (all marked in ports.py)
- MetaTrader `iATR` and Pine `ta.atr` are Wilder RMAs (first value simple mean) — ported as `atr_rma`; `major_structure.atr14` is a simple mean.
- Pine `ta.pivothigh` tie handling is undocumented → strict `>` on both sides; MQL `Fractal()` allows ties on the older side (ported as such).
- Shved: the "10 bars since the previous touch" loop reads the fractal arrays past the zone bar (ported literally, so a touch < 10 bars
  after the zone's own fractal never counts); busted zones are returned with `strength="busted"` only when `include_busted=True`
  (the original draws nothing for them); the port evaluates at the last bar like the indicator's redraw.
- cmike: `timeframeFactor` needs timestamps → 0.5 used (15m ≈ 0.26, 1h ≈ 0.48 in the original); the RR extent uses every candle up to the
  zone end exactly as the JS does (a bug in the original, kept).
- Svopex: 12 per-symbol copies in the script are the same function; one copy ported. `breakPct` default 0 kept (first-touch deletion), 100 tested.
- SDZ PRO: session filter applied with FxPro server time (Europe/Athens); hour ≥ 22 skipped.
- BigBeluga's always-true age gate ported as always true (comment in the code).
