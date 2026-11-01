# Concept: the V5 engine (David's Supply & Demand)

What the V5 engine looks for on the chart. How it is traded (entry · SL · TP · exit) is a strategy:
`rules/strategy/v5_supply_demand/`. Source: David's "MT5 EA — COMPLETE FINAL STRATEGY LOGIC V5", his
"new rules.md" (FOREXBOT vault), and his spoken rules logged in `engine/README.md`. Names in backticks are
`params.toml` keys.

## Signals it reports
- **bos / choch**: V5's structure breaks (below).
- **setup**: a complete setup that price has not come back to yet. It carries `entry`, `sl`, `tp`, the zone
  (`top`, `bottom`) and the FVG (`fvg_top`, `fvg_bottom`).

## Timeframes
- Every chart timeframe is analysed and drawn: H4, H1, M30, M15, M5.
- The live engine trades three entries: S&D M15, S&D M30, and S&D H4. S&D H4 means price is back in an H4 zone,
  then an M15 BOS or CHoCH forms whose move starts inside that zone. That M15 move's own zone + FVG is the setup.

## Structure
- Breaks are by candle **close**. A wick through a level is a sweep, not a break.
- A swing = a fractal of `structure.swing_length` bars on each side.
- With the trend, every broken swing is a **BOS**.
- Against the trend, only a **major** swing (`structure.major_swing_length` bars on each side, the last one
  before the leg's extreme) turns the trend. A minor break inside a pullback is not an event.

## The setup (in this order)
1. **BOS** on the setup timeframe: a candle closes beyond the last HH (buy) or LL (sell).
2. **Zone** inside the BOS move (from its start to the BOS candle). Demand (buy) or supply (sell) is the final
   opposite candle at most `zone.lookback_bars` bars before a displacement candle. A displacement candle has a body
   ≥ `zone.displacement_mult` × the average body of the `zone.body_average_bars` before it. If there is none, the
   mitigation block is used instead.
3. **FVG** inside the BOS move. It is required. All FVGs of one displacement are ONE cluster, and the one nearest
   to price is the trigger (`fvg.pick`).
4. The FVG must stay untouched for `fvg.protect_candles` candles. Then price must run `fvg.min_runoff_atr` ×
   ATR(14) before the pullback. Otherwise the structure is invalid.
5. The setup's numbers:
   - `entry` = `setup.fvg_depth` (10 %) into the trigger FVG;
   - `sl` = the zone's far edge + `setup.sl_buffer_points` points;
   - `tp` = the nearest untouched opposite swing (setup TF, H1, H4).

## The setup is gone when
- a newer BOS setup on the same timeframe replaces it;
- it is older than `structure.setup_max_age_bars` bars;
- price has already come back to its entry;
- price came back into the FVG too early, or there was no run first (rule 4).
