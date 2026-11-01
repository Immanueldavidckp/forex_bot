"""
mt5_bridge.py — the MetaTrader 5 side of the MT5 path. Runs under WINE PYTHON (the
MetaTrader5 package is Windows-only), never under Linux Python:

    WINEPREFIX=~/.mt5 wine C:\\...\\Python311\\python.exe -I Z:\\home\\david\\forex\\mt5_bridge.py REQ OUT

REQ is a JSON list of requests, OUT gets a JSON list of replies (same order). Linux code
calls it through mt5_client.py, which also converts server times. Results go to a file,
not stdout: if this call has to start the terminal, the terminal inherits stdout and a
reader of that pipe would never see EOF.

Requests ({"op": ...}):
  account                                   login, server, balance, equity, free margin, algo trading on/off
  info      symbol                          digits, point, volume min/step/max, filling, stops level, spread
  tick      symbol                          bid, ask, last, time (server clock)
  login     login [server] [password]       log in (no password: the terminal's saved one)
  rates     symbol tf count [start]         bars, newest last: [time, o, h, l, c, tick_volume, real_volume, spread]
                                            (server clock; start = bar offset, 0 = from the newest)
  ticks     symbol from_s [to_s] path       every tick from from_s to to_s (server clock, seconds; to_s default: now),
                                            saved with numpy at path (a Windows path): time_msc, bid, ask, flags
                                            → {n, first_msc, last_msc} (millions of ticks do not go through JSON)
  positions [symbol] [magic]                open positions
  order     symbol side volume [sl tp magic comment deviation check_only]
                                            market order (buy | sell); SL/TP ride on the order, or are set
                                            right after the fill if the server refuses stops on the order
  sltp      ticket [sl tp]                  change a position's stop / target
  close     ticket [deviation magic comment check_only]
  deals     [position] [days]               closed deals (for a position: its entry and exit)
  find      pattern [limit]                 symbols whose name / description / path contain pattern (any case),
                                            with contract, volume and tick-value facts and the last tick

MT5_TERMINAL (environment) picks another terminal64.exe in the prefix (default: the MetaQuotes one).

The account is whatever the terminal is logged into. Orders fail with retcode 10027 unless
the terminal's Algo Trading button is on.
"""
import json
import os
import sys
import time

import MetaTrader5 as mt5

TERMINAL = os.environ.get("MT5_TERMINAL", r"C:\Program Files\MetaTrader 5\terminal64.exe")
TF = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
      "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}
OK = (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED, mt5.TRADE_RETCODE_DONE_PARTIAL)


def _nt(x):
    return x._asdict() if x is not None and hasattr(x, "_asdict") else x


def _filling(info):
    # symbol_info.filling_mode is a bit mask: 1 = FOK allowed, 2 = IOC allowed; neither = RETURN
    if info.filling_mode & 1:
        return mt5.ORDER_FILLING_FOK
    if info.filling_mode & 2:
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN


def _symbol(sym):
    if not mt5.symbol_select(sym, True):
        raise ValueError(f"unknown symbol {sym}: {mt5.last_error()}")
    info = mt5.symbol_info(sym)
    if info is None:
        raise ValueError(f"no info for {sym}: {mt5.last_error()}")
    return info


def _tick(sym):
    t = mt5.symbol_info_tick(sym)
    if t is None:
        time.sleep(0.5)                 # a symbol just added to Market Watch needs a moment for its first tick
        t = mt5.symbol_info_tick(sym)
    return t


def _result(r, req):
    if r is None:
        return {"ok": False, "retcode": None, "comment": f"no reply: {mt5.last_error()}", "request": req}
    d = _nt(r)
    d.pop("request", None)
    d["ok"] = d.get("retcode") in OK or d.get("retcode") == 0   # order_check answers 0 when the order would pass
    d["request"] = req
    return d


