"""
engine/ticks.py — every tick of the symbols a /smc page watches, for the order-flow chart (David 2026-10-29: "add
the order flow chart"). FxPro has no trades on its feed (no BUY / SELL tick flags, `last` = bid, `volume` = a constant
quote size), so the order flow is estimated from these quote changes; this module only records them.

Files: engine_data/ticks/<SYMBOL>/<UTC date>.bin — raw records of TICK (t = UTC ms, bid / ask in points, MT5 flags),
meta.json {point, digits, complete: [days]}. live.step asks for the ticks with the same bridge call as the quotes:
today's new ones since the last stored tick every loop (appended to today's file), and one past day of the last
BACKFILL_DAYS per loop that is not complete yet, fetched whole and written over its file — so a day the engine was
off for, or yesterday's file that only started when the page was opened, ends up complete. Days older than KEEP_DAYS
are deleted, for every symbol, whenever a past day is fetched (this is a cache of MT5's own tick history).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Dict, List, Optional, Tuple

import numpy as np

from .config import DATA_DIR
from .feed import mt5c

TICK_DIR = os.path.join(DATA_DIR, "ticks")
TICK = np.dtype([("t", "<i8"), ("bid", "<i4"), ("ask", "<i4"), ("flags", "<u2")])
BACKFILL_DAYS = 7     # M5 / M15 footprints of the bars the page shows (M15 × 200 ≈ 2 days, M30 × 200 ≈ 4)
KEEP_DAYS = 10        # the footprint uses BACKFILL_DAYS; a few more stay for a look back (≈ 50–140 MB a symbol a week)
DAY_MS = 86_400_000
MARGIN_S = 60         # each request starts a minute before the last stored tick
REWRITE_MS = 5_000    # ...and its last 5 s on disk are written again from MT5's newest copy: MT5 can still be adding
                      # ticks to a second it has already given out (seen 2026-10-29: 10 late ticks in the last second)


def _dir(sym: str) -> str:
    return os.path.join(TICK_DIR, sym)


def _day(ms: int) -> str:
    return _dt.datetime.fromtimestamp(ms / 1000, _dt.timezone.utc).strftime("%Y-%m-%d")


def _day_ms(day: str) -> int:
    return int(_dt.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=_dt.timezone.utc).timestamp() * 1000)


def _days(sym: str) -> List[str]:
    try:
        return sorted(f[:-4] for f in os.listdir(_dir(sym)) if f.endswith(".bin"))
    except FileNotFoundError:
        return []


def meta(sym: str) -> Dict:
    try:
        with open(os.path.join(_dir(sym), "meta.json")) as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def _save_meta(sym: str, m: Dict) -> None:
    os.makedirs(_dir(sym), exist_ok=True)
    with open(os.path.join(_dir(sym), "meta.json.tmp"), "w") as f:
        json.dump(m, f)
    os.replace(os.path.join(_dir(sym), "meta.json.tmp"), os.path.join(_dir(sym), "meta.json"))


def load(sym: str, t0_ms: int, t1_ms: int) -> Tuple[np.ndarray, Optional[float]]:
    """The stored ticks with t0_ms <= t < t1_ms (UTC) and the symbol's point (prices are in points)."""
    parts = [np.fromfile(os.path.join(_dir(sym), f"{d}.bin"), dtype=TICK) for d in _days(sym)
             if _day_ms(d) + DAY_MS > t0_ms and _day_ms(d) < t1_ms]
    a = np.concatenate(parts) if parts else np.empty(0, TICK)
    return a[(a["t"] >= t0_ms) & (a["t"] < t1_ms)], meta(sym).get("point")


def _last(sym: str) -> Optional[int]:
    """The time of the newest stored tick, from the newest day file."""
    for d in reversed(_days(sym)):
        p = os.path.join(_dir(sym), f"{d}.bin")
        n = os.path.getsize(p) // TICK.itemsize
        if n:
            return int(np.fromfile(p, dtype=TICK, offset=(n - 1) * TICK.itemsize)["t"][-1])
    return None


def _cut_tail(path: str, cut: int) -> None:
    """Drop the records of a day file with t >= cut (they are at its end: the file is in time order)."""
    n = os.path.getsize(path) // TICK.itemsize
    k = max(0, n - 20_000)                          # 20,000 ticks reach far past REWRITE_MS even at 1,000 ticks / s
    tail = np.fromfile(path, dtype=TICK, offset=k * TICK.itemsize)
    i = k + int(np.searchsorted(tail["t"], cut, side="left"))
    if i == k and k:                                # an extreme burst: look at the whole file
        i = int(np.searchsorted(np.fromfile(path, dtype=TICK)["t"], cut, side="left"))
    os.truncate(path, i * TICK.itemsize)


def _to_server_s(utc_ms: int, off) -> int:
    """UTC ms → the server clock's seconds (the inverse of mt5c.server_to_utc_ms; one correction step finds a DST hour)."""
    s = utc_ms // 1000 + (utc_ms - mt5c.server_to_utc_ms(utc_ms // 1000, off)) // 1000
    return s + (utc_ms - mt5c.server_to_utc_ms(s, off)) // 1000


