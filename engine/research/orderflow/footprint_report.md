# Order-flow (footprint / cluster) chart — specification research + prototype

Fable 5.1 research agent, 2026-10-29. Research only: nothing under `/home/david/forex` was touched, no MT5 tools, no
Wine. Four sub-agents read the vendor documentation (TradingView + Sierra; ATAS / NinjaTrader / Quantower /
MotiveWave / Bookmap / Jigsaw / Exocharts), the open-source code (flowsurface, openalgo-charts, three Python repos,
Pine scripts, MQL5) and the educator sources; their notes are folded in here (URLs in §8, raw notes in `notes/`,
cloned repos in `oss/`). The prototype `footprint_proto.py` ran on the FxPro GOLD / EURUSD tick sample (§6) and
reproduces every worked example found in the documentation plus the open-source test vectors (§7).

Files (all in `/tmp/claude-1000/-home-david-forex/6f79950b-2f79-4743-8184-d36a070b7e52/scratchpad/of_research/footprint/`)
- `footprint_proto.py` — the prototype (pure Python + numpy, engine conventions)
- `verify_examples.py` — 18 documentation worked examples → all OK
- `compare_oss.py` — prototype vs line-by-line ports of openalgo-charts and OrderFlow-Analysis-Pro → all same
- `run_GOLD.txt`, `run_EURUSD.txt`, `sweep_gold.txt` — run logs (classification = changed-bid tick rule, see §2.2)
- `notes/educators.md`, `oss/` — sub-agent material

---------------------------------------------------------------------------------------------------------------

## 1. What the chart is (all sources agree)

A footprint ("cluster", "numbers bars", "volumetric bars", "volume imprint") is a candle whose price range is cut
into **rows** of equal size; each row holds two numbers, **sell × buy** (= **bid × ask**): the volume that traded
at the bid (aggressive sellers hitting the bid) on the LEFT and the volume that traded at the ask (aggressive
buyers lifting the offer) on the RIGHT. Left = bid/sell, right = ask/buy is unanimous wherever a side is stated
(Sierra "Bid Vol x Ask Vol", Quantower "Sell volume (Bid) on the left side of the bar, and the Buy volume (Ask) on
the right", Jigsaw "Buys on the right x Sells on the left", NinjaTrader example 518 / 989, ATAS "Only the left side
turns red and only the right side turns green", TradingView "sell volume left of candle, buy volume right").

Cell content modes offered by the platforms (ATAS list is the superset): **Bid × Ask** (the default everywhere),
**Delta** (ask − bid per row, one number), **Volume** (bid + ask, one number), Trades, Time, "Centered delta",
"Bid/Ask ladder"; and a **profile** mode in which the cell width is proportional to the row's volume (TradingView
"Profile" vs "Cluster", ATAS "Bid/Ask Profile", NinjaTrader "Show as profile", MotiveWave "Profile"). ATAS
calls "Volume" the "cluster" and "Bid × Ask" the "footprint"; the computations are the same table.

## 2. The exact computations — recommended rules with the sources

Notation: row `P` has `sell[P]` (bid side) and `buy[P]` (ask side); rows are consecutive multiples of the row size.

