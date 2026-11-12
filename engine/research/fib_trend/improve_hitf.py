import json, numpy as np
from multiprocessing import Pool
from engine import fib_trend as F
from engine.major_structure import atr14
from engine.research.fib_trend import improve as I
from engine.research.fib_trend.backtest import FX
def one(sym):
    m = I.M(sym); rows = []
    for tf, k in (("H8", 16), ("D1", 48)):
        bars, st, en = m.agg(k)
        if len(bars) < 300: continue
        A = atr14(bars); cl = [b["c"] for b in bars]; e200, e50 = F.ema(cl, 200), F.ema(cl, 50)
        struct = F.swing_structure(bars, F.STRUCTURE_N)
        for ef in (0.618, 0.5, 0.382):
            for s in F.retrace_setups(bars, struct, mode="every", entry_fib=ef):
                if s["entry_idx"] is None: continue
                buy = s["side"] == "buy"; j = s["entry_idx"]
                i0, px = I.fill(m, st[j], en[j], buy, s["entry_level"], False)
                if i0 is None: continue
                sc, mfe = I.schemes(m, i0, buy, px, s["H"], s["L"], A[s["h_idx"]], I.R_STOPS, I.R_TARGETS, True)
                rows.append(dict(I.feats(bars, A, e200, e50, j, buy, s["H"], s["L"], s["h_idx"]), rule="retrace", entry=str(ef), sym=sym, tf=tf, side=s["side"], swing=s["swing"], sc=sc))
    return rows
if __name__ == "__main__":
    with Pool(12) as p: R = [r for x in p.map(one, FX) for r in x]
    json.dump(R, open("engine_data/backtest/fib_trend/trades_hitf.json", "w"))
    IS = lambda rs: [r for r in rs if r["t"] < I.SPLIT]; OOS = lambda rs: [r for r in rs if r["t"] >= I.SPLIT]
    for tf in ("H8", "D1"):
        for ef in ("0.618", "0.5", "0.382"):
            Q = [r for r in R if r["tf"] == tf and r["entry"] == ef]
            for k in ("236x|f1", "0|2R", "0|3R", "236x|2R"):
                a, b, c = I.st(IS(Q), k), I.st(OOS(Q), k), I.st(Q, k)
                if a and b: print(f"{tf} e{ef} {k:8} ALL n {c['n']:5} win {c['win']:5} gross {c['gross']:+.3f} net {c['net']:+.3f} t {c['t']:+.1f} | IS net {a['net']:+.3f} t {a['t']:+.1f} | OOS net {b['net']:+.3f} t {b['t']:+.1f}")
