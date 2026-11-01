# Trade: Supply & Demand (David's V5)

## Entry
1. Price comes back `entry.fvg_depth` (10 %) into the trigger FVG, approaching from the side it left. The engine
   must see this live; it never enters late.
2. Then the entry needs its own proof: an **M5 candle closes beyond the latest confirmed M5 swing** in the trade's
   direction (`entry.confirm_tf`).
3. No M5 proof within `entry.confirm_max_bars` M5 candles (3 h) → missed, no trade.
4. Market order. On demo the size is always the minimum lot (0.01).
5. Optional second entry (the layer): one pending limit at 25 / 40 / 55 % of the way from entry to SL. The depth
   depends on how strong the pullback is (`layer.depth_*`).

## Stop loss
- S&D M15 / M30: at the setup's own zone (supply high / demand low) + `stops.sl_buffer_points` points.
- S&D H4 (entered on M15): beyond the M15 swing that started the break + the spread + `stops.sdh4_sl_atr_buffer`
  × ATR(14, M15).
- It is never moved closer just to make a trade pass. A stop narrower than `stops.sl_min_spread_x` × the spread,
  or wider than `stops.sl_max_atr` × ATR(14, M15) → no trade.
- The stop must clear the broker's stops level. Profile `profit` widens it out to that level
  (`filters.sl_widen_to_stops_level`).

## Take profit
- At the **nearest** opposite structure level price has not traded through: a swing on the setup timeframe, H1
  or H4. A nearer level is in the way, so a farther one is never picked.
- Reward : risk to that level ≥ `stops.min_rr`, or **no trade**. A made-up target is never used.
- Cost gate: the target must be at least `filters.min_target_spread_x` spreads away.

## Exit when it goes wrong
The engine today closes a trade early only in these cases:
- **Rollover**: every position is closed at `exit.flat_before_utc` (20:45 UTC), before the swap is charged.
- **Near the target, then a reversal**: price has gone ≥ `manage.near_target_progress` of the way to TP, then gives
  back `manage.reversal_giveback` of it (or an M5 candle closes against the trade). The stop moves to break-even.

> **OPEN — for David:** list every "it went wrong" case that should close a trade BEFORE its stop. For example:
> an M15 CHoCH against the trade, a close back through the zone, or no progress after N bars. Until this list
> exists, every concepter can only wait for the stop, and an LLM concepter would invent its own reasons.

Managing a winner (V5 Mode A / B):
- **Mode A** (no layer): keep the original stop until the rule above moves it to break-even.
- **Mode B** (layer filled): Target 1 = the centre between the first entry and TP (`manage.tp1_fraction`). Then
  both stops go past the first entry, and trailing follows M5 swings.
- **From 3R**: at nR the stop locks at least (n − 2)R (`manage.lock_start_r`, `manage.lock_gap_r`), plus M5 swing
  trailing. A stop only ever moves toward profit.
