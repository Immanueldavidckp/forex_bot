#!/usr/bin/env python3
"""
conductor.py - starts each cycle, waits for the six agents, applies the hard guard,
then hands the order to OpenClaw (or the paper account).

  python3 conductor.py                               # EUR/USD 1h, live prices, paper money
  python3 conductor.py --symbol USD/JPY --interval 4h --budget 200
  python3 conductor.py --handoff openclaw            # OpenClaw executes via place_order.py
  python3 conductor.py --mock-data --cycles 5        # fake prices, for testing with agent.py --mock

Cycles start just after each candle opens and pause while the forex market is closed
(Friday 17:00 to Sunday 17:00 New York).
"""
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import place_order as po  # noqa: E402
from claude_trading_desk import guard, handoff  # noqa: E402
from llm_paper_trader import (CFG, INTERVAL_SEC, MOCK_START, MockFeed, decimals, fetch_candles,  # noqa: E402
                              fetch_price, hours_to_close, in_rollover, indicators, market_open, norm, now,
                              pip_size, pnl_usd, sessions, spread_pips)

ROLES = ["research", "news", "strategy", "code", "risk", "boss"]
CYCLES = os.path.join(HERE, "cycles")


def write(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path)


def start_cycle(args, candles, n):
    d = os.path.join(CYCLES, time.strftime("%Y%m%d-%H%M%S", time.gmtime()) + f"-{n:04d}")   # UTC, like the logs
    os.makedirs(d)
    sym, dp, pip = args.symbol, decimals(args.symbol), pip_size(args.symbol)
    price, last = candles[-1]["c"], candles[-24:]
    st = po.load()
    held = st["position"]
    write(os.path.join(d, "account.json"), {
        "budget_usd": args.budget, "holding": held, "today_realized_pnl": round(st["day_pnl"], 2),
        "holding_unrealized_pnl": round(pnl_usd(sym, held["side"], held["units"], held["entry"], price), 2)
        if held else None,
        "risk_per_trade_usd": round(args.budget * float(CFG["RISK_PER_TRADE_PCT"]) / 100, 2),
        "max_leverage": float(CFG["MAX_LEVERAGE"])})
    ind = indicators(candles)
    market = {"symbol": sym, "interval": args.interval, "price": round(price, dp), "time": now(), "pip_size": pip,
              "typical_spread_pips": spread_pips(sym), "sessions_open": sessions(), "rollover_window": in_rollover(),
              "hours_to_weekly_close": round(hours_to_close(), 1),
              "last_24_closes": [round(c["c"], dp) for c in last],
              "high_24": round(max(c["h"] for c in last), dp), "low_24": round(min(c["l"] for c in last), dp),
              "ema20": round(ind["ema20"], dp), "ema50": round(ind["ema50"], dp), "rsi14": round(ind["rsi14"], 1),
              "atr14": round(ind["atr14"], dp), "atr14_pips": round(ind["atr14"] / pip, 1)}
    write(os.path.join(d, "market.json"), market)   # this file wakes up research + news
    return d, market


