# Strategy: Claude BOS → its supply / demand zone (no Kronos)

The comparison for `kronos_claude_bos_zone`: the same trade on every setup, without asking Kronos. The difference
between the two is what Kronos adds.

## Which engine gives what
- **Claude → setup** (rules/concept/claude, "setup"): a BOS → the supply / demand zone that started its move,
  still fresh → the leg's swing high / low, confirmed.

## Entry
- A limit order at the zone's entry line (its body edge), placed when the setup appears.
- Cancelled if Claude sees a CHoCH against it before the fill, or after 96 M15 bars (24 h) without a fill.
- No new orders 20:45–22:15 UTC (rollover).

## Stop loss
- Beyond the zone (demand low / supply high) + 0.25 × ATR(14) + one spread, out of a liquidity sweep.

## Take profit
- The swing high (buy) or swing low (sell) of the BOS leg.

## Exit when it goes wrong
- Only the stop loss and the take profit.
