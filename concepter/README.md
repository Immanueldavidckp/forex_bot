# concepter/: the engines and the conductor (the active part)

```
concepter/
  base.py         what every engine is: on_bar(view) → Reading (signals + marks + notes)
  toolkit.py      the ONE structure + S&D reader all engines use (David's rule, engine/major_structure.py)
  conductor.py    carries out a strategy from rules/strategy/: asks the engines, sets entry · SL · TP, exits,
                  sends the commands to the executor
  run.py          a strategy on recorded bars with the paper executor (--set key=value: a what-if)
  scan.py         one engine over a whole history: every signal it reports (where to run Kronos in a backtest)
  backtests/      backtests that put the tools together (kronos_claude_bos_zone.py)
  v5/             concepter.py: V5's bos / choch / setup signals (paper version; the live engine is engine/)
  kronos/         concepter.py: reads Kronos forecasts → direction
                  signals.py, model.py, live.py, evaluate.py …: the GPU forecaster itself (~/opt/kronos-venv)
                  backfill.py: Kronos forecasts for past bars (backtests)
  claude/         concepter.py: a model judges the chart → bos / choch / direction (new)
                  providers.py: toolkit (no model) · fake · claude · gpt · gemini
```

| engine | reports | follows | status |
|---|---|---|---|
| `v5` | bos, choch, setup (entry / sl / tp) | `rules/concept/v5` | paper here; the LIVE V5 is still `engine/` (moves in step 3) |
| `kronos` | direction (p, move) | `rules/concept/kronos` | reads recorded or live forecasts; the forecaster runs as `python -m concepter.kronos.signals` |
| `claude` | bos, choch, direction, setup (BOS → its S&D zone → the leg's swing) | `rules/concept/claude` | frame done; `toolkit` provider works (no model); model providers next |

An engine never trades and never talks to MT5. It reports what it sees. Strategies decide.

A new engine:
1. A folder `rules/concept/<name>/` (concept.md + params.toml) and a folder `concepter/<name>/`.
2. A subclass of `base.Concepter` with `name`, `timeframes`, `signal_kinds`. Read the chart with `toolkit.py`; don't
   write a second BOS / zone finder.
3. Add it to `ENGINES` in `__init__.py`, add its signals to the table in `rules/strategy/README.md`, and test it.
