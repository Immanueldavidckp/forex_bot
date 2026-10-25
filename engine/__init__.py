"""
engine — David's V5 strategy (H1 bias, M15 supply/demand + FVG, M5 BOS entry, dynamic layer) as a
code-only engine on the MT5 terminal: no Claude agents decide anything.

Built 2026-10-24 from a copy of the trading app's intraday engine (backend/intraday): its market-agnostic
analysis tools (tools/: swings, structure, FVGs, ATR …) are reused; the NSE-only parts (Shoonya, Upstox,
NSE universe, the Claude desk) were left behind (engine_data/intraday_copy_archive/).

  config.py     the V5 inputs + engine settings; control.json (trading on/off from the dashboard)
  feed.py       symbols (FxPro coins + forex majors) and bars per timeframe from MT5, in UTC
  strategy.py   V5 analysis on bars: bias, setups, trigger, target, layer, management maths
  book.py       picker → executor → monitor: setups, orders, layer, stop management, journal
  run.py        the loop (python3 -m engine.run …)
  dashboard.py  the chart page on 127.0.0.1:8770: every symbol × H4/H1/M30/M15/M5 with the V5 marks
  tools/        technical-analysis tools copied from the intraday engine
"""
