# Concept: the Kronos engine

Kronos-base is a foundation model for candles (NeoQuasar). It reads the last `forecast.context` closed
`forecast.tf` bars and samples `forecast.paths` possible paths for the next `forecast.horizon` bars (2 h).

## Signals it reports
- **direction** after every closed bar:
  - `side`: where most paths end (buy if at least half end above the last close);
  - `p`: the share of paths on that side;
  - `move`: the median path's end minus the last close, also given in ATRs (`move_atr`) and in spreads
    (`move_spread_x`);
  - `horizon_bars`: how far ahead it looks.

## What is known about it (measured, not a rule)
- Out of sample (concepter/kronos/evaluate.py, 14 months): its direction was right 48.5–50.5 % of the time on GOLD,
  EURUSD and BITCOIN M15. Its paths are too narrow: the real price ends inside the middle 80 % of paths only
  ~60 % of the time.
- At V5 zone / FVG locations it was right 51.9 %. That's small but steady, which is why it is used as a filter
  rather than on its own.
- Since 2026-10-27 it runs forecast-only (no Kronos trades).
