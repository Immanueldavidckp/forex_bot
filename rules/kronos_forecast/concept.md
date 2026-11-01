# Concept: Kronos forecast

Kronos-base (a foundation model for candles, NeoQuasar) reads the last `forecast.context` M15 bars. It samples
`forecast.paths` possible paths for the next `forecast.horizon` bars (2 h).

## Timeframes
- M15 only.

## The setup
1. At least `forecast.p_min` of the paths end on the same side of the last close.
2. The median path's move is ≥ `forecast.min_move_spread_x` × the current spread.
3. The forecast is at most `forecast.signal_max_age_sec` seconds old.

## The setup is invalid when
- the spread is over `stops.max_spread_sl` × the stop distance;
- it is a Friday after `exit.friday_last_entry_utc` UTC (forex / gold), because the 2 h hold would cross the
  weekly close.

Measured before going live (kronos/evaluate.py, 14 months): direction right 48.5–50.5 %, and it loses about the
spread with every SL/TP size tried. Since 2026-10-27 Kronos is forecast-only (no trades).
