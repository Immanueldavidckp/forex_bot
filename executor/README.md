# executor/: carries the commands out

It never decides whether a trade is good. It only refuses what breaks David's account limits (`limits.toml`,
checked by `guard.py` before every command of every concepter):

- no stop loss, or the stop / target on the wrong side
- risk at the stop over `max_risk_pct` of the balance
- today's loss (realised + open) at `daily_loss_limit_pct`
- the kill switch: `touch executor/HALT` stops new trades; `rm executor/HALT` allows them again
- a real account (`demo_only`)
- a buy and a sell on one symbol at the same time
- a concepter moving or closing another concepter's trade
- a stop moved further away (stops only move toward profit)

Closing a trade is always allowed. The stop sits at the broker, so a trade stays protected even if a concepter
crashes.

| executor | status |
|---|---|
| `paper.py` | done: recorded bars, ask = bid + spread, stop wins when one bar touches both, no slippage / swap |
| `mt5.py` | next (ARCHITECTURE.md step 2): the same guard in front of `mt5_client.py`; until then the V5 engine's own `engine/book.py` places the live trades |
