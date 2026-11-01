"""
concepter/scan.py — run ONE engine over every closed bar of a symbol's history and save each distinct signal it
reports (first time seen). Used to find the bars where an expensive engine is needed: e.g. every Claude setup, so
Kronos only has to forecast at those bars (concepter/kronos/backfill.py).

    python3 -m concepter.scan --engine claude --kinds setup --symbol GOLD --data <dir> --out <file.jsonl>
"""
from __future__ import annotations

import argparse
import bisect
import json
import time
from typing import List

from marketdata import data as MD
from shared.contracts import TF_MS, View

from . import engine as make_engine


def scan(engine_name: str, kinds: List[str], symbol: str, data_dir: str, out: str, step_tf: str = "M15",
         every: int = 2000, **kw) -> int:
    eng = make_engine(engine_name, **kw)
    info, series = MD.load(symbol, data_dir)
    closes = {k: [b.t + TF_MS[k] for b in v] for k, v in series.items()}
    seen, n, t0 = set(), 0, time.time()
    bars = series[step_tf]
    with open(out, "w") as f:
        for i in range(eng.lookback, len(bars)):
            now = bars[i].t + TF_MS[step_tf]
            view = View(symbol, now, {k: series[k][max(0, j - eng.lookback):j]
                                      for k in eng.timeframes if k in series
                                      for j in [bisect.bisect_right(closes[k], now)]}, info)
            for s in eng.on_bar(view).signals:
                if s.kind in kinds and s.key not in seen:
                    seen.add(s.key)
                    f.write(json.dumps({"now": now, **s.to_dict()}, default=float) + "\n")
                    n += 1
            if i % every == 0:
                done = (i - eng.lookback + 1) / (len(bars) - eng.lookback)
                print(f"{symbol} {i}/{len(bars)} bars, {n} signals, {time.time() - t0:.0f} s "
                      f"(~{(time.time() - t0) / max(done, 1e-9) * (1 - done) / 60:.0f} min left)", flush=True)
    print(f"done: {n} signals in {time.time() - t0:.0f} s → {out}")
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--kinds", required=True, help="comma-separated signal kinds")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--data", default=MD.SAMPLE_DIR)
    ap.add_argument("--out", required=True)
    ap.add_argument("--provider", default="toolkit", help="claude only")
    a = ap.parse_args()
    kw = {"provider": a.provider} if a.engine == "claude" else {}
    scan(a.engine, a.kinds.split(","), a.symbol, a.data, a.out, **kw)
