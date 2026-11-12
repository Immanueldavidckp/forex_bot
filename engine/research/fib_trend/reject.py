"""
engine/research/fib_trend/reject.py — WHEN TO REJECT a Fib trade (David 2026-11-12: "when can we reject this trade, a
rejecting confirmation that will save our loss; implement that in the backtest and check").

Every trade of four base versions gets the confirmations a trader could read at the entry (nothing from the future):
    adx       ADX(14) of the trading timeframe — trend strength
    rsi       RSI(14), turned so that high = stretched the trade's way
    vol       ATR(14) ÷ its 200-candle median — quiet / wild market
    ext       distance of price from EMA 21 in ATR, the trade's way — overextended?
    rng       where the entry sits in the last 100 candles' range (0 = cheap side for this trade, 1 = expensive side)
    d1        daily trend: last closed daily candle vs its EMA 50 (1 = with the trade)
    d1s       daily EMA 20 rising / falling the trade's way
    ema200    price vs EMA 200 of the trading timeframe
    cost      the spread ÷ the stop distance (known before the order)
    sess      Asia / London / New York / late, dow = weekday, sym, swing, swing_atr, pos
and a separate entry "confirm": wait for a REJECTION CANDLE at the Fib level (touches it, closes back beyond it the
trade's way), enter at the next open.

Reject rules are chosen on 2018–2022 only: the far end of a confirmation (its lowest / highest fifth) or a category
whose trades lost clearly there (t ≤ −3 and at least 0.05 R worse than the base). Middle fifths are never rules: they
were noise (first run). Then the rules are judged on 2023–2026.

    python3 -m engine.research.fib_trend.reject build     → engine_data/backtest/fib_trend/trades_rej.json
    python3 -m engine.research.fib_trend.reject report [out dir for the page's CSVs]
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict

import numpy as np

from engine import fib_trend as F
from engine.major_structure import atr14
from engine.research.fib_trend import improve as I
from engine.research.fib_trend.backtest import FX, OUT

FILE = os.path.join(OUT, "trades_rej.json")
TFS = {"H1": 2, "H2": 4, "H4": 8}


def wilder(x, n):
    out, s = np.zeros(len(x)), 0.0
    for i, v in enumerate(x):
        s = v if i == 0 else s + (v - s) / n
        out[i] = s
    return out


def indicators(bars):
    h = np.array([b["h"] for b in bars]); l = np.array([b["l"] for b in bars]); c = np.array([b["c"] for b in bars])
    up, dn = np.r_[0, h[1:] - h[:-1]], np.r_[0, l[:-1] - l[1:]]
    pdm, mdm = np.where((up > dn) & (up > 0), up, 0), np.where((dn > up) & (dn > 0), dn, 0)
    tr = np.r_[h[0] - l[0], np.maximum(h[1:] - l[1:], np.maximum(abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])))]
    atr = wilder(tr, 14)
    pdi, mdi = 100 * wilder(pdm, 14) / np.maximum(atr, 1e-12), 100 * wilder(mdm, 14) / np.maximum(atr, 1e-12)
    adx = wilder(100 * abs(pdi - mdi) / np.maximum(pdi + mdi, 1e-12), 14)
    d = np.r_[0, c[1:] - c[:-1]]
    rs = wilder(np.maximum(d, 0), 14) / np.maximum(wilder(np.maximum(-d, 0), 14), 1e-12)
    rsi = 100 - 100 / (1 + rs)
    med = np.array([np.median(atr[max(0, i - 199):i + 1]) for i in range(len(atr))])
    hi100 = np.array([h[max(0, i - 99):i + 1].max() for i in range(len(h))])
    lo100 = np.array([l[max(0, i - 99):i + 1].min() for i in range(len(l))])
    return dict(adx=adx, rsi=rsi, atr=atr, vol=atr / np.maximum(med, 1e-12), hi=hi100, lo=lo100, c=c,
                e21=np.array(F.ema(list(c), 21)), e200=np.array(F.ema(list(c), 200)))


def feats(ind, D, bars, j, buy, px, risk, sp):
    """what is known when candle j opens (indicators of candle j − 1, the last closed daily candle)"""
    k, sg = j - 1, 1 if buy else -1
    t = bars[j]["t"]
    d = int(np.searchsorted(D["t"], t, side="right")) - 2          # the daily candle before the one t is in
    hour = (t // 3600_000) % 24
    rng = (px - ind["lo"][k]) / max(ind["hi"][k] - ind["lo"][k], 1e-12)
    return {"t": t, "adx": round(float(ind["adx"][k]), 1), "rsi": round(float(ind["rsi"][k] if buy else 100 - ind["rsi"][k]), 1),
            "vol": round(float(ind["vol"][k]), 2), "ext": round(float((ind["c"][k] - ind["e21"][k]) * sg / max(ind["atr"][k], 1e-12)), 2),
            "rng": round(float(rng if buy else 1 - rng), 2),
            "d1": int((D["c"][d] - D["e50"][d]) * sg > 0) if d >= 50 else None,
            "d1s": int((D["e20"][d] - D["e20"][d - 5]) * sg > 0) if d >= 25 else None,
            "ema200": int((ind["c"][k] - ind["e200"][k]) * sg > 0), "cost": round(float(sp / risk), 3),
            "sess": "Asia" if hour < 7 else "London" if hour < 13 else "NewYork" if hour < 21 else "late",
            "dow": int((t // 86400_000 + 3) % 7)}                   # 0 = Monday


def result(m, i0, buy, px, sl, tp, limit):
    r = I.outcome(m, i0, buy, px, sl, tp, limit)
    return None if r is None else r[0]


def build_symbol(sym):
    m = I.M(sym)
    db, _, _ = m.agg(48)
    dc = [b["c"] for b in db]
    D = {"t": np.array([b["t"] for b in db]), "c": np.array(dc), "e50": np.array(F.ema(dc, 50)), "e20": np.array(F.ema(dc, 20))}
    rows = []
    for tf, k in TFS.items():
        bars, st, en = m.agg(k)
        A = atr14(bars)
        ind = indicators(bars)
        struct = F.swing_structure(bars, F.STRUCTURE_N)

        def add(base, j, i0, buy, px, sl, tp, limit, extra):
            risk = (px - sl) * (1 if buy else -1)
            if risk <= 0:
                return
            r = result(m, i0, buy, px, sl, tp, limit)
            if r is None:
                return
            f = feats(ind, D, bars, j, buy, px, risk, float(m.sp[i0]))
            rows.append(dict(f, base=base, sym=sym, tf=tf, side="buy" if buy else "sell", r=r, net=round(r - f["cost"], 3), **extra))

        # ── Go With Trend, entry as taught: "T-class" (stop under 0.236, target 1.618) and "T-wide2R" (stop under the swing low, 2R)
        for s in F.setups(bars, struct, min_rr=0):
            if s["entry_idx"] is None or s["cross_idx"] is None or s["status"] not in ("won", "lost", "open"):
                continue
            buy, j = s["side"] == "buy", s["entry_idx"]
            sg = 1 if buy else -1
            i0, px = I.fill(m, st[j], en[j], buy, s["mark"], True)
            if i0 is None:
                continue
            H, L, a = s["H"], s["L"], A[s["h_idx"]]
            ex = {"swing": s["swing"], "swing_atr": round(abs(H - L) / a, 2) if a else None, "pos": round((px - L) / (H - L), 2)}
            add("T-class", j, i0, buy, px, F.fib(H, L, 0.236) - sg * I.BUF * a, F.fib(H, L, 1.618), False, ex)
            slw = L - sg * I.BUF * a
            add("T-wide2R", j, i0, buy, px, slw, px + 2 * (px - slw), False, ex)
        if tf == "H2":
            continue
        # ── Retracement: "R-382" = limit at 0.382, stop under the swing low, 2R; "R-confirm-x" = rejection candle at x
        for s in F.retrace_setups(bars, struct, mode="every", entry_fib=0.382):
            if s["entry_idx"] is None:
                continue
            buy, j = s["side"] == "buy", s["entry_idx"]
            sg = 1 if buy else -1
            i0, px = I.fill(m, st[j], en[j], buy, s["entry_level"], False)
            if i0 is None:
                continue
            H, L, a = s["H"], s["L"], A[s["h_idx"]]
            slw = L - sg * I.BUF * a
            add("R-382", j, i0, buy, px, slw, px + 2 * (px - slw), True,
                {"swing": s["swing"], "swing_atr": round(abs(H - L) / a, 2) if a else None, "pos": round((px - L) / (H - L), 2)})
        ev = sorted(struct["events"], key=lambda x: x["idx"])
        swing = None
        for q, e in enumerate(ev):
            if e["kind"] == "CHoCH":
                swing = 1
                continue
            if swing is None:
                continue
            swing += 1
            buy = e["side"] == "buy"
            sg = 1 if buy else -1
            hi = (lambda b: b["h"]) if buy else (lambda b: b["l"])
            lo = (lambda b: b["l"]) if buy else (lambda b: b["h"])
            x, o = e["idx"], e["origin"]["idx"]
            w_end = ev[q + 1]["idx"] if q + 1 < len(ev) else len(bars)
            L = lo(bars[o])
            for ef in (0.618, 0.5, 0.382):
                h = max(range(o, x + 1), key=lambda i: hi(bars[i]) * sg)
                for j in range(x + 1, min(w_end, len(bars) - 1)):
                    b = bars[j]
                    lvl = F.fib(hi(bars[h]), L, ef)
                    if (b["c"] - L) * sg < 0:
                        break                                       # closed through the swing low: over
                    if j > h and (lo(b) - lvl) * sg <= 0 and (b["c"] - lvl) * sg > 0 and (b["c"] - b["o"]) * sg > 0:
                        H, a = hi(bars[h]), A[h]                    # the rejection candle: touched the level, closed back
                        px = bars[j + 1]["o"]
                        slw = min(L, lo(b)) - I.BUF * a if buy else max(L, lo(b)) + I.BUF * a
                        add(f"R-confirm-{ef}", j + 1, int(st[j + 1]), buy, px, slw, px + 2 * (px - slw), False,
                            {"swing": swing, "swing_atr": round(abs(H - L) / a, 2) if a else None, "pos": round((px - L) / (H - L), 2)})
                        break
                    if (hi(b) - hi(bars[h])) * sg > 0:
                        h = j
    return rows


def build():
    from multiprocessing import Pool
    with Pool(12) as p:
        rows = [r for x in p.map(build_symbol, FX) for r in x]
    json.dump(rows, open(FILE, "w"))
    print(len(rows), "trades →", FILE)


# ── the analysis ──
T_MIN = -3.0                          # how clearly a bucket must have lost in 2018–2022 to become a reject rule
NUM = ("adx", "rsi", "vol", "ext", "rng", "cost", "swing_atr", "pos")
CAT = ("d1", "d1s", "ema200", "sess", "dow", "sym", "swing", "tf")


def stat(rs):
    n = len(rs)
    if n < 2:
        return {"n": n, "win": 0, "net": 0.0, "t": 0.0, "sum": 0.0}
    v = np.array([r["net"] for r in rs])
    sd = v.std(ddof=1)
    return {"n": n, "win": round(100 * float(np.mean([r["r"] > 0 for r in rs])), 1), "net": round(float(v.mean()), 3),
            "t": round(float(v.mean() / (sd / np.sqrt(n))), 1) if sd else 0.0, "sum": round(float(v.sum()), 1)}


def buckets(IS):
    """per confirmation: its buckets (numbers: the in-sample fifths) → a function trade → bucket label"""
    out = {}
    for f in NUM:
        v = [r[f] for r in IS if r.get(f) is not None]
        if len(v) < 50:
            continue
        q = [float(x) for x in np.quantile(v, [0.2, 0.4, 0.6, 0.8])]
        out[f] = (lambda r, f=f, q=q: None if r.get(f) is None else
                  f"≤ {q[0]:g}" if r[f] <= q[0] else f"{q[0]:g} – {q[1]:g}" if r[f] <= q[1] else
                  f"{q[1]:g} – {q[2]:g}" if r[f] <= q[2] else f"{q[2]:g} – {q[3]:g}" if r[f] <= q[3] else f"> {q[3]:g}")
    for f in CAT:
        out[f] = (lambda r, f=f: None if r.get(f) is None else ("swing 6+" if f == "swing" and r[f] >= 6 else str(r[f])))
    return out


def study(rs, name, rows_out=None, rules_out=None, verbose=True):
    IS, OOS = [r for r in rs if r["t"] < I.SPLIT], [r for r in rs if r["t"] >= I.SPLIT]
    a, b = stat(IS), stat(OOS)
    B = buckets(IS)
    rules = []
    for f, fn in B.items():
        g, g2 = defaultdict(list), defaultdict(list)
        for r in IS:
            g[fn(r)].append(r)
        for r in OOS:
            g2[fn(r)].append(r)
        for lab, tr in g.items():
            if lab is None:
                continue
            s, s2 = stat(tr), stat(g2.get(lab, []))
            extreme = f in CAT or lab.startswith(("≤", ">"))       # only the far end of a number, or a category
            bad = extreme and s["n"] >= 80 and s["t"] <= T_MIN and s["net"] < a["net"] - 0.05
            if rules_out is not None:
                rules_out.append([name, f, lab, s["n"], s["net"], s["t"], s2["n"], s2["net"], int(bad)])
            if bad:
                rules.append((f, lab, s, s2))
    bad_fn = lambda r: sum(1 for f, lab, _, _ in rules if B[f](r) == lab)
    res = {}
    for need in (1, 2):
        kI, kO = [r for r in IS if bad_fn(r) < need], [r for r in OOS if bad_fn(r) < need]
        xI, xO = [r for r in IS if bad_fn(r) >= need], [r for r in OOS if bad_fn(r) >= need]
        res[need] = (stat(kI), stat(kO), stat(xI), stat(xO))
    if verbose:
        print(f"\n=== {name}: base IS n {a['n']} net {a['net']:+.3f} | OOS n {b['n']} net {b['net']:+.3f} (t {b['t']:+.1f})")
        for f, lab, s, s2 in sorted(rules, key=lambda x: x[2]["net"]):
            print(f"   reject {f:9} {lab:16} IS n {s['n']:5} net {s['net']:+.3f} t {s['t']:+.1f} | OOS n {s2['n']:5} net {s2['net']:+.3f}")
        for need, (kI, kO, xI, xO) in res.items():
            print(f"   reject if ≥{need} flag: KEPT IS n {kI['n']} net {kI['net']:+.3f} | KEPT OOS n {kO['n']} win {kO['win']} net {kO['net']:+.3f} t {kO['t']:+.1f} total {kO['sum']:+.0f}R"
                  f" || REJECTED OOS n {xO['n']} net {xO['net']:+.3f} total {xO['sum']:+.0f}R")
    if rows_out is not None:
        rows_out.append([name, "no filter", a["n"], a["net"], b["n"], b["win"], b["net"], b["t"], b["sum"], 0, 0.0, 0.0])
        for need, (kI, kO, xI, xO) in res.items():
            rows_out.append([name, f"reject when {need}+ warning{'s' if need > 1 else ''}", kI["n"], kI["net"], kO["n"], kO["win"], kO["net"], kO["t"], kO["sum"],
                             xO["n"], xO["net"], xO["sum"]])
    return rules, res, bad_fn


NAMES = {"T-class": "Go With Trend as taught (1h+2h+4h)", "T-wide2R": "Go With Trend, stop under swing low, 2R",
         "R-382": "Retracement, limit 0.382, wide stop, 2R (1h+4h)", "R-confirm-0.618": "Retracement, rejection candle at 0.618, 2R",
         "R-confirm-0.5": "Retracement, rejection candle at 0.5, 2R", "R-confirm-0.382": "Retracement, rejection candle at 0.382, 2R"}


def report(out=None):
    R = json.load(open(FILE))
    rows, rules = [], []
    for base, name in NAMES.items():
        study([r for r in R if r["base"] == base], name, rows, rules)
    if out:
        with open(os.path.join(out, "reject_summary.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "version", "filter", "trades_2018_2022", "net_2018_2022", "trades_2023_2026", "win_2023_2026", "net_2023_2026", "t_2023_2026",
                        "total_r_2023_2026", "rejected_2023_2026", "rejected_net_2023_2026", "rejected_total_r_2023_2026"])
            for i, r in enumerate(rows):
                w.writerow([f"f{i + 1}"] + r)
        with open(os.path.join(out, "reject_rules.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "version", "confirmation", "bucket", "trades_2018_2022", "net_2018_2022", "t_2018_2022", "trades_2023_2026", "net_2023_2026"])
            for i, r in enumerate([x for x in rules if x[8]]):
                w.writerow([f"r{i + 1}"] + r[:8])


if __name__ == "__main__":
    if sys.argv[1:2] == ["build"]:
        build()
    else:
        report(sys.argv[2] if len(sys.argv) > 2 else None)