def op_account(q):
    a, t = mt5.account_info(), mt5.terminal_info()
    if a is None:                                   # the terminal runs but is not logged in to any account
        return {"login": None, "server": None, "connected": bool(t and t.connected), "algo_trading": bool(t and t.trade_allowed),
                "demo": None, "equity": None, "balance": None}
    return {"login": a.login, "server": a.server, "currency": a.currency, "balance": a.balance, "equity": a.equity,
            "margin_free": a.margin_free, "leverage": a.leverage, "hedging": a.margin_mode == mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING,
            "trade_allowed": a.trade_allowed, "algo_trading": t.trade_allowed, "connected": t.connected,
            "demo": a.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO}


def op_login(q):
    """Log the terminal in to an account; without a password the one saved in the terminal is used."""
    kw = {"server": q["server"]} if q.get("server") else {}
    if q.get("password"):
        kw["password"] = q["password"]
    ok = mt5.login(int(q["login"]), timeout=60000, **kw)
    return {"ok": bool(ok), "error": None if ok else str(mt5.last_error())}


def op_info(q):
    i = _symbol(q["symbol"])
    return {k: getattr(i, k) for k in ("name", "description", "path", "digits", "point", "trade_tick_size", "trade_tick_value",
                                       "trade_contract_size", "volume_min", "volume_step", "volume_max", "filling_mode",
                                       "trade_stops_level", "trade_freeze_level", "spread", "trade_mode", "trade_exemode",
                                       "currency_profit")}


def op_tick(q):
    _symbol(q["symbol"])
    return _nt(_tick(q["symbol"]))


def op_live(q):
    """Is the symbol quoting right now? Watch its tick for up to `wait` seconds: {changed, first, last}.
    (A stale tick's time alone can't be told apart from a server clock offset.)"""
    _symbol(q["symbol"])
    first = _tick(q["symbol"])
    end = time.time() + float(q.get("wait", 8))
    last = first
    while time.time() < end:
        time.sleep(0.5)
        last = mt5.symbol_info_tick(q["symbol"]) or last
        if first is not None and last.time_msc != first.time_msc:
            break
    return {"changed": bool(first is not None and last.time_msc != first.time_msc), "first": _nt(first), "last": _nt(last)}


def op_rates(q):
    _symbol(q["symbol"])
    r = mt5.copy_rates_from_pos(q["symbol"], TF[q.get("tf", "M1")], int(q.get("start", 0)), int(q.get("count", 500)))
    if r is None:
        raise ValueError(f"no {q.get('tf')} bars for {q['symbol']}: {mt5.last_error()}")
    return [[int(b["time"]), float(b["open"]), float(b["high"]), float(b["low"]), float(b["close"]),
             int(b["tick_volume"]), int(b["real_volume"]), int(b["spread"])] for b in r]


def op_ticks(q):
    import numpy as np
    _symbol(q["symbol"])
    to_s = int(q["to_s"]) if q.get("to_s") else int(time.time()) + 3 * 86400    # past any server clock offset = up to now
    t = mt5.copy_ticks_range(q["symbol"], int(q["from_s"]), to_s, mt5.COPY_TICKS_ALL)
    if t is None:
        raise ValueError(f"no ticks for {q['symbol']}: {mt5.last_error()}")
    out = np.empty(len(t), dtype=[("time_msc", "<i8"), ("bid", "<f8"), ("ask", "<f8"), ("flags", "<u4")])
    for k in out.dtype.names:
        out[k] = t[k]
    np.save(q["path"], out)
    return {"n": int(len(t)), "first_msc": int(t["time_msc"][0]) if len(t) else None, "last_msc": int(t["time_msc"][-1]) if len(t) else None}


def op_positions(q):
    ps = mt5.positions_get(symbol=q["symbol"]) if q.get("symbol") else mt5.positions_get()
    out = [_nt(p) for p in ps or []]
    if q.get("magic") is not None:
        out = [p for p in out if p["magic"] == int(q["magic"])]
    return out


