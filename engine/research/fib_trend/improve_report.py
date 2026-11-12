"""engine/research/fib_trend/improve_report.py — the "why it loses / what was tried" tables from improve.py's trades
(trades.json) and improve_hitf.py's (trades_hitf.json): reach.csv, variants.csv, best_curve.csv in the folder given.
    python3 -m engine.research.fib_trend.improve_report <out dir>"""
import csv, datetime as D, json, os, sys
from collections import defaultdict
import numpy as np
from engine.research.fib_trend.improve import load, st, SPLIT
from engine.research.fib_trend.backtest import OUT

R = load() + json.load(open(os.path.join(OUT, "trades_hitf.json")))
out = sys.argv[1]
T = [r for r in R if r["rule"] == "trend" and r["entry"] == "class"]
U = [r for r in R if r["rule"] == "trend" and r["entry"] == "touch"]
def RT(ef, tf): return [r for r in R if r["rule"] == "retrace" and r["entry"] == ef and r["tf"] == tf]
mf = np.array([r["mfe"] for r in T if r.get("mfe") is not None])
with open(os.path.join(out, "reach.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["level", "reached_pct", "coin_flip_pct"])
    for x in (0.5, 1, 1.5, 2, 3):
        w.writerow([f"+{x:g}R", round(100 * float((mf >= x).mean()), 1), round(100 / (1 + x), 1)])
V = [
 ("Go With Trend", "as taught", "1h+2h+4h", "next candle through the 0.618 candle", "under 0.236", "Fib 1.618", T, "236|f1.618"),
 ("Go With Trend", "only entries that give 2R or more", "1h+2h+4h", "same, entry low in the Fib", "under 0.236", "Fib 1.618", [r for r in T if r["sc"].get("236|f1.618", [0, 0])[1] >= 2], "236|f1.618"),
 ("Go With Trend", "target fixed at 2R", "1h+2h+4h", "same", "under 0.236", "2R", T, "236|2R"),
 ("Go With Trend", "wider stop, 2R", "1h+2h+4h", "same", "under the swing low", "2R", T, "0|2R"),
 ("Go With Trend", "wider stop, 3R", "1h+2h+4h", "same", "under the swing low", "3R", T, "0|3R"),
 ("Go With Trend", "enter at 0.618 itself", "1h+2h+4h", "at 0.618", "under 0.236", "Fib 1.618", U, "236|f1.618"),
 ("Go With Trend", "London hours only, wider stop, 2R", "1h+2h+4h", "same as taught", "under the swing low", "2R", [r for r in T if 7 <= r["hour"] < 13], "0|2R"),
 ("Go With Trend", "4h only, wider stop, 2R", "4h", "same as taught", "under the swing low", "2R", [r for r in T if r["tf"] == "H4"], "0|2R"),
 ("Retracement", "as taught", "30m", "limit 0.618", "0.236", "Fib 1 (1:1)", RT("0.618", "M30"), "236x|f1"),
 ("Retracement", "as taught", "4h", "limit 0.618", "0.236", "Fib 1 (1:1)", RT("0.618", "H4"), "236x|f1"),
 ("Retracement", "target 2R", "4h", "limit 0.618", "0.236", "2R", RT("0.618", "H4"), "236x|2R"),
 ("Retracement", "wider stop, 2R", "1h", "limit 0.618", "under the swing low", "2R", RT("0.618", "H1"), "0|2R"),
 ("Retracement", "deeper entry, wider stop, 2R", "4h", "limit 0.5", "under the swing low", "2R", RT("0.5", "H4"), "0|2R"),
 ("Retracement", "deepest entry, wider stop, 2R", "30m", "limit 0.382", "under the swing low", "2R", RT("0.382", "M30"), "0|2R"),
 ("Retracement", "deepest entry, wider stop, 2R", "1h", "limit 0.382", "under the swing low", "2R", RT("0.382", "H1"), "0|2R"),
 ("Retracement", "deepest entry, wider stop, 2R", "4h", "limit 0.382", "under the swing low", "2R", RT("0.382", "H4"), "0|2R"),
 ("Retracement", "deepest entry, wider stop, 2R", "8h", "limit 0.382", "under the swing low", "2R", RT("0.382", "H8"), "0|2R"),
 ("Retracement", "deepest entry, wider stop, 2R", "daily", "limit 0.382", "under the swing low", "2R", RT("0.382", "D1"), "0|2R"),
 ("Retracement", "deepest entry, wider stop, 3R", "4h", "limit 0.382", "under the swing low", "3R", RT("0.382", "H4"), "0|3R"),
 ("Retracement", "deepest entry, 2R, 9 cheapest markets", "4h", "limit 0.382", "under the swing low", "2R", [r for r in RT("0.382", "H4") if r["sym"] in ("GOLD", "GBPUSD", "USDJPY", "EURJPY", "USDCAD", "EURUSD", "GBPJPY", "EURCAD", "EURGBP")], "0|2R"),
]
with open(os.path.join(out, "variants.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "rule", "change", "tf", "entry", "stop", "target", "trades", "win_pct", "breakeven_pct", "avg_rr", "gross_r", "net_r", "net_2018_2022", "net_2023_2026", "t"])
    for i, (rule, ch, tf, en, sl, tg, rs, k) in enumerate(V):
        a, b, c = st(rs, k), st([r for r in rs if r["t"] < SPLIT], k), st([r for r in rs if r["t"] >= SPLIT], k)
        cost = a["gross"] - a["net"]
        w.writerow([f"v{i + 1}", rule, ch, tf, en, sl, tg, a["n"], a["win"], round(100 * (1 + cost) / (1 + a["rr"]), 1), a["rr"], a["gross"], a["net"], b["net"], c["net"], a["t"]])
        print(f"v{i+1:<3} {rule:14} {ch:38} {tf:9} n {a['n']:6} win {a['win']:5} rr {a['rr']:4} gross {a['gross']:+.3f} net {a['net']:+.3f}  IS {b['net']:+.3f}  OOS {c['net']:+.3f}  t {a['t']:+.1f}")
best = RT("0.382", "H4"); k = "0|2R"
m = defaultdict(lambda: [0, 0.0])
for r in best:
    mo = D.datetime.fromtimestamp(r["t"] / 1000, D.timezone.utc).strftime("%Y-%m-01")
    m[mo][0] += 1; m[mo][1] += r["sc"][k][0] - r["sc"]["0|cost"]
cum = 0
with open(os.path.join(out, "best_curve.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["month", "trades", "net_r", "cum_net_r"])
    for mo in sorted(m):
        cum += m[mo][1]; w.writerow([mo, m[mo][0], round(m[mo][1], 2), round(cum, 2)])