def wait_for_team(d, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if os.path.exists(os.path.join(d, "boss.json")):
            return True
        time.sleep(2)
    return False


def report_exit(done):
    if done:
        print(f"  {done['reason'].upper()}: closed {done['side']} {done['symbol']} at {done['exit']}"
              f"  P&L {done['pnl']:+.2f}", flush=True)


def check_position(args, candles):
    """Before each cycle: simulated stops against the candles, or book what OANDA closed."""
    try:
        report_exit(po.sync() or po.check_exits(candles))   # each one ignores the other kind of position
    except Exception as e:
        print("  position check error:", e, flush=True)


def wait_next(args):
    """Sleep until just after the next candle opens; meanwhile keep a paper position's stop and target honest."""
    step = INTERVAL_SEC[args.interval]
    nxt = (time.time() // step + 1) * step + 20
    while (left := nxt - time.time()) > 0:
        time.sleep(min(60, left))
        if args.handoff == "paper" and po.load()["position"]:
            try:
                report_exit(po.check_price(fetch_price(args.symbol)))
            except Exception as e:
                print("  price check error:", e, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="EUR/USD", help="a USD pair: EUR/USD GBP/USD AUD/USD NZD/USD USD/JPY ...")
    ap.add_argument("--interval", default="1h", choices=INTERVAL_SEC)
    ap.add_argument("--budget", type=float, default=50, help="USD; each trade risks RISK_PER_TRADE_PCT of it")
    ap.add_argument("--handoff", default="paper", choices=["paper", "openclaw"])
    ap.add_argument("--team-timeout", type=int, default=900, help="seconds to wait for the boss")
    ap.add_argument("--cycles", type=int, default=0, help="0 = forever")
    ap.add_argument("--mock-data", action="store_true")
    args = ap.parse_args()
    args.symbol = norm(args.symbol)

    if args.handoff == "paper":       # paper can never send real orders, whatever desk.env says
        po.LIVE = False
        po.STATE_FILE = os.path.join(po.HERE, "paper_state.json")
    if args.mock_data:                # fake prices never reach a broker or the real paper account
        po.LIVE = False
        po.STATE_FILE = os.path.join(po.HERE, "mock_state.json")
        if os.path.exists(po.STATE_FILE):
            os.remove(po.STATE_FILE)
    held = po.load()["position"]
    if held and held["symbol"] != args.symbol:
        sys.exit(f"{os.path.basename(po.STATE_FILE)} holds {held['symbol']}; close it first "
                 f"(python3 place_order.py close) or run the desk on {held['symbol']}")
    os.makedirs(CYCLES, exist_ok=True)
    feed = MockFeed(7, start=MOCK_START.get(args.symbol, 1.0)) if args.mock_data else None
    money = (f"OANDA {CFG['OANDA_ENV'].upper()}" + (" - REAL MONEY" if CFG["OANDA_ENV"] == "live" else " demo")
             if po.LIVE else "simulated")
    print(f"=== CONDUCTOR {args.symbol} every {args.interval}, budget ${args.budget:g}, handoff={args.handoff}, "
          f"orders {money} ===", flush=True)

    n = 0
    while args.cycles == 0 or n < args.cycles:
        if not args.mock_data and not market_open():
            print(f"{now()} forex market closed until Sunday 17:00 New York - waiting", flush=True)
            while not market_open():
                time.sleep(300)
            continue
        n += 1
        try:
            candles = feed.get() if feed else fetch_candles(args.symbol, args.interval)
        except Exception as e:
            print("data error:", e, flush=True)
            time.sleep(60)
            continue
        check_position(args, candles)

        d, market = start_cycle(args, candles, n)
        print(f"\n{now()} cycle {os.path.basename(d)} {args.symbol} {market['price']} - team working...", flush=True)
        order = result = None
        if wait_for_team(d, args.team_timeout):
            reports = {r: json.load(open(os.path.join(d, f"{r}.json"))) for r in ROLES}
            st = po.load()                        # the position may have been stopped out while the team worked
            if not args.mock_data:                # judge the plan against the price now, not at cycle start
                try:
                    market = {**market, "price": round(fetch_price(args.symbol), decimals(args.symbol)),
                              "rollover_window": in_rollover(), "hours_to_weekly_close": round(hours_to_close(), 1)}
                except Exception as e:
                    print("  price refresh failed, using cycle price:", e, flush=True)
            final = guard(reports, market, st["position"], args.budget, st["day_pnl"])
            if final["action"] in ("buy", "sell", "close"):
                order, result = handoff(final, args.symbol, args.handoff, market["price"])
        else:
            final = {"action": "hold", "why": "team timed out"}
        write(os.path.join(d, "final.json"), {"final": final, "order": order, "result": result})
        open(os.path.join(d, "closed"), "w").close()
        size = f" {final['side']} {final['units']} units" if final.get("units") else ""
        print(f"  DECISION {final['action'].upper()}{size}: {final.get('why', '')[:90]}", flush=True)
        if result:
            print(f"  EXECUTION {result}", flush=True)

        if not args.mock_data and (args.cycles == 0 or n < args.cycles):
            wait_next(args)

    s = po.load()
    print(f"\nrealized P&L {s['total_pnl']:+.2f}  holding {s['position'] or 'nothing'}")


if __name__ == "__main__":
    main()
