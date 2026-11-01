# Concept: Supply & Demand (David's V5)

What the V5 engine trades on demo today (2026-11-01, filter profile `profit`). Source: David's "MT5 EA —
COMPLETE FINAL STRATEGY LOGIC V5", his "new rules.md" (FOREXBOT vault), and his spoken rules logged in
`engine/README.md`. Numbers in brackets are `params.toml` keys.

## Timeframes
- Every chart timeframe is analysed and drawn: H4, H1, M30, M15, M5.
- Three entries may trade:
  - **S&D M15** and **S&D M30**: the setup below on that timeframe.
  - **S&D H4**: price comes back to an H4 setup's zone. Inside that zone an M15 BOS or CHoCH forms in the same
    direction. Its move must start inside the H4 zone. That M15 move's own zone + FVG is then the setup (an M15
    trade).
- M15 / M30 entries do NOT need the H4 / H1 bias (`structure.bias_exempt_tfs`). The bias is still worked out and
  shown, for information only.

## Structure
- Breaks are by candle **close**. A wick through a level is a sweep, not a break.
- A swing = a fractal of `structure.swing_length` bars on each side.
- With the trend, every broken swing is a **BOS**.
- Against the trend, only a **major** swing (`structure.major_swing_length` bars each side, the last one before
  the leg's extreme) turns the trend. Breaking a minor swing inside a pullback is not an event.

## The setup (in this order)
1. **BOS** on the setup timeframe: a candle closes beyond the last HH (buy) or LL (sell).
2. **Zone** inside the BOS move (from its start to the BOS candle):
   - demand (buy) / supply (sell) = the final opposite candle, at most `zone.lookback_bars` bars before a
     displacement candle;
   - a displacement candle has a body ≥ `zone.displacement_mult` × the average body of the `zone.body_average_bars`
     before it;
   - if there is no such candle, use the mitigation block.
3. **FVG** inside the BOS move. It is required. All FVGs of one displacement are ONE cluster; the trigger is the
   one nearest to price (`fvg.pick`).
4. The FVG must stay untouched for `fvg.protect_candles` candles after it forms. Then price must run on at least
   `fvg.min_runoff_atr` × ATR(14) before the pullback. Otherwise the setup is invalid structure.

## The setup is invalid when
- a newer BOS setup on the same timeframe replaces it;
- it is older than `structure.setup_max_age_bars` bars of its own timeframe and was never reached;
- price came back into the FVG too early, or there was no run before the pullback (rule 4);
- a CHoCH against it closes before the fill;
- price does not come back within `filters.setup_expiry_m15_bars` M15 bars.
