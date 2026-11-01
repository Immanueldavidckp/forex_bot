# Shared brief — supply & demand research for David's /smc page (2026-10-30)

David (trader, owner of the project) asked: "here it have missed the supply and demand — this is an important topic;
supply and demand should be the VALID one, it has to show the supply or demand only for the valid one; go to the
internet and all open source and all available sources to find and select the supply and demand."

## Rules you must follow
- Research only. Do NOT edit anything under /home/david/forex. Do NOT call any mt5 / MetaTrader MCP tools, do NOT run
  Wine or MT5. Do NOT write to any Obsidian vault (~/Obsidian, ~/FOREXBOT): the main session logs.
- Write only into your own folder under /tmp/claude-1000/-home-david-forex/6f79950b-2f79-4743-8184-d36a070b7e52/scratchpad/sd_research/
- Python3 + numpy 2.5 only (no pandas). Run Python that reads downloaded/cloned code with `python3 -I`.
- Cite URLs; at least two independent sources for every rule; say where sources disagree and recommend one.

## David's own rules (they WIN where they define a thing) — read-only files
- ~/FOREXBOT/FOREXBOT/1 Strategy/Rules/Supply and Demand.md, ~/FOREXBOT/FOREXBOT/1 Strategy/Rules/new rules.md (§8–16),
  ~/FOREXBOT/FOREXBOT/1 Strategy/V5 Strategy (original).md (§3–6).
- Summary: Supply = the final bullish candle before a strong bearish displacement; Demand = the final bearish candle
  before a strong bullish displacement. Displacement = a candle body ≥ 1.5 × the average body of the previous 10
  candles. The displacement must break a valid previous confirmed swing low (supply) / high (demand) with a candle
  CLOSE beyond it (= BOS) → only then the zone is VALID; no BOS → INVALID, do not mark it. "Do NOT mark every
  supply / demand: only valid BOS-producing zones." The FVG of the same displacement is required for a trade setup.
  An FVG traded back into within 2 candles, or before a 0.5 ATR run, makes the setup invalid.

## What exists in the code (read-only, for conventions and to build on)
- /home/david/forex/engine/major_structure.py — David's structure rule: BOS at the leg extreme, CHoCH only at the
  protected swing, no internal breaks (this is the page's "BOS / CHoCH").
- /home/david/forex/engine/smc_marks.py — OB / FVG / liquidity / premium-discount on that structure. Its OB is already
  "the last opposite candle before the last displacement of each major break" (David's V5 candle). David says S&D is
  MISSING, so the S&D layer must be the supply/demand METHOD (base candles before an explosive move, zone edges,
  freshness, validity / odds enhancers), consistent with his rules, and the report must say how it differs from OB.
- /home/david/forex/engine/strategy.py (`_zone`, displacement), /home/david/forex/engine/config.py (STRATEGY values).

## Data (read-only)
- /home/david/forex/engine_data/history/<SYMBOL>.json, 54 FxPro symbols (GOLD, EURUSD, GBPUSD, USDJPY, AUDUSD, …,
  BITCOIN, ETHEREUM, …): {"bars": {"M5"|"M15"|"M30"|"H1"|"H4": [[t_ms_utc_open, open, high, low, close, spread,
  tick_volume], ...]}} (oldest first; M5 99,000 bars, M15 33,000, H1 8,500, H4 2,200; only GOLD + EURUSD carry tick
  volume, other files have 6 columns). Times are UTC ms; David reads IST (UTC+5:30).
