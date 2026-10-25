#!/usr/bin/env python3
"""
place_order.py - the only part of the desk that touches money: account state plus order execution.
Fills are simulated unless desk.env has LIVE=1; then orders go to the broker: OANDA (OANDA_ENV=practice is
a demo account, OANDA_ENV=live is real money), or with BROKER=mt5 the MT5 terminal under Wine through
mt5_client.py (demo accounts only unless MT5_ALLOW_REAL=1). MT5 trades in lots: the desk's units become
units / contract size, rounded down to the lot step. Live orders carry their stop and target, so the
broker holds them even if this machine dies.

  python3 place_order.py status
  python3 place_order.py check                     # are the OANDA settings working?
  python3 place_order.py open --symbol EUR/USD --side long --units 250 --stop 1.08120 --target 1.08700 --price 1.08300
  python3 place_order.py close --symbol EUR/USD
  python3 place_order.py watch                     # enforce simulated stops / book broker closes
  python3 place_order.py --simulate --state paper_state.json status

The conductor (directly, or through OpenClaw from a ticket) runs open/close with --ticket ID;
a ticket executes at most once, and what it did is recorded in the state file.
"""
import argparse, contextlib, fcntl, json, os, sys, time

from llm_paper_trader import (CFG, decimals, fetch_price, instrument, norm, notional_usd, now, oanda, pip_size,
                              pnl_usd, spread_pips, trading_day)

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = CFG["LIVE"] == "1"
DEFAULT_STATE = os.path.join(HERE, "live_state.json")
STATE_FILE = DEFAULT_STATE


# ---------------------------------------------------------------- state
def blank():
    return {"position": None, "day": trading_day(), "day_pnl": 0.0, "total_pnl": 0.0, "trades": [], "tickets": {}}


def load():
    try:
        with open(STATE_FILE) as f:
            st = {**blank(), **json.load(f)}
    except FileNotFoundError:
        st = blank()
    if st["day"] != trading_day():
        st["day"], st["day_pnl"] = trading_day(), 0.0
    return st


def save(st):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=1)
    os.replace(tmp, STATE_FILE)


