"""
kronos/signals.py — the GPU side of Kronos' trades (service kronos-signals; the trades are engine/kronos_book.py).

    cd ~/forex && ~/opt/kronos-venv/bin/python -m kronos.signals

Never talks to MT5: the engine writes each symbol's closed M15 bars to engine_data/kronos/feed/<SYMBOL>.json once
per bar; for every new last bar this draws KRONOS["PATHS"] Kronos-base paths of the next KRONOS["HORIZON"] bars and
writes engine_data/kronos/signals.json ({symbol: last, p_up, median / q10 / q90 per forecast bar, ...}), and appends
each forecast to signals.jsonl.
"""
from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd

from engine.config import KRONOS as K

from .model import COLS, load, paths

FEED_DIR = os.path.join(K["DIR"], "feed")
SIGNALS_FILE = os.path.join(K["DIR"], "signals.json")
HISTORY_FILE = os.path.join(K["DIR"], "signals.jsonl")
STEP = pd.Timedelta(minutes={"M5": 5, "M15": 15, "M30": 30, "H1": 60}[K["TF"]])
CHUNK = 4                                  # symbols per GPU pass (4 × 16 paths)


def log(msg: str) -> None:
    print(f"[kronos {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def frame(rows) -> pd.DataFrame:
    return pd.DataFrame([r[1:6] for r in rows], columns=COLS, index=pd.to_datetime([r[0] for r in rows], unit="ms"))


def main() -> int:
    pred = load()
    log(f"Kronos-base loaded on {pred.device}; {', '.join(K['SYMBOLS'])} {K['TF']}, {K['PATHS']} paths × {K['HORIZON']} bars")
    try:
        with open(SIGNALS_FILE) as f:
            sigs = json.load(f)
    except (FileNotFoundError, ValueError):
        sigs = {}
    while True:
        todo = []
        for sym in K["SYMBOLS"]:
            try:
                with open(os.path.join(FEED_DIR, f"{sym}.json")) as f:
                    rows = json.load(f)["bars"]
            except (FileNotFoundError, ValueError, KeyError):
                continue
            if len(rows) >= K["CONTEXT"] and rows[-1][0] != (sigs.get(sym) or {}).get("bar_t"):
                todo.append((sym, rows[-K["CONTEXT"]:]))
        # CHUNK symbols per GPU pass, signals.json written after each: the first symbols can trade ~1 min after the
        # close instead of waiting for all 20 (~3 min alone on the GTX 1650, ~6 min while kronos.evaluate shares it)
        for k in range(0, len(todo), CHUNK):
            part = todo[k:k + CHUNK]
            t0 = time.time()
            cl = paths(pred, [frame(r) for _, r in part], STEP, K["HORIZON"], K["PATHS"], batch=16)
            secs = round(time.time() - t0, 1)
            for (sym, rows), c in zip(part, cl):
                last = float(rows[-1][4])
                s = {"symbol": sym, "bar_t": rows[-1][0], "last": last, "paths": K["PATHS"], "horizon": K["HORIZON"],
                     "p_up": round(float((c[:, -1] > last).mean()), 4),
                     "median": [round(float(x), 8) for x in np.median(c, axis=0)],
                     "q10": [round(float(x), 8) for x in np.percentile(c, 10, axis=0)],
                     "q90": [round(float(x), 8) for x in np.percentile(c, 90, axis=0)],
                     "made_ms": int(time.time() * 1000), "secs": secs}
                with open(HISTORY_FILE, "a") as f:
                    f.write(json.dumps(s) + "\n")
                s["each"] = [[round(float(x), 8) for x in p] for p in c]     # every path (latest only: the big chart draws them)
                sigs[sym] = s
                log(f"{sym}: P(up) {s['p_up']:.0%}, median {s['median'][-1] - last:+.5g} in {K['HORIZON']} bars")
            tmp = SIGNALS_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(sigs, f)
            os.replace(tmp, SIGNALS_FILE)
        time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
