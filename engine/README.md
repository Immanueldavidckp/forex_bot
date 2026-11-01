# V5 engine (code only, MT5)

David's "MT5 EA — COMPLETE FINAL STRATEGY LOGIC V5" as an engine: no Claude agents, the code picks, enters
and manages. Built 2026-10-24 from a copy of the trading app's intraday engine; its analysis tools
(`tools/`) are reused, the NSE parts are archived in `../engine_data/intraday_copy_archive/`.

```
picker    H4 + H1 bias computed for the cards, but M15 / M30 entries do NOT need it (bias_exempt_tfs,
          David 2026-10-25 evening) — they trade on their own timeframe's structure; the G4 gate passes
          on those TFs and only logs the bias values
          → BOS on the setup's timeframe: a candle CLOSES beyond the last HH (buy) / LL (sell)   (David 2026-10-24)
          → in the BOS move (its start → the BOS candle): supply / demand = final opposite candle before
            a displacement ≥ 1.5 × the 10-bar average body; with none, the mitigation block
          → the FVGs of that move (required; new rules 2026-10-25: they are ONE cluster, the nearest is the trigger)
          → entry when price comes back 10 % into that FVG (seen live, never late)
          every timeframe H4 / H1 / M30 / M15 / M5 is analysed and drawn; only ENGINE["trade_tfs"] may enter
          three entries (David 2026-10-25): S&D M15 and S&D M30 = the setup above on that timeframe;
          S&D H4 = price back at an H4 setup's entry → an M15 BOS or CHoCH the same way whose move starts inside
            the H4 zone (H4 entry ↔ H4 invalidation) → that M15 move's own zone + FVG → entry 10 % inside it
            (an M15 trade: SL = its M15 zone); the H4 zone ends at an M15 close beyond its invalidation, a newer
            H4 BOS setup, 192 M15 bars, or once one of its entries is taken
executor  normal at market 2.5 % risk, SL = this setup's own zone (supply high / demand low) + 20 points,
          TP = first untouched opposite structure (setup TF / H1 / H4 swing) ≥ 1:3
          SL/TP fix (David 2026-10-24), checked right before the order, any NO → no trade, nothing moved to pass:
          BOS / zone / FVG all of this one setup, SL on the right side and ≤ 3 × M15 ATR(14),
          a real structure target on the right side (none → no trade, never a made-up 3R), RR ≥ 3, < 20 positions
          + ONE dynamic layer (pending limit, 1.5 %) at 25 / 40 / 55 % of entry→SL by movement strength
monitor   Mode A: original SL until ≥ 80 % of the way to TP and a reversal → break-even
          Mode B (layer filled): Target 1 = centre → both SLs past the first entry, then M5-swing trailing
          from 3R: lock (n − 2)R at nR + M5-swing trailing; a stop only moves toward profit
limits    ≤ 20 open positions (pending layers reserve their slot), no daily trade limit
```

Dashboard (David 2026-10-25): every card shows the three entries — **S&D H4**, **S&D M30**, **S&D M15** — each on
the chart its entry is taken on (S&D H4 = M15 with the H4 zones on it). Click one: its two timeframes (S&D H4: H4 zones
+ M15 entry; S&D M30 / M15: H4 for the bias only + that timeframe) and every mark on / off — only that entry
(remembered in the browser). Setups superseded by a newer BOS setup, and refused ones, are not drawn (David 2026-10-25). The big chart's header carries the current setup's rule check in order — "now: structure ✓ (BOS ↑/↓) · FVG ✓ (n of m) · waiting: …" (on the S&D H4 chart, "H4 zone ✓" first) — in place of the old grey hidden-things note. Every setup says how it went: "waiting pullback" or "waiting M5 BOS" (retraced, new rules §18; both with the dashed SL~ / TP~ it would trade with if price came back now, worked out again on every analysis, also against the bias, which since 2026-10-25 is informational only: M15/M30 entries do not need H4/H1 agreement), "entry taken · open" / "entry taken · closed ±$" or "failed · against bias / missed / refused / expired / FVG traded into too soon / no run before the retrace / no M5 entry BOS / zone lost before the M5 BOS / …" (hover: why). An open trade's entry / SL / TP as they are now; a level off the chart sits as an ↑ / ↓ tag on its edge.

