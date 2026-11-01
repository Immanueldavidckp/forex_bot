# Architecture

David's layout (2026-11-01):

```
 marketdata/        PRICES IN. Nothing decided.
     │                  recorded bars + Kronos forecasts (paper) · MT5 (live)
     ▼
 concepter/         THE ENGINES: each one reads the chart by its OWN concept rules and reports what it sees
   v5/                  bos · choch · setup (zone + FVG + entry / sl / tp)          ← rules/concept/v5
   kronos/              direction (16 forecast paths, p, move)                       ← rules/concept/kronos
   claude/  (new)       bos · choch · direction, judged by a model                   ← rules/concept/claude
     │  signals
     ▼
 conductor          carries out ONE strategy (concepter/conductor.py)               ← rules/strategy/<name>
     │                  "direction from Kronos, BOS from Claude → entry · stop · target · exit"
     │  Open / Modify / Close
     ▼
 executor/          places and manages the orders behind David's limits (limits.toml): SL required · max risk ·
                    daily loss stop · kill switch · demo only · no opposite sides · a strategy only touches its own
                    trades · stops only toward profit

 rules/             everything written down, never runs:
   concept/<engine>/    what each engine looks for (concept.md + params.toml)
   strategy/<name>/     the recipes, common to all engines (strategy.md + strategy.toml)
```

## Why it is built this way
- **An engine sees; a strategy decides.** Engines report signals and never trade, so one engine can serve many
  strategies, and one strategy can mix engines. A new idea ("Kronos direction + V5 zone", "Claude BOS + V5 target")
  is a new `rules/strategy/<name>/strategy.toml`, not new code.
- **Cheap first, costly last.** The conductor asks the engines in the order of the strategy's `[[need]]` list and
  stops at the first one that fails. Put Kronos first and Claude last, and Claude is only asked when Kronos agrees.
- **Every engine sees the same chart.** `concepter/toolkit.py` is the one structure + S&D reader (David's BOS /
  CHoCH rule). Engines can disagree about what it means, never about where the BOS is.
- **A model's answer is checked.** A BOS from the Claude engine counts only if a candle really closed beyond its
  level. An unreadable answer, or a dead model, means "no signal", never a crash.
- **The executor only carries out.** It refuses whatever breaks David's account limits, whoever sent it. So a bad
  rule or a confused model cannot blow up the account, and a paper run and live trading use the same code.

## Every top-level item

| item | part | why |
|---|---|---|
| `marketdata/` | market data | recorded bars + forecasts; the live MT5 files move in at step 2 |
| `concepter/` | engines + conductor | v5 · kronos (incl. the GPU forecaster, moved from `kronos/`) · claude |
| `rules/` | rules | `concept/` per engine, `strategy/` common recipes |
| `executor/` | executor | guard, David's `limits.toml`, paper broker (`mt5.py` next) |
| `shared/` | the language between all parts | `contracts.py` (Bar, Signal, Mark, Open / Modify / Close, Position …), `rules.py` (reads rules/) |
| `engine/` | **the LIVE V5 engine + dashboard**: market data, concepts, decisions, orders, web pages in one folder | it trades on demo right now (`v5-engine`, `v5-dashboard`), so it is split up step by step, never moved in one go |
| `mt5_bridge.py`, `mt5_client.py` | market data + executor (live) | the only way to MT5 (Wine). Stay at the top until step 2: the running engine and the bridge's start path depend on it |
| `mt5_mcp.py` | a tool for Claude (chat) | MT5 tools for Claude; registered by its path |
| `team/`, `claude_trading_desk.py`, `llm_paper_trader.py`, `place_order.py`, `desk.env.example`, `files.zip` | the OLD 6-agent desk | not used by anything above; to be archived. `team/roles/desk.md` holds private client details and must never be shared |
| `tests/` | tests | `test_architecture.py` (all of the above, offline) · `test_desk.py` (old desk) |
| `engine_data/` | data (not in git) | history, ticks, engine state, logs, Kronos forecasts, /learn labels |

## Live vs new
The V5 engine in `engine/` still trades on demo exactly as before. It reads `engine/config.py`, not `rules/`.
`tests/test_architecture.py` fails if `rules/concept/v5`, `rules/strategy/v5_supply_demand`,
`rules/concept/kronos` or `rules/strategy/kronos_forecast` ever disagree with `engine/config.py`. The steps:

1. ✅ Layout: marketdata · concepter (v5 · kronos · claude) · rules (concept · strategy) · executor; conductor,
   paper runner, 3 strategies, tests. All three strategies run end to end on recorded bars.
2. `executor/mt5.py` (the guard in front of MT5), and the live MT5 files into `marketdata/`, at one planned
   engine restart.
3. V5 for real: the gates (filters.py, profit.py), the M5 confirmation, the layer and Mode A / B move from
   `engine/` into the v5 engine + the conductor. Replay old vs new on the same bars: same trades → switch the service.
4. V5 on David's structure rule (the toolkit) instead of `strategy.structure()`.
5. The Claude engine on a real model (`concepter/claude/providers.py`); compare it with the `toolkit` baseline on
   paper before any demo trade.
6. The dashboard draws every engine's marks + each strategy's trades and profit.

## Still open (David)
- `rules/strategy/kronos_direction_claude_bos`: the numbers are a first draft (p ≥ 0.75, BOS within 4 bars, stop
  at the BOS origin + 0.25 ATR, RR 2, exits).
- `rules/strategy/v5_supply_demand`: **exit when it goes wrong**, which events close a trade before its stop?
- `executor/limits.toml`: `daily_loss_limit_pct = 5` is a proposal, not in the live engine.

## Run it
```
python3 -m pytest tests/test_architecture.py -q
python3 -m concepter.run --strategy kronos_direction_claude_bos --symbols GOLD,EURUSD
python3 -m concepter.run --strategy v5_supply_demand --symbols GOLD --days 20
python3 -m concepter.run --strategy kronos_forecast --symbols GOLD,EURUSD
```
Output: `runs/<strategy>-<time>/` (journal, trades, marks, summary).
