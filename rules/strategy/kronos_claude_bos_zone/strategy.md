# Strategy: Kronos direction + Claude BOS → its supply / demand zone

David, 2026-11-01: "run the Kronos and Claude BOS, identify the supply or demand regarding that, take the trade, set
the SL above the supply / below the demand by a bit for safety from the liquidity sweep, then the target is the
respective swing high or swing low regarding that BOS".

## Which engine gives what
1. **Kronos → direction** on the bar the setup appears: ≥ 75 % of its 16 paths on one side (`p ≥ 0.75`), and a
   median move of ≥ 2 spreads.
2. **Claude → setup** in the SAME direction (rules/concept/claude, "setup"):
   - a BOS;
   - the supply / demand zone that started that BOS move (demand for a buy, supply for a sell), still fresh;
   - the leg's swing high (buy) or swing low (sell), confirmed by 3 bars without a new extreme.

Kronos is asked first; Claude only when Kronos agrees.

## Entry
- A **limit order at the zone's entry line** (its body edge), placed when both agree. Price has to come back to
  the zone.
- Cancelled if Claude sees a CHoCH against it before the fill, or after 96 M15 bars (24 h) without a fill.
- No new orders 20:45–22:15 UTC (rollover).

## Stop loss
- **Beyond the zone**: below the demand's low (buy) or above the supply's high (sell), plus 0.25 × ATR(14) and one
  spread. That margin keeps the stop out of a liquidity sweep just past the zone's edge.

## Take profit
- **The swing high (buy) or swing low (sell) of the BOS leg**: the extreme price reached before the pullback.
- No minimum RR: the swing decides (the backtest reports the RR of each trade).

## Exit when it goes wrong
- Only the stop loss and the take profit. (Still open for David: close on a CHoCH against, a time limit,
  break-even?)
