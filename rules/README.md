# rules/: the strategies, written down

Rules never run. They are what the concepters follow. Each strategy is its own folder:

```
rules/<strategy>/
  concept.md     what the setup looks like on the chart: structure, zone, FVG …
  trade.md       how to trade it, always these four sections:
                   ## Entry
                   ## Stop loss
                   ## Take profit
                   ## Exit when it goes wrong
  params.toml    the same rules as numbers, for the code concepters (V5); [strategy] name / version / status
```

- **The words and the numbers say the same thing.** Change one, change the other in the same commit, and raise
  `version` in `params.toml`. The LLM concepters (Claude, GPT, Gemini) read the words. The V5 engine reads the
  numbers.
- **Only David changes a rule.** A concepter that thinks a rule is wrong says so in its notes. It does not trade
  around it.
- **A new strategy = copy `_template/`**, fill it in, and set `status = "draft"` until David approves it.

| strategy | status | who follows it today |
|---|---|---|
| `supply_demand` | live on demo (0.01 lot) | the V5 engine (`engine/`, reads `engine/config.py` until it is moved: see ARCHITECTURE.md) |
| `kronos_forecast` | forecast only (trading off since 2026-10-27) | Kronos (`kronos/` + `engine/kronos_book.py`) |
