# Forex desk

Six Claude Code agents (`claude -p`) work one forex pair together, cycle by cycle. A conductor feeds them prices,
hard rules written in code decide what is actually allowed, and the order goes to a paper account or through
OpenClaw to `place_order.py` (simulated, OANDA demo or OANDA live).

This is the desk from `files.zip`, rebuilt for forex. The zip expected three modules that weren't in it
(`claude_trading_desk.py`, `llm_paper_trader.py`, `place_order.py`), so they're written here for FX.

```
market.json ─┬─> research ─┐
             └─> news ─────┴─> strategy ─> code ─> risk ─> boss ─> guard (code) ─> paper | OpenClaw ─> place_order.py
```

| role     | does                                                                    | tools                |
|----------|-------------------------------------------------------------------------|----------------------|
| research | trend, support/resistance, stretch, session liquidity                   | none                 |
| news     | central banks, data, calendar for both currencies; hours to next event  | WebSearch, WebFetch  |
| strategy | buy (long) / sell (short) / close / hold, with stop + target            | none                 |
| code     | recomputes pips, ATRs, reward:risk, side of price                       | none                 |
| risk     | approve / reduce / reject                                               | none                 |
| boss     | final call                                                              | none                 |

Each agent runs with `--safe-mode --tools …`. That keeps your own CLAUDE.md, MCP servers (Gmail, Drive…), hooks
and skills out of the desk; only the news agent can reach the web.

## Quick start

```bash
cp desk.env.example desk.env            # optional; defaults are paper-safe
python3 llm_paper_trader.py EUR/USD 1h  # check the price feed
python3 -m unittest discover -s tests   # offline tests

team/start_desk.sh paper mock           # plumbing test: fake prices, no Claude calls
team/start_desk.sh                      # real agents, live EUR/USD prices, paper money
SYMBOL=USD/JPY INTERVAL=4h BUDGET=200 MODEL=sonnet team/start_desk.sh
```

`start_desk.sh` uses tmux when it's installed (`sudo pacman -S tmux`). Without tmux it runs everything in the
current terminal, with agent output in `team/logs/`.

Pairs: any pair with USD on one side (EUR/USD, GBP/USD, AUD/USD, NZD/USD, USD/JPY, USD/CHF, USD/CAD).
Intervals: 15m, 30m, 1h, 4h, 1d. Cycles start just after each candle opens and pause from Friday 17:00 to
Sunday 17:00 New York.

## Money ladder

| command                      | desk.env                         | orders                                       | state file          |
|------------------------------|----------------------------------|----------------------------------------------|---------------------|
| `start_desk.sh paper mock`   | anything                         | simulated, fake prices                       | `mock_state.json`   |
| `start_desk.sh` (paper)      | anything                         | simulated, live prices                       | `paper_state.json`  |
| `start_desk.sh openclaw`     | `LIVE=0`                         | OpenClaw runs place_order.py, simulated      | `live_state.json`   |
| `start_desk.sh openclaw`     | `LIVE=1`, `OANDA_ENV=practice`   | OANDA **demo** account                       | `live_state.json`   |
| `start_desk.sh openclaw`     | `LIVE=1`, `OANDA_ENV=live`       | OANDA **real money**                         | `live_state.json`   |

Simulated fills pay the pair's typical spread. Live OANDA orders are FOK market orders with a slippage bound,
and they carry their stop-loss and take-profit, so the broker holds the stop even if this machine goes down.

## Hard rules (in code, `claude_trading_desk.guard` + `place_order.check_order`)

Opening a trade needs **all** of these. If any one fails, the decision is HOLD:
- no agent errors, boss direction = strategy direction, quant `valid`, risk approve/reduce, boss confidence ≥ 0.6
- long: stop < price < target, short: target < price < stop; reward:risk ≥ 1.5
- stop 0.5–3 ATR away and ≥ 4× the spread
- no high-impact event within 2 h (an event News flags for the next 24 h without a known time counts as now),
  not in the 16:45–17:15 NY rollover, not within 2 h of the weekly close
- daily realized loss under 3% of budget
- size: `budget × 1% × size_pct ÷ stop distance`, capped by 10× leverage and `MAX_NOTIONAL_USD` (computed by the
  guard; no agent ever picks the units)

One position at a time. While a position is open the desk can only hold or close it (an opposite signal means
exit, never flip). Closing is always allowed. Before the decision the guard re-checks the plan against the price
at that moment, not the price at cycle start. All limits are set in `desk.env`.

## OpenClaw handoff

