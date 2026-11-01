# Trade: Kronos forecast

## Entry
- Market order in the forecast's direction, minimum lot (0.01), on the bar after the forecast.

## Stop loss
- `stops.sl_atr` × ATR(14, M15) from the entry.

## Take profit
- `stops.tp_atr` × ATR(14, M15) from the entry (target twice the stop).

## Exit when it goes wrong
- Time exit: closed after `exit.hold_bars` M15 bars (the forecast horizon) if neither SL nor TP was hit.
- Free margin below `exit.min_free_margin_pct` % → no new trade.
