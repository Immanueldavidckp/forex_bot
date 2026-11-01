"""
concepter/run.py — run a STRATEGY on recorded bars with the paper executor (no MT5 needed: the friend's laptop,
backtests, trying a new model).

    python3 -m concepter.run --strategy kronos_direction_claude_bos --symbols GOLD,EURUSD
    python3 -m concepter.run --strategy v5_supply_demand --symbols GOLD --days 20
    python3 -m concepter.run --strategy kronos_direction_claude_bos --claude fake     (any provider)

Each closed bar of the strategy's timeframe, in time order across the symbols:
    1. the executor sees the bar (limit fills, SL / TP hits)
    2. the conductor runs the strategy: manages its trades, asks the engines in the [[need]] order, maybe opens
    3. every command goes to the executor (David's limits first); the result is logged
Output in runs/<strategy>-<time>/: journal.jsonl (each decision: signals used, commands, results, notes), trades.jsonl,
marks_<SYM>.json (the last marks, for drawing), summary.json.
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import time
from typing import Any, Dict, List, Optional

from marketdata import data as MD
from shared import rules as R
from shared.contracts import TF_MS, View

from executor.paper import PaperExecutor

from . import engine as make_engine
from .conductor import Conductor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(strategy: str, symbols: List[str], engine_kw: Optional[Dict[str, dict]] = None, days: Optional[float] = None,
        balance: float = 10_000.0, out_dir: Optional[str] = None, data_dir: str = MD.SAMPLE_DIR,
        quiet: bool = False, engines: Optional[Dict] = None, overrides: Optional[Dict[str, Any]] = None) -> Dict:
    S = R.strategy(strategy)
    for key, val in (overrides or {}).items():              # a what-if on this run only; the file is not changed
        *path, last = key.split(".")
        node = S.spec
        for k in path:
            node = node.setdefault(k, {})
        node[last] = val
    S.problems = S.check(R.engines())
    engine_kw = {k: dict(v) for k, v in (engine_kw or {}).items()}
    engine_kw.setdefault("kronos", {}).setdefault("data_dir", data_dir)     # recorded forecasts sit with the bars
    engines = engines or {n: make_engine(n, **engine_kw.get(n, {})) for n in sorted(S.engines)}
    tf = S.timeframe
    infos, series, closes = {}, {}, {}
    for s in symbols:
        infos[s], series[s] = MD.load(s, data_dir)
        closes[s] = {k: [b.t + TF_MS[k] for b in v] for k, v in series[s].items()}
    ex = PaperExecutor(infos, balance=balance)
    cond = Conductor(S, engines, ex)

    def view_for(symbol: str, now: int, tfs: List[str], lookback: int) -> View:
        out = {}
        for k in tfs:
            if k in series[symbol]:
                i = bisect.bisect_right(closes[symbol][k], now)
                out[k] = series[symbol][k][max(0, i - lookback):i]
        return View(symbol=symbol, now=now, bars=out, info=infos[symbol])

    warm = max([e.lookback for e in engines.values()] + [200])
    steps = sorted((b.t + TF_MS[tf], s, i) for s in symbols for i, b in enumerate(series[s][tf]) if i >= warm)
    if days:
        steps = [x for x in steps if x[0] >= steps[-1][0] - days * 86_400_000]

    journal: List[Dict] = []
    last_marks: Dict[str, list] = {}
    t0 = time.time()
    for now, sym, i in steps:
        for t in ex.on_bar(sym, series[sym][tf][i], now):
            journal.append({"t": now, "symbol": sym, "event": "exit", "trade": t.to_dict()})
        d, results = cond.step(sym, now, view_for)
        if d.marks:
            last_marks[sym] = [m.to_dict() for m in d.marks]
        if d.commands or d.signals:
            journal.append({"t": now, "symbol": sym, "event": "decision", "notes": d.notes.strip(" |"),
                            "signals": [s.to_dict() for s in d.signals], "results": [r.to_dict() for r in results]})

    trades = ex.trades()
    summary = {"strategy": f"{S.name} {S.version}", "overrides": overrides or {}, "engines": sorted(S.engines), "symbols": symbols,
               "bars": len(steps), "trades": len(trades), "won": sum(1 for t in trades if t.pnl > 0),
               "total_r": round(sum(t.r for t in trades), 2), "pnl": round(sum(t.pnl for t in trades), 2),
               "open_at_end": len(ex.positions()),
               "refused": sum(1 for j in journal if j["event"] == "decision" for r in j["results"] if not r["ok"]),
               "seconds": round(time.time() - t0, 1)}
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "journal.jsonl"), "w") as f:
            f.writelines(json.dumps(j, default=float) + "\n" for j in journal)
        with open(os.path.join(out_dir, "trades.jsonl"), "w") as f:
            f.writelines(json.dumps(t.to_dict()) + "\n" for t in trades)
        for s, mk in last_marks.items():
            with open(os.path.join(out_dir, f"marks_{s}.json"), "w") as f:
                json.dump(mk, f, default=float)
        with open(os.path.join(out_dir, "summary.json"), "w") as f:
            json.dump(summary, f, indent=1)
    if not quiet:
        print(json.dumps(summary, indent=1))
    return {"summary": summary, "journal": journal, "trades": trades, "executor": ex}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strategy", default="kronos_direction_claude_bos", help=f"one of {R.strategies()}")
    ap.add_argument("--symbols", default="GOLD,EURUSD")
    ap.add_argument("--claude", default="toolkit", help="the Claude engine's model: toolkit | fake | claude | gpt | gemini")
    ap.add_argument("--kronos", default="recorded", help="recorded | live")
    ap.add_argument("--days", type=float, default=None, help="only the last N days of the data")
    ap.add_argument("--balance", type=float, default=10_000.0)
    ap.add_argument("--data", default=MD.SAMPLE_DIR)
    ap.add_argument("--out", default=None, help="default runs/<strategy>-<time>")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="what-if on this run only, e.g. --set stop.buffer_atr=0.5 (the strategy file is not changed)")
    a = ap.parse_args()
    over = {}
    for kv in a.set:
        k, v = kv.split("=", 1)
        try:
            over[k] = json.loads(v)
        except ValueError:
            over[k] = v
    out = a.out or os.path.join(ROOT, "runs", f"{a.strategy}-{time.strftime('%Y%m%d-%H%M%S')}")
    run(a.strategy, a.symbols.split(","), {"claude": {"provider": a.claude}, "kronos": {"source": a.kronos}},
        a.days, a.balance, out, a.data, overrides=over)
    print("→", out)


if __name__ == "__main__":
    main()
