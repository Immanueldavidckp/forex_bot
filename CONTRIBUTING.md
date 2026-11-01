# Working on this together

Read `ARCHITECTURE.md` first (5 minutes). In short:
- **engines** (`concepter/`) read the chart and report signals;
- **strategies** (`rules/strategy/`) say which engine's signal to take and where entry, stop and target go;
- the **executor** carries out the trades behind fixed safety limits.

## What you need
- Python 3.11 or newer, `pip install numpy pytest`
- No MetaTrader, no broker account. Everything runs on the recorded data in `marketdata/sample/`:
  - 60 days of GOLD + EURUSD bars;
  - the Kronos forecasts of 10-26 → 10-28;
  - the paper executor.

```
python3 -m pytest tests/test_architecture.py -q                                   # must pass before and after
python3 -m concepter.run --strategy kronos_direction_claude_bos --symbols GOLD     # the whole chain
```

## Your first job: GPT and Gemini as the engine's model
The Claude engine (`concepter/claude/concepter.py`) already does the work:
- the prompt (its concept rules in words + numbers);
- the chart packet (David's structure, zones, bars);
- checking every answer against the bars.

What is missing is the model call:

1. In `concepter/claude/providers.py`, add a class per model with `name = "gpt"` (or `"gemini"`) and
   `complete(system: str, user: str) -> str`, and return it from `get()`.
   - Read the API key from the environment (`OPENAI_API_KEY`, `GEMINI_API_KEY`).
   - Read the model name from `LLM_MODEL`.
   - Ask the model for JSON only.
2. Compare it with the no-model baseline on the same days. Every call costs money, so keep it short:
   ```
   python3 -m concepter.run --strategy kronos_direction_claude_bos --symbols GOLD --claude toolkit
   python3 -m concepter.run --strategy kronos_direction_claude_bos --symbols GOLD --claude gpt
   ```
   The model is only asked when Kronos already agrees (the strategy's `[[need]]` order).
3. `runs/<name>/journal.jsonl` shows each decision: which signals were used, what the model said, and what was
   dropped and why. If the model keeps reporting breaks that never closed beyond the level, improve the prompt.
   Never loosen the checks.

A new strategy idea = a new folder in `rules/strategy/` (see `rules/strategy/README.md`). Propose it in a pull
request with `status = "draft"`.

## Rules of the road
- **Never commit an API key or password.** Keep them in the environment or in `.env` (git ignores it).
- **Work on your own branch** (`friend/gpt-provider` …) and open a pull request into `main`.
- **`rules/` and `executor/limits.toml` are David's.** A new draft strategy is welcome; changing an existing rule
  goes in the pull request description first.
- **Don't edit `engine/`.** It trades on David's laptop right now. Anything you need from it goes through
  `concepter/toolkit.py`.
- **`shared/contracts.py` is the agreement between all parts.** Change it only after talking it over.
- `engine/third_party/` holds non-commercial licences (LuxAlgo port, SMC Zones): personal use only.
- Tests pass before you push. New behaviour gets a test in `tests/`.
