"""
engine/replay_charts.py — pictures of a filter_replay run of the LIVE plan (David 2026-10-31: "check our current
plan which is running the same way" — the same end-to-end check + pictures as the updated S&D rules got).

    python3 -m engine.replay_charts engine_data/filters/replay-2026-10-31-330d-profit-live.json --name "V5 live plan"
        -> engine_data/filters/charts/<json name>/ 00_summary.png, 01_funnel.png, trade_NN_*.png, trades.csv, <name>.pdf

Each trade: the setup timeframe's candles, the zone (supply orange / demand blue), the FVG, the BOS level, entry
(amber), SL (red), TP (teal), the layer (dashed amber), the entry and the exit as the live management closed it.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from . import filters as FL  # noqa: E402
from . import learn  # noqa: E402
from .config import DATA_DIR  # noqa: E402
from .sd_backtest_charts import (BG, DEMAND, ENTRY, GRID, INK, INK2, MUTED, SL, SUPPLY, TP, candles, fx, ist,  # noqa: E402
                                 tag)

OUT = os.path.join(DATA_DIR, "filters", "charts")
EXIT_NAME = {"sl": "stopped", "tp": "target hit", "swap": "closed before the 20:45 UTC swap", "open": "still open"}


def trades_of(res: List[Dict]) -> List[Dict]:
    out = []
    for r in res:
        if "error" in r:
            continue
        for a in r["on"]["attempts"]:
            if a["status"] == "signal":
                out.append({**a, "symbol": r["symbol"]})
    return sorted(out, key=lambda a: a["entry_t"])


def trade_png(a: Dict, n: int, of: int, path: str) -> None:
    sym, tf, side = a["symbol"], a["tf"], a["side"]
    sell = side == "sell"
    ms = learn.TF_MS[tf]
    rows = learn.load_bars(sym, tf, 10 ** 7)
    bars = learn.to_dicts(rows)
    T = [b["t"] for b in bars]
    import bisect
    M, L = a.get("managed") or {}, a["levels"]
    t_exit = M.get("exit_t") or bars[-1]["t"]
    i_a = bisect.bisect_left(T, min(x for x in (a["zone"].get("t"), a["touch_t"]) if x))
    i_e = bisect.bisect_left(T, t_exit)
    i0, i1 = max(0, i_a - 25), min(len(bars), i_e + 25)
    if i1 - i0 > 300:
        i0 = max(0, i1 - 300)
    w = bars[i0:i1]
    t0 = w[0]["t"]
    X = lambda t: (t - t0) / ms
    fig, ax = plt.subplots(figsize=(16, 9), dpi=100)
    fig.subplots_adjust(left=0.05, right=0.80, top=0.86, bottom=0.09)
    candles(ax, w, t0, ms)
    z, f = a["zone"], a.get("fvg")
    core = [L["entry"], L["stop"]] + [v for v in (z.get("top"), z.get("bottom")) if v is not None]
    lo, hi = min(min(b["l"] for b in w), *core), max(max(b["h"] for b in w), *core)
    pad = (hi - lo) * 0.08
    ylo, yhi = lo - pad, hi + pad
    xe, xx, xr = X(a["entry_t"]), X(t_exit), len(w) + 0.5
    xl = min(max(xx, xe + 12), xr)
    zc = SUPPLY if sell else DEMAND
    if z.get("top") is not None:
        zx0 = max(X(z["t"]), -0.5)
        ax.add_patch(Rectangle((zx0, z["bottom"]), xl - zx0, z["top"] - z["bottom"], facecolor=zc, alpha=0.16, edgecolor=zc, linewidth=1.2, zorder=1))
        ax.text(zx0 + 0.5, z["top"] if sell else z["bottom"], f"{'supply' if sell else 'demand'} zone {fx(z['bottom'])} – {fx(z['top'])}",
                color=INK2, fontsize=8.5, va="bottom" if sell else "top")
    if f and f.get("top") is not None:
        fx0 = max(X(f["t"]), -0.5)
        ax.add_patch(Rectangle((fx0, f["bottom"]), xl - fx0, f["top"] - f["bottom"], facecolor=MUTED, alpha=0.14, edgecolor=MUTED,
                               linewidth=0.8, linestyle="--", zorder=1))
        ax.text(fx0 + 0.5, f["top"], "FVG", color=MUTED, fontsize=8, va="bottom")
    b_ = a.get("bos") or {}
    if b_.get("level") is not None and ylo <= b_["level"] <= yhi:
        lx0 = max(X(b_["level_t"]), -0.5)
        ax.hlines(b_["level"], lx0, max(X(b_["t"]), lx0 + 1), colors=MUTED, linestyles="--", linewidth=1)
        ax.text(lx0 + 0.5, b_["level"], f"{b_.get('kind') or 'BOS'} {fx(b_['level'])}", color=MUTED, fontsize=8, va="bottom")
    risk = abs(L["entry"] - L["stop"])
    lines = [(L["entry"], ENTRY, "-", f"{'SELL' if sell else 'BUY'} {fx(L['entry'])}"), (L["stop"], SL, "-", f"SL {fx(L['stop'])}  (−1R)"),
             (L["target"], TP, "-", f"TP {fx(L['target'])}  (+{abs(L['target'] - L['entry']) / risk:.1f}R)")]
    if L.get("layer") is not None:
        lines.append((L["layer"], ENTRY, "--", f"layer {fx(L['layer'])}"))
    off_b, off_a = [], []
    for p, col, ls, lab in lines:
        if ylo <= p <= yhi:
            ax.hlines(p, xe, xl, colors=col, linestyles=ls, linewidth=1.6, zorder=5)
            tag(ax, xr + 0.6, p, lab, col)
        else:
            (off_b if p < ylo else off_a).append((p, col, lab))
    for k, (p, col, lab) in enumerate(sorted(off_b)):
        tag(ax, xr + 0.6, ylo + (yhi - ylo) * (0.04 + 0.05 * k), lab + "  ↓", col)
    for k, (p, col, lab) in enumerate(sorted(off_a, reverse=True)):
        tag(ax, xr + 0.6, yhi - (yhi - ylo) * (0.04 + 0.05 * k), lab + "  ↑", col)
    ax.scatter([xe], [L["entry"]], marker="v" if sell else "^", s=150, color=ENTRY, edgecolors=BG, linewidths=1.5, zorder=9)
    if M.get("exit_t"):
        px = {"sl": M.get("final_stop"), "swap": M.get("exit_px"), "tp": L["target"]}.get(M["exit"], L["entry"])
        col = SL if (M.get("r") or 0) < 0 else TP if (M.get("r") or 0) > 0 else MUTED
        ax.scatter([X(M["exit_t"])], [px], marker="X", s=120, color=col, edgecolors=BG, linewidths=1.5, zorder=9)
    ax.axvline(X(a["touch_t"]), color=GRID, linewidth=1, zorder=0)
    ax.text(X(a["touch_t"]), yhi, " pullback", color=MUTED, fontsize=8, va="top")
    ax.set_xlim(-1, xr + 0.5)
    ax.set_ylim(ylo, yhi)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ticks = list(range(0, len(w), max(1, len(w) // 9)))
    ax.set_xticks(ticks, [ist(w[i]["t"]) for i in ticks])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    r_m, O = M.get("r"), a.get("outcome") or {}
    fig.text(0.05, 0.955, f"{sym} {tf} · trade {n} of {of} · {'SELL' if sell else 'BUY'} · {a.get('entry_type') or 'S&D'} · "
             f"result {('%+.2fR' % r_m) if r_m is not None else 'open'} with the live management", fontsize=14, fontweight="bold")
    fig.text(0.05, 0.925, f"pullback {ist(a['touch_t'])} · M5 entry BOS {ist(a.get('entry_bos_t'))} · entry {ist(a['entry_t'])} · "
             f"{EXIT_NAME.get(M.get('exit'), M.get('exit'))} {ist(M.get('exit_t'))} · layer {M.get('layer') or '-'} · stop moved {M.get('stop_moved', 0)}×",
             fontsize=10, color=INK2)
    fig.text(0.05, 0.897, f"target: {L.get('target_label') or '-'} · plain stop / target would give {O.get('r') if O.get('r') is not None else 'open'}R "
             f"({O.get('exit')}) · best move +{O.get('mfe_r', 0):.1f}R · spread {((L.get('ask') or 0) - (L.get('bid') or 0)):.5g} · times IST",
             fontsize=10, color=INK2)
    fig.text(0.05, 0.02, "▼ / ▲ entry · × exit · grey dashed box = the FVG the setup needed · dashed line = the BOS the setup came from",
             fontsize=9, color=MUTED)
    fig.savefig(path)
    plt.close(fig)


def funnel_png(res: List[Dict], tr: List[Dict], days: int, name: str, path: str, never: List[str]) -> Dict:
    recs = [x for r in res if "error" not in r for x in r["on"]["records"]]
    first = Counter(x["first_fail"] for x in recs)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 9), dpi=100, gridspec_kw={"width_ratios": [3, 2], "wspace": 0.35})
    fig.subplots_adjust(left=0.08, right=0.97, top=0.80, bottom=0.08)
    gates = list(FL.GATES)
    vals = [first.get(g, 0) for g in gates]
    labels = [f"{g} {FL.GATES[g]}" for g in gates]
    a1.barh(labels[::-1], vals[::-1], color=MUTED, height=0.6)
    for y, v in enumerate(vals[::-1]):
        a1.text(v, y, f"  {v}", va="center", color=INK, fontsize=10)
    a1.set_title("where the live plan's pullbacks were refused (first failing gate)", color=INK, fontsize=11, loc="left")
    a1.grid(axis="x", color=GRID, linewidth=0.6)
    for s in ("top", "right"):
        a1.spines[s].set_visible(False)
    md = [t["managed"]["r"] for t in tr if (t.get("managed") or {}).get("r") is not None]
    fx_ = [t["outcome"]["r"] for t in tr if (t.get("outcome") or {}).get("r") is not None]
    a2.axis("off")
    rows = [("pullbacks to a setup (attempts)", len(recs)), ("passed every gate", first.get(None, 0)), ("TRADES taken", len(tr)),
            ("live management: won / lost", f"{sum(1 for r in md if r > 0)} / {sum(1 for r in md if r < 0)}"),
            ("live management: total", f"{sum(md):+.2f}R"), ("plain stop / target: total", f"{sum(fx_):+.2f}R"),
            ("symbols the cost gate never lets trade", f"{len(never)} of 53")]
    for k, (lab, v) in enumerate(rows):
        a2.text(0.0, 0.95 - k * 0.075, lab, color=INK2, fontsize=11, transform=a2.transAxes)
        a2.text(1.0, 0.95 - k * 0.075, str(v), color=INK, fontsize=11, ha="right", fontweight="bold", transform=a2.transAxes)
    import textwrap
    a2.text(0.0, 0.95 - len(rows) * 0.075 - 0.01, "\n".join(textwrap.wrap("never: " + ", ".join(never), 62)), color=MUTED, fontsize=8.5,
            va="top", transform=a2.transAxes)
    ok = [r for r in res if "error" not in r]
    fig.text(0.07, 0.94, f"{name}: the live engine code replayed over {days} days ({ist(min(r['start'] for r in ok), '%d %b %Y')} → "
             f"{ist(max(r['end'] for r in ok), '%d %b %Y')}) on the {len(ok)} symbols it can trade", fontsize=15, fontweight="bold")
    fig.text(0.07, 0.905, "filter profile “profit” (as running): S&D M15 / M30 + S&D H4, M5 entry BOS, gates G1–G9, RR ≥ 2, 0.01 lot,",
             fontsize=10.5, color=INK2)
    fig.text(0.07, 0.878, "flat before the 20:45 UTC swap; management = Book.trail (break-even, T1, locks, layer)", fontsize=10.5, color=INK2)
    fig.savefig(path)
    plt.close(fig)
    return {"attempts": len(recs), "passed": first.get(None, 0), "first_fail": {g: first.get(g, 0) for g in gates},
            "trades": len(tr), "managed_R": round(sum(md), 2), "fixed_R": round(sum(fx_), 2),
            "won": sum(1 for r in md if r > 0), "lost": sum(1 for r in md if r < 0)}


def compare_png(summ: Dict, sd: Dict, path: str) -> None:
    """the running plan next to the updated S&D rules (sd_backtest), rule by rule and result by result"""
    fig = plt.figure(figsize=(16, 9), dpi=100)
    fig.text(0.04, 0.95, "Our running plan (V5, profile “profit”) next to the updated supply / demand rules", fontsize=16, fontweight="bold")
    rows = [
        ("", "running plan (V5 engine, live now)", "updated S&D rules (Drive doc, 31 Oct)"),
        ("symbols", "14 forex pairs — cost gate G9 refuses all 36 crypto + NZDUSD, GBPJPY, EURCHF", "any (tested on ETHEREUM M30)"),
        ("zone", "V5 BOS → zone in the move (≥ 1.5× displacement) + FVG required, FVG untouched", "valid /smc zone (major BOS / CHoCH, ≥ 1.5×, ≤ 1.5 ATR)"),
        ("filter", "9 gates G1–G9 (swing, break, regime, location, stop/RR, market, cost)", "OTA score 0–10 (departure, base, fresh, margin, curve + H4)"),
        ("entry", "pullback to the entry, then M5 close beyond the latest M5 swing", "score ≥ 9 limit at zone 50 %; 7–8.5 the same M5 confirmation"),
        ("stop", "zone invalidation + buffer, widened to the broker's stops level", "distal / M5 rejection + 0.2 ATR + spread (sell)"),
        ("target", "nearest opposing structure, RR ≥ 2", "TP1 50 % at the broken BOS → break-even; TP2 the leg extreme"),
        ("management", "layer, break-even, T1, locks; flat before the 20:45 UTC swap", "TP1 then break-even"),
    ]
    a = sd["stats"]["all"]
    res = [("trades in ~11 months", f"{summ['trades']} (from {summ['attempts']:,} pullbacks)", f"{a.get('n', 0)} (from {sd['returns']} returns)"),
           ("result", f"{summ['managed_R']:+.2f}R live management ({summ['fixed_R']:+.1f}R plain stop / target)",
            f"{a.get('total_R', 0):+.1f}R, {a.get('wins', 0)} won"),
           ("same way?", "same family: zone after a break + M5 BOS entry", "different filter, targets and crypto allowed")]
    xs = [0.04, 0.17, 0.58]
    y = 0.86
    for k, r in enumerate(rows + [("", "", "")] + res):
        for j, (x, v) in enumerate(zip(xs, r)):
            fig.text(x, y, v, fontsize=10.5 if k else 11, color=(MUTED if j == 0 else INK) if k else MUTED,
                     fontweight="bold" if (k == 0 or k > len(rows)) and j else None)
        y -= 0.055
    fig.text(0.04, y - 0.03, "Both are checked on our own FxPro history with the same rules for fills and spread (M5 candles, a candle touching stop "
             "and target counts the stop).", fontsize=10, color=INK2)
    fig.text(0.04, y - 0.065, f"The running plan almost never trades: {summ['first_fail']['G1']} pullbacks die at G1 (the break was a minor pivot), "
             f"{summ['first_fail']['G2']} at G2 (FVG traded through / weak break), and the stop / RR and location checks fail on almost all of the rest.",
             fontsize=10, color=INK2)
    fig.savefig(path)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="pictures of a filter_replay run")
    ap.add_argument("path")
    ap.add_argument("--name", default="V5 live plan")
    ap.add_argument("--days", type=int, default=330)
    ap.add_argument("--sd", default="", help="an sd_backtest result to put next to it (the updated S&D rules)")
    a = ap.parse_args()
    with open(a.path) as f:
        res = json.load(f)
    out = os.path.join(OUT, os.path.basename(a.path)[:-5])
    os.makedirs(out, exist_ok=True)
    for old in os.listdir(out):
        if old.endswith(".png"):
            os.remove(os.path.join(out, old))
    with open(os.path.join(DATA_DIR, "symbol_cost.json")) as f:
        costs = json.load(f)
    never = sorted(s for s, v in costs.items() if v["spread_atr"] > 0.10)
    tr = trades_of(res)
    pages = [os.path.join(out, "01_funnel.png")]
    summ = funnel_png(res, tr, a.days, a.name, pages[0], never)
    if a.sd:
        with open(a.sd) as f:
            sd = json.load(f)
        pages.insert(0, os.path.join(out, "00_compare.png"))
        compare_png(summ, sd, pages[0])
    for k, t in enumerate(tr, 1):
        r = (t.get("managed") or {}).get("r")
        p = os.path.join(out, f"trade_{k:02d}_{t['symbol']}_{t['tf']}_{ist(t['entry_t'], '%Y%m%d_%H%M')}_{t['side']}_"
                              f"{('%+.2fR' % r) if r is not None else 'open'}.png")
        trade_png(t, k, len(tr), p)
        pages.append(p)
    with open(os.path.join(out, "trades.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["n", "symbol", "tf", "entry_type", "side", "pullback_ist", "entry_ist", "entry", "sl", "tp", "layer", "exit", "exit_ist",
                     "R_live_management", "R_stop_target", "best_move_R"])
        for k, t in enumerate(tr, 1):
            M, O, L = t.get("managed") or {}, t.get("outcome") or {}, t["levels"]
            wr.writerow([k, t["symbol"], t["tf"], t.get("entry_type"), t["side"].upper(), ist(t["touch_t"], "%Y-%m-%d %H:%M"),
                         ist(t["entry_t"], "%Y-%m-%d %H:%M"), L["entry"], L["stop"], L["target"], L.get("layer"), M.get("exit"),
                         ist(M.get("exit_t"), "%Y-%m-%d %H:%M"), M.get("r"), O.get("r"), O.get("mfe_r")])
    with PdfPages(os.path.join(out, f"{a.name.replace(' ', '_')}_replay.pdf")) as pdf:
        for p in pages:
            fig = plt.figure(figsize=(16, 9), dpi=100)
            fig.figimage(plt.imread(p), 0, 0)
            pdf.savefig(fig)
            plt.close(fig)
    with open(os.path.join(out, "summary.json"), "w") as f:
        json.dump(summ, f, indent=1)
    print(out)
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
