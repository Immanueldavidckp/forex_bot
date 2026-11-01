# rules/strategy/: the recipes, common to all engines

A strategy says **which engine gives which signal**, and how those signals become **entry · stop loss · take
profit · exit**. It never runs on its own; `concepter/conductor.py` carries it out and sends the trade to the
executor.

```
rules/strategy/<name>/
  strategy.md     in words, always these sections:
                    ## Which engine gives what · ## Entry · ## Stop loss · ## Take profit · ## Exit when it goes wrong
  strategy.toml   the same, in the form below
```

## strategy.toml

```toml
[strategy]
name = "kronos_direction_claude_bos"
version = "0.1"
status = "draft"            # draft | paper | demo | live
timeframe = "M15"           # the conductor runs on each closed bar of this timeframe
magic = 5050701             # its trades on MT5 carry this number

# 1. WHICH ENGINE GIVES WHAT. Checked in this order; the first one that fails stops the round, so the next
#    engine is not even asked. The first need sets the side; the others must agree (same_side = true).
[[need]]
engine = "kronos"           # a folder in rules/concept/
signal = "direction"        # a kind that engine reports
max_age_bars = 1            # how many bars old the signal may be (1 = from the bar that just closed)
min = { p = 0.75 }          # the signal's numbers: at least …
# max = { … }               # … at most

[[need]]
engine = "claude"
signal = "bos"
max_age_bars = 4

# 2. ENTRY
[entry]
type = "market"             # market | limit
# limit_at = "claude.bos.level"     # a limit at any needed signal's number: <engine>.<signal>.<number>
# expires_bars = 12                 # an unfilled limit is cancelled after this many bars
no_entry_utc = ["20:45", "22:15"]   # no entries in this window (the rollover)
# friday_last_utc = "19:30"

# 3. STOP LOSS: at a signal's number (+ buffer), or k × ATR(14) from the entry
[stop]
at = "claude.bos.origin"    # or: atr = 1.0
buffer_atr = 0.25           # beyond it by 0.25 × ATR(14)
plus_spread = true          # and one spread more
max_atr = 3.0               # wider than 3 ATR → no trade
min_spread_x = 3.0          # narrower than 3 spreads → no trade
# max_spread_frac = 0.3     # spread more than 30 % of the stop → no trade

# 4. TAKE PROFIT: at a signal's number, a reward : risk, or k × ATR
[target]
rr = 2.0                    # or: at = "v5.setup.tp"   or: atr = 2.0
min_rr = 2.0                # less than this → no trade
min_spread_x = 10.0         # a target closer than 10 spreads is not worth the cost → no trade

# 5. EXIT WHEN IT GOES WRONG / MANAGING
[exit]
close_on = ["claude.choch"] # close when this engine reports this signal AGAINST the trade
hold_bars = 8               # close after 8 bars
breakeven_at_r = 1.0        # at +1R the stop moves to the entry
flat_at_utc = "20:45"       # close everything at this time (before the swap)
```

Numbers a signal can be pointed at (`<engine>.<signal>.<number>`):

| engine | signal | numbers |
|---|---|---|
| v5 | bos, choch | level, origin, close |
| v5 | setup | level (= entry), entry, sl, tp, rr, top, bottom, fvg_top, fvg_bottom |
| kronos | direction | level (last close), p, p_up, move, move_atr, move_spread_x, horizon_bars |
| claude | bos, choch | level, origin, close |
| claude | direction | level (last close) |

`[live_engine]` in a strategy.toml holds numbers that the live engine in `engine/` uses but the conductor does not
do yet (M5 confirmation, the layer, Mode A / B). They are kept here so all of a strategy's numbers sit in one place.

| strategy | engines | status |
|---|---|---|
| `v5_supply_demand` | v5 | demo: the live engine in `engine/` trades it; the conductor runs the paper version |
| `kronos_forecast` | kronos | forecast-only since 2026-10-27 |
| `kronos_direction_claude_bos` | kronos → claude | draft, David's example (2026-11-01) |
