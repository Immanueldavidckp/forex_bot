# V5 engine (code only, MT5)

David's "MT5 EA — COMPLETE FINAL STRATEGY LOGIC V5" as an engine: no Claude agents, the code picks, enters
and manages. Built 2026-10-24 from a copy of the trading app's intraday engine; its analysis tools
(`tools/`) are reused, the NSE parts are archived in `../engine_data/intraday_copy_archive/`.

```
picker    H4 + H1 bias, they must agree (each HH+HL buy / LH+LL sell / else no trade)   (David 2026-10-25; was H1 only)
          → BOS on the setup's timeframe: a candle CLOSES beyond the last HH (buy) / LL (sell)   (David 2026-10-24)
          → in the BOS move (its start → the BOS candle): supply / demand = final opposite candle before
            a displacement ≥ 1.5 × the 10-bar average body; with none, the mitigation block
          → the FVGs of that move (required; with two or more the 2nd, counted left to right)
          → entry when price comes back 10 % into that FVG (seen live, never late)
          every timeframe H4 / H1 / M30 / M15 / M5 is analysed and drawn; only ENGINE["trade_tfs"] may enter
          three entries (David 2026-10-25): S&D M15 and S&D M30 = the setup above on that timeframe;
          S&D H4 = price back at an H4 setup's entry → an M15 BOS or CHoCH the same way whose move starts inside
            the H4 zone (H4 entry ↔ H4 invalidation) → that M15 move's own zone + FVG → entry 10 % inside it
            (an M15 trade: SL = its M15 zone); the H4 zone ends at an M15 close beyond its invalidation, a newer
            H4 BOS setup, 192 M15 bars, or once one of its entries is taken
executor  normal at market 2.5 % risk, SL = this setup's own zone (supply high / demand low) + 20 points,
          TP = first untouched opposite structure (setup TF / H1 / H4 swing) ≥ 1:3
          SL/TP fix (David 2026-10-24), checked right before the order, any NO → no trade, nothing moved to pass:
          BOS / zone / FVG all of this one setup, SL on the right side and ≤ 3 × M15 ATR(14),
          a real structure target on the right side (none → no trade, never a made-up 3R), RR ≥ 3, < 20 positions
          + ONE dynamic layer (pending limit, 1.5 %) at 25 / 40 / 55 % of entry→SL by movement strength
monitor   Mode A: original SL until ≥ 80 % of the way to TP and a reversal → break-even
          Mode B (layer filled): Target 1 = centre → both SLs past the first entry, then M5-swing trailing
          from 3R: lock (n − 2)R at nR + M5-swing trailing; a stop only moves toward profit
limits    ≤ 20 open positions (pending layers reserve their slot), no daily trade limit
```

Dashboard (David 2026-10-25): every card shows the three entries — **S&D H4**, **S&D M30**, **S&D M15** — each on
the chart its entry is taken on (S&D H4 = M15 with the H4 zones on it). Click one: its two timeframes (S&D H4: H4 zones
+ M15 entry; S&D M30 / M15: H4 for the bias only + that timeframe) and every mark on / off — only that entry
(remembered in the browser). Setups superseded by a newer BOS setup are not drawn.

## Run (from `~/forex`, system `python3`)

```bash
python3 -m engine.run check            # account, symbols, one analysis pass, no orders
python3 -m engine.run run              # the loop (service: v5-engine)
python3 -m engine.dashboard            # http://127.0.0.1:8770 (service: v5-dashboard)
python3 -m engine.run trading on|off   # or the button on the dashboard
python3 -m pytest -q engine            # offline tests (fake MT5)
```

