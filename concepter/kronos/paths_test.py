"""
concepter/kronos/paths_test.py — does drawing 32 Kronos paths instead of 16 make the live trades better? (David 2026-10-27)

    ~/opt/kronos-venv/bin/python -m concepter.kronos.paths_test run [--symbols GOLD,EURUSD,BITCOIN]
    ~/opt/kronos-venv/bin/python -m concepter.kronos.paths_test report

run     the evaluate.py origins (every SPACING bars from FROM, no gap inside the 2 h), 32 paths each, written to
        engine_data/kronos/results/paths32.jsonl with the next HORIZON bars (high, low, close), the spread and ATR.
        Origins go in an interleaved order (every 4th first, all symbols in turn), so a run stopped early still
        covers the whole period; a rerun skips what is done.
report  the same forecasts scored with the first 4 / 8 / 16 / all 32 paths, and with paths 17-32 as a second
        16-path set (how much two 16-path draws differ by chance). Trades follow the live rule in
        engine/kronos_book.decide: P_MIN of the paths on one side, the median end on that side, median move
        >= MIN_MOVE_SPREAD_X x spread, spread <= MAX_SPREAD_SL x stop; buy at ask (bars are bid), SL_ATR / TP_ATR,
        exit at the HORIZON-th close; a bar touching both stop and target counts as the stop.
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from engine.config import KRONOS as K
from .evaluate import CTX, FROM, HORIZON, RES, SPACING, STEP, bars

PATHS = 32
OUT = os.path.join(RES, "paths32.jsonl")
SETS = [("4", 0, 4), ("8", 0, 8), ("16", 0, 16), ("32", 0, 32), ("16 (paths 17-32)", 16, 32)]


def _atr(w, n: int = K["ATR_PERIOD"]) -> float:
    """engine/kronos_book.atr on the window's last n bars."""
    h, l, c = w["high"].to_numpy(), w["low"].to_numpy(), w["close"].to_numpy()
    tr = np.maximum(h[-n:], c[-n - 1:-1]) - np.minimum(l[-n:], c[-n - 1:-1])
    return float(tr.mean())


def run(symbols, batch_origins: int = 2) -> None:
    from .model import load, paths
    os.makedirs(RES, exist_ok=True)
    have = set()
    if os.path.exists(OUT):
        have = {(r["symbol"], r["t"]) for r in map(json.loads, open(OUT))}
    jobs = []
    for sym in symbols:
        df = bars(sym)
        t = df.index
        k = 0
        for i in range(max(CTX, int(t.searchsorted(FROM))), len(df) - HORIZON, SPACING):
            if t[i + HORIZON - 1] - t[i - 1] != HORIZON * STEP:
                continue
            if (sym, str(t[i - 1])) not in have:
                jobs.append(((k % 4 != 0, k % 2 != 0, k, sym), sym, df, i))
            k += 1
    jobs.sort(key=lambda j: j[0])
    print(f"{len(jobs)} origins to do ({len(have)} done), {PATHS} paths each", flush=True)
    pred = load()
    t0 = time.time()
    with open(OUT, "a") as f:
        for k in range(0, len(jobs), batch_origins):
            chunk = jobs[k:k + batch_origins]
            wins = [df.iloc[i - CTX:i] for _, _, df, i in chunk]
            cl = paths(pred, wins, STEP, HORIZON, PATHS, batch=32)
            for (_, sym, df, i), w, c in zip(chunk, wins, cl):
                fut = df.iloc[i:i + HORIZON]
                f.write(json.dumps({"symbol": sym, "t": str(w.index[-1]), "last": float(w["close"].iloc[-1]),
                                    "spread": float(w["spread"].iloc[-1]), "atr": _atr(w),
                                    "fut": [[float(r.high), float(r.low), float(r.close)] for r in fut.itertuples()],
                                    "end": [round(float(x), 6) for x in c[:, -1]]}) + "\n")
            f.flush()
            n = k + len(chunk)
            if n % 20 == 0 or n == len(jobs):
                print(f"  {n}/{len(jobs)}  {(time.time() - t0) / n:.1f}s/origin", flush=True)


