#!/usr/bin/env python3
"""
mt5_client.py — Linux Python's handle on the MT5 demo terminal (Wine). Every call runs
mt5_bridge.py once under Wine Python with a batch of requests (≈3 s a batch, mostly Wine
start-up), so callers batch: one call per scan, not one per symbol.

Server clock: bar and tick times are the broker server's own wall clock. Default (offset=None):
MetaQuotes-Demo's rule, New York time + 7 h all year (it changes with US DST: the Nasdaq open is
16:30 on the server). Other brokers: pass offset = server minus UTC, which detect_offset() measures
from a fresh tick of a symbol that is quoting (BTCUSD trades 24/7). bars() returns the engine's bar
shape {"t": epoch ms UTC, "o", "h", "l", "c", "v"}; D1 bars are stamped at noon (New York, or UTC
with an offset) of their server day, so the bar lands on the right session date. v = exchange
volume when the server has it (stocks), else tick volume (CFDs).

    python3 mt5_client.py account
    python3 mt5_client.py positions [--magic N]
    python3 mt5_client.py tick IBIT
    python3 mt5_client.py bars IBIT M5 20
    python3 mt5_client.py find BTC                      # the broker's bitcoin symbol(s)
    python3 mt5_client.py offset BTCUSD                 # server clock minus UTC, from a live tick
    python3 mt5_client.py close TICKET                  # flatten one position by hand
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import tempfile
import time
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
WINEPREFIX = os.path.expanduser(os.environ.get("MT5_WINEPREFIX", "~/.mt5"))
WINE_PY = os.environ.get("MT5_WINE_PY", r"C:\users\david\AppData\Local\Programs\Python\Python311\python.exe")
BRIDGE = os.path.join(HERE, "mt5_bridge.py")
NY = ZoneInfo("America/New_York")
SERVER_AHEAD_OF_NY = _dt.timedelta(hours=7)


class Mt5Error(RuntimeError):
    pass


def _winpath(p: str) -> str:
    return "Z:" + os.path.abspath(p).replace("/", "\\")


def terminal_running() -> bool:
    return subprocess.run(["pgrep", "-f", r"[t]erminal64\.exe"], stdout=subprocess.DEVNULL).returncode == 0


def call(reqs: List[Dict], timeout: float = 120) -> List[Dict]:
    """Run a batch; → one {"result": ...} or {"error": ...} per request. MT5_NO_LAUNCH=1 (the V5 engine, which
    starts the terminal as its own service): raise instead of letting MetaTrader5.initialize() start it."""
    if os.environ.get("MT5_NO_LAUNCH") == "1" and not terminal_running():
        raise Mt5Error("MT5 terminal is not running")
    with tempfile.TemporaryDirectory(prefix="mt5-") as tmp:
        req, out = os.path.join(tmp, "req.json"), os.path.join(tmp, "out.json")
        with open(req, "w") as f:
            json.dump(reqs, f)
        env = {**os.environ, "WINEPREFIX": WINEPREFIX, "WINEDEBUG": "-all"}
        try:
            p = subprocess.run(["wine", WINE_PY, "-I", _winpath(BRIDGE), _winpath(req), _winpath(out)], env=env,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise Mt5Error(f"bridge timed out after {timeout:.0f} s (terminal hung?)") from None
        if not os.path.exists(out):
            err = p.stderr.decode(errors="replace").strip().splitlines()
            raise Mt5Error(f"bridge wrote nothing (exit {p.returncode}): " + " | ".join(err[-3:]))
        with open(out) as f:
            return json.load(f)


def one(req: Dict, timeout: float = 120):
    r = call([req], timeout)[0]
    if "error" in r:
        raise Mt5Error(r["error"])
    return r["result"]


# ── server clock → UTC ──────────────────────────────────────────────────────

def server_to_utc_ms(t: int, offset=None) -> int:
    """offset: server clock minus UTC (a timedelta, the same for every bar), or the server's time zone (a tzinfo:
    each bar with its own date's offset, so bars from before a DST change keep theirs); None = New York + 7 h."""
    wall = _dt.datetime.fromtimestamp(t, _dt.timezone.utc).replace(tzinfo=None)
    if isinstance(offset, _dt.tzinfo):
        return int(wall.replace(tzinfo=offset).timestamp() * 1000)
    if offset is not None:
        return int((wall - offset).replace(tzinfo=_dt.timezone.utc).timestamp() * 1000)
    return int((wall - SERVER_AHEAD_OF_NY).replace(tzinfo=NY).timestamp() * 1000)


