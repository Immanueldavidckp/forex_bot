"""
kronos/fetch.py — FxPro bars WITH tick volume for the Kronos test (the engine's history cache has no volume).

    python3 -m kronos.fetch [--symbols GOLD,EURUSD,BITCOIN] [--tfs M5,M15,H1]   → engine_data/kronos/bars/<SYMBOL>_<TF>.json

Rows: [t_utc_ms, o, h, l, c, tick_volume, spread_price]; server times converted like engine.history.
"""
from __future__ import annotations

import argparse
import json
import os

from engine.config import DATA_DIR
from engine.history import server_to_utc_ms
from engine.feed import mt5c

OUT = os.path.join(DATA_DIR, "kronos", "bars")
COUNTS = {"M5": 99000, "M15": 33000, "H1": 8500}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="GOLD,EURUSD,BITCOIN")
    ap.add_argument("--tfs", default=",".join(COUNTS), help="comma list of " + "/".join(COUNTS))
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    syms = a.symbols.split(",")
    tfs = {tf: COUNTS[tf] for tf in a.tfs.split(",")}
    infos = mt5c.call([{"op": "info", "symbol": s} for s in syms], timeout=180)
    for s, inf in zip(syms, infos):
        pt = float(inf["result"]["point"])
        res = mt5c.call([{"op": "rates", "symbol": s, "tf": tf, "count": n} for tf, n in tfs.items()], timeout=600)
        for tf, r in zip(tfs, res):
            if "result" not in r:
                print(s, tf, "FAILED", r.get("error"))
                continue
            rows = [[server_to_utc_ms(x[0]), x[1], x[2], x[3], x[4], x[5], round(x[7] * pt, 10)] for x in r["result"]]
            with open(os.path.join(OUT, f"{s}_{tf}.json"), "w") as f:
                json.dump({"symbol": s, "tf": tf, "info": inf["result"], "bars": rows}, f)
            print(s, tf, len(rows), "bars", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
