"""
engine/research/fib_trend/backtest.py — the class rule "FIB GO WITH TREND" (engine/fib_trend.py) on our saved MT5
history: every forex pair + gold, 1 h / 2 h (rebuilt from the 30-min history, 6+ years) and 4 h.

Each trade exactly as the chart layer and the live book see it: entry = the touch candle's high / low hit by the next
candle (buy / sell stop), stop 0.236 − 0.1 ATR, target 1.618, RR ≥ 1, both in one candle = the stop. Cost: the bar's
spread (history column 5, price units) taken from every trade, in R.

    python3 -m engine.research.fib_trend.backtest            → table + engine_data/backtest/fib_trend/summary_n<N>.json
    python3 -m engine.research.fib_trend.backtest 3          the structure's pivot length (default STRUCTURE_N)
    python3 -m engine.research.fib_trend.backtest results    both rules, every class timeframe → results.json (in git)
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

from engine import fib_trend as F

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
HIST = os.path.join(ROOT, "engine_data", "history")
OUT = os.path.join(ROOT, "engine_data", "backtest", "fib_trend")
FX = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "EURJPY", "GBPJPY", "EURGBP", "EURCHF",
      "EURCAD", "GBPCHF", "GBPCAD", "CADCHF", "CADJPY", "CHFJPY", "GOLD"]


def rows(sym: str, tf: str):
    d = json.load(open(os.path.join(HIST, f"{sym}.json")))["bars"]
    if tf in ("M15", "M30", "H4"):
        return d[tf]
    src, k = d["M30"], {"H1": 2, "H2": 4}[tf]
    out, cur = [], None
    for r in src:
        t0 = r[0] - r[0] % (k * 1800_000)
        if cur is None or cur[0] != t0:
            if cur:
                out.append(cur)
            cur = [t0, r[1], r[2], r[3], r[4], r[5]]
        else:
            cur[2], cur[3], cur[4], cur[5] = max(cur[2], r[2]), min(cur[3], r[3]), r[4], max(cur[5] or 0, r[5] or 0)
    if cur:
        out.append(cur)
    return out[:-1]                                   # the last one may be incomplete


def run(sym: str, tf: str, n: int = F.STRUCTURE_N, rule: str = "trend"):
    R = rows(sym, tf)
    bars = [{"t": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4], "sp": float(r[5] or 0)} for r in R]
    S = F.setups(bars, n=n) if rule == "trend" else F.retrace_setups(bars, n=n, mode=rule.split(":")[1])
    trades = []
    for s in S:
        if s["status"] not in ("won", "lost"):
            continue
        risk = abs(s["entry"] - s["sl"])
        cost = bars[s["entry_idx"]]["sp"] / risk if risk else 0
        trades.append({"sym": sym, "tf": tf, "side": s["side"], "t": bars[s["entry_idx"]]["t"], "entry": s["entry"],
                       "sl": s["sl"], "tp": s["tp"], "rr": s["rr"], "r": s["result"], "cost_r": round(cost, 3),
                       "net_r": round(s["result"] - cost, 3), "bars": s["exit_idx"] - s["entry_idx"] + 1})
    why = defaultdict(int)
    for s in S:
        if s["status"] == "no trade":
            why[s["why"].split(" before")[0].split(" at the")[0]] += 1
    return {"bars": len(bars), "from": bars[0]["t"] if bars else None, "swings": len(S), "trades": trades, "why": dict(why)}


def stats(T):
    n = len(T)
    if not n:
        return {"n": 0}
    w = sum(1 for t in T if t["r"] > 0)
    net = sum(t["net_r"] for t in T)
    return {"n": n, "won": w, "win_pct": round(100 * w / n, 1), "gross_r": round(sum(t["r"] for t in T), 2),
            "net_r": round(net, 2), "per_trade": round(net / n, 3), "avg_rr": round(sum(t["rr"] for t in T) / n, 2)}


RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")
PLAN = {"trend": ("H1", "H2", "H4"), "retrace:safety": ("M15", "M30", "H1", "H4"), "retrace:every": ("M30", "H4")}


def results() -> int:
    """every rule × timeframe the class names → results.json (in git: the /smc page's backtest line, /api/fib/backtest)"""
    out = {"made": __import__("time").strftime("%Y-%m-%d"), "symbols": FX, "structure_n": F.STRUCTURE_N, "rules": {}}
    for rule, tfs in PLAN.items():
        for tf in tfs:
            T, per = [], {}
            for sym in FX:
                r = run(sym, tf, F.STRUCTURE_N, rule)
                T += r["trades"]
                per[sym] = stats(r["trades"])
            out["rules"][f"{rule} {tf}"] = {"all": stats(T), "per_symbol": per,
                                            "since": min((t["t"] for t in T), default=None)}
            print(rule, tf, out["rules"][f"{rule} {tf}"]["all"], flush=True)
    json.dump(out, open(RESULTS, "w"), indent=1)
    return 0


def main() -> int:
    if sys.argv[1:2] == ["results"]:
        return results()
    n = int(sys.argv[1]) if len(sys.argv) > 1 else F.STRUCTURE_N
    os.makedirs(OUT, exist_ok=True)
    res, allT = {}, defaultdict(list)
    for tf in ("H1", "H2", "H4"):
        for sym in FX:
            r = run(sym, tf, n)
            res[f"{sym} {tf}"] = {k: v for k, v in r.items() if k != "trades"} | {"stats": stats(r["trades"])}
            allT[tf] += r["trades"]
            st = res[f"{sym} {tf}"]["stats"]
            print(f"{sym:7} {tf}  {r['bars']:6} bars  swings {r['swings']:4}  trades {st['n']:3}  "
                  + (f"won {st['win_pct']:5}%  net {st['net_r']:7}R" if st["n"] else ""), flush=True)
    summary = {tf: stats(T) for tf, T in allT.items()}
    summary["all"] = stats([t for T in allT.values() for t in T])
    for k, v in summary.items():
        print(k, v)
    json.dump({"summary": summary, "per_chart": res, "trades": allT}, open(os.path.join(OUT, f"summary_n{n}.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
