"""
concepters/run.py — run a concepter on recorded bars with the paper executor (no MT5 needed: the friend's laptop,
backtests, trying a new LLM).

    python3 -m concepters.run --concepter demo --rules supply_demand --symbols GOLD,EURUSD
    python3 -m concepters.run --concepter llm --provider fake --rules supply_demand --symbols GOLD --days 5

Each closed bar of the concepter's first timeframe, in time order across the symbols:
    1. the executor sees the bar (limit fills, SL / TP hits)
    2. the concepter gets its View (closed bars only, its own positions) and returns a Decision
    3. every command goes to the executor (guard first); the result is logged
Output in runs/<name>/: journal.jsonl (decisions with commands + results), trades.jsonl, marks_<SYM>.json (the last
marks, for drawing), summary.json.
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import time
from typing import Dict, List, Optional

from shared import data as DATA
from shared import rules as RULES
from shared.contracts import TF_MS, Bar, View

from executor.paper import PaperExecutor

from . import make

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(concepter, symbols: List[str], days: Optional[float] = None, balance: float = 10_000.0,
        out_dir: Optional[str] = None, data_dir: str = DATA.SAMPLE_DIR, quiet: bool = False) -> Dict:
    tfs = list(concepter.timeframes)
    base = tfs[0]
    infos, series = {}, {}
    for s in symbols:
        infos[s], bars = DATA.load(s, data_dir)
        series[s] = {tf: bars[tf] for tf in tfs if tf in bars}
    closes = {s: {tf: [b.t + TF_MS[tf] for b in series[s][tf]] for tf in series[s]} for s in symbols}
    ex = PaperExecutor(infos, balance=balance)

    steps = sorted((b.t + TF_MS[base], s, i) for s in symbols for i, b in enumerate(series[s][base]))
    if days:
        start = steps[-1][0] - days * 86_400_000
        warm = steps[0][0] + concepter.lookback * TF_MS[base]
        steps = [x for x in steps if x[0] >= max(start, warm)]

    journal: List[Dict] = []
    last_marks: Dict[str, list] = {}
    t0 = time.time()
    for now, sym, i in steps:
        bar: Bar = series[sym][base][i]
        for t in ex.on_bar(sym, bar, now):
            journal.append({"t": now, "symbol": sym, "event": "exit", "trade": t.to_dict()})
        view = View(symbol=sym, now=now,
                    bars={tf: series[sym][tf][max(0, k - concepter.lookback):k]
                          for tf in series[sym] for k in [bisect.bisect_right(closes[sym][tf], now)]},
                    positions=ex.positions(concepter=concepter.name, symbol=sym), info=infos[sym], account=ex.account())
        dec = concepter.on_bar(view)
        last_marks[sym] = [m.to_dict() for m in dec.marks]
        if dec.commands or (dec.notes and not dec.notes.startswith(("not asked", "not enough"))):
            results = [ex.submit(c).to_dict() for c in dec.commands]
            journal.append({"t": now, "symbol": sym, "event": "decision", "notes": dec.notes, "results": results})

    trades = ex.trades()
    wins = [t for t in trades if t.pnl > 0]
    summary = {"concepter": concepter.name, "rules": f"{concepter.rules.name} {concepter.rules.version}",
               "symbols": symbols, "bars": len(steps), "trades": len(trades), "won": len(wins),
               "total_r": round(sum(t.r for t in trades), 2), "pnl": round(sum(t.pnl for t in trades), 2),
               "open_at_end": len(ex.positions()), "refused": sum(1 for j in journal if j["event"] == "decision"
                                                                  for r in j["results"] if not r["ok"]),
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
    ap.add_argument("--concepter", default="demo", help="demo | llm")
    ap.add_argument("--rules", default="supply_demand", help=f"one of {RULES.available()}")
    ap.add_argument("--provider", default="fake", help="llm only: fake | gpt | gemini | claude")
    ap.add_argument("--ask", default="near_zone", help="llm only: near_zone | every_bar")
    ap.add_argument("--symbols", default="GOLD,EURUSD")
    ap.add_argument("--days", type=float, default=None, help="only the last N days of the data")
    ap.add_argument("--balance", type=float, default=10_000.0)
    ap.add_argument("--data", default=DATA.SAMPLE_DIR)
    ap.add_argument("--out", default=None, help="default runs/<concepter>-<rules>-<time>")
    a = ap.parse_args()
    rules = RULES.load(a.rules)
    kw = {"provider": a.provider, "ask": a.ask} if a.concepter == "llm" else {}
    c = make(a.concepter, rules, **kw)
    out = a.out or os.path.join(ROOT, "runs", f"{c.name}-{rules.name}-{time.strftime('%Y%m%d-%H%M%S')}")
    run(c, a.symbols.split(","), a.days, a.balance, out, a.data)
    print("→", out)


if __name__ == "__main__":
    main()
