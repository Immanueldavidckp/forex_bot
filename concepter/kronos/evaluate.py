"""
concepter/kronos/evaluate.py — does Kronos-base see where FxPro prices go next? Two out-of-sample tests on M15 bars.

    ~/opt/kronos-venv/bin/python -m concepter.kronos.evaluate standalone [--symbols GOLD,EURUSD,BITCOIN]
    ~/opt/kronos-venv/bin/python -m concepter.kronos.evaluate v5
    ~/opt/kronos-venv/bin/python -m concepter.kronos.evaluate report

standalone  every SPACING bars from FROM: 512 closed bars in, HORIZON bars out, SAMPLES paths each; scored
            against the real close HORIZON bars later (direction hit rate, rank IC, and a toy "trade the
            forecast" P&L net of the bar's spread vs always-long and momentum).
v5          every V5 backtest trade on M15 since FROM (engine_data/backtest/setups.jsonl, traded): the same
            forecast from the bars closed before the entry touch; does the trade's fixed-target R differ when
            Kronos agrees with the side?

Kronos' pre-training data ends before its Aug 2025 release, so FROM = 2025-09-01 keeps every forecast out of
sample. Results append to engine_data/kronos/results/*.jsonl (a rerun skips what is done).
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd

from engine.config import DATA_DIR

BARS = os.path.join(DATA_DIR, "kronos", "bars")
RES = os.path.join(DATA_DIR, "kronos", "results")
SETUPS = os.path.join(DATA_DIR, "backtest", "setups.jsonl")
FROM = pd.Timestamp("2025-09-01")
CTX, HORIZON, SAMPLES, SPACING = 512, 8, 4, 32     # M15: 128 h in, 2 h out, 4 paths, an origin every 8 h
STEP = pd.Timedelta("15min")


def bars(sym: str, tf: str = "M15") -> pd.DataFrame:
    d = json.load(open(os.path.join(BARS, f"{sym}_{tf}.json")))
    b = d["bars"]
    return pd.DataFrame([r[1:7] for r in b], columns=["open", "high", "low", "close", "volume", "spread"],
                        index=pd.to_datetime([r[0] for r in b], unit="ms"))


def done(path: str, key: str) -> set:
    if not os.path.exists(path):
        return set()
    return {json.loads(l)[key] for l in open(path)}


def run(jobs, df, out_path, extra, batch_origins=8):
    """jobs: [(key, i)] with i = index of the first forecast bar; window = df[i-CTX:i]."""
    from .model import load, paths
    pred = load()
    t0 = time.time()
    with open(out_path, "a") as f:
        for k in range(0, len(jobs), batch_origins):
            chunk = jobs[k:k + batch_origins]
            wins = [df.iloc[i - CTX:i] for _, i in chunk]
            cl = paths(pred, wins, STEP, HORIZON, SAMPLES, batch=32)
            for (key, i), w, c in zip(chunk, wins, cl):
                last = float(w["close"].iloc[-1])
                f.write(json.dumps({"key": key, "t": str(w.index[-1]), "last": last,
                                    "end": [round(float(x), 6) for x in c[:, -1]], **extra(key, i)}) + "\n")
            f.flush()
            n = k + len(chunk)
            print(f"  {n}/{len(jobs)}  {(time.time() - t0) / n:.1f}s/origin", flush=True)


def standalone(symbols):
    os.makedirs(RES, exist_ok=True)
    for sym in symbols:
        df = bars(sym)
        out = os.path.join(RES, f"standalone_{sym}.jsonl")
        have = done(out, "key")
        t = df.index
        jobs = []
        for i in range(max(CTX, int(t.searchsorted(FROM))), len(df) - HORIZON, SPACING):
            # the HORIZON bars must run without a gap (no weekend / daily break inside the forecast)
            if t[i + HORIZON - 1] - t[i - 1] != HORIZON * STEP or str(t[i - 1]) in have:
                continue
            jobs.append((str(t[i - 1]), i))
        print(f"{sym}: {len(jobs)} origins", flush=True)

        def extra(key, i, df=df):
            return {"real": float(df["close"].iloc[i + HORIZON - 1]), "spread": float(df["spread"].iloc[i]),
                    "mom": float(df["close"].iloc[i - 1] - df["close"].iloc[i - 1 - HORIZON])}
        run(jobs, df, out, extra)


def v5():
    os.makedirs(RES, exist_ok=True)
    out = os.path.join(RES, "v5_m15.jsonl")
    have = done(out, "key")
    rows = [json.loads(l) for l in open(SETUPS)]
    trades = [r for r in rows if r.get("traded") and r["tf"] == "M15" and pd.Timestamp(r["touch_t"], unit="ms") >= FROM
              and (r.get("fixed") or {}).get("r") is not None and r["id"] not in have]
    by_sym = {}
    for r in trades:
        by_sym.setdefault(r["symbol"], []).append(r)
    print(f"v5: {len(trades)} trades on {len(by_sym)} symbols", flush=True)
    for sym, rs in sorted(by_sym.items(), key=lambda kv: -len(kv[1])):
        df = bars(sym)
        meta = {r["id"]: r for r in rs}
        jobs = []
        for r in rs:
            # bars that closed before the entry touch: open time + 15 min <= touch
            i = int(df.index.searchsorted(pd.Timestamp(r["touch_t"], unit="ms") - STEP, side="right"))
            if i >= CTX:
                jobs.append((r["id"], i))
        print(f"{sym}: {len(jobs)} trades", flush=True)

        def extra(key, i, meta=meta, sym=sym):
            r = meta[key]
            return {"symbol": sym, "market": r["market"], "side": r["side"], "r": r["fixed"]["r"], "managed_r": (r.get("managed") or {}).get("r"),
                    "touch_t": r["touch_t"]}
        run(jobs, df, out, extra)


# ---------------------------------------------------------------------------------------------------- report

def _hit(sig, ret):
    m = (sig != 0) & (ret != 0)
    return float((np.sign(sig[m]) == np.sign(ret[m])).mean()), int(m.sum())


def _z(hit, n):
    return (hit - 0.5) / np.sqrt(0.25 / n) if n else 0.0


def report() -> str:
    lines = [f"Kronos-base out-of-sample test, M15, {CTX} bars in, {HORIZON} bars (2 h) out, {SAMPLES} paths, from {FROM.date()}", ""]
    for p in sorted(f for f in os.listdir(RES) if f.startswith("standalone_")):
        d = pd.read_json(os.path.join(RES, p), lines=True)
        if d.empty:
            continue
        sym = p[len("standalone_"):-6]
        end = np.vstack(d["end"].to_numpy())
        last, real, spr = d["last"].to_numpy(), d["real"].to_numpy(), d["spread"].to_numpy()
        ret = real - last
        mean_pred = end.mean(1) - last
        p_up = (end > last[:, None]).mean(1)
        hit, n = _hit(mean_pred, ret)
        conf = (p_up == 1) | (p_up == 0)
        hit_c, n_c = _hit(np.where(conf, p_up - 0.5, 0), ret)
        ic = pd.Series(mean_pred).rank().corr(pd.Series(ret).rank())       # Spearman without scipy
        bps = lambda x: 1e4 * float(np.mean(x / last))  # noqa: E731
        k_pnl = np.sign(mean_pred) * ret - spr
        long_pnl = ret - spr
        mom_pnl = np.sign(d["mom"].to_numpy()) * ret - spr
        lines += [f"{sym}: {len(d)} forecasts {d['t'].iloc[0][:10]} → {d['t'].iloc[-1][:10]}",
                  f"  direction hit {hit:.1%} (n {n}, z {_z(hit, n):+.1f}); all 4 paths agree: {hit_c:.1%} (n {n_c}, z {_z(hit_c, n_c):+.1f})",
                  f"  rank IC forecast vs real 2 h move {ic:+.3f}",
                  f"  per trade, after spread: follow Kronos {bps(k_pnl):+.2f} bps | always long {bps(long_pnl):+.2f} | momentum {bps(mom_pnl):+.2f}"
                  f" | spread cost {bps(spr):.2f}", ""]
    vp = os.path.join(RES, "v5_m15.jsonl")
    if os.path.exists(vp):
        d = pd.read_json(vp, lines=True)
        if not d.empty:
            end = np.vstack(d["end"].to_numpy())
            p_up = (end > d["last"].to_numpy()[:, None]).mean(1)
            sgn = np.where(d["side"] == "buy", 1, -1)
            p_with = np.where(sgn == 1, p_up, 1 - p_up)
            d["agree"] = np.select([p_with > 0.5, p_with < 0.5], ["agree", "against"], "split")
            d["p_with"] = p_with
            lines += [f"V5 M15 trades since {FROM.date()} (fixed 3R target): {len(d)} trades, avg {d['r'].mean():+.3f}R, win {(d['r'] > 0).mean():.1%}"]
            for g in ("agree", "split", "against"):
                s = d[d["agree"] == g]
                if len(s):
                    lines.append(f"  Kronos {g:7s}: {len(s):5d} trades  avg {s['r'].mean():+.3f}R  win {(s['r'] > 0).mean():.1%}  sum {s['r'].sum():+.1f}R")
            for g, s in (("all 4 paths with the trade", d[d["p_with"] == 1]), ("all 4 paths against", d[d["p_with"] == 0])):
                if len(s):
                    lines.append(f"  {g:27s}: {len(s):5d} trades  avg {s['r'].mean():+.3f}R  win {(s['r'] > 0).mean():.1%}")
            fx = d[d["market"] == "forex"]
            a, b = fx[fx["agree"] == "agree"], fx[fx["agree"] == "against"]
            if len(a) and len(b):
                lines.append(f"  forex only: agree {len(a)} avg {a['r'].mean():+.3f}R | against {len(b)} avg {b['r'].mean():+.3f}R")
    txt = "\n".join(lines)
    with open(os.path.join(RES, "report.txt"), "w") as f:
        f.write(txt + "\n")
    return txt


def main() -> int:
    ap = argparse.ArgumentParser(description="Kronos-base out-of-sample test on FxPro M15 bars")
    ap.add_argument("mode", choices=["standalone", "v5", "report"])
    ap.add_argument("--symbols", default="GOLD,EURUSD,BITCOIN")
    a = ap.parse_args()
    if a.mode == "standalone":
        standalone(a.symbols.split(","))
    elif a.mode == "v5":
        v5()
    print(report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
