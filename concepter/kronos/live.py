"""
concepter/kronos/live.py — Kronos-base forecast from the live FxPro terminal (read-only: bars in, no orders).

    MT5_NO_LAUNCH=1 ~/opt/kronos-venv/bin/python -m concepter.kronos.live [--symbol GOLD] [--tf M15] [--bars 16] [--paths 16]

Prints P(up) at the end of the forecast and the median / 10–90 % path; saves engine_data/kronos/live_<SYM>_<TF>.png.
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from engine.config import DATA_DIR
from engine.history import server_to_utc_ms
import mt5_client as mt5c

from .model import load, paths

STEPS = {"M5": "5min", "M15": "15min", "M30": "30min", "H1": "1h", "H4": "4h"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="GOLD")
    ap.add_argument("--tf", default="M15", choices=list(STEPS))
    ap.add_argument("--bars", type=int, default=16, help="bars to forecast")
    ap.add_argument("--paths", type=int, default=16)
    a = ap.parse_args()
    raw = mt5c.one({"op": "rates", "symbol": a.symbol, "tf": a.tf, "count": 513})
    df = pd.DataFrame([x[1:6] for x in raw], columns=["open", "high", "low", "close", "volume"],
                      index=pd.to_datetime([server_to_utc_ms(x[0]) for x in raw], unit="ms"))
    df = df.iloc[:-1]                                    # the newest bar is still forming
    step = pd.Timedelta(STEPS[a.tf])
    cl = paths(load(), [df.iloc[-512:]], step, a.bars, a.paths, batch=16)[0]
    last = float(df["close"].iloc[-1])
    q10, q50, q90 = np.percentile(cl, [10, 50, 90], axis=0)
    p_up = float((cl[:, -1] > last).mean())
    when = df.index[-1] + step
    print(f"{a.symbol} {a.tf}: last closed bar {df.index[-1]} UTC close {last}")
    print(f"Kronos-base, {a.paths} paths, next {a.bars} bars (to {when + (a.bars - 1) * step} UTC):")
    print(f"  P(up) {p_up:.0%}   median end {q50[-1]:.5g} ({(q50[-1] / last - 1) * 1e4:+.1f} bps)   10–90 %: {q10[-1]:.5g} … {q90[-1]:.5g}")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fut = pd.date_range(when, periods=a.bars, freq=step)
        h = df.iloc[-96:]
        fig, ax = plt.subplots(figsize=(11, 4.5))
        ax.plot(h.index, h["close"], color="#333", lw=1.2, label="FxPro close")
        for c in cl:
            ax.plot(fut, c, color="#4a7bd0", alpha=0.18, lw=0.8)
        ax.fill_between(fut, q10, q90, color="#4a7bd0", alpha=0.15, label="Kronos 10–90 %")
        ax.plot(fut, q50, color="#1f4fa8", lw=1.8, label=f"Kronos median (P up {p_up:.0%})")
        ax.set_title(f"{a.symbol} {a.tf} — Kronos-base forecast, {a.paths} paths")
        ax.legend(loc="upper left")
        ax.grid(alpha=0.25)
        out = os.path.join(DATA_DIR, "kronos", f"live_{a.symbol}_{a.tf}.png")
        fig.tight_layout()
        fig.savefig(out, dpi=110)
        print("  chart", out)
    except Exception as e:  # the chart is a nice-to-have
        print("  no chart:", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
