"""
engine/research/profit/scan.py — scan candidate entry rules for a POSITIVE dollar expectancy at 0.01 lot.

    python3 engine/research/profit/scan.py [--tf M15] [--market forex,metals]

Every rule is run on every symbol, pooled, and printed next to the same-geometry random control. The
t-statistic is on the pooled per-trade dollars. Dozens of rules x several geometries are tried here, so a
single t ~ 2 means nothing on its own -- the multiple-testing correction is applied in the report.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab

HIST = lab.HIST


def ema(x, n):
    a = 2.0 / (n + 1.0)
    out = np.empty_like(x); out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    up = np.where(d > 0, d, 0.0); dn = np.where(d < 0, -d, 0.0)
    ru = ema(up, n); rd = ema(dn, n)
    return 100 - 100 / (1 + ru / np.maximum(rd, 1e-12))


def roll_max(x, n):
    out = np.full(len(x), np.nan)
    if len(x) > n:
        s = np.lib.stride_tricks.sliding_window_view(x, n)
        out[n - 1:] = s.max(axis=1)
    return out


def roll_min(x, n):
    out = np.full(len(x), np.nan)
    if len(x) > n:
        s = np.lib.stride_tricks.sliding_window_view(x, n)
        out[n - 1:] = s.min(axis=1)
    return out


def utc_hour(t_ms):
    return ((t_ms // 3600000) % 24).astype(int)


def utc_dow(t_ms):
    return (((t_ms // 86400000) + 4) % 7).astype(int)   # 0=Mon


# ---- rules: each returns (idx, side) ----
def rules(b, a):
    c, h, l, o = b["c"], b["h"], b["l"], b["o"]
    n = len(c)
    i = np.arange(n)
    hr = utc_hour(b["t"]); dw = utc_dow(b["t"])
    out = {}

    for N in (20, 50):
        hh, ll = roll_max(h, N), roll_min(l, N)
        prev_hh = np.concatenate(([np.nan], hh[:-1])); prev_ll = np.concatenate(([np.nan], ll[:-1]))
        up = c > prev_hh; dn = c < prev_ll
        idx = np.concatenate((i[up], i[dn])); sd = np.concatenate((np.ones(up.sum()), -np.ones(dn.sum())))
        out[f"breakout_{N}"] = (idx, sd)
        out[f"fade_breakout_{N}"] = (idx, -sd)

    r = rsi(c, 14)
    buy = (r < 30) & (np.concatenate(([50.0], r[:-1])) >= 30)
    sell = (r > 70) & (np.concatenate(([50.0], r[:-1])) <= 70)
    idx = np.concatenate((i[buy], i[sell])); sd = np.concatenate((np.ones(buy.sum()), -np.ones(sell.sum())))
    out["rsi_revert"] = (idx, sd)
    out["rsi_follow"] = (idx, -sd)

    f, s = ema(c, 12), ema(c, 48)
    cu = (f > s) & (np.concatenate(([0.0], f[:-1])) <= np.concatenate(([0.0], s[:-1])))
    cd = (f < s) & (np.concatenate(([0.0], f[:-1])) >= np.concatenate(([0.0], s[:-1])))
    idx = np.concatenate((i[cu], i[cd])); sd = np.concatenate((np.ones(cu.sum()), -np.ones(cd.sum())))
    out["ema_cross"] = (idx, sd)
    out["ema_cross_fade"] = (idx, -sd)

    m = np.nanmean(np.abs(np.diff(c, prepend=c[0])))
    big_up = (c - o) > 1.5 * a; big_dn = (o - c) > 1.5 * a
    idx = np.concatenate((i[big_up], i[big_dn])); sd = np.concatenate((np.ones(big_up.sum()), -np.ones(big_dn.sum())))
    out["displacement_follow"] = (idx, sd)
    out["displacement_fade"] = (idx, -sd)

    # session / hour: long-only and short-only at each UTC hour
    for H in range(0, 24, 1):
        at = i[(hr == H)]
        if len(at) > 200:
            out[f"hour{H:02d}_long"] = (at, np.ones(len(at)))

    # London open (07 UTC) break of the Asian range (00-06 UTC)
    return out


def run_symbol(sym, tf, geoms, acc):
    b = lab.load(sym, tf)
    if b is None or len(b["c"]) < 3000:
        return
    a = lab.atr(b, 14)
    R = rules(b, a)
    for g in geoms:
        sl, tp, mb = g
        ctrl = lab.control(b, 6000, sl, tp, mb, a, seed=7)
        acc[("CONTROL", g)].append((ctrl, sym))
        for name, (idx, sd) in R.items():
            if len(idx) < 30:
                continue
            res = lab.simulate(b, np.asarray(idx), np.asarray(sd), sl, tp, mb, a)
            if res.get("n"):
                acc[(name, g)].append((lab.score(res), sym))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="M15")
    ap.add_argument("--markets", default="forex,metals")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    want = set(args.markets.split(","))

    syms = []
    for fn in sorted(os.listdir(HIST)):
        if not fn.endswith(".json"):
            continue
        s = fn[:-5]
        try:
            with open(os.path.join(HIST, fn)) as f:
                d = json.load(f)
        except Exception:
            continue
        if d.get("market") in want:
            syms.append(s)

    geoms = [(1.0, 2.0, 32), (1.5, 1.5, 32), (2.0, 1.0, 32), (1.0, 1.0, 16)]
    acc = defaultdict(list)
    for s in syms:
        run_symbol(s, args.tf, geoms, acc)
        print(".", end="", flush=True)
    print()

    rows = []
    for (name, g), lst in acc.items():
        pooled_n = sum(x[0]["n"] for x in lst)
        if pooled_n < 500:
            continue
        # pool per-trade dollars across symbols by weighting each symbol's mean by its n
        tot = sum(x[0]["total"] for x in lst)
        mean = tot / pooled_n
        var = sum((x[0]["se"] ** 2) * (x[0]["n"] ** 2) for x in lst if np.isfinite(x[0]["se"]))
        se = (var ** 0.5) / pooled_n if var > 0 else float("nan")
        t = mean / se if se and np.isfinite(se) and se > 0 else 0.0
        rows.append({"rule": name, "geom": f"sl{g[0]}/tp{g[1]}/{g[2]}b", "n": pooled_n,
                     "mean": mean, "t": t, "total": tot})

    rows.sort(key=lambda r: -r["t"])
    print(f"\n{'rule':<24}{'geometry':<18}{'n':>8}{'mean$':>10}{'t':>8}{'total$':>12}")
    for r in rows[:45]:
        print(f"{r['rule']:<24}{r['geom']:<18}{r['n']:>8}{r['mean']:>10.4f}{r['t']:>8.2f}{r['total']:>12.2f}")
    print("\n--- controls ---")
    for r in rows:
        if r["rule"] == "CONTROL":
            print(f"{r['rule']:<24}{r['geom']:<18}{r['n']:>8}{r['mean']:>10.4f}{r['t']:>8.2f}{r['total']:>12.2f}")
    if args.out:
        with open(args.out, "w") as f:
            json.dump(rows, f, indent=1)
        print("\nwrote", args.out)


if __name__ == "__main__":
    main()
