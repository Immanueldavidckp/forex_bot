"""
engine/live.py — the live market on the /smc page (David 2026-10-29: "add the live market"): the tick and the
forming bar of every chart timeframe, only for the symbols a page is watching.

The dashboard touches engine_data/live/want/<SYMBOL> on every poll (want); each engine loop reads the symbols
touched in the last WANT_S seconds with one bridge call (step) and writes engine_data/live/<SYMBOL>.json:
{"sym", "at" (written, ms), "t_ms" (the tick's time, UTC ms), "bid", "ask", "bars": {tf: [[t_ms, o, h, l, c, v], ...]}}
— the engine's own bar counts per timeframe (ENGINE["bars"]), the forming one last. learn.load_bars reads the closed
ones like a view file: GOLD is no V5 symbol (no view file), so this is what brings its chart up to now. The page
itself gets only the last LIVE_BARS of each timeframe (read). The same call records the watched symbols' ticks for the
order-flow chart (ticks.py). The engine stays MT5's only user.
"""
from __future__ import annotations

import json
import os
import time
from typing import Dict, List

from .book import _write
from .config import CHART_EXTRA, DATA_DIR, ENGINE, LIVE_DIR
from .feed import Feed, mt5c, now_ms
from .ticks import Store

TICKS = Store()

HIST_DIR = os.path.join(DATA_DIR, "history")
WANT_DIR = os.path.join(LIVE_DIR, "want")
WANT_S = 60          # a page polls every few seconds: a symbol nobody asked for in a minute is not read any more
MAX_SYMBOLS = 8      # one bridge call stays small, whoever has pages open
QUOTES = "quotes.json"   # in LIVE_DIR, every loop: the tick of EVERY symbol, so a chart is live the moment it opens
QUOTE_S = 60         # a quote older than this is not live any more (the engine stopped)
LIVE_BARS = 2        # to the page: the bar that just closed + the forming one, so it never misses a close between reloads


def want(sym: str) -> None:
    """The dashboard's side: a page is watching `sym` now."""
    os.makedirs(WANT_DIR, exist_ok=True)
    p = os.path.join(WANT_DIR, sym)
    with open(p, "a"):
        os.utime(p)


def wanted(symbols) -> List[str]:
    """The symbols asked for in the last WANT_S seconds that the engine knows, newest ask first."""
    try:
        names = os.listdir(WANT_DIR)
    except FileNotFoundError:
        return []
    now, asked = time.time(), []
    for s in names:
        try:
            age = now - os.path.getmtime(os.path.join(WANT_DIR, s))
        except FileNotFoundError:
            continue
        if age <= WANT_S and s in symbols:
            asked.append((age, s))
    return [s for _, s in sorted(asked)][:MAX_SYMBOLS]


def read(sym: str) -> Dict:
    """The dashboard's side: the last live file of `sym` with the last LIVE_BARS bars per timeframe, {} when there is none."""
    try:
        with open(os.path.join(LIVE_DIR, f"{sym}.json")) as f:
            d = json.load(f)
    except (FileNotFoundError, ValueError):
        d = {}
    d["bars"] = {tf: b[-LIVE_BARS:] for tf, b in d.get("bars", {}).items()}
    # David 2026-11-12 "most of the symbols are not live": a symbol's own file only starts one engine loop after its
    # page opened — until then (and whenever it is older) the all-symbols quote file gives the tick
    try:
        with open(os.path.join(LIVE_DIR, QUOTES)) as f:
            qs = json.load(f)
        q = qs.get("q", {}).get(sym)
    except (FileNotFoundError, ValueError):
        q = None
    if q and qs.get("at", 0) - d.get("at", 0) > 5000:              # its own file was not written in that loop
        fresh = qs["at"] - d.get("at", 0) < QUOTE_S * 1000          # the bars are still this minute's: keep them
        d = {"sym": sym, "at": qs["at"], "t_ms": q[0], "bid": q[1], "ask": q[2], "bars": d["bars"] if fresh else {}}
    return d if d.get("at") else {}


def step(feed: Feed) -> List[str]:
    """The engine's side, once per loop: one bridge call for the watched symbols → their live files. → the symbols read."""
    try:                                          # the V5 symbols + the ones with a saved history (GOLD)
        known = set(feed.symbols) | {f[:-5] for f in os.listdir(HIST_DIR) if f.endswith(".json")}
    except FileNotFoundError:
        known = set(feed.symbols)
    known |= set(CHART_EXTRA)
    asked = wanted(known)
    syms = asked + [s for s in CHART_EXTRA if s not in asked]      # no view file: their bars come only from here, always
    tfs, off = ENGINE["chart_tfs"], feed.clock()
    reqs: List[Dict] = []
    for s in syms:
        reqs += [{"op": "tick", "symbol": s}] + [{"op": "rates", "symbol": s, "tf": tf, "count": ENGINE["bars"][tf]} for tf in tfs]
    rest = sorted(known - set(syms))                               # everything else: just the tick → quotes.json
    quote_reqs = [{"op": "tick", "symbol": s} for s in rest]
    tick_reqs = [(s, r) for s in asked for r in TICKS.requests(s, now_ms(), off)]
    res = mt5c.call(reqs + quote_reqs + [r for _, r in tick_reqs], timeout=120)
    k, done = 1 + len(tfs), []
    quotes = {}
    for s, x in list(zip(syms, res[::k])) + list(zip(rest, res[len(reqs):len(reqs) + len(rest)])):
        q = x.get("result") if isinstance(x, dict) else None
        if q and q.get("bid"):
            quotes[s] = [mt5c.server_to_utc_ms(int(q["time"]), off) if q.get("time") else None, q.get("bid"), q.get("ask")]
    os.makedirs(LIVE_DIR, exist_ok=True)
    _write(os.path.join(LIVE_DIR, QUOTES), {"at": now_ms(), "q": quotes})
    for i, s in enumerate(syms):
        tk, rates = res[i * k], res[i * k + 1:(i + 1) * k]
        if "result" not in tk or not tk["result"]:
            continue
        q = tk["result"]
        bars = {tf: [[mt5c.server_to_utc_ms(x[0], off), x[1], x[2], x[3], x[4], int(x[5])] for x in r["result"]]
                for tf, r in zip(tfs, rates) if r.get("result")}
        _write(os.path.join(LIVE_DIR, f"{s}.json"),
               {"sym": s, "at": now_ms(), "t_ms": mt5c.server_to_utc_ms(int(q["time"]), off) if q.get("time") else None,
                "bid": q.get("bid"), "ask": q.get("ask"), "bars": bars})
        done.append(s)
    errors = []
    for (s, r), x in zip(tick_reqs, res[len(reqs) + len(rest):]):          # in order: a symbol's info before its ticks
        try:
            TICKS.take(s, r, x, off)
        except Exception as e:
            errors.append(f"{type(e).__name__}: {e}")
    if errors:                                                 # the quotes are written; run.py logs this once
        raise RuntimeError("ticks: " + "; ".join(errors))
    return done
