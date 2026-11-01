# Strategy: Supply & Demand (David's V5)

What the live engine (`engine/`) trades on demo today (2026-11-01, filter profile `profit`). The conductor runs a
paper version of it from `strategy.toml`. The parts it does not do yet are marked *(live engine only)*, and their
numbers are under `[live_engine]`.

## Which engine gives what
- **V5 → setup**: everything comes from the V5 engine (`rules/concept/v5`): the BOS, the zone, the FVG, and the
  setup's entry, SL and TP.

## Entry
1. Price comes back 10 % into the trigger FVG (`v5.setup.entry`), approaching from the side it left. The engine
   must see this live; it never enters late. The setup must be reached within `entry.expires_bars` M15 bars.
2. *(live engine only)* The entry then needs its own proof: an **M5 candle closes beyond the latest confirmed M5
   swing** in the trade's direction (`live_engine.confirm_tf`). No proof within `live_engine.confirm_max_bars` M5
   candles (3 h) → missed.
3. On demo the size is always the minimum lot (0.01).
4. *(live engine only)* One optional second entry (the layer): a pending limit at 25 / 40 / 55 % of the way from
   entry to SL, depending on how strong the pullback is.
5. No entries 20:45–22:15 UTC (rollover). Symbols whose median spread is over `live_engine.max_spread_atr` of an
   ATR are never traded *(live engine only)*. Today that rules out every crypto CFD.

## Stop loss
- S&D M15 / M30: at the setup's own zone (supply high / demand low) + 20 points (`v5.setup.sl`).
- *(live engine only)* S&D H4, entered on M15: beyond the M15 swing that started the break, + the spread
  + `live_engine.sdh4_sl_atr_buffer` × ATR(14, M15).
- It is never moved closer just to make a trade pass. A stop narrower than `stop.min_spread_x` × the spread, or
  wider than `stop.max_atr` × ATR(14, M15) → no trade.
- *(live engine only)* A stop inside the broker's stops level is widened out to it.

## Take profit
- At the **nearest** opposite structure level price has not traded through: a swing on M15, H1 or H4
  (`v5.setup.tp`). A nearer level is in the way, so a farther one is never picked.
- Reward : risk ≥ `target.min_rr`, or **no trade**. A made-up target is never used.
- Cost gate: the target must be at least `target.min_spread_x` spreads away.

## Exit when it goes wrong
Today the trade closes early only in these cases:
- **Rollover**: everything closes at `exit.flat_at_utc` (20:45 UTC), before the swap is charged.
- *(live engine only)* **Near the target, then a reversal**: price has gone ≥ `live_engine.near_target_progress` of
  the way to TP, then gives back `live_engine.reversal_giveback` of it (or an M5 candle closes against the trade).
  The stop moves to break-even.

> **OPEN — for David:** list every "it went wrong" case that should close a trade BEFORE its stop. For example: a
> V5 CHoCH against the trade (`close_on = ["v5.choch"]`), a close back through the zone, or no progress after N
> bars (`hold_bars`).

Managing a winner *(live engine only)*:
- **Mode A** (no layer): keep the original stop until the rule above moves it to break-even.
- **Mode B** (layer filled): Target 1 = the centre between the first entry and TP. Then both stops go past the
  first entry, and trailing follows M5 swings.
- **From 3R**: at nR the stop locks at least (n − 2)R, plus M5 swing trailing. A stop only ever moves toward profit.
