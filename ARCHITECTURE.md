# Architecture

David's design (2026-11-01). Three parts, each with one job:

```
 rules/          THE STRATEGIES, written down. They never run anything.
   supply_demand/      concept.md   what the setup looks like on the chart
   kronos_forecast/    trade.md     entry · stop loss · take profit · exit when it goes wrong
   (next strategy)/    params.toml  the same rules as numbers
        │
        │  a concepter loads ONE strategy and follows it
        ▼
 concepters/     THE ACTIVE PART: each one does all the main work
   v5        code (David's V5 engine)       ┐  on every closed bar:
   kronos    forecast model                 │   1. read the chart (shared/toolkit.py: the same structure + zones for all)
   claude    LLM  ─┐                        │   2. draw what it sees (marks → dashboard)
   gpt       LLM   ├ concepters/llm         │   3. command the executor: open · move the stop · close
   gemini    LLM  ─┘                        ┘
        │
        │  Open / Modify / Close  (shared/contracts.py)
        ▼
 executor/       DOES WHAT IT IS TOLD, never decides whether a trade is good
   guard.py + limits.toml   David's account limits, the same for every concepter:
                            SL required · max risk · daily loss stop · kill switch · demo only ·
                            no opposite sides on one symbol · a concepter only touches its own trades ·
                            stops only move toward profit
   paper.py                 pretend broker on recorded bars (backtests, the friend's laptop)
   mt5 (next)               the real terminal through mt5_client.py → mt5_bridge.py (Wine)
```

## Why it is built this way
- **One strategy, many concepters.** V5, Claude, GPT and Gemini can follow the SAME `rules/supply_demand`.
  Each owns its trades (its own name and MT5 magic number), so their results can be compared fairly.
- **Rules in words AND numbers.** The LLMs read the words. The code reads the numbers. The words name each number
  as `section.key`, and an LLM gets both.
- **The concepter decides; the executor only carries out.** A concepter never talks to MT5. It returns commands,
  and the executor checks them against David's limits before anything reaches the broker. So:
  - a bad rule or a confused LLM cannot blow up the account;
  - every concepter can be tested on recorded bars;
  - the backtest and live trading run the same concepter code.
- **Every concepter sees the same chart.** `shared/toolkit.py` is the one place structure (David's BOS / CHoCH rule)
  and S&D zones are computed. Two concepters cannot disagree about where the BOS is, only about what to do.
- **An LLM answer is a proposal.** It becomes a command only after `concepters/checks.py` agrees with the
  strategy's numbers (sides, RR ≥ min_rr, a reason). A broken or unreadable answer is a "wait".

## Folder map

| folder | what | who changes it |
|---|---|---|
| `rules/` | the strategies | **David only** |
| `concepters/` | `base.py` (what a concepter is), `checks.py`, `run.py` (paper runner), `demo/`, `llm/` | David + friend (own folder) |
| `executor/` | `guard.py`, `limits.toml`, `paper.py` (`mt5.py` next) | David (limits: **David only**) |
| `shared/` | `contracts.py` (the data passed between the parts), `rules.py`, `toolkit.py`, `data.py`, `sample_data/` | both, agreed first |
| `engine/` | **the live V5 engine + dashboard, trading on demo right now** (and the chart toolkit's code) | David only |
| `kronos/` | the Kronos forecaster | David |
| `team/`, root `*.py` | the older Claude-agent desk + the MT5 bridge | David |
| `tests/` | `test_architecture.py`: the new parts, offline | both |
| `runs/` | output of `concepters.run` (not in git) | — |

## What is live today, and what is new
The V5 engine (`engine/`) still trades on demo as before: services `v5-engine`, `v5-dashboard`. It reads
`engine/config.py`, not `rules/`. Nothing in `engine/` was moved or changed. The new folders are the frame the
engine moves into, one step at a time, and each step is checked against the old behaviour before the switch:

1. ✅ Snapshot of everything (tag `pre-architecture-2026-11-01`). New frame: contracts, rules, guard, paper
   executor, runner, demo + LLM concepters, tests.
2. `executor/mt5.py`: the guard in front of the real terminal (`mt5_client.py`), on demo.
3. V5 as a concepter (`concepters/v5/`): `engine/strategy.py` + the deciding half of `engine/book.py`, reading
   `rules/supply_demand/params.toml`. Replay old vs new on the same bars: same trades → switch the service.
4. V5 on David's structure rule (`major_structure.py` through the toolkit) instead of `strategy.structure()`. Today
   `/smc` shows one and the engine trades the other.
5. Kronos as a concepter (`rules/kronos_forecast`), so `engine/kronos_book.py`'s own order code goes.
6. The dashboard draws every concepter's marks + trades, and shows the profit per concepter.
7. Claude / GPT / Gemini concepters: paper first, demo only after a paper run David has looked at.

Until step 3, `tests/test_architecture.py` checks that `rules/supply_demand/params.toml` and `engine/config.py`
hold the same numbers, so a change in one place cannot go unnoticed.

## Still open (David)
- `rules/supply_demand/trade.md` → **Exit when it goes wrong**: which events close a trade before its stop?
- `executor/limits.toml` → `daily_loss_limit_pct = 5`: a proposal, not in the live engine yet.
- May two concepters hold the same side of one symbol at once? (The opposite side is blocked.)

## Run it
```
python3 -m pytest tests/test_architecture.py -q                     # offline, ~2 s
python3 -m concepters.run --concepter demo --symbols GOLD,EURUSD     # paper run on the sample bars
python3 -m concepters.run --concepter llm --provider fake --symbols GOLD --days 3
```