In `openclaw` mode the conductor writes a ticket to `tickets/T….md` holding one exact command, for example:

```
python3 /home/david/forex/place_order.py --simulate open --symbol EUR/USD --price 1.1226 --ticket T… --side long --units 120 --stop 1.1205 --target 1.1260
```

and runs `OPENCLAW_CMD --message-file <ticket>` (default `openclaw agent --agent main --json --timeout 300`).
The conductor then checks the state file to see whether that ticket was really executed, and with what size.
It never relies on OpenClaw's reply. A ticket executes at most once, even if it is retried.
OpenClaw needs exec permission for `python3 /home/david/forex/place_order.py`. If its exec approvals prompt
for every command, approve that one, or the ticket times out and the desk records "did not execute".
The `stops` window (`place_order.py watch`) enforces simulated stops every 30 s and records when OANDA closes a trade.

## OANDA

1. Create a practice account at oanda.com, then generate an API token (My Account → Manage API Access).
2. Put `OANDA_TOKEN` and `OANDA_ACCOUNT` (like `101-001-1234567-001`) in `desk.env`.
3. `python3 place_order.py check` should print the account balance.
4. Set `LIVE=1` (still `OANDA_ENV=practice`) and run `team/start_desk.sh openclaw`.

With a token set, prices also come from OANDA instead of Yahoo.

## MT5 demo (Wine)

The MetaTrader 5 terminal runs under Wine (`WINEPREFIX=~/.mt5`, logged into the MetaQuotes-Demo account) and
the `MetaTrader5` package only exists for Windows, so the MT5 path has two halves:

- `mt5_bridge.py` runs under **Wine Python** and does the MT5 calls: account, symbol info, ticks, bars,
  positions, market orders with SL/TP attached, SL/TP changes, closes, deals. It takes a JSON batch of
  requests and writes the replies to a file.
- `mt5_client.py` is the Linux side: one Wine call per batch (≈1 s with the terminal open, ≈3 s cold),
  and server time → UTC (MetaQuotes-Demo runs on New York time + 7 h all year).

```bash
python3 mt5_client.py account            # login, equity, Algo Trading on/off, demo or not
python3 mt5_client.py positions
python3 mt5_client.py bars IBIT M5 10
python3 mt5_client.py close TICKET       # flatten one position by hand
```

Orders fail with retcode 10027 unless the terminal's Algo Trading button is on (Ctrl+E). MetaQuotes-Demo
lists Nasdaq stocks/ETFs, forex, metals and index CFDs, with no crypto: for 24/7 BTCUSD log the terminal
into a crypto-CFD broker's demo account. The client works with whatever account the terminal is on
(`find BTC` resolves the broker's symbol name, `offset BTCUSD` measures its server clock).

**This desk on MT5:** `BROKER=mt5` in desk.env (with `LIVE=1` to send orders) makes `place_order.py` trade the
terminal's account and the candles/prices come from MT5 too. Units become lots (EUR/USD: 0.01 lot = 1,000
units; XAUUSD: 1 lot = 100 oz), rounded down; below 0.01 lot the order is refused, so give it a `--budget`
and `MAX_NOTIONAL_USD` that size to at least that. `python3 place_order.py check` shows the MT5 account.

**The trading app's desk** (`~/treding/trading/backend`, `python -m intraday.mt5_desk`) uses this client
for one trade a day: `--market etf` (US bitcoin ETFs, MetaQuotes-Demo) or `--market crypto` (BTCUSD).

## Hand tools

```bash
python3 place_order.py status                                   # live_state.json
python3 place_order.py --state paper_state.json status          # paper account
python3 place_order.py close --symbol EUR/USD                   # flatten by hand
python3 place_order.py watch
```

## Files

```
llm_paper_trader.py     settings, pair maths, trading hours, candles (OANDA / Yahoo), indicators, MockFeed
place_order.py          account state, simulated + OANDA execution, stop watcher, CLI
claude_trading_desk.py  parse_json, mock_agent, guard, handoff (paper / OpenClaw ticket)
team/agent.py           one agent per role, watches team/cycles/<id>/
team/conductor.py       runs the cycles
team/start_desk.sh      opens the whole desk
team/roles/*.md         the six role prompts
tests/                  offline tests (+ a fake OpenClaw)
```

Each cycle leaves `team/cycles/<UTC time>-<n>/` containing market, account, the six reports and `final.json`
(the decision, the order and the execution result).

This is an experiment, not advice. Run it on paper and then on the OANDA demo account for a good while before
real money. LLM agents are not a proven edge, and leverage cuts both ways.