def _day_ms(t: int, offset: Optional[_dt.timedelta] = None) -> int:
    d = _dt.datetime.fromtimestamp(t, _dt.timezone.utc).date()
    tz = NY if offset is None else _dt.timezone.utc
    return int(_dt.datetime(d.year, d.month, d.day, 12, tzinfo=tz).timestamp() * 1000)


def offset_from_tick(tick_time: float, now_utc: Optional[float] = None, max_age_sec: float = 120) -> _dt.timedelta:
    """Server clock minus UTC from a tick's server time, rounded to the nearest 30 min. A tick older than
    max_age_sec cannot tell the offset apart from staleness: raise."""
    now_utc = time.time() if now_utc is None else now_utc
    diff = float(tick_time) - now_utc
    half_hours = round(diff / 1800.0)
    age = half_hours * 1800.0 - diff                   # how far the tick lags behind "now" on its own clock
    if age > max_age_sec or age < -max_age_sec:
        raise Mt5Error(f"last tick is {age:.0f} s old (max {max_age_sec:.0f}): the symbol is not quoting now")
    return _dt.timedelta(minutes=30 * half_hours)


def live(symbol: str, wait: float = 8) -> Dict:
    """Watch the symbol's tick for up to `wait` s: {changed, first, last}. changed = it is quoting now."""
    return one({"op": "live", "symbol": symbol, "wait": wait}, timeout=wait + 60)


def detect_offset(symbol: str, max_age_sec: float = 120) -> _dt.timedelta:
    """Only from a symbol whose tick moves while we watch: a stale tick (market closed) whose age happens
    to be near a whole half hour would otherwise pass for a clock offset (Friday's EURUSD read as UTC-6)."""
    w = live(symbol)
    if not w.get("changed"):
        raise Mt5Error(f"{symbol} is not quoting now (no new tick in 8 s)")
    return offset_from_tick(w["last"]["time"], max_age_sec=max_age_sec)


def to_bars(raw: List[list], tf: str, offset: Optional[_dt.timedelta] = None) -> List[Dict]:
    stamp = _day_ms if tf == "D1" else server_to_utc_ms
    return [{"t": stamp(r[0], offset), "o": r[1], "h": r[2], "l": r[3], "c": r[4], "v": float(r[6] or r[5]),
             "spread": r[7] if len(r) > 7 else None} for r in raw]      # spread in points (the V5 filter layer's Gate 8)


def bars_many(wants: List[tuple], timeout: float = 120, offset: Optional[_dt.timedelta] = None) -> Dict[tuple, List[Dict]]:
    """wants: [(symbol, tf, count), ...] in one bridge call → {(symbol, tf): bars} (failed ones left out)."""
    res = call([{"op": "rates", "symbol": s, "tf": tf, "count": n} for s, tf, n in wants], timeout)
    out = {}
    for (s, tf, _), r in zip(wants, res):
        if "result" in r:
            out[(s, tf)] = to_bars(r["result"], tf, offset)
    return out


def bars(symbol: str, tf: str = "M1", count: int = 500, offset: Optional[_dt.timedelta] = None) -> List[Dict]:
    return to_bars(one({"op": "rates", "symbol": symbol, "tf": tf, "count": count}), tf, offset)


# ── account and trading ─────────────────────────────────────────────────────

def account() -> Dict:
    return one({"op": "account"})


def info(symbol: str) -> Dict:
    return one({"op": "info", "symbol": symbol})


def tick(symbol: str) -> Dict:
    return one({"op": "tick", "symbol": symbol})


def positions(magic: Optional[int] = None, symbol: Optional[str] = None) -> List[Dict]:
    return one({"op": "positions", "magic": magic, "symbol": symbol})