### 2.1 Rows (price binning)
- **Row size = k × point (tick)**, fixed in price so a price always lands in the same row (Sierra "Volume at Price
  Multiplier", NinjaTrader "Ticks per level, default 1", MotiveWave "Tick Interval", ATAS "Scale", Quantower "Custom
  step, default 1 tick", Pine `request.footprint(ticks_per_row, …)`: "the price range of each row equals the value
  of 100 * syminfo.mintick").
- **Bin rule: `row_index = floor(price_in_points / k)`**, row labelled by its lower edge (`index × k × point`).
  Everyone floors or rounds to a grid; they differ only in the label: Sierra labels a group by its **upper** price,
  flowsurface rounds to the nearest step (half away from zero), openalgo-charts rounds the tick to the nearest row
  centre (half-to-even), the MQL5 footprint blog floors. Recommendation: floor, lower-edge label — same as
  `engine/volume_profile.py`, so the footprint rows and the volume-profile rows coincide when the sizes match.
  Do it in integer points (`np.rint(price / point)`), never in floats: the first float version of the prototype
  put 1.11800 / 0.00002 = 55889.999… into the wrong row.
- **Auto row size.** Two conventions exist: TradingView "Auto = 0.2 × NormalizedATR" (recomputed on symbol /
  timeframe change) and a rows-per-bar target ("3 to 30 ideally" — Simplified Footprint; "roughly 20 to 30 rows on
  a 5-minute bar" — FootprintKit; ATAS "Auto … groups several adjacent levels into one"). Instrument tables from
  educators: NQ / gold futures "4–5 ticks per row", "NQ/ES = 4–8, Gold = 2–4" (GC tick = 0.10 $ → 0.2–0.5 $).
  **Recommended rule (prototype `row_size`): row = median(bar high − low of the timeframe) / 12, rounded to the
  nearest 1-2-5 multiple of the point, never below the point.** On the sample it gives GOLD M5 0.20 $, M15 0.50 $,
  EURUSD M5 0.2 pip, M15 0.5 pip — i.e. 17 rows on the median gold M5 bar (p90 33), 14 on M15, which is inside
  every source's 10–30 window and matches the GC "2–4 ticks" advice. The `volume_profile.row_size` rule (price /
  10,000, 1-2-5) gives 0.5 $ on gold (7 rows per M5 bar) — too coarse for M5, right for M15/M30; keep that rule for
  the profile and this one for the footprint, or let the user pick ticks per row (every platform exposes it).
- **Zoom:** rows merge as the chart zooms out (TradingView "Auto" merges rows, Bookmap "Vertical Smart Scaling …
  tick aggregation", LuxAlgo "Auto"). With floor binning merging two rows = adding the two cells — the browser
  can re-bin from the finest table it was sent.

### 2.2 Side classification (volume source)
Exchange platforms take the aggressor side from the tape (Sierra: "AskVolume is the volume of trades that
occurred at the best Ask price or higher… BidVolume … at the best Bid price or lower. If a trade occurs between
the Bid and Ask … based upon whether the trade is an uptick or a downtick"; flowsurface `Trade.is_sell` straight
from the feed; NinjaTrader "BidAsk" delta type). Without a tape the universal fallback is the **tick rule**:
- MotiveWave: "When the price increases, it is considered an 'Ask Tick' and when it decreases it is considered a
  'Bid Tick'. If the price remains the same, the Bid/Ask Tick is inherited from the previous tick"; "MotiveWave will
  assign a value of 1 to every tick" for forex.
- NinjaTrader "UpDownTick: Accumulates the volume of up ticks vs down ticks"; "Forex instruments are not
  supported with the Delta type Bid Ask"; "Last data is bid data for forex instruments".
- TradingView (footprint and Volume Delta): intrabar close > open → buy, < → sell, equal → compare with the previous
  intrabar close, still equal → inherit.
- openalgo-charts `createTradeClassifier('tickRule')`: `price > last ? 'ask' : price < last ? 'bid' : lastSide`;
  MQL5 footprint blog: flags → `last ≥ ask / ≤ bid` → quote direction with `prevDir`; srl-python-indicators counts
  an unchanged tick on BOTH sides (minority, rejected: it double-counts volume).
**FxPro has no tape** (README: BUY/SELL flags never set, `volume` constant, `last ≈ bid`), so the prototype
estimates the side. Default = the aggressor agent's recommendation (coordinator, 2026-10-29): **the bid tick rule on
CHANGED quotes only** — bid up → 1 buy, bid down → 1 sell, binned at the NEW bid at the chart's row; ticks whose bid
did not change are dropped (no carry-forward; on the sample 65 % of gold ticks and 85 % of EURUSD ticks are
unchanged-bid ticks, mostly ask-only or `last`/volume updates). The MotiveWave / TradingView carry-forward variant
(`classify_tick_rule_bid_carry`) and a mid-price variant are kept; the function is swappable (`classify=`). Every source that mentions spot FX calls this an approximation
("reading bar geometry and calling it order flow" — MQL5 blog; LuxAlgo "Treat delta as feed-dependent";
NinjaTrader and Trader Dale say not to use bid × ask setups on spot FX at all). The chart must say
"estimated from quote ticks" on its face.

### 2.3 Per-bar numbers
| quantity | rule | sources |
|---|---|---|
| **volume** | Σ rows (sell + buy) | all |
| **delta** | Σ buy − Σ sell = Σ row deltas | learn.atas "total contracts at the ask − total at the bid"; NinjaTrader "Sum of all level deltas"; Sierra "AskV − BidV"; Pine `footprint.delta()` |
| **delta %** | 100 × delta / volume | learn.atas, Quantower "Delta / Volume * 100", TradingView "Delta / Volume × 100", NinjaTrader, Sierra "percentage that this volume difference is of the total volume" |
| **max / min delta** | highest / lowest value of the running (tick-by-tick) cumulative delta inside the bar, starting at 0 | Sierra "the maximum value of this difference which existed during the formation of the chart bar"; Linnsoft "highest delta achieved during formation of the bar"; TradingView Volume Delta candle "open is always 0", high/low = extremes; NinjaTrader "Either can be positive or negative"; Bookmap; openalgo tracks per tick |
| **POC** | the row with the largest sell + buy | Sierra "the price point at which the volume is the greatest"; Pine `footprint.poc()` "row that has the largest total volume"; ATAS "Maximum Level"; all |
| POC tie | not documented by any vendor; flowsurface and openalgo take the **higher** price, OrderFlow-Analysis-Pro / MQL5 blog the first found. Recommended: the row nearest the bar's middle, then the lower (= `engine/volume_profile.py`); 5 of 817 gold M5 bars had a tie | code only |
| **value area** | va % of the bar volume grown from the POC **one row at a time**, adding the bigger neighbour (tie → the upper row), **until the area holds ≥ va %** | openalgo `valueArea`, OrderFlow-Analysis-Pro `_compute_value_area`, MotiveWave "centered around the Point of Control", Quantower "70 % by default", Pine `va_percent` "default 70", Exocharts / NinjaTrader profile **68 %** ("one standard deviation") |
| VA stop rule | TradingView's Volume Profile help: "If adding it would exceed the target, stop" (area ≤ target) — TV alone; Sierra/CBOT/ATAS/the two OSS libs stop once ≥ target. Prototype: `va_stop="reach"` (default) / `"never_exceed"` | TV help page vs the rest |
| VA step | `engine/volume_profile.py` uses the CBOT two-row step for the session profile; no footprint platform does per bar → `va_step=1` for the footprint, 2 kept as an option | — |
| **CVD** | cumulative Σ bar delta; **reset at the start of each trading day / session is the default** (TradingView "Session CVD … reset once per day (fixed 1D period)", NinjaTrader "cumulated throughout the session", MotiveWave "reset at the beginning of each session", Exocharts "Session", Sierra "Reset at Start of Trading Day" recommended, ATAS checkbox "Session Delta Mode"); "no reset" is offered everywhere for swing use (ATAS "uses all the data loaded in the chart", Exocharts "Full data", Linnsoft "Cum Delta - All") | — |
| CVD drawing | candles: open = previous close (0 after a reset), high / low = previous close + max / min delta of the bar, close = previous close + delta (Sierra Cumulative Delta Bars, TradingView CVD, NinjaTrader) | Sierra ID 292, TV 43000725058 |

FxPro's day is the server day (00:00 EET, 24 h session) → `cvd_reset="day"` = the session reset; §2 of
`volume_profile.py` already uses the same day boundary.

### 2.4 Imbalances
- **Diagonal, unanimous.** Buy (ask) imbalance at row P: `buy[P]` vs `sell[P − 1 row]`; sell (bid) imbalance at P:
  `sell[P]` vs `buy[P + 1 row]`. Sierra: "the Bid Volume at one price level is compared diagonally to the Ask
  Volume at the next higher price level. And the Ask Volume is compared to the Bid Volume at the next lower price
  level"; TradingView "buy volume at a price level exceeds the sell volume at the level below"; Pine docs; ATAS
  "a bid is compared with an ask, which is one level higher"; NinjaTrader example "Buy volume of 518 is compared
  to the diagonal below sell volume of 989"; MotiveWave glossary; Exocharts "Buys are compared diagonally down-left;
  sells are compared diagonally up-right"; flowsurface, openalgo, the JOAT Pine script, the MQL5 blog. Reason given
  (learn.atas, LuxAlgo, Jigsaw): the two cells are the two sides of the spread at the moment of the trade — buyers
  lift the offer at P while sellers hit the bid one tick below. Horizontal (same row) exists as an option in
  NinjaTrader (8.0.19+), Bookmap ("Horizontal Delta") and in OrderFlow-Analysis-Pro's code; Jigsaw warns it is
  wrong. **Recommendation: diagonal.**
- **Edges:** the top row's bid and the bottom row's ask have nothing to compare with and are never imbalances
  (Sierra "the highest Bid Volume and lowest Ask Volume are never dominant because there is nothing to compare
  against"; openalgo test "does not compare the rows beyond the bar high and low").
- **Ratio.** `dominant ≥ ratio × opposite`. Published defaults: TradingView **300 %**, Pine `imbalance_percent`
  "default is 300", openalgo-charts 3, JOAT Pine 3.0, Volume Footprint Simplifyed 300 %, flowsurface
  `THRESHOLD_PERCENT = 200` meaning qty > 3 × (same thing), MQL5 blog "typically 3×"; educators "300 % (3:1)" (LuxAlgo,
  NinjaTrader blog, damnpropfirms, Trader Dale), "250–400 recommended" (Exocharts), "200–300" (Quantower),
  "200 % and 400 % thresholds are standard" (learn.atas). Outliers: ATAS platform default **150 %**, NinjaTrader
  Volumetric **1.5** (both need their own extra filters), Sierra none (its how-to uses 4 = 400 %). **Recommendation:
  3.0 (300 %)** — the majority and every open-source default. Note the arithmetic: TradingView / ATAS / Exocharts
  mean "3 times the other side" (300 % = ×3), NOT "300 % more".
- **≥ vs >.** TradingView "max(buy, sell) ≥ (percentage / 100) × min(buy, sell)" (≥), openalgo `>=`, ATAS "must
  exceed" (>, their 350 % example: ask 30 → bid must exceed 105), flowsurface `>`, Sierra "larger value" (>). Only
  matters at exactly 3×; prototype `strict=False` (≥) default, `strict=True` reproduces ATAS / Sierra / flowsurface.
- **Minimum volume.** Sierra "Bid/Ask Minimum Volume Compare Threshold … default 0" (both compared values below it →
  no compare); Jigsaw "Minimum Imbalance Volume"; ATAS "Volume Filter" + "Minimum Difference"; NinjaTrader
  "Minimum delta for imbalance, default 10" (a minimum *difference*); openalgo `threshold` = minimum dominant
  quantity, default 0; LuxAlgo "a minimum-volume filter so near-empty levels cannot trigger flags"; educators
  "50–100 contracts" on futures. **Recommendation: a minimum on the dominant cell**, expressed for tick-count data as
  a share of the bar's volume (§6: 1 % of the bar ≈ 35 ticks on gold M5 cuts the imbalance share from 17 % of the
  cells to 12 %, 2 % → 9 %); prototype parameter `min_vol` (absolute; the caller computes it from the bar volume).
- **Zeros.** Sierra default: a zero denominator → "no comparison will be performed" (opt-in "Zeros as Ones" or
  "±1000 %"); flowsurface `IGNORE_ZEROS = true`; ATAS "Ignore Zero Values" and Exocharts "Imbalance ignore zeros"
  options; TradingView documents nothing (300 × 0 = 0, so any positive cell beside a zero would pass); openalgo and
  OrderFlow-Analysis-Pro count positive-vs-zero as an imbalance (openalgo: only when the empty row is *inside* the
  bar range). **Recommendation: `zero_rule="skip"`** (no comparison when the opposite cell is 0) — the Sierra /
  flowsurface default and the safe choice on estimated data, where zeros at thin edges are common; `"count"` is the
  openalgo behaviour (needed to reproduce its tests).
- **Stacked imbalances:** ≥ `stack` consecutive rows with an imbalance on the same side. Default **3** everywhere a
  number is given (ATAS indicator "3 neighbouring price levels as it is set by default", openalgo `minStack 3`,
  LuxAlgo "default 3", Trader Dale, therighttrader, l4z0r, damnpropfirms, MQL5 blog "3 or more", Sierra's example
  3); JOAT Pine uses 4; TradingView / Exocharts / Quantower leave it unstated. A gap (an untraded row) breaks the
  run (openalgo test "breaks stacks across gaps"). The zone = the band from the lowest to the highest stacked row
  (therighttrader "Mark the whole zone"), drawn as a rectangle extended to the right (ATAS, TradingView "projects
  stacked imbalances until subsequent prices intersect the levels", LuxAlgo "extend right until price trades back
  into it", ATAS users: lines vanish on first touch). **Invalidation: nobody requires a close** — "trades back into
  it" (LuxAlgo, mmt.gg, TradingView "intersect"), "accepts through the far side" (therighttrader). Recommendation
  for the SMC page, consistent with its OB / FVG statuses: `fresh → touched` (a wick into the zone) → `broken`
  (a close beyond the far edge); the prototype keeps both the touch count and the break.
- **Unfinished auction** (ATAS "unfinished auction", Trader Dale "failed auction", Footprint Classic "tops or
  bottoms traded both ways", Sierra "Highlight Nonzero Bid&Ask Volume at High/Low"): at the bar's high, bid AND ask
  both non-zero → unfinished; a 0 on the bid at the high (0 on the ask at the low) → finished (learn.atas "a zero at
  the edge means a finished auction"; Axia finished example "122×0"; openalgo `highBid > 0 && highAsk > 0`). It is
  marked with a line until price revisits the level (ATAS, Sierra extension line, LuxAlgo "Extend until revisited";
  openalgo ends it at the first later bar whose high > price / low < price). Exocharts does not document it.
  **Caveat for FxPro data (§6): with the bid tick rule the flag is degenerate** — at point resolution the top price
  can only ever receive up-ticks (0/817 unfinished), and with wider rows it merely counts within-row reversals
  (76 % of the gold M5 bars "unfinished" at 0.2 $). Keep the field, compute it at point resolution from a
  classification that can put both sides on one price (the other agent's quote-based method), or hide it.

### 2.5 Delta footprint, volume footprint, profile-in-bar
- **Delta footprint:** one number per row, `buy[P] − sell[P]` (TradingView "Delta" type, ATAS "Delta", NinjaTrader
  "Delta" style, Bookmap "Horizontal Delta"); Sierra also offers the **diagonal** per-row delta `buy[P] − sell[P−1]`
  ("Ask Side Diagonal Difference"), Bookmap "Diagonal delta". Colour by sign, intensity by |value|.
- **Volume footprint:** `buy[P] + sell[P]` per row (TradingView "Total", ATAS "Volume" = the classic cluster).
- **Profile in bar:** the same rows drawn as horizontal bars whose width ∝ volume, optionally split into the
  sell / buy segments (TradingView "Profile": "proportional to the trading volume at that level"; LuxAlgo "Volume
  Profile mode shows total volume per row, split into buy/sell segments"; NinjaTrader "Show as profile"). Width
  normalisation: per bar (flowsurface `Datapoint`), per visible range (`VisibleRange`), or a 0.2 / 0.8 blend
  (`Hybrid`); ATAS "Proportion mode: Bars / Visible Area / Whole Chart".

## 3. Rendering conventions (defaults for a browser canvas)
- **Text:** `sell x buy` per row, bid left of the candle axis, ask right (Sierra separators "x, |, space, or two
  spaces"); integers; abbreviate ≥ 10,000 as "12.3k" (Sierra "Use Large Volume Number Formatting", Exocharts
  "Short numbers (1.25M)"). Hide the text when a row is shorter than the font (Exocharts "Min. cluster height to
  show text", Bookmap "font size falls below 7 … not displayed", ATAS "Width to Show Text") — then show only colour.
- **Cell colour (default = by delta):** green shade for buy > sell, red for sell > buy, intensity ∝ |row delta|
  relative to the bar's max (ATAS "Delta" scheme, NinjaTrader "Strength sensitivity 20", TradingView four-step
  gradient: ratio (v − min)/(max − min) < 0.25 / 0.5 / 0.75 / ≥ 0.75, buy and sell gradiented separately).
  Alternatives: by volume heat-map (ATAS "Heatmap by Volume" with an upper cut-off, e.g. the top 5 % get the
  strongest colour), by bid/ask proportion.
- **Imbalance:** highlight only the dominant number — buy imbalance = the ask number (right) in bright green /
  cyan, sell imbalance = the bid number (left) in bright red / magenta (ATAS "Only the left side turns red and only
  the right side turns green", NinjaTrader cyan / magenta, Exocharts bordered box, TradingView a vertical line
  beside the level; Jigsaw yellow). Stacked zone: a translucent rectangle from the lowest to the highest stacked
  row, extended right until broken; dotted after a touch.
- **POC:** a rectangle around the row (Sierra "drawing a rectangle around the price level", ATAS "Maximum Level"
  border, Exocharts "POC border width", LuxAlgo outline) — if a cell is both an imbalance and the POC, show the
  POC (NinjaTrader: "If a cell qualifies as both imbalance and maximum, the maximum is displayed").
- **Value area:** VAH / VAL ticks or a faint fill (TradingView "VAH line above all levels included", MotiveWave
  "Range Fill").
- **Unfinished auction:** a short horizontal line from the bar's extreme to the right until revisited (ATAS, Sierra
  "Column 1 with extension line").
- **Panes below the chart:** (1) **delta per bar** as columns, green / red (ATAS Delta indicator; TradingView
  "Table" row Delta); optional max / min delta as thin wicks on the column (TradingView Volume Delta candle: open 0,
  high = max delta, low = min delta, close = delta); (2) **CVD** as a line or as candles (open = previous close,
  wicks = max / min, NinjaTrader "Candle body outline / wick"), reset at the day boundary (a tick mark where it
  resets); (3) a stats strip: volume, delta, delta %, max / min delta, POC, CVD (TradingView "Info box"; ATAS
  "Cluster Statistic"; Exocharts FPBS rows; Sierra "Calculated Values").
- **Zoomed out:** switch to plain candles when a bar is narrower than ~ 60 px (ATAS "When the chart is zoomed
  out, Footprint charts automatically switch to Candles mode" — setting "Auto Transform Candles to Clusters";
  LuxAlgo "cross-fades to plain candles"); in between, hide text and keep the coloured cells / profile bars
  (NinjaTrader "Hide text … imbalances and maximums as cell border colours"). Merge rows (add cells) when a row is
  shorter than ~ 10 px (Bookmap tick aggregation on vertical zoom, TradingView "Auto" row size).
- **Alignment:** footprint text to the left and right of a thin candle (open–close bar in the middle: NinjaTrader
  "Center open close bar", ATAS "Full Row" / "Bid/Ask Ladder"); profile mode drawn inside the candle box.

## 4. Where the sources disagree — and the choice made
| topic | positions | choice |
|---|---|---|
| imbalance ratio default | 300 % (TV, Pine, OSS, educators) vs ATAS 150 % / NinjaTrader 1.5 vs Sierra none (4 in how-to) | **3.0**; ratio is a user setting (2–4 sensible) |
| ≥ or > | TV / openalgo ≥; ATAS / Sierra / flowsurface > | ≥ (`strict` flag available) |
| zero opposite cell | Sierra / flowsurface skip (default); ATAS / Exocharts option; openalgo / OF-Analysis-Pro count; TV silent | **skip** |
| min-volume filter | Sierra min of both; Jigsaw / openalgo min dominant; NinjaTrader min difference 10; ATAS both | min dominant cell, ≈ 1 % of bar volume on tick data |
| stacked count | 3 (ATAS, openalgo, LuxAlgo, educators) vs 4 (JOAT) | **3** |
| stacked zone invalidation | trade-through (LuxAlgo, TV, mmt.gg, ATAS users) vs "accepts through" | touched on a wick, broken on a close through (matches the page's OB / FVG) |
| value area % | 70 (Pine, Quantower, MotiveWave, TV, openalgo) vs 68 (Exocharts, NinjaTrader profile, OF-Analysis-Pro) | **70** |
| VA stop rule | reach ≥ target (Sierra, CBOT, ATAS, both OSS) vs never exceed (TV VP help) | reach (option kept) |
| VA step | 1 row (all footprint tools) vs 2 rows (CBOT, engine volume_profile for the session profile) | 1 for the bar, 2 stays for the session profile |
| POC tie | higher price (flowsurface, openalgo) vs first found | nearest the middle, then lower (engine rule; 0.6 % of bars) |
| row label | lower edge (floor: MQL5, engine) vs upper (Sierra VAP multiplier) vs centre (openalgo, flowsurface) | lower edge |
| auto row size | 0.2 × ATR (TV) vs 10–30 rows per bar target | median range / 12 → 1-2-5 (both land near 0.2–0.5 $ on gold) |
| CVD reset | session / day default (TV, NT, MotiveWave, Exocharts, Sierra) vs never (ATAS unchecked) | day (= FxPro session); "none" switchable |
| unchanged tick | inherit (MotiveWave, TV, openalgo, MQL5) vs BUY (OF-Analysis-Pro) vs both (srl) | inherit |
| unfinished auction | both non-zero at the extreme (ATAS learn, Sierra, openalgo, Trader Dale) vs "bid trades at the high" (ATAS blog) — same condition | both non-zero; degenerate under the bid tick rule (§6) |

## 5. Recommended spec (deterministic)
```
inputs   ticks (t_ms server, bid, ask), tf_ms, point, row_pts (int ≥ 1; auto = round125(median bar range / 12) / point)
         classify(ticks) → +1 / −1 / 0           (default: sign(Δbid); 0 = unchanged bid, dropped; swappable)
         ratio = 3.0, min_vol (≈ 1 % of the bar's volume), zero_rule = skip, stack = 3,
         va_pct = 0.70, va_step = 1, va_stop = reach, cvd_reset = day
bars     bar = ticks with the same floor(t / tf_ms); ticks with side 0 are dropped
rows     r = rint(bid / point) // row_pts; price label = r × row_pts × point; sell[r] += 1 if side < 0 else buy[r] += 1
         (every row between the bar's lowest and highest traded row exists, empty ones as 0 x 0)
per bar  volume = Σ(sell + buy); delta = Σbuy − Σsell; delta_pct = 100 delta / volume
         max_delta / min_delta = max / min of cumsum(side) within the bar (≥ 0 / ≤ 0)
         poc = argmax(sell + buy) (tie: nearest the middle row, then lower)
         VA: from poc, add the bigger neighbour row (tie: upper) until Σ ≥ va_pct × volume → val, vah
         imb_buy[r]  = buy[r] ≥ min_vol and sell[r−1] > 0 and buy[r] ≥ ratio × sell[r−1]      (r > lowest row)
         imb_sell[r] = sell[r] ≥ min_vol and buy[r+1] > 0 and sell[r] ≥ ratio × buy[r+1]      (r < highest row)
         stacked_* = maximal runs of ≥ stack consecutive imb rows (an empty row breaks a run) → zone [low row, high row + 1 row)
         unfinished_high = sell[top] > 0 and buy[top] > 0 ; unfinished_low likewise at the bottom row
across   cvd[i] = cvd[i−1] + delta[i], = delta[i] on the first bar of a server day
         zones: fresh → touched (a later bar's wick enters) → broken (a later bar closes beyond the far edge)
```
Everything above is what `footprint_proto.footprint()` does; `analyze_table()` applies the per-bar part to a
`{price: (sell, buy)}` table (documentation examples, unit tests, or a table re-binned in the browser).

## 6. Prototype on the FxPro sample
`python3 footprint_proto.py GOLD | EURUSD` (logs `run_GOLD.txt`, `run_EURUSD.txt`; numpy 2.5, no pandas).

| | GOLD M5 | GOLD M15 | EURUSD M5 | EURUSD M15 |
|---|---|---|---|---|
| ticks (3 days) | 2,822,368 (load 3.0 s) | — | 1,297,581 (load 1.5 s) | — |
| changed-bid tick rule | buy 483,385 / sell 492,097 / dropped 1,846,886 | | buy 95,212 / sell 95,688 / dropped 1,106,681 | |
| median bar range | 3.13 $ | 5.47 $ | 2.3 pips | 4.2 pips |
| row (range / 12 → 1-2-5) | **0.20 $** | **0.50 $** | **0.2 pip** | **0.5 pip** |
| bars / cells / rows per bar | 817 / 16,176 / 19.8 (median 17, p90 33, max 130) | 273 / 3,879 / 14.2 | 853 / 12,991 / 15.2 | 285 / 3,198 / 11.2 |
| `footprint()` time | 0.34 s | 0.21 s | 0.16 s | 0.08 s |
| internal checks | all True | all True | all True | all True |
| imbalances (ratio 3, no min) | 16.5 % of cells, 14 stacked zones | 20.3 %, 5 | 11.6 %, 2 | 18.3 %, 2 |
| imbalances (ratio 3, min_vol 10) | 13.1 %, 2 zones | 20.0 %, 4 | 3.4 %, 0 | 15.5 %, 0 |
| counted ticks per bar | median 1,152 (p10 637, p90 1,785) | | | |
| delta % per bar | median 4.0 %, p90 10.4 %, max 21.2 % (absolute) | | | |
| delta sign = candle direction | 65 % of bars | | | |
| POC ties | 9 of 817 bars | | | |

Internal checks (`check()`): Σ rows = volume; delta = Σ buy − Σ sell; the bar's bid low / high fall inside the
lowest / highest row; POC inside the VA; min_delta ≤ min(0, delta) ≤ max(0, delta) ≤ max_delta; CVD = Σ delta with
the day reset — all True on all four runs (the first float-binned version failed the row check on EURUSD; fixed
by integer points). A row with volume on one side only is common at the bar edges; empty rows inside a bar are
1.1 % of the cells at 0.2 $.

Sensitivity (`sweep_gold.txt`, gold M5, row 0.2, changed-bid rule): ratio 2 → 32 % of cells imbalanced (129
zones), 2.5 → 22 % (40), **3 → 16.5 % (14)**, 4 → 10 % (1); with min_vol 10: 26 / 18 / 13 / 8 %; horizontal
comparison at 3 → 1.2 %. min_vol as a share of the bar's volume: 0.5 % → 14 %, **1 % → 12 % (1 zone)**, 2 % → 8 %,
3 % → 6 %. On tick-rule data a one-way sweep is all buys row after row, so diagonal imbalances fire far more than
on a tape (where passive fills balance the rows) — hence the recommendation of a volume floor (and the
user-settable ratio); stacked zones are rare (≈ 1 per 60–400 gold M5 bars at ratio 3 with a floor). Unfinished
auction by row size: 0.01 → 0 %, 0.05 → 36 %, 0.2 → 76 %, 0.5 → 89 % of bars — the flag measures the row width,
not the auction (§2.4). The carry-forward variant gave nearly the same picture (17.4 % / 22 zones; 76 % unfinished),
with 3× the counted volume per bar.

Example bars (text renderer: price | sell x buy; `*` POC, `|` value area, `<` sell imbalance, `>` buy imbalance;
min_vol 5, ratio 3; server time; counts = changed-bid ticks):
```
2026-10-27 03:40 server  O 4016.5 H 4017.63 L 4014.52 C 4016.43  vol 1543  delta +17 (+1 %)  max +27 min -80  POC 4016.2  VA 4015.4–4016.8  unfinished low
      4017.6         0 x 1
      4017.4         3 x 3
      4017.2         4 x 6
        4017   <    30 x 54
      4016.8 |      74 x 97
      4016.6 |      51 x 44
      4016.4 |      40 x 70
      4016.2 *      99 x 112
        4016 |      85 x 76
      4015.8 |      93 x 95
      4015.6 |      82 x 71
      4015.4 |      76 x 53
      4015.2        27 x 16
        4015        35 x 36
      4014.8        50 x 38
      4014.6        13 x 7     >
      4014.4         1 x 1
```
(`<` at 4017: sell 30 ≥ 3 × buy 6 one row up; `>` at 4014.6: buy 7 ≥ 3 × sell 1 one row down; the top row 0 x 1
is a finished high in the classic reading — only up-ticks reached 4017.6 — the bottom row 1 x 1 "unfinished".)
```
2026-10-27 03:15 server  O 4013.2 H 4013.64 L 4006.73 C 4006.92  vol 1481  delta -161 (-11 %)  max +1 min -161  POC 4009.4  VA 4007.2–4010.0  unfinished low
      4013.6         0 x 1
      4013.4   <     9 x 12
        ...
      4010.6   <    13 x 10    >
      4010.4         1 x 2
      4010.2   <     6 x 3
        4010 | <    17 x 9
      4009.8 | <    28 x 25
      4009.6 |      34 x 30
      4009.4 *      64 x 69
      4009.2 |      51 x 39
        ...
      4007.2 | <     8 x 10
        4007        18 x 7
      4006.8         7 x 3
      4006.6         1 x 1
  stacked buy []  stacked sell [(4009.8, 4010.2)]
```
(a −11 % down-bar; the stacked sell zone 4009.8–4010.4 is three bid cells each ≥ 3 × the ask one row up: 28 vs 9,
17 vs 3, 6 vs 2 — sellers hitting the bid through 4010 with no lifting above; the zone is carried forward until a
later bar closes above 4010.4.)
The full text of both runs (every bar's header line and the two example bars each) is in `run_GOLD.txt` /
`run_EURUSD.txt`.

## 7. Verification
(a) **Internal** — §6, all checks True on GOLD / EURUSD × M5 / M15.

(b) **Documentation worked examples** (`verify_examples.py`, 18 checks, all OK):
- Sierra Numbers Bars "Diagonal Dominant Side" table (Bid|Ask top→bottom A 0|56, B 293|359, C 48|532, D 1008|830,
  E 682|452, F 16|0): doc says bid-dominant B, D; ask-dominant B, D, E; A's bid and F's ask uncompared → prototype
  (`ratio=1, strict`) gives exactly that.
- Sierra "Ask Volume Bid Volume Difference Per Tick" −83.33; Sierra VAP Threshold Alert ask 100 / bid 50 = 200 %
  (fires at threshold 200, not 201).
- TradingView help: "506.37 ('buy') ≥ (300 / 100) × 166.433 ('sell')" → buy imbalance at level 3 (and 499 does not).
- TradingView Volume Profile VA algorithm (never exceed, tie → closer / above) and the Sierra / ATAS "reach" rule
  on the same 6-row profile: 2–3 (68 %) vs 2–4 (82 %); tie → upper row first.
- NinjaTrader Volumetric doc: 740 − 220 = 520; "989 / 518 = 1.9092" > 1.5 → sell imbalance; bar 3463 − 4535 = −1072.
- ATAS blog 300 % example (116/26, 86/8, 58/18, 64/15, 218/67, 190/49) → six bid imbalances, one stacked sell zone;
  ATAS cluster-settings "ask 30 at 350 % → bid must exceed 105" (105 no, 106 yes with `strict`).
- flowsurface `exceeds_diagonal_threshold` (200 % = strictly > 3×): 300 vs 100 no, 301 yes.
- learn.atas unfinished auction (both non-zero at the high); 3-row stacked buy zone.

(c) **Open-source implementations** (`compare_oss.py`): the auto-mode sandbox refused to execute the cloned
repositories (external code), so their functions were **ported line by line** into the comparison script
(openalgo-charts `diagonalImbalances`, `stackedImbalances`, `valueArea`; OrderFlow-Analysis-Pro
`imbalance_levels`, `_compute_value_area`) and run on nine toy tables, including openalgo's own unit-test vectors
("keeps both buy and sell flags on a row when forming a stack" → stack 4..2 + sell flag at 4; "breaks stacks across
gaps" → 6..4 only; "untraded row inside the bar compared with zero" → buy 4, sell 2; "rows beyond the high and low
are not compared" → none). Prototype (with `zero_rule="count"` to match openalgo) = openalgo port on every case,
and the three value-area implementations agree (VAL 2, POC 3, VAH 4; tie → upper). OrderFlow-Analysis-Pro's
horizontal rule is printed beside them to show how different a same-row comparison is (e.g. Sierra's table: six
flags instead of five, on other rows). If David allows it, `cd oss/openalgo-charts && npm install && npx vitest run
tests/footprint-data.test.ts` runs the original tests (node 24 is installed).

## 8. Sources
TradingView: Volume Footprint chart https://www.tradingview.com/support/solutions/43000726164-volume-footprint-chart ;
Volume Profile (VA algorithm) https://www.tradingview.com/support/solutions/43000502040-volume-profile/ ; Volume
Delta https://www.tradingview.com/support/solutions/43000725057 ; Cumulative Volume Delta
https://www.tradingview.com/support/solutions/43000725058-cumulative-volume-delta ; Pine v6 `request.footprint()`
https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/ , type system (footprint /
volume_row) https://www.tradingview.com/pine-script-docs/language/type-system/ , release notes Jan 2026
https://www.tradingview.com/pine-script-docs/release-notes/ ; scripts: FootprintKit
https://www.tradingview.com/script/c7gwEeFB-FootprintKit/ , Simplified Footprint
https://www.tradingview.com/script/kszclif5-Simplified-Footprint/ , Order Flow Footprint [JOAT]
https://www.tradingview.com/script/3QFpGbCR , Volume Footprint Simplifyed https://www.tradingview.com/script/n807k0fu ,
LuxAlgo Volume Footprint https://www.tradingview.com/script/cdU6E9rm .
Sierra Chart: Numbers Bars https://www.sierrachart.com/index.php?page=doc/NumbersBars.php ; Volume At Price
Threshold Alert V2 https://www.sierrachart.com/index.php?page=doc/StudiesReference.php&ID=386 ; Cumulative Delta
Bars https://www.sierrachart.com/index.php?page=doc/StudiesReference.php&ID=292 ; Volume Value Area Lines
https://www.sierrachart.com/index.php?page=doc/StudiesReference.php&ID=209 ; Chart Settings (VAP multiplier)
https://www.sierrachart.com/index.php?page=doc/ChartSettings.html .
ATAS: Cluster settings https://help.atas.net/en/support/solutions/articles/72000606631 ; zoom → candles
https://help.atas.net/en/support/solutions/articles/72000602349 ; scale
https://start.atas.net/step-2.-explore-your-workspace/chart-settings ; imbalance blog
https://atas.net/blog/how-to-find-and-trade-imbalance/ ; learn.atas imbalances
https://learn.atas.net/volume-basics/volume-analysis/imbalances , patterns
https://learn.atas.net/volume-basics/volume-analysis/footprint-patterns , delta
https://learn.atas.net/volume-basics/volume-analysis/reading-footprint-delta ; unfinished auction
https://atas.net/atas-possibilities/indicators/unfinished-auction-what-it-is-and-how-to-trade-it ; stacked
imbalance indicator https://atas.net/atas-possibilities/getting-acquainted-with-atas-advantages-of-working-with-indicators ;
cluster statistic https://atas.net/blog/cluster-statistic-basics/ ; CVD https://atas.net/blog/cumulative-delta-analysis/ ;
basics https://atas.net/blog/basicos-de-footprint/ .
NinjaTrader 8: Volumetric bars https://static.ninjatrader.com/support/helpGuides/nt8/order_flow_volumetric_bars.htm ;
Cumulative Delta https://static.ninjatrader.com/support/helpGuides/nt8/order_flow_cumulative_delta.htm ; Volume
Profile https://static.ninjatrader.com/support/helpGuides/nt8/order_flow_volume_profile.htm ; footprint guide
https://ninjatrader.com/futures/blogs/footprint-charts-guide/ .
Quantower: cluster chart https://help.quantower.com/quantower/analytics-panels/chart/volume-analysis-tools/cluster-chart ;
volume profiles https://help.quantower.com/quantower/analytics-panels/chart/volume-analysis-tools/volume-profiles.md ;
imbalance blog https://www.quantower.com/blog/imbalance-footprint-chart-and-rithmic-plugin .
MotiveWave: Volume Imprint https://docs.motivewave.com/guides/volume-order-flow-analysis-guide/volume-imprint ;
Volume Analysis guide v6 (PDF) https://www.motivewave.com/guides/MotiveWave_Volume_Analysis_Version_6.pdf ; forex
tick rule https://docs.motivewave.com/knowledge-base/study/forex-with-volume-related-studies .
Bookmap: Footprint add-on https://bookmap.com/knowledgebase/docs/Addons-Footprint ; CVD
https://bookmap.com/knowledgebase/docs/KB-Indicators-CVD ; Imbalance indicator
https://bookmap.com/knowledgebase/docs/KB-Indicators-Imbalance . Jigsaw: JT FootPrint
https://daytradr.jigsawtrading.com/jt-footprint.html ; blog https://www.jigsawtrading.com/blog/footprint-charts .
Exocharts: chart & cluster settings https://help.exocharts.com/hc/en-us/articles/50662221262353-Chart-and-Cluster-Settings ;
VA / POC / imbalance https://help.exocharts.com/hc/en-us/articles/4408108187537 ; imbalance text
https://help.exocharts.com/hc/en-us/articles/48802532393489 ; stacked
https://help.exocharts.com/hc/en-us/articles/48802486842257 ; FPBS https://help.exocharts.com/hc/en-us/sections/4408065926801 .
Linnsoft bar statistics https://www.linnsoft.com/techind/bar-statistics .
Open source: flowsurface (Rust, GPL-3) https://github.com/akenshaw/flowsurface — `data/src/chart/kline/footprint.rs`
(binning, POC), `src/widget/chart/kline/footprint.rs` (`exceeds_diagonal_threshold`), `data/src/chart/kline.rs`
(THRESHOLD_PERCENT 200, IGNORE_ZEROS), `data/src/chart/kline/poc.rs` (naked POC); openalgo-charts (TS, Apache-2)
https://github.com/marketcalls/openalgo-charts — `src/profile/footprint.ts`, `footprint-classify.ts`,
`footprint-signals.ts`, `profile-model.ts`, `tests/footprint-data.test.ts`; OrderFlow-Analysis-Pro (Python, MIT)
https://github.com/mahmoud20138/OrderFlow-Analysis-Pro — `orderflow_system/analytics/footprint.py`,
`volume_profile.py`, `data/mt5_feed.py`; srl-python-indicators https://github.com/srlcarlg/srl-python-indicators ;
OrderflowChart https://github.com/murtazayusuf/OrderflowChart ; CSharp-NT8-OrderFlowKit
https://github.com/gbzenobi/CSharp-NT8-OrderFlowKit . MQL5: "Building a Footprint Chart in MQL5"
https://www.mql5.com/en/blogs/post/774467 ; tick volume blog https://www.mql5.com/en/blogs/post/777201 ; delta
article https://www.mql5.com/en/articles/3708 ; CodeBase Footprint XRay https://www.mql5.com/en/code/75210 .
Educators: LuxAlgo bid-ask imbalance https://www.luxalgo.com/library/concept/bid-ask-imbalance.md , footprint docs
https://docs.luxalgo.com/llms.mdx/docs/charts/order-flow/footprint/content.md , volume delta
https://www.luxalgo.com/library/concept/volume-delta.md ; Trader Dale imbalances
https://www.trader-dale.com/the-most-powerful-order-flow-imbalance-setups-full-training-9-dec-25/ , failed auction
https://www.trader-dale.com/order-flow-failed-auction-a-simple-guide-for-beginners/ ; therighttrader
https://therighttrader.com/learn/volume-and-order-flow/stacked-imbalances ; damnpropfirms
https://damnpropfirms.com/trading-guides/spot-volume-clusters-footprint-charts/ ; mmt.gg https://mmt.gg/learn/footprint ;
l4z0r https://l4z0r.substack.com/p/the-daytraders-toolbox-introduction-to-bid-x-ask-split-footprint-candles-f41502939ee6 ;
Axia https://axiafutures.com/blog/how-to-create-sierra-chart-footprint/ ; ProRealCode CVD reset
https://www.prorealcode.com/prorealtime-indicators/trend-reset-cumulative-delta/ ; traderspost Pine footprint
https://blog.traderspost.io/article/pine-script-footprint-requests .
Not reachable: Volfix help (403), Exocharts HTML (403, read via its Zendesk API), ATAS "Stacked Imbalance" help
article (JS-only body), MQL5Book IndDeltaVolume (404), Vandoriz MT5 footprint engine (404).
