"""
marketdata/data.py — RECORDED market data for paper runs, without MT5 (the friend's laptop, backtests).

    marketdata/sample/<SYMBOL>.json.gz           {symbol, info, bars: {TF: [[t_ms, o, h, l, c, spread, volume], ...]}}
    marketdata/sample/kronos_<SYMBOL>.jsonl.gz   Kronos forecasts as the forecaster made them live (one per line)

The bars are a cut of David's MT5 history (engine_data/history/<SYMBOL>.json, FxPro demo, BID prices, spread in
PRICE units = the bar's minimum spread). The forecasts are engine_data/kronos/signals.jsonl (the live Kronos-base
forecaster, 16 paths, 2026-10-26 → 10-28) without the single paths.

    python3 -m marketdata.data export GOLD EURUSD [--days 60]     (David's laptop: new samples)
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
from typing import Dict, List, Tuple

from shared.contracts import Bar

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(HERE, "sample")
DATA_DIR = os.path.join(os.path.dirname(HERE), "engine_data")


def load(symbol: str, folder: str = SAMPLE_DIR) -> Tuple[Dict, Dict[str, List[Bar]]]:
    """→ (symbol info, {tf: [Bar, ...]})."""
    with gzip.open(os.path.join(folder, f"{symbol}.json.gz"), "rt") as f:
        d = json.load(f)
    bars = {tf: [Bar(t=int(r[0]), o=r[1], h=r[2], l=r[3], c=r[4],
                     spread=(r[5] if len(r) > 5 and r[5] is not None else 0),
                     v=(r[6] if len(r) > 6 and r[6] is not None else 0))
                 for r in rows]
            for tf, rows in d["bars"].items()}
    return d["info"], bars


def load_kronos(symbol: str, folder: str = SAMPLE_DIR) -> List[Dict]:
    """Recorded Kronos forecasts of one symbol, oldest first ([] when there are none)."""
    path = os.path.join(folder, f"kronos_{symbol}.jsonl.gz")
    if not os.path.exists(path):
        return []
    with gzip.open(path, "rt") as f:
        return sorted((json.loads(line) for line in f if line.strip()), key=lambda r: r["bar_t"])


def available(folder: str = SAMPLE_DIR) -> List[str]:
    return sorted(f[:-len(".json.gz")] for f in os.listdir(folder) if f.endswith(".json.gz"))


def export(symbols: List[str], tfs: List[str], days: int, out_dir: str = SAMPLE_DIR, with_kronos: bool = True) -> None:
    """Cut the newest `days` (0 = all) of David's MT5 history (and every recorded Kronos forecast) into out_dir."""
    os.makedirs(out_dir, exist_ok=True)
    keep = ("name", "description", "digits", "point", "trade_tick_size", "trade_tick_value", "trade_contract_size",
            "volume_min", "volume_step", "volume_max", "trade_stops_level", "currency_profit")
    forecasts: Dict[str, List[str]] = {s: [] for s in symbols}
    try:
        with open(os.path.join(DATA_DIR, "kronos", "signals.jsonl")) as f:
            for line in f:
                r = json.loads(line)
                if r.get("symbol") in forecasts:
                    r.pop("each", None)
                    forecasts[r["symbol"]].append(json.dumps(r, separators=(",", ":")))
    except FileNotFoundError:
        pass
    for sym in symbols:
        with open(os.path.join(DATA_DIR, "history", f"{sym}.json")) as f:
            d = json.load(f)
        out = {"symbol": sym, "info": {k: d["info"].get(k) for k in keep}, "bars": {}}
        for tf in tfs:
            rows = d["bars"].get(tf, [])
            if rows:
                start = rows[-1][0] - days * 86_400_000 if days else 0
                out["bars"][tf] = [r for r in rows if r[0] >= start]
        with gzip.open(os.path.join(out_dir, f"{sym}.json.gz"), "wt") as f:
            json.dump(out, f, separators=(",", ":"))
        if forecasts[sym] and with_kronos:
            with gzip.open(os.path.join(out_dir, f"kronos_{sym}.jsonl.gz"), "wt") as f:
                f.write("\n".join(forecasts[sym]) + "\n")
        print(sym, {tf: len(v) for tf, v in out["bars"].items()}, f"kronos forecasts {len(forecasts[sym])}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("symbols", nargs="+")
    e.add_argument("--tfs", default="M5,M15,H1,H4")
    e.add_argument("--days", type=int, default=60, help="0 = the whole history")
    e.add_argument("--out", default=SAMPLE_DIR)
    e.add_argument("--no-kronos", action="store_true", help="leave the recorded live forecasts out")
    a = ap.parse_args()
    export(a.symbols, a.tfs.split(","), a.days, a.out, not a.no_kronos)
