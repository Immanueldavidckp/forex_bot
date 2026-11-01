# Strategy: Kronos direction + Claude BOS (draft)

David's example (2026-11-01): "select the direction from Kronos and check the BOS from Claude, by using that set the
entry, SL, TP". The numbers are a first draft for David to change.

## Which engine gives what
1. **Kronos → direction.** It comes from the bar that just closed, with at least 75 % of the paths on one side
   (`p ≥ 0.75`), and a median move of at least 2 spreads. This sets the side.
2. **Claude → BOS** on M15 in the SAME direction, closed within the last 4 bars.

Claude is only asked when Kronos already agrees, so the costly engine runs only on the bars that matter.

## Entry
- Market order on the close of the bar where both agree.
- No entries 20:45–22:15 UTC (the rollover: spreads blow out, and the swap is charged).

## Stop loss
- Beyond the start of Claude's BOS move (`claude.bos.origin`) by 0.25 × ATR(14) + one spread.
- A stop wider than 3 ATR, or narrower than 3 spreads → no trade.

## Take profit
- 2 × the risk (RR 2). A target closer than 10 spreads → no trade.

## Exit when it goes wrong
- Claude reports a **CHoCH against** the trade → close.
- After 8 bars (Kronos' 2 h horizon) → close. The forecast it was based on has run out.
- At +1R the stop moves to the entry.
- Flat at 20:45 UTC, before the swap.
