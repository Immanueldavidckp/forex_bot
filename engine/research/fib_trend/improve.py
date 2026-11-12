"""
engine/research/fib_trend/improve.py — WHY the class's Fib rules lose, and which changes (reward ≥ 2 × risk) help.
David 2026-11-12: "do the analysis why it is on the losing side, how can we make this profitable, minimum 2R, backtest".

Every trade of both rules is rebuilt on the 30-min history (2018-06 →) — H1 / H2 / H4 candles are built from it and each
trade's fill, stop and target are followed on the 30-min candles inside them (the first backtest used the trading
timeframe's own candles: a candle touching stop and target counted as a loss). Per trade it stores the features a
filter could use and the result of every entry × stop × target scheme, so schemes are compared on the SAME setups.

    python3 -m engine.research.fib_trend.improve build     → engine_data/backtest/fib_trend/trades.json (slow, ~10 min)
    python3 -m engine.research.fib_trend.improve report    → the diagnosis + the scheme table (in-sample / out-of-sample)
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

from engine import fib_trend as F
from engine.major_structure import atr14
from engine.research.fib_trend.backtest import FX, HIST, OUT

TRADES = os.path.join(OUT, "trades.json")
SPLIT = 1672531200000                 # 2023-01-01: before = choose (in-sample), after = check (out-of-sample)
TFS = {"M30": 1, "H1": 2, "H2": 4, "H4": 8}
BUF = F.SL_BUFFER_ATR


class M:                              # one symbol's 30-min history as arrays
    def __init__(self, sym):
        r = np.array([x[:6] for x in json.load(open(os.path.join(HIST, f"{sym}.json")))["bars"]["M30"]], dtype=float)
        self.t, self.o, self.h, self.l, self.c, self.sp = (r[:, i] for i in range(6))
        self.t = self.t.astype(np.int64)

    def agg(self, k):
        """→ (bars of k × 30 min, the first 30-min index of each)"""
        g = self.t - self.t % (k * 1800_000)
        st = np.flatnonzero(np.r_[True, g[1:] != g[:-1]])
        en = np.r_[st[1:], len(g)]
        bars = [{"t": int(g[a]), "o": self.o[a], "h": self.h[a:b].max(), "l": self.l[a:b].min(), "c": self.c[b - 1]}
                for a, b in zip(st, en)]
        return bars[:-1], st[:-1], en[:-1]


def fill(m, a, b, buy, level, stop_order):
    """the 30-min candle inside [a, b) where an order at `level` fills, and its price (gap → the open)"""
    for i in range(a, b):
        if stop_order:
            if (m.h[i] >= level) if buy else (m.l[i] <= level):
                o = m.o[i]
                return i, (max(o, level) if buy else min(o, level))
        elif (m.l[i] <= level) if buy else (m.h[i] >= level):
            o = m.o[i]
            return i, (min(o, level) if buy else max(o, level))
    return None, None


def outcome(m, i0, buy, entry, sl, tp, limit=False):
    """→ (R, candles held, MFE in R before the end). Stop and target in one 30-min candle = the stop. A LIMIT order's
    fill candle can only stop it: its high (buy) may have come before the fill. A stop order's fill candle can do both
    (its low may have come before the fill: counted against the trade, the worst case)."""
    risk = (entry - sl) if buy else (sl - entry)
    if risk <= 0:
        return None
    for maxn in (300, 8000):
        h, l = m.h[i0:i0 + maxn], m.l[i0:i0 + maxn]
        a = np.flatnonzero(l <= sl) if buy else np.flatnonzero(h >= sl)
        b = np.flatnonzero(h >= tp) if buy else np.flatnonzero(l <= tp)
        if limit:
            b = b[b > 0]
        if a.size or b.size or len(h) < maxn:
            break
    ia, ib = (a[0] if a.size else None), (b[0] if b.size else None)
    end = min(x for x in (ia, ib, len(h) - 1) if x is not None)
    lo_ = 1 if limit and end > 0 else 0
    seg_h, seg_l = h[lo_:end + 1], l[lo_:end + 1]
    mfe = ((seg_h.max() - entry) if buy else (entry - seg_l.min())) / risk if len(seg_h) else 0.0
    if ia is None and ib is None:
        r = ((m.c[min(i0 + maxn, len(m.c)) - 1] - entry) * (1 if buy else -1)) / risk
    elif ib is None or (ia is not None and ia <= ib):
        r = -1.0
    else:
        r = abs(tp - entry) / risk
    return round(float(r), 3), int(end), round(float(mfe), 2)


def schemes(m, i0, buy, entry, H, L, atr, stops, targets, limit=False):
    """every stop × target for one filled entry → {name: R}, + MFE for the first stop"""
    sg = 1 if buy else -1
    out, mfe = {}, None
    for sn, sf in stops.items():
        sl = (F.fib(H, L, sf) - sg * BUF * atr) if sn != "236x" else F.fib(H, L, sf)
        risk = (entry - sl) * sg
        if risk <= 0:
            continue
        for tn, tv in targets.items():
            tp = F.fib(H, L, tv) if tn.startswith("f") else entry + sg * tv * risk
            if (tp - entry) * sg <= 0:
                continue
            r = outcome(m, i0, buy, entry, sl, tp, limit)
            if r:
                out[f"{sn}|{tn}"] = [r[0], round(abs(tp - entry) / risk, 2)]
                if mfe is None and tn in ("3R",):
                    mfe = r[2]
        out[f"{sn}|cost"] = round(float(m.sp[i0]) / risk, 3)
    return out, mfe


T_STOPS = {"236": 0.236, "0": 0.0}                      # under 0.236 (class) / under the swing low
T_TARGETS = {"f1.618": 1.618, "2R": 2.0, "3R": 3.0, "f2.618": 2.618}
R_STOPS = {"236x": 0.236, "0": 0.0}                     # exactly 0.236 (class) / under the previous swing low
R_TARGETS = {"f1": 1.0, "2R": 2.0, "3R": 3.0, "f1.618": 1.618}


def feats(bars, A, e200, e50, i, buy, H, L, h_idx):
    sg = 1 if buy else -1
    c = bars[i - 1]["c"]
    return {"t": bars[i]["t"], "hour": (bars[i]["t"] // 3600_000) % 24, "swing_atr": round(abs(H - L) / A[h_idx], 2) if A[h_idx] else None,
            "ema200": int((c - e200[i - 1]) * sg > 0), "ema50_200": int((e50[i - 1] - e200[i - 1]) * sg > 0),
            "atr": A[h_idx]}


def build_symbol(sym):
    m = M(sym)
    rows = []
    for tf, k in TFS.items():
        bars, st, en = m.agg(k)
        if len(bars) < 500:
            continue
        A = atr14(bars)
        cl = [b["c"] for b in bars]
        e200, e50 = F.ema(cl, 200), F.ema(cl, 50)
        struct = F.swing_structure(bars, F.STRUCTURE_N)
        if tf != "M30":                                   # ── FIB GO WITH TREND ──
            for s in F.setups(bars, struct, min_rr=0):
                ft = s.get("first_touch")
                if ft is None or s["cross_idx"] is None:
                    continue
                buy = s["side"] == "buy"
                hi = (lambda b: b["h"]) if buy else (lambda b: b["l"])
                lo = (lambda b: b["l"]) if buy else (lambda b: b["h"])
                # entry "class": the next candle through the touch candle's high (the rule as taught)
                if s["entry_idx"] is not None and s["status"] in ("won", "lost", "open"):
                    j = s["entry_idx"]
                    i0, px = fill(m, st[j], en[j], buy, s["mark"], True)
                    if i0 is not None:
                        H, L = s["H"], s["L"]
                        sc, mfe = schemes(m, i0, buy, px, H, L, A[s["h_idx"]], T_STOPS, T_TARGETS)
                        rows.append(dict(feats(bars, A, e200, e50, j, buy, H, L, s["h_idx"]), rule="trend", entry="class", sym=sym, tf=tf,
                                         side=s["side"], swing=s["swing"], pos=round((px - L) / (H - L), 3), sc=sc, mfe=mfe))
                # entry "touch": a stop order AT 0.618 itself, the first time price comes back to it
                j, hh, ll = ft
                H, L = hi(bars[hh]), lo(bars[ll])
                lvl = F.fib(H, L, F.ENTRY_FIB)
                i0, px = fill(m, st[j], en[j], buy, lvl, True)
                if i0 is not None:
                    sc, mfe = schemes(m, i0, buy, px, H, L, A[hh], T_STOPS, T_TARGETS)
                    rows.append(dict(feats(bars, A, e200, e50, j, buy, H, L, hh), rule="trend", entry="touch", sym=sym, tf=tf,
                                     side=s["side"], swing=s["swing"], pos=round((px - L) / (H - L), 3), sc=sc, mfe=mfe))
        if tf != "H2":                                    # ── FIB RETRACEMENT (every BOS; the swing number is kept) ──
            for ef in (0.618, 0.5, 0.382):
                for s in F.retrace_setups(bars, struct, mode="every", entry_fib=ef):
                    if s["entry_idx"] is None:
                        continue
                    buy = s["side"] == "buy"
                    j = s["entry_idx"]
                    i0, px = fill(m, st[j], en[j], buy, s["entry_level"], False)
                    if i0 is None:
                        continue
                    H, L = s["H"], s["L"]
                    sc, mfe = schemes(m, i0, buy, px, H, L, A[s["h_idx"]], R_STOPS, R_TARGETS, True)
                    rows.append(dict(feats(bars, A, e200, e50, j, buy, H, L, s["h_idx"]), rule="retrace", entry=str(ef), sym=sym, tf=tf,
                                     side=s["side"], swing=s["swing"], pos=round((px - L) / (H - L), 3), sc=sc, mfe=mfe))
    return rows


def build():
    from multiprocessing import Pool
    os.makedirs(OUT, exist_ok=True)
    with Pool(12) as p:
        res = p.map(build_symbol, FX)
    rows = [r for x in res for r in x]
    json.dump(rows, open(TRADES, "w"))
    print(len(rows), "trades →", TRADES)


def st(rs, key):
    """net stats of scheme `key` over trades rs → (n, win %, gross R/trade, net R/trade, t of the net mean, avg RR)"""
    stop = key.split("|")[0]
    v = [(r["sc"][key][0], r["sc"][key][0] - r["sc"][f"{stop}|cost"], r["sc"][key][1]) for r in rs if key in r["sc"]]
    n = len(v)
    if n < 2:
        return None
    net = np.array([x[1] for x in v])
    g = np.array([x[0] for x in v])
    sd = net.std(ddof=1)
    return {"n": n, "win": round(100 * float((g > 0).mean()), 1), "gross": round(float(g.mean()), 3), "net": round(float(net.mean()), 3),
            "t": round(float(net.mean() / (sd / np.sqrt(n))), 2) if sd else 0, "rr": round(float(np.mean([x[2] for x in v])), 2)}


def load():
    return json.load(open(TRADES))


if __name__ == "__main__":
    if sys.argv[1:2] == ["build"]:
        build()