Backtest (the live strategy code replayed on FxPro's history, David 2026-10-25: find the worthless setups from data):

```bash
python3 -m engine.history               # bars from MT5 → engine_data/history/<SYMBOL>.json (≈ 11 months M5 coins, 16 forex)
python3 -m engine.backtest run          # every touched setup + outcome + chart features → engine_data/backtest/setups.jsonl
python3 -m engine.backtest report       # the engine now, the live filters, targets, features, rules trained on
                                        # the older 60 % and judged on the newer 40 % → engine_data/backtest/report.txt
python3 -m engine.bt_charts --n 12      # pictures of winners / losers → engine_data/backtest/charts/
```

Services: `systemctl --user status|stop|restart v5-engine v5-dashboard` (systemd user units, enabled at login).

**The engine runs MT5 itself** (`engine/terminal.py`, David 2026-10-25). The terminal is the user unit `mt5-terminal`
(started by the engine, not at login), so an engine restart never closes it. Every loop: not running → start; MT5
calls fail twice, or Wine was updated under it → restart (unit + stray terminal / wineserver of `~/.mt5`); not
connected for 2 min → restart; other or no account → log in to `ENGINE["mt5_login"]` (the terminal's saved password,
or `MT5_PASSWORD` in `engine_data/mt5.env`); Algo Trading off → `common.ini [Experts] Enabled=1` + restart (hourly).
Restarts ≥ 3 min apart, after 5 in an hour 15 min apart. `stop` keeps it off (`control.json "mt5": "off"`) until `start`.
The engine service sets `MT5_NO_LAUNCH=1`, so its own MT5 calls never start a terminal outside the unit.

```bash
python3 -m engine.run mt5 status|start|stop|restart|login     # or the MT5 buttons in the dashboard header
``` Log: `engine_data/engine.log`,
decisions: `engine_data/journal.jsonl`, state: `engine_data/state.json`.

Size: since 2026-10-25 `ENGINE["lot_mode"] = "min"` — every normal and layer order is the symbol's minimum lot (0.01),
to test the engine without real exposure (David); `"risk"` = V5's 2.5 % / 1.5 % sizing.

Starts in **watch mode**: complete setups are recorded as "signal" and drawn, nothing is sent until trading
is switched on. Orders need a demo account and the terminal's Algo Trading on. Magic number 5050505.

## Choices made where V5 describes judgement in words (all in `config.py`)

| V5 | engine |
|---|---|
| BOS (pictures, 2026-10-24) | a candle CLOSE beyond a swing labelled HH (buy) / LL (sell); beyond an LH / HL it is a CHoCH (always drawn, light grey; not traded). Swings stay breakable until closed through; a break drops the other side's swings older than its move |
| "supply / demand at the BOS" | V5 §3-4 inside the BOS move (from the lowest low / highest high since the broken swing to the BOS candle) |
| "mitigation block when no supply / demand" | §6 pattern inside the BOS move, used only when that move has no supply / demand zone |
| "FVG inside the BOS", "3 FVGs → the 2nd" | every FVG whose middle candle lies in the BOS move; with 2 or more the 2nd from the left (`fvg_pick`) |
| "entry like 10 %" | 10 % inside that FVG from the side price comes back from (`fvg_entry_depth`) |
| newer BOS before the pullback | the older setup is "superseded" (not traded), but only by a BOS that has its own setup (zone or MB + FVG); a small BOS without one is not used and cancels nothing (David 2026-10-24, kept 2026-10-25). The entry views of the dashboard don't draw superseded setups |
| S&D H4 trigger (2026-10-25) | the first and every later M15 BOS / CHoCH the same way after price reached the H4 entry, whose move's start lies between the H4 entry and the H4 invalidation; a BOS that already has its S&D M15 setup is that same setup (one trade, marked with the H4 parent) |
| §13-14 layer depth by movement | weak / moderate / strong = 0-1 / 2 / 3 of: retracement bodies ≥ 1.3 × the 20 before, ≥ 4 candles in a row, ≥ 1.5 M5 ATR travelled → depth 25 / 40 / 55 % |
| §22 "very close to the target and reversal begins" | best price ≥ 80 % of the way, then gave back 10 % or an M5 candle closed against |
| §26 Target 1 "centre" | halfway between the normal entry and the final target |
| §27-28 "SL below/above the first entry" | first entry ∓ max(0.1 R, 20 points) |
| §31 protect more at 3R / 4R / 5R | lock (n − 2)R at nR, plus M5-swing trailing |
| entry only live | price must reach the entry in the forming or latest completed (recent) M5 bar; earlier ones are "missed", never traded late |
| not in V5 | refuse when the spread is over 35 % of the stop distance, or the SL/TP is inside the broker's stops level from the closing price (ask for sells, bid for buys) |
| §2 bias | HH+HL but the last H1 close below the last HL (or LH+LL and a close above the last LH) = broken = no trade |