def op_order(q):
    sym, side = q["symbol"], q["side"].lower()
    info = _symbol(sym)
    tick = _tick(sym)
    if tick is None:
        raise ValueError(f"no price for {sym}")
    price = tick.ask if side == "buy" else tick.bid
    req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": sym, "volume": float(q["volume"]),
           "type": mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL, "price": price,
           "deviation": int(q.get("deviation", 10)), "magic": int(q.get("magic", 0)), "comment": str(q.get("comment", ""))[:31],
           "type_time": mt5.ORDER_TIME_GTC, "type_filling": _filling(info)}
    if q.get("sl"):
        req["sl"] = round(float(q["sl"]), info.digits)
    if q.get("tp"):
        req["tp"] = round(float(q["tp"]), info.digits)
    if q.get("check_only"):
        return _result(mt5.order_check(req), req)
    res = _result(mt5.order_send(req), req)
    if (q.get("allow_bare") and not res["ok"] and res.get("retcode") == mt5.TRADE_RETCODE_INVALID_STOPS
            and ("sl" in req or "tp" in req)):
        # opt-in only: for a server that refuses ANY stop on an opening order, open bare and attach them. Off by default:
        # when the stop itself is too close (FxPro LITECOIN, 2026-10-24) it opened and closed the trade, paying the spread
        # every time
        bare = {k: v for k, v in req.items() if k not in ("sl", "tp")}
        res = _result(mt5.order_send(bare), bare)
        if res["ok"]:
            pos = [p for p in mt5.positions_get(symbol=sym) or [] if p.magic == req["magic"]]
            if pos:
                p = max(pos, key=lambda p: p.time_msc)
                res["sltp"] = op_sltp({"ticket": p.ticket, "sl": req.get("sl"), "tp": req.get("tp")})
                if not res["sltp"]["ok"]:
                    # never leave a position without its stop: take it straight back off
                    res["unprotected_closed"] = op_close({"ticket": p.ticket, "comment": "no stop: closed"})
                    res["ok"] = False
                    res["comment"] = "opened without stops and could not attach them: closed again"
    return res


def op_pending(q):
    """A pending order at `price` with its stop and target: a buy below the ask / sell above the bid is a
    limit order, the other side a stop order. Good till cancelled (the caller cancels it when it expires)."""
    sym, side, price = q["symbol"], q["side"].lower(), float(q["price"])
    info = _symbol(sym)
    tick = _tick(sym)
    if tick is None:
        raise ValueError(f"no price for {sym}")
    if side == "buy":
        typ = mt5.ORDER_TYPE_BUY_LIMIT if price < tick.ask else mt5.ORDER_TYPE_BUY_STOP
    else:
        typ = mt5.ORDER_TYPE_SELL_LIMIT if price > tick.bid else mt5.ORDER_TYPE_SELL_STOP
    req = {"action": mt5.TRADE_ACTION_PENDING, "symbol": sym, "volume": float(q["volume"]), "type": typ,
           "price": round(price, info.digits), "magic": int(q.get("magic", 0)), "comment": str(q.get("comment", ""))[:31],
           "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_RETURN}
    if q.get("sl"):
        req["sl"] = round(float(q["sl"]), info.digits)
    if q.get("tp"):
        req["tp"] = round(float(q["tp"]), info.digits)
    send = mt5.order_check if q.get("check_only") else mt5.order_send
    res = _result(send(req), req)
    if not res["ok"] and res.get("retcode") == mt5.TRADE_RETCODE_INVALID_FILL:
        req["type_filling"] = _filling(info)                 # some servers want their own filling mode on pending orders
        res = _result(send(req), req)
    res["order_type"] = {mt5.ORDER_TYPE_BUY_LIMIT: "buy limit", mt5.ORDER_TYPE_BUY_STOP: "buy stop",
                         mt5.ORDER_TYPE_SELL_LIMIT: "sell limit", mt5.ORDER_TYPE_SELL_STOP: "sell stop"}[typ]
    return res


def op_orders(q):
    """Pending orders (optionally this magic only)."""
    out = [_nt(o) for o in mt5.orders_get() or []]
    if q.get("magic") is not None:
        out = [o for o in out if o["magic"] == int(q["magic"])]
    return out


def op_cancel(q):
    """Delete a pending order."""
    req = {"action": mt5.TRADE_ACTION_REMOVE, "order": int(q["ticket"])}
    return _result(mt5.order_send(req), req)


def op_sltp(q):
    p = mt5.positions_get(ticket=int(q["ticket"]))
    if not p:
        raise ValueError(f"no open position {q['ticket']}")
    p = p[0]
    info = _symbol(p.symbol)
    req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "symbol": p.symbol,
           "sl": round(float(q["sl"]), info.digits) if q.get("sl") else p.sl,
           "tp": round(float(q["tp"]), info.digits) if q.get("tp") else p.tp}
    return _result(mt5.order_send(req), req)


