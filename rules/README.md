# rules/: everything written down. Rules never run anything.

```
rules/
  concept/            WHAT EACH ENGINE LOOKS FOR on the chart (one folder per engine in concepter/)
    v5/                 concept.md (words) + params.toml (numbers): BOS → zone → FVG → setup
    kronos/             the forecast: 16 paths of the next 8 M15 bars → direction
    claude/             the model judges David's structure: BOS / CHoCH / direction (new)
  strategy/           THE RECIPES, common to all engines: which engine gives what, then entry · SL · TP · exit
    v5_supply_demand/            V5 alone: the live strategy on demo
    kronos_forecast/             Kronos alone: forecast-only now
    kronos_direction_claude_bos/ David's example: direction from Kronos, BOS from Claude (draft)
```

- **Concept = one engine's eyes. Strategy = how the eyes are combined into a trade.** An engine reports signals
  (a direction, a BOS, a setup …). A strategy picks the signals it wants from the engines it wants, and says where the
  entry, the stop and the target go. How to write one: `strategy/README.md`.
- **Words and numbers say the same thing.** The Claude engine reads the words; the code reads the numbers. Change
  both in the same commit and raise the version.
- **Only David changes a rule.** An engine that finds a rule unclear says so in its notes; it does not work around it.
- **A new engine** = a folder here in `concept/` + one in `concepter/`. **A new strategy** = a folder in `strategy/`,
  no new code.
