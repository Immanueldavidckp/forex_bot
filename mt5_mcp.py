#!/usr/bin/env python3
"""
mt5_mcp.py — an MCP server (stdio) that gives Claude the MetaTrader 5 terminal running under Wine:
account, positions, quotes, symbol search, bars, and orders. Standard library only; every tool call
goes through mt5_client.py → mt5_bridge.py (Wine Python, ≈1 s a call with the terminal open).

    claude mcp add --scope user mt5 -- python3 /home/david/forex/mt5_mcp.py

It works with whatever account the terminal is logged into. Safety, in code:
  - orders only on a DEMO account unless MT5_ALLOW_REAL=1 is set in the server's environment
  - every new order needs a stop loss (the broker holds it)
  - orders are tagged with magic MT5_MCP_MAGIC (default 24102099) so they can be told apart from the desks'
  - check_only=true runs the broker's order check without trading

Bar times are UTC: the server clock offset is measured from a live tick, or (market closed)
MetaQuotes-Demo's New York + 7 h is used.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mt5_client as mt5c  # noqa: E402

PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
MAGIC = int(os.environ.get("MT5_MCP_MAGIC", "24102099"))
ALLOW_REAL = os.environ.get("MT5_ALLOW_REAL") == "1"
TIMEFRAMES = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")

_S = {"type": "string"}
_N = {"type": "number"}
_I = {"type": "integer"}
TOOLS = [
    {"name": "account", "description": "The MT5 account the terminal is logged into: login, server, balance, equity, "
                                       "free margin, leverage, demo or real, Algo Trading on/off.",
     "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True}},
    {"name": "positions", "description": "Open positions (ticket, symbol, buy/sell, volume, open price, SL, TP, current price, "
                                         "profit, magic). Optional filters: symbol, magic.",
     "inputSchema": {"type": "object", "properties": {"symbol": _S, "magic": _I}}, "annotations": {"readOnlyHint": True}},
    {"name": "quote", "description": "Latest bid/ask/last of a symbol and how old the tick is (seconds).",
     "inputSchema": {"type": "object", "properties": {"symbol": _S}, "required": ["symbol"]}, "annotations": {"readOnlyHint": True}},
    {"name": "find_symbols", "description": "Search the broker's symbols by name/description/path (e.g. 'BTC', 'XAU', 'EUR'): "
                                            "exact symbol names, contract size, lot min/step, tick value, last bid/ask.",
     "inputSchema": {"type": "object", "properties": {"pattern": _S, "limit": _I}, "required": ["pattern"]},
     "annotations": {"readOnlyHint": True}},
    {"name": "symbol_info", "description": "Trading facts of one symbol: digits, point, contract size, lot min/step/max, "
                                           "filling mode, stops level, spread, trade mode.",
     "inputSchema": {"type": "object", "properties": {"symbol": _S}, "required": ["symbol"]}, "annotations": {"readOnlyHint": True}},
    {"name": "bars", "description": "OHLCV bars, oldest first, times in UTC. timeframe: M1 M5 M15 M30 H1 H4 D1; count up to 1000.",
     "inputSchema": {"type": "object", "properties": {"symbol": _S, "timeframe": {"type": "string", "enum": list(TIMEFRAMES)},
                                                      "count": _I}, "required": ["symbol"]},
     "annotations": {"readOnlyHint": True}},
    {"name": "deals", "description": "Closed deals: of one position (its entry and exit), or of the last N days.",
     "inputSchema": {"type": "object", "properties": {"position": _I, "days": _N}}, "annotations": {"readOnlyHint": True}},
    {"name": "place_order", "description": "Market order with a stop loss (required) and optional take profit, at the live price. "
                                           "side: buy or sell; volume in lots. Demo accounts only. check_only=true asks the "
                                           "broker to check it without trading.",
     "inputSchema": {"type": "object", "properties": {"symbol": _S, "side": {"type": "string", "enum": ["buy", "sell"]},
                                                      "volume": _N, "sl": _N, "tp": _N, "comment": _S,
                                                      "deviation_points": _I, "check_only": {"type": "boolean"}},
                     "required": ["symbol", "side", "volume", "sl"]},
     "annotations": {"readOnlyHint": False, "destructiveHint": False}},
    {"name": "modify_position", "description": "Change the stop loss and/or take profit of an open position (by ticket).",
     "inputSchema": {"type": "object", "properties": {"ticket": _I, "sl": _N, "tp": _N}, "required": ["ticket"]},
     "annotations": {"readOnlyHint": False}},
    {"name": "close_position", "description": "Close an open position at the market (by ticket). Demo accounts only. "
                                              "check_only=true asks the broker to check it without trading.",
     "inputSchema": {"type": "object", "properties": {"ticket": _I, "comment": _S, "check_only": {"type": "boolean"}},
                     "required": ["ticket"]},
     "annotations": {"readOnlyHint": False, "destructiveHint": True}},
]


def _need_demo() -> dict:
    a = mt5c.account()
    if not a.get("demo") and not ALLOW_REAL:
        raise ValueError(f"refused: {a['server']} {a['login']} is a REAL account (set MT5_ALLOW_REAL=1 to allow)")
    if not a.get("algo_trading"):
        raise ValueError("Algo Trading is off in the MT5 terminal (toolbar button / Ctrl+E): orders would fail with 10027")
    return a


_offsets: dict = {}


def _live(symbol: str):
    """(is it quoting now, latest tick, server clock offset or None). The offset is measured from a tick that
    moved while we watched, then kept for the session; closed market → MetaQuotes-Demo's New York + 7 h."""
    w = mt5c.live(symbol, wait=3)
    t = w.get("last") or {}
    if w.get("changed") and symbol not in _offsets:
        try:
            _offsets[symbol] = mt5c.offset_from_tick(t["time"])
        except Exception:
            pass
    return bool(w.get("changed")), t, _offsets.get(symbol, next(iter(_offsets.values()), None))