@contextlib.contextmanager
def locked():
    """Load-modify-save under a file lock: conductor, stop watcher and OpenClaw may all touch the state."""
    with open(STATE_FILE + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        st = load()
        yield st
        save(st)


def mt5():
    return CFG["BROKER"] == "mt5"


def mode():
    if not LIVE:
        return "simulated"
    return "mt5" if mt5() else f"oanda-{CFG['OANDA_ENV']}"


def _account():
    if not CFG["OANDA_ACCOUNT"]:
        raise RuntimeError("OANDA_ACCOUNT is not set in desk.env")
    return CFG["OANDA_ACCOUNT"]


def _half_spread(symbol):
    return spread_pips(symbol) * pip_size(symbol) / 2


def _book(st, exit_price, reason, pnl=None):
    p = st["position"]
    if pnl is None:
        pnl = pnl_usd(p["symbol"], p["side"], p["units"], p["entry"], exit_price)
    trade = {**p, "exit": round(exit_price, decimals(p["symbol"])), "closed": now(), "reason": reason,
             "pnl": round(pnl, 2)}
    st["trades"] = st["trades"][-199:] + [trade]
    st["day_pnl"] += pnl
    st["total_pnl"] += pnl
    st["position"] = None
    return trade


def _record(st, ticket, res):
    if ticket:
        st["tickets"] = dict(list(st["tickets"].items())[-99:])
        st["tickets"][ticket] = res
    return res


# ---------------------------------------------------------------- orders
def check_order(symbol, side, units, stop, target, price):
    """Last line of defence, whoever is calling: sane side, size and stop/target geometry."""
    if side not in ("long", "short"):
        return f"side must be long or short, not {side}"
    if not (isinstance(units, int) and units >= 1):
        return "units must be a whole number >= 1"
    lo, hi = (stop, target) if side == "long" else (target, stop)
    if not lo < price < hi:
        return f"{side} needs {'stop < price < target' if side == 'long' else 'target < price < stop'}"
    value, cap = notional_usd(symbol, units, price), float(CFG["MAX_NOTIONAL_USD"])
    if value > cap:
        return f"order worth ${value:,.0f} is above MAX_NOTIONAL_USD ${cap:,.0f}"
    return None


def open_position(symbol, side, units, stop, target, price=None, ticket=None):
    symbol = norm(symbol)
    with locked() as st:
        if ticket and ticket in st["tickets"]:
            return st["tickets"][ticket]               # same ticket twice (a retry) -> same answer, no new order
        return _record(st, ticket, _open(st, symbol, side, units, stop, target, price))


def _open(st, symbol, side, units, stop, target, price):
    if st["position"]:
        return {"ok": False, "error": f"already holding {st['position']['side']} {st['position']['symbol']}"}
    try:
        price = price or fetch_price(symbol)
        err = check_order(symbol, side, units, stop, target, price)
        if err:
            return {"ok": False, "error": err}
        if LIVE and mt5():
            fill, trade_id, units = _mt5_open(symbol, side, units, stop, target, price)
        elif LIVE:
            fill, trade_id = _oanda_open(symbol, side, units, stop, target, price)
        else:
            h = _half_spread(symbol)
            fill, trade_id = (price + h if side == "long" else price - h), None
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
    fill = round(fill, decimals(symbol))
    st["position"] = {"symbol": symbol, "side": side, "units": units, "entry": fill, "stop": stop,
                      "target": target, "opened": now(), "opened_t": time.time(), "mode": mode(),
                      "trade_id": trade_id, "broker": ("mt5" if mt5() else "oanda") if trade_id else None}
    return {"ok": True, "mode": mode(), "action": "open", "symbol": symbol, "side": side, "units": units,
            "fill": fill, "stop": stop, "target": target, "trade_id": trade_id}


def _oanda_open(symbol, side, units, stop, target, price):
    d, slip = decimals(symbol), float(CFG["MAX_SLIPPAGE_PIPS"]) * pip_size(symbol)
    bound = price + slip if side == "long" else price - slip      # FOK: no fill beyond this price
    order = {"type": "MARKET", "instrument": instrument(symbol), "units": str(units if side == "long" else -units),
             "timeInForce": "FOK", "positionFill": "DEFAULT", "priceBound": f"{bound:.{d}f}",
             "stopLossOnFill": {"price": f"{stop:.{d}f}"}, "takeProfitOnFill": {"price": f"{target:.{d}f}"}}
    r = oanda(f"/v3/accounts/{_account()}/orders", {"order": order}, "POST")
    fill = r.get("orderFillTransaction") or {}
    if not fill.get("tradeOpened"):
        raise RuntimeError("OANDA: " + ((r.get("orderCancelTransaction") or {}).get("reason") or "order not filled"))
    return float(fill["price"]), fill["tradeOpened"]["tradeID"]


def _mt5_account():
    import mt5_client
    a = mt5_client.account()
    if not a.get("demo") and CFG["MT5_ALLOW_REAL"] != "1":
        raise RuntimeError(f"MT5 terminal is on a REAL account ({a['server']} {a['login']}); set MT5_ALLOW_REAL=1 to allow it")
    if not a.get("algo_trading"):
        raise RuntimeError("Algo Trading is off in the MT5 terminal (Ctrl+E)")
    return a


def _mt5_open(symbol, side, units, stop, target, price):
    """Market order with stop + target. -> (fill, position ticket, units actually traded)."""
    import mt5_client
    from llm_paper_trader import mt5_symbol
    _mt5_account()
    sym = mt5_symbol(symbol)
    info = mt5_client.info(sym)
    contract, step, vmin = float(info["trade_contract_size"]), float(info["volume_step"]), float(info["volume_min"])
    lots = round(int(units / contract / step + 1e-9) * step, 8)
    if lots < vmin:
        raise RuntimeError(f"{units} units is below the MT5 minimum of {vmin:g} lot ({vmin * contract:g} units)")
    dev = max(1, int(float(CFG["MAX_SLIPPAGE_PIPS"]) * pip_size(symbol) / float(info["point"])))
    magic = int(CFG["MT5_MAGIC"])
    r = mt5_client.order(sym, "buy" if side == "long" else "sell", lots, stop, target, magic, "forex desk", dev)
    if not r.get("ok"):
        raise RuntimeError(f"MT5: {r.get('retcode')} {r.get('comment')}")
    pos = [p for p in mt5_client.positions(magic, sym)]
    p = max(pos, key=lambda p: p["time_msc"]) if pos else None
    return float(p["price_open"] if p else r["price"]), (p["ticket"] if p else r.get("order")), int(round(lots * contract))


def _mt5_closed(ticket):
    """(exit price, realized P&L incl. commission and swap) of a closed MT5 position, or None while it is open."""
    import mt5_client
    if any(p["ticket"] == int(ticket) for p in mt5_client.positions(int(CFG["MT5_MAGIC"]))):
        return None
    ds = mt5_client.deals(position=int(ticket))
    outs = [d for d in ds if d["entry"] == 1]
    pnl = sum(float(d.get(k, 0) or 0) for d in ds for k in ("profit", "commission", "swap", "fee"))
    return (float(outs[-1]["price"]) if outs else None), pnl


def close_position(symbol=None, price=None, reason="desk", ticket=None):
    with locked() as st:
        if ticket and ticket in st["tickets"]:
            return st["tickets"][ticket]
        return _record(st, ticket, _close(st, symbol, price, reason))


def _close(st, symbol, price, reason):
    p = st["position"]
    if not p:
        return {"ok": False, "error": "no open position"}
    if symbol and norm(symbol) != p["symbol"]:
        return {"ok": False, "error": f"open position is {p['symbol']}, not {norm(symbol)}"}
    try:
        if p.get("broker") == "mt5":
            import mt5_client
            r = mt5_client.close(int(p["trade_id"]), f"forex desk {reason}"[:31])
            if not r.get("ok"):
                raise RuntimeError(f"MT5 close: {r.get('retcode')} {r.get('comment')}")
            done = None
            for _ in range(5):                      # the deal reaches the history a moment after the fill
                done = _mt5_closed(p["trade_id"])
                if done and done[0] is not None:
                    break
                time.sleep(1)
            px = (done[0] if done and done[0] is not None else float(r.get("price") or p["entry"]))
            trade = _book(st, px, reason, done[1] if done else None)
        elif p.get("trade_id"):                     # a broker trade is closed at the broker, whatever LIVE says now
            f = oanda(f"/v3/accounts/{_account()}/trades/{p['trade_id']}/close", {"units": "ALL"},
                      "PUT")["orderFillTransaction"]
            trade = _book(st, float(f["price"]), reason, float(f.get("pl", 0)) + float(f.get("financing", 0)))
        else:
            px, h = price or fetch_price(p["symbol"]), _half_spread(p["symbol"])
            trade = _book(st, px - h if p["side"] == "long" else px + h, reason)
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
    return {"ok": True, "mode": p["mode"], "action": "close", "symbol": p["symbol"], "side": p["side"],
            "units": p["units"], "exit": trade["exit"], "pnl": trade["pnl"]}


# ---------------------------------------------------------------- stops
def check_exits(candles):
    """Simulated position: close at the stop or target once the bid (long) / ask (short) reaches it.
    Candles that ended before the position opened are ignored and the one it opened in counts only
    with its close; a gap through a level fills at the gapped price. Stop wins when one candle touches both."""
    with locked() as st:
        p = st["position"]
        if not p or p.get("trade_id"):
            return None                              # broker trades carry real stops at OANDA, see sync()
        before = [c for c in candles if c["t"] < p["opened_t"]]
        bars = [(c["c"],) * 3 for c in before[-1:]] + [(c["o"], c["h"], c["l"]) for c in candles
                                                        if c["t"] >= p["opened_t"]]
        h = _half_spread(p["symbol"]) * (-1 if p["side"] == "long" else 1)
        for o, hi, lo in bars:
            o, hi, lo = o + h, hi + h, lo + h
            if p["side"] == "long":
                if o <= p["stop"] or o >= p["target"]:
                    return _book(st, o, "stop" if o <= p["stop"] else "target")
                if lo <= p["stop"]:
                    return _book(st, p["stop"], "stop")
                if hi >= p["target"]:
                    return _book(st, p["target"], "target")
            else:
                if o >= p["stop"] or o <= p["target"]:
                    return _book(st, o, "stop" if o >= p["stop"] else "target")
                if hi >= p["stop"]:
                    return _book(st, p["stop"], "stop")
                if lo <= p["target"]:
                    return _book(st, p["target"], "target")
    return None


def check_price(price):
    return check_exits([{"t": time.time(), "o": price, "h": price, "l": price, "c": price}])


def sync():
    """Broker trade: if OANDA closed it (stop or target), book the realized result."""
    with locked() as st:
        p = st["position"]
        if not p or not p.get("trade_id"):
            return None
        if p.get("broker") == "mt5":
            done = _mt5_closed(p["trade_id"])
            if not done:
                return None
            px = done[0] if done[0] is not None else p["entry"]
            reason = "stop" if abs(px - p["stop"]) < abs(px - p["target"]) else "target"
            return _book(st, px, reason, done[1])
        t = oanda(f"/v3/accounts/{_account()}/trades/{p['trade_id']}")["trade"]
        if t["state"] != "CLOSED":
            return None
        px = float(t.get("averageClosePrice") or p["entry"])
        reason = "stop" if abs(px - p["stop"]) < abs(px - p["target"]) else "target"
        return _book(st, px, reason, float(t.get("realizedPL", 0)) + float(t.get("financing", 0)))


def watch(every):
    print(f"=== STOP WATCHER {mode()} every {every}s, state {os.path.basename(STATE_FILE)} ===", flush=True)
    while True:
        try:
            p = load()["position"]
            done = (sync() if p.get("trade_id") else check_price(fetch_price(p["symbol"]))) if p else None
            if done:
                print(f"{now()} {done['reason'].upper()}: {done['side']} {done['symbol']} closed at {done['exit']}"
                      f"  P&L {done['pnl']:+.2f}", flush=True)
        except Exception as e:
            print(f"{now()} watch error: {e}", flush=True)
        time.sleep(every)


# ---------------------------------------------------------------- CLI
def main():
    global LIVE, STATE_FILE
    ap = argparse.ArgumentParser(description="forex desk order executor")
    ap.add_argument("--state", help="state file (default live_state.json next to this script)")
    ap.add_argument("--simulate", action="store_true", help="never send to the broker, whatever desk.env says")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("check")
    sub.add_parser("watch").add_argument("--every", type=int, default=30, help="seconds between checks")
    o = sub.add_parser("open")
    o.add_argument("--symbol", required=True)
    o.add_argument("--side", required=True, choices=["long", "short"])
    o.add_argument("--units", required=True, type=int)
    o.add_argument("--stop", required=True, type=float)
    o.add_argument("--target", required=True, type=float)
    c = sub.add_parser("close")
    c.add_argument("--symbol")
    c.add_argument("--reason", default="manual")
    for s in (o, c):
        s.add_argument("--price", type=float, help="reference mid price (simulated fill; LIVE slippage bound)")
        s.add_argument("--ticket")
    a = ap.parse_args()
    STATE_FILE = os.path.abspath(a.state) if a.state else STATE_FILE
    LIVE = LIVE and not a.simulate

    if a.cmd == "watch":
        return watch(a.every)
    if a.cmd == "check" and mt5():
        acct = _mt5_account()
        print(f"MT5 account {acct['server']} {acct['login']} ({'demo' if acct['demo'] else 'REAL'}): {acct['currency']} "
              f"balance {acct['balance']}  equity {acct['equity']}  Algo Trading {'on' if acct['algo_trading'] else 'OFF'}  "
              f"(LIVE={int(LIVE)}, magic {CFG['MT5_MAGIC']})")
        return
    if a.cmd == "check":
        acct = oanda(f"/v3/accounts/{_account()}/summary")["account"]
        print(f"OANDA {CFG['OANDA_ENV']} account {acct['id']}: {acct['currency']} balance {acct['balance']}  "
              f"NAV {acct['NAV']}  open trades {acct['openTradeCount']}  (LIVE={int(LIVE)})")
        return
    if a.cmd == "status":
        st = load()
        print(json.dumps({"mode": mode(), "state_file": STATE_FILE, "position": st["position"],
                          "day_pnl": round(st["day_pnl"], 2), "total_pnl": round(st["total_pnl"], 2),
                          "last_trades": st["trades"][-5:]}, indent=1))
        return
    if a.cmd == "open":
        res = open_position(a.symbol, a.side, a.units, a.stop, a.target, a.price, a.ticket)
    else:
        res = close_position(a.symbol, a.price, a.reason, a.ticket)
    print(json.dumps(res))
    sys.exit(0 if res.get("ok") else 1)


if __name__ == "__main__":
    main()
