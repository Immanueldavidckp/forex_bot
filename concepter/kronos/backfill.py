"""
concepter/kronos/backfill.py — Kronos forecasts for PAST bars, exactly as the live forecaster (signals.py) makes
them: the last CONTEXT closed M15 bars (open, high, low, close, tick volume) up to that bar → PATHS paths of the
next HORIZON bars. For backtests: forecast only at the bars a strategy needs (e.g. every Claude setup from
concepter/scan.py), not at every bar (~10 s a forecast on the GTX 1650).

    cd ~/forex && ~/opt/kronos-venv/bin/python -m concepter.kronos.backfill --symbol GOLD --data <dir> \
        --at <scan.jsonl>            → <dir>/kronos_<SYMBOL>.jsonl.gz  (what concepter/kronos reads as "recorded")

Resumable: forecasts already in <dir>/kronos_<SYMBOL>.partial.jsonl are skipped.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import time

import numpy as np
import pandas as pd

from engine.config import KRONOS as K
from marketdata import data as MD
from shared.contracts import TF_MS

from .model import COLS, load, paths


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--at", required=True, help="jsonl with a 'now' (bar close, UTC ms) per line")
    ap.add_argument("--chunk", type=int, default=4, help="forecast points per GPU pass")
    a = ap.parse_args()
    tf, ctx, hz, npaths = K["TF"], K["CONTEXT"], K["HORIZON"], K["PATHS"]
    ms = TF_MS[tf]
    _, series = MD.load(a.symbol, a.data)
    bars = series[tf]
    idx = {b.t: i for i, b in enumerate(bars)}
    with open(a.at) as f:
        want = sorted({json.loads(line)["now"] - ms for line in f if line.strip()})      # bar OPEN times
    part = os.path.join(a.data, f"kronos_{a.symbol}.partial.jsonl")
    done = set()
    if os.path.exists(part):
        with open(part) as f:
            done = {json.loads(line)["bar_t"] for line in f if line.strip()}
    todo = [t for t in want if t not in done and t in idx and idx[t] + 1 >= ctx]
    skipped = [t for t in want if t not in idx or idx[t] + 1 < ctx]
    print(f"{a.symbol}: {len(want)} bars asked, {len(done)} done, {len(todo)} to do, {len(skipped)} without "
          f"{ctx} bars of history", flush=True)
    pred = load()
    step = pd.Timedelta(milliseconds=ms)
    t0 = time.time()
    for k in range(0, len(todo), a.chunk):
        ts = todo[k:k + a.chunk]
        wins = []
        for t in ts:
            rows = bars[idx[t] + 1 - ctx: idx[t] + 1]
            wins.append(pd.DataFrame([[b.o, b.h, b.l, b.c, b.v] for b in rows], columns=COLS,
                                     index=pd.to_datetime([b.t for b in rows], unit="ms")))
        cl = paths(pred, wins, step, hz, npaths, batch=16)
        with open(part, "a") as f:
            for t, c in zip(ts, cl):
                last = float(bars[idx[t]].c)
                f.write(json.dumps({"symbol": a.symbol, "bar_t": t, "last": last, "paths": npaths, "horizon": hz,
                                    "p_up": round(float((c[:, -1] > last).mean()), 4),
                                    "median": [round(float(x), 8) for x in np.median(c, axis=0)],
                                    "q10": [round(float(x), 8) for x in np.percentile(c, 10, axis=0)],
                                    "q90": [round(float(x), 8) for x in np.percentile(c, 90, axis=0)],
                                    "made": "backfill"}) + "\n")
        n = k + len(ts)
        el = time.time() - t0
        print(f"{n}/{len(todo)} in {el / 60:.1f} min (~{el / n * (len(todo) - n) / 60:.0f} min left)", flush=True)
    with open(part) as f:
        lines = sorted((line for line in f if line.strip()), key=lambda s: json.loads(s)["bar_t"])
    with gzip.open(os.path.join(a.data, f"kronos_{a.symbol}.jsonl.gz"), "wt") as f:
        f.writelines(lines)
    print(f"done: {len(lines)} forecasts → {a.data}/kronos_{a.symbol}.jsonl.gz", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