def trade_r(r: dict, sg: int) -> float | None:
    """R of one live-rule trade (None when the spread is too wide for the stop)."""
    spr, a = r["spread"], r["atr"]
    sl_d, tp_d = K["SL_ATR"] * a, K["TP_ATR"] * a
    if a <= 0 or spr > K["MAX_SPREAD_SL"] * sl_d:
        return None
    entry = r["last"] + spr if sg == 1 else r["last"]
    ask = spr if sg == -1 else 0.0           # a sell closes at the ask
    for h, l, c in r["fut"]:
        hit_sl = (l + ask <= entry - sl_d) if sg == 1 else (h + ask >= entry + sl_d)
        hit_tp = (h + ask >= entry + tp_d) if sg == 1 else (l + ask <= entry - tp_d)
        if hit_sl:
            return -1.0
        if hit_tp:
            return tp_d / sl_d
    return sg * (r["fut"][-1][2] + ask - entry) / sl_d


def decide(r: dict, end: np.ndarray):
    """→ (forecast side by the median, trade side or 0, R or None)."""
    last = r["last"]
    p_up = float((end > last).mean())
    move = float(np.median(end)) - last
    med = int(np.sign(move))
    agree = max(p_up, 1 - p_up)
    if agree < K["P_MIN"]:
        return med, 0, None
    sg = 1 if p_up >= K["P_MIN"] else -1
    if med != sg or abs(move) < K["MIN_MOVE_SPREAD_X"] * r["spread"]:
        return med, 0, None
    R = trade_r(r, sg)
    return med, (sg if R is not None else 0), R


def report() -> str:
    rows = [json.loads(l) for l in open(OUT)]
    syms = sorted({r["symbol"] for r in rows})
    lines = [f"Kronos-base, {PATHS} paths vs fewer: {len(rows)} forecasts ({', '.join(syms)}), M15, {CTX} bars in, "
             f"2 h out, from {FROM.date()}",
             f"live rule: {K['P_MIN']:.0%} of paths agree, median move >= {K['MIN_MOVE_SPREAD_X']:g} x spread, "
             f"SL {K['SL_ATR']:g} ATR / TP {K['TP_ATR']:g} ATR / 2 h exit, after spread", ""]
    res = {}
    for name, a, b in SETS:
        res[name] = [decide(r, np.asarray(r["end"][a:b])) for r in rows]
    real = np.array([np.sign(r["fut"][-1][2] - r["last"]) for r in rows])
    for scope in syms + ["ALL"]:
        m = np.array([scope in ("ALL", r["symbol"]) for r in rows])
        lines.append(f"{scope} ({m.sum()} forecasts)")
        lines.append(f"  {'paths':18s} {'direction hit':>14s} {'trades':>7s} {'won':>6s} {'avg R':>7s} {'± SE':>6s} {'sum R':>7s}")
        for name, *_ in SETS:
            d = res[name]
            med = np.array([x[0] for x in d])
            ok = m & (med != 0) & (real != 0)
            hit = float((med[ok] == real[ok]).mean())
            R = np.array([x[2] for x, mm in zip(d, m) if mm and x[1] != 0])
            se = R.std(ddof=1) / np.sqrt(len(R)) if len(R) > 1 else 0.0
            lines.append(f"  {name:18s} {hit:13.1%}  {len(R):7d} {(R > 0).mean() if len(R) else 0:6.1%} "
                         f"{R.mean() if len(R) else 0:+7.3f} {se:6.3f} {R.sum():+7.1f}")
        lines.append("")
    # how often the decision itself changes
    for x, y in (("16", "32"), ("16", "16 (paths 17-32)")):
        dx, dy = res[x], res[y]
        diff = sum(a[1] != b[1] for a, b in zip(dx, dy))
        both = sum(a[1] != 0 and a[1] == b[1] for a, b in zip(dx, dy))
        lines.append(f"{x} vs {y}: trade decision differs on {diff} of {len(rows)} forecasts ({diff / len(rows):.1%}); "
                     f"same trade in both {both}")
    txt = "\n".join(lines)
    with open(os.path.join(RES, "paths32_report.txt"), "w") as f:
        f.write(txt + "\n")
    return txt


def main() -> int:
    ap = argparse.ArgumentParser(description="Kronos 16 vs 32 paths on the live trade rule")
    ap.add_argument("mode", choices=["run", "report"])
    ap.add_argument("--symbols", default="GOLD,EURUSD,BITCOIN")
    a = ap.parse_args()
    if a.mode == "run":
        run(a.symbols.split(","))
    print(report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