def op_close(q):
    p = mt5.positions_get(ticket=int(q["ticket"]))
    if not p:
        raise ValueError(f"no open position {q['ticket']}")
    p = p[0]
    info = _symbol(p.symbol)
    tick = _tick(p.symbol)
    buy = p.type == mt5.POSITION_TYPE_SELL           # closing a sell = buying it back
    vol = min(float(q["volume"]), p.volume) if q.get("volume") else p.volume     # a smaller volume = a partial close
    req = {"action": mt5.TRADE_ACTION_DEAL, "position": p.ticket, "symbol": p.symbol, "volume": vol,
           "type": mt5.ORDER_TYPE_BUY if buy else mt5.ORDER_TYPE_SELL, "price": tick.ask if buy else tick.bid,
           "deviation": int(q.get("deviation", 20)), "magic": int(q.get("magic", p.magic)),
           "comment": str(q.get("comment", "close"))[:31], "type_time": mt5.ORDER_TIME_GTC, "type_filling": _filling(info)}
    if q.get("check_only"):
        return _result(mt5.order_check(req), req)
    return _result(mt5.order_send(req), req)


def op_deals(q):
    if q.get("position"):
        ds = mt5.history_deals_get(position=int(q["position"]))
    else:
        now = time.time() + 86400                       # the server clock runs ahead of UTC
        ds = mt5.history_deals_get(int(now - 86400 * float(q.get("days", 3))), int(now))
    return [_nt(d) for d in ds or []]


def op_find(q):
    pat = str(q["pattern"]).upper()
    hits = [s for s in mt5.symbols_get() or [] if pat in (s.name + " " + s.description + " " + s.path).upper()]
    out = []
    for s in hits[:int(q.get("limit", 10))]:
        mt5.symbol_select(s.name, True)
        t = _tick(s.name)
        out.append({"name": s.name, "path": s.path, "description": s.description, "trade_mode": s.trade_mode,
                    "digits": s.digits, "trade_contract_size": s.trade_contract_size, "volume_min": s.volume_min,
                    "volume_step": s.volume_step, "trade_tick_value": s.trade_tick_value, "trade_tick_size": s.trade_tick_size,
                    "currency_profit": s.currency_profit, "tick_time": t.time if t else None,
                    "bid": t.bid if t else None, "ask": t.ask if t else None})
    return out


OPS = {k[3:]: v for k, v in globals().items() if k.startswith("op_")}


def main():
    req_path, out_path = sys.argv[1], sys.argv[2]
    with open(req_path) as f:
        reqs = json.load(f)
    out = []
    if not mt5.initialize(path=TERMINAL, timeout=60000):
        out = [{"error": f"MT5 initialize failed: {mt5.last_error()}"} for _ in reqs]
    else:
        try:
            for q in reqs:
                try:
                    out.append({"result": OPS[q["op"]](q)})
                except Exception as e:
                    out.append({"error": f"{type(e).__name__}: {e}"})
        finally:
            mt5.shutdown()
    with open(out_path + ".tmp", "w") as f:
        json.dump(out, f, default=str)
    os.replace(out_path + ".tmp", out_path)


if __name__ == "__main__":
    main()