**The learning chart** (David 2026-10-25: "the engine is not finding the correct structure, so I draw it and you
train the engine from that"): `/learn` on the local dashboard; the internet copy shows it view-only unless the link carries the secret key (`engine_data/learn/key.txt`), so strangers with the tunnel link cannot write into the training labels. Pick a symbol and
timeframe, then draw the structure as it SHOULD be — BOS / CHoCH (the broken level, dragged to the break candle,
side ↑/↓), FVG / supply / demand boxes, swing ▲▼, and ✓ regions over spans marked completely. Labels land in
`engine_data/learn/labels.jsonl` (append-only; deletes and notes are extra lines, nothing is lost); the engine's
own finds show faded next to them, and the top line says how far they agree. Training: `python3 -m engine.learn
report` (every label: ok / called otherwise / missed, plus the engine's extra finds inside ✓ regions) and
`python3 -m engine.learn fit` (re-runs the structure finding over a grid of swing_length × displacement_mult,
scores each against the labels — the live config always among them as the baseline — and writes `engine_data/learn/fit.json` — config.py is never touched; David
applies the winner). With ~200+ labels the same file can feed a real classifier.

**SMC compare** (David 2026-10-28: "use this in our website and show", not in MT5): `/smc` draws two free SMC
indicators next to the V5 engine on the same bars, any symbol and timeframe, and lists their live zones nearest
price and their latest confirmations. Both are computed in Python from the bar files (`smc_compare.py`): **SMC
Zones** (allanninal, PolyForm-Noncommercial — the author's own Python reference, `third_party/smc_zones_ref.py`;
swing 3, ATR 14, FVG ≥ 0.2 ATR, OB ends on a close past its far edge) and **LuxAlgo Smart Money Concepts** (CC
BY-NC-SA — a Python port, `third_party/luxalgo_smc.py`: internal 5 / swing 50 structure, order blocks, FVG,
EQH/EQL, premium / discount, strong / weak high / low). `test_smc_compare.py` holds both to what the MT5
indicators drew on our GOLD / EURUSD M15 bars (identical). Non-commercial licences: personal use only.
`python3 -m engine.smc_compare report --sym GOLD --tf M15` prints the same as text.

Since 2026-10-28/29 the page opens on **David's own structure** (`major_structure.py`: BOS only at a leg's extreme after
a ≥ 3 ATR pullback, CHoCH only at the protected swing, a close ≥ 0.25 ATR beyond; boxed "Bull BOS / Bear CHoCH" marks,
nothing internal — 14 of his 18 drawn lines, the engine 13) and on the marks hung on it (`smc_marks.py`, researched
against public SMC sources, his V5 rules win where they define a thing): **OB** = the last opposite candle before
the last displacement of each major break (full wick, 50 % line; live until a close through it, then breaker),
**FVG** = gaps ≥ 0.3 ATR inside the major breaking moves only (touched / 50 % / filled / inverted, plus his V5
invalidation), **liquidity** = EQH / EQL (≥ 2 swings within 0.5 ATR, a ≥ 1 ATR pullback between), swing highs /
lows and PDH / PDL not yet taken, and sweeps (wick through + close back inside, or a failed break within 3
candles), **premium / discount** = protected swing ↔ the leg's high / low, EQ 50 %, OTE 62–79 %. The free
indicators stay behind their buttons.

**Supply / demand** (`supply_demand.py`, David 2026-10-30: "supply and demand should be the valid one … go to the
internet and all open source"; three Fable 5.1 agents read Seiden's SFO article, Online Trading Academy's odds
enhancers, LuxAlgo, Dukascopy and the open-source S&D indicators — `research/supply_demand/`) draws **only the valid
zones**: a base of 1–3 small-body candles (or David's last opposite candle) before a displacement candle (body ≥ 1.5 ×
the mean of the 10 before) whose move out **closed beyond a major swing** — his BOS / CHoCH gate, "do NOT mark every
supply / demand" — with the box ≤ 1.5 ATR and price never back at its proximal edge before that break. Box = the
base's wicks, the dashed line = the body edge (entry); each zone carries its kind (RBR / DBD / RBD / DBR), its life
cycle from the break on (fresh → tested → spent after 3 visits → broken on a close through the distal edge → flipped),
and a 0–10 checklist of the educators' odds enhancers (departure, FVG in the move out, time at the base, freshness,
trend, curve, room). **The checklist is shown, never a filter, and it is not an edge**: measured over 39,106 zones
(GOLD, EURUSD, GBPUSD, USDJPY, AUDUSD, M15 + H1, ~16 months) the zones held at the first return 58.2 % of the time
against 57.9 % for random levels of the same size, side and distance, and the BOS gate, freshness, base count,
displacement, trend and location all moved that by ±2 points with no consistent sign (`research/supply_demand/
validity_report.md`). Valid = David's definition still intact — the zones his strategy trades from — not a prediction.
The side panel says how many candidates were dropped and why; "mitigated" shows the used and broken ones.

