# Brad Goh (The Trading Geek) — Market Mechanics Ep 7: Institutional Supply & Demand Zones

https://www.youtube.com/watch?v=52aKS7HN_jI · 32:08 · uploaded 2026-05-22 · playlist "Market Mechanics" (free mentorship).
Read 2026-11-01 from the English captions (auto-generated) and 12 frames (skill `youtube-reader`). Summary in our words.

| time | what he teaches |
|---|---|
| 0:00 | most traders draw too many boxes; the zones that matter are where price exploded with intent |
| 2:19 | demand = where buying entered hard enough to break price out of a consolidation upward; supply = the mirror; the zone is the ORIGIN of that move, where institutions left unfilled orders |
| 5:08 | balance → imbalance: the consolidation before the breakout is the zone; price returns to it later |
| 7:43 | tip: scan for big candles (imbalance), then find where the move started; the stronger the move away, the stronger the zone |
| 10:18 | RANGE method: box from the highest point to the lowest point of the whole consolidation (wick to wick) |
| 12:55 | in a pullback with no real consolidation: from the pullback's high to its low |
| 14:58 | PIVOT method: only the candle that caused the reversal (wick included) — tighter, better reward : risk, but more missed fills; test both over ~100 trades and keep one |
| 19:42 | wide ranges are acceptable; a zone can be respected several times |
| 22:25 | MITIGATION: a zone counts as used only when price returns to its 50 % line (fib 0 / 0.5 / 1 on the box); a touch of the edge is not a mitigation; an unmitigated zone is expected to be revisited, a mitigated one is more likely to fail |
| 29:30 | never trade a zone alone: structure must agree (don't sell in a bullish structure), wait for the liquidity sweep, aggressive entry at the zone vs confirmation entry (lower-timeframe structure shift); premium / discount is the next episode |

Implemented as `engine/sd_brad.py` (layer "S&D Brad" on /smc). Compared with the research rule `engine/sd_classic.py`:
same idea (origin of the imbalance, no BOS needed to draw it), but Brad draws WICK to WICK, any consolidation or pullback
(not only small-body candles), no height cap, and mitigation at 50 % instead of the first touch.
