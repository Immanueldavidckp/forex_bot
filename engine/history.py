"""
engine/history.py — FxPro's bar history for the backtest, saved once per symbol so replays never touch MT5.

    python3 -m engine.history [--symbols BITCOIN,EURUSD]     → engine_data/history/<SYMBOL>.json
    python3 -m engine.history --tfs M15,M30,H4               only these timeframes, as deep as the terminal goes
                                                             (DEEP bars each); the file's other timeframes are kept

Per timeframe as many bars as the terminal gives (M5 99,000 ≈ 11 months of a coin, 16 of a forex pair; the
higher timeframes reach further back, so their windows are full from the first M5 bar). Bar times are the
server's wall clock, which follows EU summer time (UTC+3 / UTC+2, Cyprus); they are stored as epoch ms UTC
with the spread in price units and the tick volume: {"info", "market", "bars": {tf: [[t, o, h, l, c, spread, tick_volume], ...]}}
(files saved before 2026-10-29 have no tick volume).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import time
from typing import Dict, List
from zoneinfo import ZoneInfo

from .config import DATA_DIR, ENGINE
from .feed import Feed, mt5c

HIST_DIR = os.path.join(DATA_DIR, "history")
COUNTS = {"M5": 99000, "M15": 33000, "M30": 16500, "H1": 8500, "H4": 2200}
DEEP = 99999          # the terminal's "Max bars in chart" is 100,000 (common.ini MaxBars); more = "Invalid params"
SERVER_TZ = ZoneInfo(ENGINE["server_tz"])      # FxPro: UTC+2 in winter, UTC+3 in EU summer time


def server_to_utc_ms(t: int) -> int:
    wall = _dt.datetime.fromtimestamp(t, _dt.timezone.utc).replace(tzinfo=SERVER_TZ)
    return int(wall.timestamp() * 1000)


def fetch(sym: str, info: Dict, market: str, counts: Dict[str, int] = COUNTS) -> Dict:
    res = mt5c.call([{"op": "rates", "symbol": sym, "tf": tf, "count": n} for tf, n in counts.items()], timeout=600)
    bars: Dict[str, List[list]] = {}
    pt = float(info["point"])
    for tf, r in zip(counts, res):
        if "result" not in r:
            if counts is COUNTS:
                raise RuntimeError(f"{sym} {tf}: {r.get('error')}")
            continue          # a deep fetch: the terminal is often still downloading — main() asks again
        bars[tf] = [[server_to_utc_ms(x[0]), x[1], x[2], x[3], x[4], round((x[7] if len(x) > 7 else 0) * pt, 10),
                    int(x[5])] for x in r["result"]]
    return {"symbol": sym, "market": market, "info": info, "fetched": int(time.time()), "bars": bars}


def main() -> int:
    ap = argparse.ArgumentParser(description="save FxPro's bar history for the backtest")
    ap.add_argument("--symbols", default="", help="comma list (default: every symbol the engine trades)")
    ap.add_argument("--tfs", default="", help="comma list: deepen only these timeframes (DEEP bars), keep the rest")
    a = ap.parse_args()
    tfs = [t for t in a.tfs.split(",") if t]
    if any(t not in COUNTS for t in tfs):
        ap.error(f"--tfs: one of {','.join(COUNTS)}")
    counts = {t: DEEP for t in tfs} or COUNTS
    os.makedirs(HIST_DIR, exist_ok=True)
    feed = Feed()
    syms = feed.discover()
    if a.symbols:
        want = a.symbols.split(",")
        for s in [s for s in want if s not in syms]:     # not one the engine trades (GOLD): asked for by name
            r = mt5c.call([{"op": "info", "symbol": s}], timeout=60)[0]
            if "result" not in r:
                print(f"{s}: no such symbol ({r.get('error')})", flush=True)
                continue
            old = os.path.join(HIST_DIR, f"{s}.json")
            feed.info[s] = r["result"]
            feed.market[s] = json.load(open(old)).get("market", "other") if os.path.exists(old) else "other"
            syms.append(s)
        syms = [s for s in syms if s in want]
    for i, s in enumerate(syms, 1):
        t0 = time.time()
        try:
            d = fetch(s, feed.info[s], feed.market[s], counts)
            for _ in range(4):                           # deep fetch: ask again for what the terminal had not loaded
                todo = {tf: n for tf, n in counts.items() if tf not in d["bars"]}
                if not todo:
                    break
                time.sleep(15)
                d["bars"].update(fetch(s, feed.info[s], feed.market[s], todo)["bars"])
            missing = [tf for tf in counts if tf not in d["bars"]]
            if missing:
                print(f"{i}/{len(syms)} {s}: {','.join(missing)} not given by the terminal, the old bars kept", flush=True)
        except Exception as e:
            print(f"{i}/{len(syms)} {s}: FAILED {e}", flush=True)
            continue
        path = os.path.join(HIST_DIR, f"{s}.json")
        if tfs and os.path.exists(path):                 # keep the timeframes not asked for
            with open(path) as f:
                old = json.load(f)
            d["bars"] = {**old.get("bars", {}), **d["bars"]}
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(d, f, separators=(",", ":"))
        os.replace(tmp, path)
        span = ", ".join(f"{tf} {len(b)} from {_dt.datetime.fromtimestamp(b[0][0] / 1000, _dt.timezone.utc):%Y-%m-%d}"
                         for tf, b in d["bars"].items() if b and tf in counts)
        print(f"{i}/{len(syms)} {s}: {span} ({time.time() - t0:.0f} s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
