"""
engine/history.py — FxPro's bar history for the backtest, saved once per symbol so replays never touch MT5.

    python3 -m engine.history [--symbols BITCOIN,EURUSD]     → engine_data/history/<SYMBOL>.json

Per timeframe as many bars as the terminal gives (M5 99,000 ≈ 11 months of a coin, 16 of a forex pair; the
higher timeframes reach further back, so their windows are full from the first M5 bar). Bar times are the
server's wall clock, which follows EU summer time (UTC+3 / UTC+2, Cyprus); they are stored as epoch ms UTC
with the spread in price units: {"info", "market", "bars": {tf: [[t, o, h, l, c, spread], ...]}}.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import time
from typing import Dict, List
from zoneinfo import ZoneInfo

from .config import DATA_DIR
from .feed import Feed, mt5c

HIST_DIR = os.path.join(DATA_DIR, "history")
COUNTS = {"M5": 99000, "M15": 33000, "M30": 16500, "H1": 8500, "H4": 2200}
SERVER_TZ = ZoneInfo("Asia/Nicosia")          # FxPro: UTC+2 in winter, UTC+3 in EU summer time


def server_to_utc_ms(t: int) -> int:
    wall = _dt.datetime.fromtimestamp(t, _dt.timezone.utc).replace(tzinfo=SERVER_TZ)
    return int(wall.timestamp() * 1000)


def fetch(sym: str, info: Dict, market: str) -> Dict:
    res = mt5c.call([{"op": "rates", "symbol": sym, "tf": tf, "count": n} for tf, n in COUNTS.items()], timeout=600)
    bars: Dict[str, List[list]] = {}
    pt = float(info["point"])
    for tf, r in zip(COUNTS, res):
        if "result" not in r:
            raise RuntimeError(f"{sym} {tf}: {r.get('error')}")
        bars[tf] = [[server_to_utc_ms(x[0]), x[1], x[2], x[3], x[4], round((x[7] if len(x) > 7 else 0) * pt, 10)] for x in r["result"]]
    return {"symbol": sym, "market": market, "info": info, "fetched": int(time.time()), "bars": bars}


def main() -> int:
    ap = argparse.ArgumentParser(description="save FxPro's bar history for the backtest")
    ap.add_argument("--symbols", default="", help="comma list (default: every symbol the engine trades)")
    a = ap.parse_args()
    os.makedirs(HIST_DIR, exist_ok=True)
    feed = Feed()
    syms = feed.discover()
    if a.symbols:
        syms = [s for s in syms if s in a.symbols.split(",")]
    for i, s in enumerate(syms, 1):
        t0 = time.time()
        try:
            d = fetch(s, feed.info[s], feed.market[s])
        except Exception as e:
            print(f"{i}/{len(syms)} {s}: FAILED {e}", flush=True)
            continue
        with open(os.path.join(HIST_DIR, f"{s}.json"), "w") as f:
            json.dump(d, f, separators=(",", ":"))
        m5 = d["bars"]["M5"]
        print(f"{i}/{len(syms)} {s}: {len(m5)} M5 bars from {_dt.datetime.fromtimestamp(m5[0][0] / 1000, _dt.timezone.utc):%Y-%m-%d}"
              f" ({time.time() - t0:.0f} s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