def _to_utc(t_server: np.ndarray, off) -> np.ndarray:
    """Server-clock ms → UTC ms, with each hour's own offset (a DST change falls on an hour)."""
    hours, inv = np.unique(t_server // 3_600_000, return_inverse=True)
    shift = np.array([h * 3_600_000 - mt5c.server_to_utc_ms(int(h * 3600), off) for h in hours], dtype=np.int64)
    return t_server - shift[inv]


class Store:
    """The engine's side: which ticks to ask for this loop (requests) and what to do with the reply (take)."""

    def __init__(self):
        self.last: Dict[str, Optional[int]] = {}

    def requests(self, sym: str, now_ms: int, off) -> List[Dict]:
        server_s = lambda utc_ms: _to_server_s(utc_ms, off)
        tmp = os.path.join(TICK_DIR, "tmp")
        os.makedirs(tmp, exist_ok=True)
        m, reqs = meta(sym), []
        if not m.get("point"):
            reqs.append({"op": "info", "symbol": sym, "kind": "info"})
        if sym not in self.last:
            self.last[sym] = _last(sym)
        today = _day_ms(_day(now_ms))
        if self.last[sym] and self.last[sym] < today:                   # past days come whole (below), not by catching up
            self.last[sym] = None
        start = max(today, self.last[sym] - REWRITE_MS) if self.last[sym] else today
        reqs.append({"op": "ticks", "symbol": sym, "from_s": server_s(start) - MARGIN_S, "kind": "new", "start": start,
                     "path": mt5c._winpath(os.path.join(tmp, f"{sym}-new.npy"))})
        todo = [d for d in range(today - DAY_MS, today - BACKFILL_DAYS * DAY_MS - 1, -DAY_MS) if _day(d) not in m.get("complete", [])]
        if todo:                                                        # the newest past day not complete yet
            reqs.append({"op": "ticks", "symbol": sym, "from_s": server_s(todo[0]) - MARGIN_S, "to_s": server_s(todo[0] + DAY_MS) + MARGIN_S,
                         "kind": "day", "day": _day(todo[0]), "path": mt5c._winpath(os.path.join(tmp, f"{sym}-day.npy"))})
        return reqs

    def take(self, sym: str, req: Dict, res: Dict, off) -> int:
        """One reply → the day files. → the ticks stored."""
        if "result" not in res:
            raise RuntimeError(f"{sym} {req['kind']}: {res.get('error')}")
        m = meta(sym)
        if req["kind"] == "info":
            _save_meta(sym, {**m, "point": res["result"]["point"], "digits": res["result"]["digits"]})
            return 0
        point = m.get("point")
        if not point:
            return 0
        if not res["result"]["n"]:
            if req["kind"] == "day":                                    # a weekend day: complete with nothing in it
                _save_meta(sym, {**m, "complete": sorted(set(m.get("complete", [])) | {req["day"]})})
            return 0
        reply = os.path.join(TICK_DIR, "tmp", f"{sym}-{req['kind']}.npy")
        raw = np.load(reply)
        os.remove(reply)                                                # read once: no copies left behind
        a = np.empty(len(raw), TICK)
        a["t"] = _to_utc(raw["time_msc"], off)
        a["bid"] = np.rint(raw["bid"] / point)
        a["ask"] = np.rint(raw["ask"] / point)
        a["flags"] = raw["flags"]
        if req["kind"] == "day":                                        # a whole past day, over whatever its file had
            a = a[(a["t"] >= _day_ms(req["day"])) & (a["t"] < _day_ms(req["day"]) + DAY_MS)]
            a.tofile(os.path.join(_dir(sym), f"{req['day']}.bin"))
            _save_meta(sym, {**m, "complete": sorted(set(m.get("complete", [])) | {req["day"]})})
            prune()
            return len(a)
        a = a[a["t"] >= req["start"]]                                   # the reply from `start` replaces what the file has
        if not len(a):
            return 0
        path = os.path.join(_dir(sym), f"{_day(req['start'])}.bin")
        if self.last.get(sym) and os.path.exists(path):
            _cut_tail(path, req["start"])
        days = a["t"] // DAY_MS
        for d in np.unique(days):
            with open(os.path.join(_dir(sym), f"{_day(int(d) * DAY_MS)}.bin"), "ab") as f:
                a[days == d].tofile(f)
        self.last[sym] = int(a["t"][-1])
        return len(a)



def prune() -> None:
    """Delete the day files older than KEEP_DAYS of every symbol (also the ones no page watches any more)."""
    cut = _day_ms(_dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")) - KEEP_DAYS * DAY_MS
    for sym in os.listdir(TICK_DIR):
        if sym == "tmp" or not os.path.isdir(_dir(sym)):
            continue
        old = [d for d in _days(sym) if _day_ms(d) < cut]
        for d in old:
            os.remove(os.path.join(_dir(sym), f"{d}.bin"))
        if old:
            m = meta(sym)
            _save_meta(sym, {**m, "complete": [d for d in m.get("complete", []) if d not in old]})
