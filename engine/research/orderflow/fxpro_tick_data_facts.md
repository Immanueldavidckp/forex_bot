# FxPro MT5 demo data sample for the order-flow research (pulled 2026-10-29 19:08 IST, read-only)

Files
- GOLD_ticks.csv.gz, EURUSD_ticks.csv.gz — every tick of the last ~3 days from MetaTrader5.copy_ticks_range(COPY_TICKS_ALL).
  Columns: time_msc_server, bid, ask, last, volume, volume_real, flags.
  time_msc_server = FxPro SERVER wall clock (EET: UTC+2 since 2026-10-25) written as epoch ms → UTC ms = value − 7,200,000.
  IST (what David reads) = UTC + 5:30.
- GOLD_depth_60s.json, EURUSD_depth_60s.json — 60 snapshots (1 per second) of MetaTrader5.market_book_get():
  [{"t_local_ms", "tick_time_msc_server", "bid", "ask", "book": [[type, price, volume], ...]}], type 1 = SELL (ask side), 2 = BUY (bid side).
- stats.json — counts per tick flag, symbol facts.

What the data is (checked):
- MT5 flags: BID=2, ASK=4, LAST=8, VOLUME=16, BUY=32, SELL=64. BUY / SELL are NEVER set → no aggressor side from the broker.
- `last` equals the bid on ~97 % of ticks; `volume` is a constant (GOLD 110 or 130, EURUSD always 200000) = the quoted
  size, NOT traded volume. FxPro is an OTC CFD broker: there is no exchange tape. Real traded volume is not available.
- GOLD: ~2.8 M ticks / 3 days, digits 2 (0.01), contract 100 oz. EURUSD: ~1.3 M ticks, digits 5.
- Depth: ~10 levels per side, sizes look like fixed broker tiers (GOLD mirrored: 110/100…/200/1400/25000).
