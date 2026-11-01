# Working on this together

Read `ARCHITECTURE.md` first (5 minutes). Short version: **rules** = the strategy in writing, **concepters** =
whatever reads the chart and decides (code or an LLM), **executor** = carries out trades behind fixed safety
limits.

## What you need
- Python 3.11 or newer, `pip install numpy pytest`
- No MetaTrader, no broker account. Everything here runs on the recorded bars in `shared/sample_data/` (60 days of
  GOLD + EURUSD, M5 / M15 / H1 / H4) with the paper executor.

```
python3 -m pytest tests/test_architecture.py -q                     # must pass before and after your change
python3 -m concepters.run --concepter demo --symbols GOLD,EURUSD     # see the whole chain work
```

## Your first job: GPT and Gemini as concepters
`concepters/llm/concepter.py` already does the work: the prompt (role + the strategy's rules + the answer format),
the chart packet, reading and checking the answer. What is missing is the model call:

1. In `concepters/llm/providers.py`, add a class per model with `name = "gpt"` (or `"gemini"`) and
   `complete(system: str, user: str) -> str`, and return it from `get()`. Read the API key from the environment
   (`OPENAI_API_KEY`, `GEMINI_API_KEY`) and the model name from `LLM_MODEL`. Ask the model for JSON only.
2. Try it on a few days first, because every call costs money:
   `python3 -m concepters.run --concepter llm --provider gpt --symbols GOLD --days 2`
   With the default `--ask near_zone`, the model is only asked when price is near a live S&D zone or a trade is open.
3. Look at `runs/<name>/journal.jsonl`: what the model said each time, and which answers were refused and why.
   If it keeps breaking a rule, improve the prompt. Never loosen `concepters/checks.py`.

## Rules of the road
- **Never commit an API key or password.** Keep them in the environment or in `.env` (git ignores it).
- **Work on your own branch** (`friend/gpt-provider` …) and open a pull request into `architecture`.
- **Don't edit `rules/` or `executor/limits.toml`.** They are David's. If you think a rule is wrong or unclear,
  write it in the pull request.
- **Don't edit `engine/`.** It trades on David's laptop right now. Everything you need from it goes through
  `shared/toolkit.py`.
- **`shared/contracts.py` is the agreement between all parts.** Change it only after talking it over.
- `engine/third_party/` holds non-commercial licences (LuxAlgo port, SMC Zones): personal use only.
- Tests pass before you push. New behaviour gets a test in `tests/`.