def _offset(symbol: str):
    return _live(symbol)[2]


def _iso(ms: int) -> str:
    return _dt.datetime.fromtimestamp(ms / 1000, _dt.timezone.utc).strftime("%Y-%m-%d %H:%M")


def call_tool(name: str, a: dict):
    if name == "account":
        return mt5c.account()
    if name == "positions":
        return mt5c.positions(a.get("magic"), a.get("symbol"))
    if name == "quote":
        quoting, t, off = _live(a["symbol"])
        last_utc = _iso(mt5c.server_to_utc_ms(int(t["time"]), off)) if t.get("time") else None
        return {"symbol": a["symbol"], "bid": t.get("bid"), "ask": t.get("ask"), "last": t.get("last"),
                "last_tick_utc": last_utc, "quoting_now": quoting}
    if name == "find_symbols":
        return mt5c.find(a["pattern"], int(a.get("limit") or 20))
    if name == "symbol_info":
        return mt5c.info(a["symbol"])
    if name == "bars":
        tf = a.get("timeframe") or "H1"
        if tf not in TIMEFRAMES:
            raise ValueError(f"timeframe must be one of {', '.join(TIMEFRAMES)}")
        n = max(1, min(1000, int(a.get("count") or 100)))
        bs = mt5c.bars(a["symbol"], tf, n, _offset(a["symbol"]))
        return [{"time_utc": _iso(b["t"]), "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]} for b in bs]
    if name == "deals":
        return mt5c.deals(a.get("position"), float(a.get("days") or 3))
    if name == "place_order":
        _need_demo()
        if not a.get("sl"):
            raise ValueError("a stop loss (sl) is required")
        return mt5c.order(a["symbol"], a["side"], float(a["volume"]), float(a["sl"]), float(a.get("tp") or 0), MAGIC,
                          str(a.get("comment") or "claude mcp"), int(a.get("deviation_points") or 20),
                          check_only=bool(a.get("check_only")))
    if name == "modify_position":
        _need_demo()
        return mt5c.sltp(int(a["ticket"]), float(a.get("sl") or 0), float(a.get("tp") or 0))
    if name == "close_position":
        _need_demo()
        return mt5c.close(int(a["ticket"]), str(a.get("comment") or "claude mcp close"), check_only=bool(a.get("check_only")))
    raise ValueError(f"unknown tool {name}")


def handle(msg: dict):
    method, mid = msg.get("method"), msg.get("id")
    if method == "initialize":
        want = (msg.get("params") or {}).get("protocolVersion")
        return {"protocolVersion": want if want in PROTOCOLS else PROTOCOLS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "mt5", "version": "1.0.0"},
                "instructions": "MetaTrader 5 terminal (Wine) on this laptop. Use find_symbols for exact names; "
                                "orders need a stop loss and only run on demo accounts."}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        p = msg.get("params") or {}
        try:
            res = call_tool(p.get("name"), p.get("arguments") or {})
            failed = isinstance(res, dict) and res.get("ok") is False
            return {"content": [{"type": "text", "text": json.dumps(res, default=str)}], "isError": failed}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "isError": True}
    if mid is None:
        return None                                    # a notification (initialized, cancelled): no reply
    raise LookupError(method)


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        try:
            res = handle(msg)
            if msg.get("id") is None:
                continue
            out = {"jsonrpc": "2.0", "id": msg["id"], "result": res}
        except LookupError as e:
            out = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32601, "message": f"method not found: {e}"}}
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            out = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32603, "message": str(e)}}
        sys.stdout.write(json.dumps(out, default=str) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
