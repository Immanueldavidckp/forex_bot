"""
engine/bt_charts.py — pictures of backtest setups, to look at what the engine called BOS / supply-demand /
FVG on the chart and how the trade went.

    python3 -m engine.bt_charts [--n 12] [--ids ID,ID]   → engine_data/backtest/charts/<id>.png + index.json

Default: the traded M15 / M30 setups, n winners and n losers picked evenly over time. Each picture is the
setup's own timeframe from a little before the BOS move to a little after the exit: the BOS level and candle,
the move's origin, the supply / demand zone (or mitigation block), the chosen FVG, entry / SL / TP, the touch
and the exit.
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from .backtest import OUT_DIR, SETUPS_FILE, load  # noqa: E402
from .feed import TF_MIN  # noqa: E402
from .history import HIST_DIR  # noqa: E402

CHART_DIR = os.path.join(OUT_DIR, "charts")
UP, DOWN = "#26a69a", "#ef5350"


def draw(rec: Dict, bars: List[Dict], path: str) -> None:
    ms = TF_MIN[rec["tf"]] * 60_000
    T = [b["t"] for b in bars]
    end_t = rec["touch_t"] + ((rec.get("fixed") or {}).get("bars") or 40) * 300_000
    a = max(0, bisect.bisect_left(T, rec["origin_t"]) - 25)
    b = min(len(bars), bisect.bisect_right(T, end_t) + 12)
    seg = bars[a:b]
    if not seg:
        return
    x = lambda t: (t - seg[0]["t"]) / ms
    fig, ax = plt.subplots(figsize=(13, 6.2), dpi=90)
    fig.patch.set_facecolor("#0f1115")
    ax.set_facecolor("#0f1115")
    for i, k in enumerate(seg):
        c = UP if k["c"] >= k["o"] else DOWN
        ax.plot([i, i], [k["l"], k["h"]], color=c, lw=0.8)
        ax.add_patch(Rectangle((i - 0.32, min(k["o"], k["c"])), 0.64, max(abs(k["c"] - k["o"]), 1e-12), color=c))
    n = len(seg)
    z, f = rec["poi"], rec["fvg"]
    zc = "#ef5350" if rec["side"] == "sell" else "#26a69a"
    ax.add_patch(Rectangle((x(z["t"]) - 0.4, z["bottom"]), n - x(z["t"]), z["top"] - z["bottom"], color=zc, alpha=0.18))
    ax.text(x(z["t"]), z["top"] if rec["side"] == "sell" else z["bottom"], f" {rec['feats']['kind']}", color=zc, fontsize=9,
            va="bottom" if rec["side"] == "sell" else "top")
    ax.add_patch(Rectangle((x(f["t"]) - 0.4, f["bottom"]), n - x(f["t"]), f["top"] - f["bottom"], color="#7aa2ff", alpha=0.25))
    ax.text(x(f["t"]), f["top"], f" FVG {rec['feats']['fvg_pick']}/{rec['feats']['fvg_n']}", color="#7aa2ff", fontsize=9, va="bottom")
    ax.hlines(rec["bos_level"], x(rec.get("bos_level_t", rec["bos_t"] - 12 * ms)), x(rec["bos_t"]) + 1, color="#f5c542", lw=1.2, ls="--")
    ax.text(x(rec["bos_t"]) + 1, rec["bos_level"], " BOS", color="#f5c542", fontsize=9, va="center")
    ax.axvline(x(rec["origin_t"]), color="#888", lw=0.6, ls=":")
    t0 = x(rec["touch_t"])
    for y, c, lab in ((rec["entry"], "#e6e9ef", "entry"), (rec["stop"], "#ef5350", "SL"), (rec.get("tp_used"), "#66bb6a", "TP"),
                      (rec.get("layer"), "#ffa726", "layer")):
        if y:
            ax.hlines(y, t0, n, color=c, lw=1.1)
            ax.text(n, y, f" {lab} {y:g}", color=c, fontsize=8, va="center")
    ax.axvline(t0, color="#e6e9ef", lw=0.6, ls="--")
    fx, mg = rec.get("fixed") or {}, rec.get("managed") or {}
    if fx.get("bars") is not None:
        ax.axvline(x(rec["touch_t"] + fx["bars"] * 300_000), color="#66bb6a" if fx["r"] > 0 else "#ef5350", lw=0.9)
    ft = rec["feats"]
    title = (f"{rec['symbol']} {rec['tf']} {rec['side'].upper()}  {'WIN' if (fx.get('r') or 0) > 0 else 'LOSS'} fixed {fx.get('r')}R  "
             f"managed {mg.get('r')}R  (went {fx.get('mfe_r')}R before the stop)\n"
             f"disp {ft['disp_x']}×  zone {ft['zone_atr']} ATR  FVG {ft['fvg_atr']} ATR  move {ft['move_atr']} ATR  break {ft['break_atr']} ATR  "
             f"SL {ft['sl_atr']}×ATR15  RR {ft['rr']}  H4 {ft['h4']}  {rec['tf']} trend {ft['tf_trend']}  BOS streak {ft['bos_streak']}  "
             f"CHoCH against {ft['choch_against']}  waited {ft['age_bars']} bars  {ft['strength']}")
    ax.set_title(title, color="#e6e9ef", fontsize=9, loc="left")
    ax.tick_params(colors="#888", labelsize=8)
    for s in ax.spines.values():
        s.set_color("#333")
    ticks = list(range(0, n, max(1, n // 8)))
    import datetime as _dt
    ax.set_xticks(ticks, [_dt.datetime.fromtimestamp(seg[i]["t"] / 1000, _dt.timezone.utc).strftime("%m-%d %H:%M") for i in ticks])
    ax.set_xlim(-1, n + 6)
    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="draw backtest setups")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--ids", default="")
    ap.add_argument("--out", default=CHART_DIR)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rs = [json.loads(line) for line in open(SETUPS_FILE)]
    if a.ids:
        want = set(a.ids.split(","))
        pick = [r for r in rs if r["id"] in want]
    else:
        tr = sorted([r for r in rs if r["traded"] and r["live_tf"] and (r.get("fixed") or {}).get("r") is not None], key=lambda r: r["touch_t"])
        wins, losses = [r for r in tr if r["fixed"]["r"] > 0], [r for r in tr if r["fixed"]["r"] < 0]
        even = lambda xs: [xs[int(i * len(xs) / a.n)] for i in range(min(a.n, len(xs)))]
        pick = even(wins) + even(losses)
    cache: Dict[str, Dict] = {}
    index = []
    for r in pick:
        if r["symbol"] not in cache:
            cache[r["symbol"]] = load(os.path.join(HIST_DIR, f"{r['symbol']}.json"))["bars"]
        p = os.path.join(a.out, f"{r['id']}.png")
        draw(r, cache[r["symbol"]][r["tf"]], p)
        index.append({"id": r["id"], "png": p, "r": r["fixed"]["r"] if r.get("fixed") else None})
        print(p)
    with open(os.path.join(a.out, "index.json"), "w") as f:
        json.dump(index, f, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
