# Strategy: Kronos forecast

Kronos alone, as `engine/kronos_book.py` traded it from 2026-10-26 to 10-27. Forecast-only since then: no trades.

## Which engine gives what
- **Kronos → direction** from the bar that just closed, with `p ≥ 0.75` and a median move of ≥ 2 spreads.

## Entry
- Market order in that direction, minimum lot (0.01).
- Forex / gold: no entry on a Friday after 19:30 UTC, because the 2 h hold would cross the weekly close.

## Stop loss
- 1 × ATR(14, M15) from the entry.
- A spread over 30 % of the stop distance → no trade.

## Take profit
- 2 × ATR(14, M15) from the entry (target twice the stop).

## Exit when it goes wrong
- Time exit: closed after 8 M15 bars (the forecast horizon) if neither SL nor TP was hit.
- The live engine also opens no new trade below 30 % free margin.
