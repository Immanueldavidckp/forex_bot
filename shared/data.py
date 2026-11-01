"""
shared/data.py — bars for the paper runs, without MT5.

    shared/sample_data/<SYMBOL>.json.gz    {symbol, info, bars: {TF: [[t_ms, o, h, l, c, spread, volume], ...]}}

The sample is a cut of David's MT5 history (engine_data/history/<SYMBOL>.json, FxPro demo, bid prices; spread
already in PRICE units, the bar's minimum spread). `python3 -m shared.data export GOLD EURUSD` makes new samples on
David's laptop.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
from typing import Dict, List, Tuple

from .contracts import Bar

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(HERE, "sample_data")
HISTORY_DIR = os.path.join(os.path.dirname(HERE), "engine_data", "history")


def load(symbol: str, folder: str = SAMPLE_DIR) -> Tuple[Dict, Dict[str, List[Bar]]]:
    """→ (symbol info, {tf: [Bar, ...]})."""
    path = os.path.join(folder, f"{symbol}.json.gz")
    with gzip.open(path, "rt") as f:
        d = json.load(f)
    bars = {tf: [Bar(t=int(r[0]), o=r[1], h=r[2], l=r[3], c=r[4],
                     spread=(r[5] if len(r) > 5 and r[5] is not None else 0),
                     v=(r[6] if len(r) > 6 and r[6] is not None else 0))
                 for r in rows]
            for tf, rows in d["bars"].items()}
    return d["info"], bars


def available(folder: str = SAMPLE_DIR) -> List[str]:
    return sorted(f[:-len(".json.gz")] for f in os.listdir(folder) if f.endswith(".json.gz"))


def export(symbols: List[str], tfs: List[str], days: int) -> None:
    """Cut the newest `days` of David's MT5 history into shared/sample_data (run on David's laptop)."""
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    keep = ("name", "description", "digits", "point", "trade_tick_size", "trade_tick_value", "trade_contract_size",
            "volume_min", "volume_step", "volume_max", "trade_stops_level", "currency_profit")
    for sym in symbols:
        with open(os.path.join(HISTORY_DIR, f"{sym}.json")) as f:
            d = json.load(f)
        out = {"symbol": sym, "info": {k: d["info"].get(k) for k in keep}, "bars": {}}
        for tf in tfs:
            rows = d["bars"].get(tf, [])
            if not rows:
                continue
            start = rows[-1][0] - days * 86_400_000
            out["bars"][tf] = [r for r in rows if r[0] >= start]
        path = os.path.join(SAMPLE_DIR, f"{sym}.json.gz")
        with gzip.open(path, "wt") as f:
            json.dump(out, f, separators=(",", ":"))
        print(sym, {tf: len(v) for tf, v in out["bars"].items()}, f"{os.path.getsize(path) // 1024} KB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("symbols", nargs="+")
    e.add_argument("--tfs", default="M5,M15,H1,H4")
    e.add_argument("--days", type=int, default=60)
    a = ap.parse_args()
    export(a.symbols, a.tfs.split(","), a.days)
