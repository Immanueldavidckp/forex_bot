# marketdata/: prices in, nothing decided

| what | where today | why it is there |
|---|---|---|
| **recorded** bars + Kronos forecasts for paper runs | `marketdata/data.py`, `marketdata/sample/` | 60 days of GOLD + EURUSD (M5 / M15 / H1 / H4) and the live Kronos forecasts of 10-26 → 10-28, so anyone can run a strategy without MT5 |
| **live** MT5 connection | `mt5_bridge.py` (Wine Python, the only file that talks to MT5), `mt5_client.py` (Linux side) | still at the top folder: the running engine imports `mt5_client` from there and the bridge is started by its path; Claude's mt5 MCP server (`mt5_mcp.py`) is registered by its path |
| **live** bars, history, ticks, MT5 process | `engine/feed.py`, `engine/history.py`, `engine/ticks.py`, `engine/live.py`, `engine/terminal.py` | part of the live engine; they move here together with it |

The live files move here at one planned engine restart, so the running engine never loses its MT5 connection
mid-trade (ARCHITECTURE.md step 2).

```
python3 -m marketdata.data export GOLD EURUSD --days 60     # new samples from David's MT5 history (his laptop)
```
