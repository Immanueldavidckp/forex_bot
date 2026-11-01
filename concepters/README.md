# concepters/: the active part

A concepter follows one strategy from `rules/`. On every closed bar it gets a `View` (the chart + only its own
positions) and returns a `Decision`: marks to draw, commands for the executor, and notes saying why.

| concepter | where | status |
|---|---|---|
| `v5` | still `engine/` (strategy.py + book.py) | live on demo; moves here in ARCHITECTURE.md step 3 |
| `kronos` | still `kronos/` + `engine/kronos_book.py` | forecast-only; moves here in step 5 |
| `llm` (claude / gpt / gemini) | `llm/` | frame done; the model calls are next (`llm/providers.py`) |
| `demo` | `demo/` | plumbing demo, **not a strategy**: copy it to start a new concepter |

A new concepter:
1. A subclass of `base.Concepter` with a unique `name` and the `timeframes` it needs.
2. Read the chart with `shared/toolkit.py`. Don't write your own BOS / zone finder.
3. Run every command through `checks.py`.
4. Add it to `REGISTRY` and `MAGIC` in `__init__.py`, and add a test in `tests/`.