def order(symbol: str, side: str, volume: float, sl: float = 0.0, tp: float = 0.0, magic: int = 0, comment: str = "",
          deviation: int = 10, check_only: bool = False) -> Dict:
    """Market order with its stop and target. → the server's reply (ok, retcode, comment, order, deal, price, volume)."""
    return one({"op": "order", "symbol": symbol, "side": side, "volume": volume, "sl": sl, "tp": tp, "magic": magic,
                "comment": comment, "deviation": deviation, "check_only": check_only})


def pending(symbol: str, side: str, volume: float, price: float, sl: float = 0.0, tp: float = 0.0, magic: int = 0,
            comment: str = "", check_only: bool = False) -> Dict:
    """Pending order at `price` (buy below / sell above the market = limit, else stop) with stop + target, good till
    cancelled. → the server's reply (ok, retcode, comment, order = the pending order's ticket, order_type)."""
    return one({"op": "pending", "symbol": symbol, "side": side, "volume": volume, "price": price, "sl": sl, "tp": tp,
                "magic": magic, "comment": comment, "check_only": check_only})


def orders(magic: Optional[int] = None) -> List[Dict]:
    """Pending orders (this magic only when given)."""
    return one({"op": "orders", "magic": magic})


def cancel(ticket: int) -> Dict:
    """Delete a pending order."""
    return one({"op": "cancel", "ticket": ticket})


def modify(ticket: int, price: float = 0.0, sl: float = 0.0, tp: float = 0.0) -> Dict:
    """Move a pending order's price / stop / target (0 = keep)."""
    return one({"op": "modify", "ticket": ticket, "price": price, "sl": sl, "tp": tp})


def sltp(ticket: int, sl: float = 0.0, tp: float = 0.0) -> Dict:
    return one({"op": "sltp", "ticket": ticket, "sl": sl, "tp": tp})


def close(ticket: int, comment: str = "close", deviation: int = 20, check_only: bool = False, volume: Optional[float] = None) -> Dict:
    """Flatten a position, or only `volume` lots of it (partial close)."""
    return one({"op": "close", "ticket": ticket, "comment": comment, "deviation": deviation, "check_only": check_only, "volume": volume})


def find(pattern: str, limit: int = 10) -> List[Dict]:
    """Symbols whose name / description / path contain `pattern`, with their contract facts and last tick."""
    return one({"op": "find", "pattern": pattern, "limit": limit})


def deals(position: Optional[int] = None, days: float = 3) -> List[Dict]:
    return one({"op": "deals", "position": position, "days": days})


def main():
    ap = argparse.ArgumentParser(description="MT5 demo terminal from Linux (through Wine Python)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("account")
    p = sub.add_parser("positions")
    p.add_argument("--magic", type=int)
    p = sub.add_parser("tick")
    p.add_argument("symbol")
    p = sub.add_parser("bars")
    p.add_argument("symbol")
    p.add_argument("tf", nargs="?", default="M1")
    p.add_argument("count", nargs="?", type=int, default=20)
    p = sub.add_parser("close")
    p.add_argument("ticket", type=int)
    p = sub.add_parser("find")
    p.add_argument("pattern")
    p = sub.add_parser("offset")
    p.add_argument("symbol")
    a = ap.parse_args()
    if a.cmd == "account":
        r = account()
    elif a.cmd == "positions":
        r = positions(a.magic)
    elif a.cmd == "tick":
        r = tick(a.symbol)
    elif a.cmd == "bars":
        r = [{**b, "ny": _dt.datetime.fromtimestamp(b["t"] / 1000, NY).strftime("%Y-%m-%d %H:%M")}
             for b in bars(a.symbol, a.tf, a.count)]
    elif a.cmd == "find":
        r = find(a.pattern)
    elif a.cmd == "offset":
        r = {"symbol": a.symbol, "server_minus_utc_hours": detect_offset(a.symbol).total_seconds() / 3600}
    else:
        r = close(a.ticket)
    print(json.dumps(r, indent=1, default=str))


if __name__ == "__main__":
    main()