The rest of the concept table (2026-10-29, "every concept a professional uses is a rule"; each researched by a
Fable 5.1 agent against the public reference implementations, the sources are in each module's docstring) sits
behind the **concepts:** buttons, all hung on the same major structure, all known only from closed bars:

| row | buttons | module | the rule in one line |
|---|---|---|---|
| 2 | Sessions | `levels.py` (+ PWH/PWL, PMH/PML pools in `smc_marks.py`) | Asia 20–00 NY, London 08–16:30 London, NY 08–17 NY in their own time zones; H/L with the liquidity lifecycle; killzones; D/W/M/midnight/08:30 opens; pullback depth of the major leg |
| 3 | Candles, all candles | `candles.py` | TA-Lib's 61 patterns, a port that matches TA-Lib bar for bar (`test_candles.py`); shown by default: reversals that make a 10-bar extreme at a level of their own side |
| 4 | Trend lines | `trendlines.py` | pivot(5) pairs rising / falling ≥ 0.5 ATR, legs ≥ 2 ATR, touches = pivot(3) within 0.5 ATR, break = close 0.25 ATR beyond; parallel + regression channel |
| 5 | Patterns | `chart_patterns.py` | H&S, double / triple, triangles, wedges, rectangles, flags / pennants on pivots, ATR tolerances (LMW, Osler & Chang, Bulkowski, Trendoscope) |
| 6 | Fib, VWAP, RSI/MACD | `indicators.py` | Fib of the major leg + BOS extension; Wilder ATR (and MT5's SMA ATR), RSI, MACD = TA-Lib to 1e-12; TradingView's divergence recipe; VWAP of the server day / week / protected swing |
| 7 | Volume profile | `volume_profile.py` | rows fixed in price, tick volume spread over each bar's range, POC, 70 % value area by the CBOT two-row step, HVN / LVN, naked POCs |
| 8 | Wyckoff, Elliott | `wyckoff.py`, `elliott.py` | Wyckoff: SC → AR → ST → Spring / Test → SOS → LPS state machine (distribution mirrored), phases provisional until the SOS; Elliott: the hard impulse / diagonal / zigzag / flat rules on the major zigzag, Fibonacci score, invalidation |

VWAP and the volume profile need MT5 tick volume: `history.py` saves it since 2026-10-29 (re-run
`python3 -m engine.history` for a symbol whose file is older; without it the profile is time-at-price and there is
no VWAP).

## Run (from `~/forex`, system `python3`)

```bash
python3 -m engine.run check            # account, symbols, one analysis pass, no orders
python3 -m engine.run run              # the loop (service: v5-engine)
python3 -m engine.dashboard            # http://127.0.0.1:8770 (service: v5-dashboard)
python3 -m engine.run trading on|off   # or the button on the dashboard
python3 -m pytest -q engine            # offline tests (fake MT5)
```

Backtest (the live strategy code replayed on FxPro's history, David 2026-10-25: find the worthless setups from data):

```bash
python3 -m engine.history               # bars from MT5 → engine_data/history/<SYMBOL>.json (≈ 11 months M5 coins, 16 forex)
python3 -m engine.backtest run          # every touched setup + outcome + chart features → engine_data/backtest/setups.jsonl
python3 -m engine.backtest report       # the engine now, the live filters, targets, features, rules trained on
                                        # the older 60 % and judged on the newer 40 % → engine_data/backtest/report.txt
python3 -m engine.bt_charts --n 12      # pictures of winners / losers → engine_data/backtest/charts/
```

Services: `systemctl --user status|stop|restart v5-engine v5-dashboard` (systemd user units, enabled at login).

**The engine runs MT5 itself** (`engine/terminal.py`, David 2026-10-25). The terminal is the user unit `mt5-terminal`
(started by the engine, not at login), so an engine restart never closes it. Every loop: not running → start; MT5
calls fail twice, or Wine was updated under it → restart (unit + stray terminal / wineserver of `~/.mt5`); not
connected for 2 min → restart; other or no account → log in to `ENGINE["mt5_login"]` (the terminal's saved password,
or `MT5_PASSWORD` in `engine_data/mt5.env`); Algo Trading off → `common.ini [Experts] Enabled=1` + restart (hourly).
Restarts ≥ 3 min apart, after 5 in an hour 15 min apart. `stop` keeps it off (`control.json "mt5": "off"`) until `start`.
The engine service sets `MT5_NO_LAUNCH=1`, so its own MT5 calls never start a terminal outside the unit.

```bash
python3 -m engine.run mt5 status|start|stop|restart|login     # or the MT5 buttons in the dashboard header
``` Log: `engine_data/engine.log`,
decisions: `engine_data/journal.jsonl`, state: `engine_data/state.json`.

**Structure filter layer** (`engine/filters.py`, David 2026-10-25, branch `feature/structure-filters`): eight hard gates
checked right before any order, on top of the V5 checks; `config.STRUCTURE_FILTERS_ENABLED` (default True), all
thresholds in `config.FILTERS`. G1 the broken swing is significant (3/3 fractal, leg ≥ 1 ATR); G2 body close + a 1-3
candle displacement ≥ 1.5 ATR leaving an FVG ≥ 0.3 ATR, entry FVG untraded (else "drift"); G3 the setup timeframe trends
with the trade (HH+HL / LH+LL), not a < 3 ATR range; G4 H4 + H1 bias with the trade, M30 not against H4 (log-only on
M15 / M30, the bias_exempt_tfs); G5 impulse from
the discount / premium half of the H4 leg, zone not revisited, nearest structure ≥ 3 × the stop away; G6 S&D H4 on M15:
SL beyond the M15 swing that started the break + spread + 0.25 ATR(M15), stop ≥ stops level, ≥ 3 × spread, ≤ 3 ATR(M15),
TP = the nearest opposing significant swing (setup TF / H1 / H4), RR ≥ 3, SL / TP on the tick size; G7 back in the FVG
within 12 M15 candles, no CHoCH against before the fill, one trade per H4 zone, no re-entry on a zone that lost; G8 ATR(M15)
≥ its 30th percentile of 200 bars, spread ≤ 1.5 × the 20-bar average, inside the symbol's sessions. While on: at most 5
positions + pending layers (MAX_POSITIONS), 0.01 lot. Every entry attempt (counter-bias ones too) → one record with a
boolean per gate, the values, the first gate that failed and what the engine without the layer would have done →
`engine_data/filters/candidates-YYYY-MM-DD.jsonl`.

Profiles (`config.FILTER_PROFILES`, overrides on top of `FILTERS`): **strict** = the spec as written (0 of 1,482 attempts
passed in the 7-day replay: on FxPro the crypto spread is ~2 × ATR(M15) and the nearest structure is rarely 3 R away);
**test** = what the 0.01-lot test trades (David 2026-10-25 "consider the new logic and take the entry"): RR ≥ 2 to the
nearest structure, premium / discount and zone freshness logged but not required, a stop inside the broker's stops
level moved out to it. G1-G4, G7, G8, the ≤ 3 ATR(M15) stop cap and the 3 × spread rule are the same in both. 120-day
replay: V5 alone 352 trades -33 R; strict 2 trades -2 R; test 19 trades, 6 won, +16.1 R (stop / target only).
With the 2026-10-26 structure rework (same 120 days, offline): old marking, test profile 8 trades 5 won +11.7 R;
new marking 2 trades 1 won +1.8 R — the new continuation-BOS setups anchor on minor swings, so G1 (significant
swing) is now the first failing gate for 45 % of attempts (was 26 %). The marking now matches David's drawn lines
15/18 (was 10/18); G1/G2 may want retuning to the new marking (David's call, `learn fit` + this replay).

```bash
python3 -m engine.run filters on|off|status     # instant switch (control.json), no restart
python3 -m engine.run filters strict|test       # the profile, also instant
python3 -m engine.filter_replay --days 7        # last 7 days through the live code, layer off vs on → engine_data/filters/replay-<date>.txt
python3 -m engine.filter_replay --offline --days 120 --on-only --tag 120d   # longer, from engine_data/history
```

Size: since 2026-10-25 `ENGINE["lot_mode"] = "min"` — every normal and layer order is the symbol's minimum lot (0.01),
to test the engine without real exposure (David); `"risk"` = V5's 2.5 % / 1.5 % sizing.

Starts in **watch mode**: complete setups are recorded as "signal" and drawn, nothing is sent until trading
is switched on. Orders need a demo account and the terminal's Algo Trading on. Magic number 5050505.

## The cost layer and the "profit" profile (David 2026-10-30)

David asked for logic that makes more profit, taking every valid trade with no cap on trades or positions
and always the 0.01 minimum lot. What the measurement said, and what was built because of it:

**Direction is a coin flip; the spread is the whole P&L.** On our own 16 months of FxPro history
(`engine/research/profit/`, 0.01 lot, one full spread per round trip), random entries decompose as

| | per trade |
|---|---|
| gross, before cost | **-$0.024** (t = -1.91) — a coin flip, as expected |
| cost, one spread | **+$0.081** |
| net | **-$0.106** |

About 360 rule x geometry combinations were scanned (Donchian breakout and its fade, RSI reversion and its
follow, EMA cross both ways, displacement follow/fade, every hour of the day, time-series momentum) over
M15 / H1 / H4. **Not one reached t > 1.0**, where chance alone across that many tests should have thrown up
several above 2. Two candidates looked strong and both died under scrutiny:

- *hour 21 UTC long, t = 7.7* — an artifact of charging half a spread. MT5 bars are bid prices; at the
  rollover the bid is marked down 5-27x its usual distance and then recovers, so buying that dip looked
  free. Charging the full round-trip spread (the honest model, now in `lab.py`) takes it to t = 0.40.
- *gold time-series momentum, t = 9.2* — 2,140 overlapping 120-bar holds on ONE symbol that rose 23 %:
  about 18 independent bets. Corrected for the overlap, t ~ 0.8.

The one effect with strong published evidence, the Krohn-Mueller-Whelan dollar drift around the daily fixes
(*J. Finance* 79(1) 2024, four datasets, 1999-2019), is **not present in our 2025-26 sample** (pooled
t = -0.39), which matches the paper's own finding that it decayed after 2013.

So the lever is not a better entry. It is paying less for the entries the engine already takes.
`engine/profit.py` holds that layer; it never judges direction.

- **G9, a ninth gate** in `filters.py`: refuses a setup that is simply too dear — a symbol whose spread is
  over 10 % of its ATR, a live spread over 1.5x its own median (this is what keeps the engine out of the
  rollover), a target under 10 spreads away, or any entry inside 20:45-22:15 UTC.
- **`engine_data/symbol_cost.json`** (`python3 -m engine.profit`): median spread / ATR(14, M15) per symbol.
  15 are worth trading (gold + 14 majors and crosses); **39 are not, including every one of the 36 crypto
  CFDs** — their spread is 31 % to 284x of an M15 ATR, so they can never pay for themselves.
- **Flat before the swap**: positions close at 20:45 UTC rather than pay financing (gold long -$0.58..0.96
  a night, USDJPY short -$0.28, crypto 20 %/yr).
- **No opposing positions on one symbol** — both sides pay the spread for zero net exposure.
- **No caps, a margin floor instead**: profile `profit` sets `MAX_POSITIONS: 0` (= unlimited in
  `Book.max_slots`) and drops `NO_REENTRY_AFTER_LOSS` and `ONE_TRADE_PER_H4_ZONE`, which are caps on trade
  count rather than quality gates. The account is protected by a 30 % free-margin floor, so the number of
  open positions is never the thing being limited.

`python3 -m engine.run filters profit` switches to it.

**What this does and does not claim.** It does not claim an edge: with gross expectancy at zero, no entry
rule found here turns a profit, and taking more trades multiplies the spread paid rather than the profit.
What it does is stop the engine paying for trades that cannot pay for themselves. The honest expectation is
a much slower bleed than the current engine, not a profit.

## The 24/7 run and its profit report (David 2026-10-30)

"Run this in the 24/7, will check how much profit it can make." What that means in practice:

- `v5-engine` is **enabled at boot** with a drop-in (`~/.config/systemd/user/v5-engine.service.d/24-7.conf`)
  setting `Restart=always`. The engine starts `mt5-terminal` itself (`control.json` `mt5=auto`,
  `terminal.ensure_running`), so enabling the one unit brings the desk back after a reboot. `forex-awake`
  keeps the laptop from sleeping; user lingering is on.
- `engine_data/profit_run.json` marks when the run began, so the report can be anchored to it rather than
  mixing in the older Kronos and hand-placed trades.
- **`python3 -m engine.pnl --run`** prints what the run has actually made. The engine also writes it to
  `engine_data/pnl.json` every 5 minutes (it is MT5's only user), the dashboard serves it at `/api/pnl`,
  and the header strip shows it.

Every number is net of commission and swap. The report prints a **95 % confidence interval for the true
mean**, and while that interval spans zero it says the result is indistinguishable from zero no matter how
good the total looks. That is not decoration: at 0.01 lot a trade's dollar outcome has a standard deviation
several times its mean, so a few dozen trades can show any total at all. Kronos' own 214 live trades are
the worked example — **+$15.37 total, but t = 0.60, and about 1,612 trades would be needed to tell that
mean from zero.**

What the run can and cannot show: with gross expectancy measured at zero (see the cost layer above), the
honest expectation is a slow negative drift of roughly one spread per trade. The report exists so that a
lucky fortnight is not mistaken for an edge.

**One thing "24/7" does not mean.** The cost gate rules out all 36 crypto CFDs, and those are the only
instruments that trade at weekends. Forex and gold close from Friday ~21:00 UTC to Sunday ~21:00 UTC, and
the book goes flat before the 20:45 UTC swap each day. So the engine *runs* around the clock but *trades*
only while the forex week is open. Letting it trade the weekend would mean re-admitting instruments whose
spread is 31 % to 284 % of an M15 ATR, which the measurement says costs more than it can win.

## Strategy status on /smc (David 2026-10-30)

"Show which charts are approaching our trading strategy, what is in trade with its P&L, and the SL / TP on
the chart." That is `engine/status.py` -> `/api/status` -> the **Strategy** panel and layer on /smc.

- **Approaching** — every setup still alive, nearest to firing first. A V5 setup walks BOS/CHoCH -> zone ->
  FVG -> price back to the entry -> M5 BOS -> the nine gates -> order, so its status *is* the step it is on
  (`pullback`, `M5 BOS`, `READY`), and "away" is how far price still has to travel, in ATR.
- Each row carries its entry, SL, TP and RR. The engine writes a committed plan only for its trade
  timeframes (M15 / M30), so an H4 or M5 setup shows **`~SL` = the zone's far edge**, which is where the
  stop will go, marked provisional rather than left blank.
- **Symbols the cost gate refuses are listed separately, not hidden**, with the reason ("TRON costs 941 % of
  an ATR to trade"). Without that the panel would show crypto setups about to fire that the engine will
  never take.
- **In trade** — live P&L per position with its entry, current price, SL, TP and how far it has run in R.
- **On the chart** — entry (amber), SL (red) and TP (cyan) as labelled lines: dashed for a setup waiting,
  solid for an open trade. Hovering a line names the setup.
- **The 24/7 run** is at the bottom of the panel, with the same confidence interval the report prints.

Everything is read from files the engine already writes (state, view, overview, pnl), so the dashboard
never touches MT5. Clicking a row switches the chart to that symbol.

## Choices made where V5 describes judgement in words (all in `config.py`)

| V5 | engine |
|---|---|
| BOS (pictures, 2026-10-24; reworked from the learning chart 2026-10-26) | a candle CLOSE beyond a swing (a wick through is not a break). WITH the trend every broken swing is a BOS — an HL / LH broken while the bias already points that way is the trend going on, not a change (David drew the engine's old continuation "CHoCH"s as BOS: his 18 lines matched 10 before, 15 after). AGAINST the trend only major structure turns it: the last `major_swing_length` (4) fractal formed before the current leg extreme — a close beyond it is the turn, BOS / CHoCH by that major swing's HH/LL vs LH/HL label, drawn at the major level; a retrace poking through minor swings is no event, the levels are just spent (the old engine flipped its bias there and pruned the real BOS levels, so lines like EURUSD 1.12684 / 1.15744 / 1.11882 had no event at all). CHoCH stays drawn light grey, not traded. Minor swings stay breakable until closed through; a break drops the other side's minor swings older than its move |
| "supply / demand at the BOS" | V5 §3-4 inside the BOS move (from the lowest low / highest high since the broken swing to the BOS candle) |
| "mitigation block when no supply / demand" | §6 pattern inside the BOS move, used only when that move has no supply / demand zone |
| "FVG inside the BOS", FVG cluster (new rules §15) | every FVG whose middle candle lies in the BOS move is one associated cluster = one setup; the retrace trigger is the nearest one (`fvg_pick` "nearest"; an int picks that one from the left, the engine before 2026-10-25) |
| the retrace is not the entry (new rules §18) | after the touch the setup waits (`waiting M5 BOS`) for an M5 candle CLOSING beyond the latest confirmed M5 swing in the trade direction (`entry_confirm` "M5"; empty = enter at the touch); cancelled when the setup TF closes beyond the zone or after `m5_confirm_max_bars` M5 candles |
| an FVG traded back into early is no structure (David 2026-10-25) | the next `fvg_protect_candles` (2) candles must not trade into the entry FVG, then price must run ≥ `fvg_min_runoff_atr` (0.5) × ATR(14) beyond it before the first retrace, or the setup turns `invalid` |
| "entry like 10 %" | 10 % inside that FVG from the side price comes back from (`fvg_entry_depth`) |
| newer BOS before the pullback | the older setup is "superseded" (not traded), but only by a BOS that has its own setup (zone or MB + FVG); a small BOS without one is not used and cancels nothing (David 2026-10-24, kept 2026-10-25). The entry views of the dashboard don't draw superseded setups |
| S&D H4 trigger (2026-10-25) | the first and every later M15 BOS / CHoCH the same way after price reached the H4 entry, whose move's start lies between the H4 entry and the H4 invalidation; a BOS that already has its S&D M15 setup is that same setup (one trade, marked with the H4 parent) |
| §13-14 layer depth by movement | weak / moderate / strong = 0-1 / 2 / 3 of: retracement bodies ≥ 1.3 × the 20 before, ≥ 4 candles in a row, ≥ 1.5 M5 ATR travelled → depth 25 / 40 / 55 % |
| §22 "very close to the target and reversal begins" | best price ≥ 80 % of the way, then gave back 10 % or an M5 candle closed against |
| §26 Target 1 "centre" | halfway between the normal entry and the final target |
| §27-28 "SL below/above the first entry" | first entry ∓ max(0.1 R, 20 points) |
| §31 protect more at 3R / 4R / 5R | lock (n − 2)R at nR, plus M5-swing trailing |
| entry only live | price must reach the entry in the forming or latest completed (recent) M5 bar; earlier ones are "missed", never traded late |
| not in V5 | refuse when the spread is over 35 % of the stop distance, or the SL/TP is inside the broker's stops level from the closing price (ask for sells, bid for buys) |
| §2 bias | HH+HL but the last H1 close below the last HL (or LH+LL and a close above the last LH) = broken = no trade |
