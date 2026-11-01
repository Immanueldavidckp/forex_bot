"""
engine/sd_backtest_charts.py — pictures of an sd_backtest run (David 2026-10-31: "upload in the trade folder in the
drive image with what you have done … marking in the chart with strategy and TP, SL, entry").

    python3 -m engine.sd_backtest_charts ETHEREUM M30
        -> engine_data/sd_backtest/ETHEREUM_M30/  00_summary.png, 01_overview.png, trade_NN_*.png, 99_live_setup.png,
           ETHEREUM_M30_sd_backtest.pdf (all pages), trades.csv, summary.md

Colours follow the /smc page: supply orange, demand blue, entry amber, SL red, TP teal; text stays in ink colours.
Times are IST (UTC+5:30), like the dashboard.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from . import learn, supply_demand  # noqa: E402
from .sd_backtest import (CONFIRM_SCORE, LIMIT_SCORE, OUT_DIR, SL_BUF_ATR, TP_CUSHION_ATR, Chart, leg_extreme,  # noqa: E402
                          plan_levels, score)

BG, PANEL, GRID, INK, INK2, MUTED = "#0b0e14", "#121722", "#232a3a", "#e6e9ef", "#b4bccc", "#7d879c"
BULL, BEAR = "#26a69a", "#ef5350"
SUPPLY, DEMAND = "#ffa726", "#42a5f5"
ENTRY, SL, TP = "#e5c07b", "#e06c75", "#56b6c2"
IST = _dt.timedelta(hours=5, minutes=30)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": INK, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": GRID, "figure.facecolor": BG,
                     "axes.facecolor": BG, "savefig.facecolor": BG})


def ist(ms: Optional[int], fmt: str = "%d %b %H:%M") -> str:
    return "-" if ms is None else (_dt.datetime.fromtimestamp(ms / 1000, _dt.timezone.utc) + IST).strftime(fmt)


def fx(p: Optional[float]) -> str:
    return "-" if p is None else f"{p:,.2f}"


def candles(ax, bars: List[Dict], t0: int, ms: int, width: float = 0.62) -> None:
    for b in bars:
        x = (b["t"] - t0) / ms
        up = b["c"] >= b["o"]
        col = BULL if up else BEAR
        ax.vlines(x, b["l"], b["h"], color=col, linewidth=0.8, zorder=2)
        lo, hi = min(b["o"], b["c"]), max(b["o"], b["c"])
        ax.add_patch(Rectangle((x - width / 2, lo), width, max(hi - lo, 1e-9), facecolor=col, edgecolor=col, linewidth=0.5, zorder=3))


def tag(ax, x: float, y: float, text: str, col: str, ha: str = "left", size: float = 8.5) -> None:
    ax.text(x, y, text, color=INK, fontsize=size, ha=ha, va="center", zorder=8,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": PANEL, "edgecolor": col, "linewidth": 1.1})


# ── one trade ────────────────────────────────────────────────────────────────

def trade_png(c: Chart, x: Dict, n: int, of: int, path: str) -> None:
    z = x["z"]
    sell = z["side"] == "supply"
    zc = SUPPLY if sell else DEMAND
    ms = c.ms
    bars = c.bars
    t_end = x["t_exit"] or bars[-1]["t"]
    i_touch = c.closed_before(x["t_touch"])
    i_end = c.closed_before(t_end)
    i0 = max(0, i_touch - 60)
    i1 = min(len(bars), i_end + 25)
    if i1 - i0 > 320:                                     # a long trade: keep its start and end readable
        i0 = max(0, i1 - 320)
    w = bars[i0:i1]
    t0 = w[0]["t"]
    X = lambda t: (t - t0) / ms
    fig, ax = plt.subplots(figsize=(16, 9), dpi=100)
    fig.subplots_adjust(left=0.05, right=0.80, top=0.86, bottom=0.09)
    candles(ax, w, t0, ms)
    lo = min(b["l"] for b in w)
    hi = max(b["h"] for b in w)
    core = [x["E"], x["S"], z["top"], z["bottom"]]
    ylo, yhi = min(lo, *core), max(hi, *core)
    pad = (yhi - ylo) * 0.08
    ylo, yhi = ylo - pad, yhi + pad
    xe = X(x["t_entry"])
    xx = X(t_end) + (0 if x["t_exit"] else 0.5)
    xr = len(w) + 0.5
    xl = min(max(xx, xe + 12), xr)                       # the trade's lines: at least 12 candles long to be seen
    # the zone
    zx0 = max(X(z["t0"]), -0.5)
    ax.add_patch(Rectangle((zx0, z["bottom"]), xx - zx0, z["top"] - z["bottom"], facecolor=zc, alpha=0.16, edgecolor=zc, linewidth=1.2, zorder=1))
    ax.hlines(z["mid"], zx0, xx, colors=zc, linestyles=(0, (1, 3)), linewidth=1, alpha=0.8, zorder=1)
    zlab = f"{'Supply' if sell else 'Demand'} zone {fx(z['bottom'])} – {fx(z['top'])}  ·  base {ist(z['t0'])}" + \
           ("" if X(z["t0"]) >= -0.5 else "  (formed before this window)")
    ax.text(zx0 + 0.5, z["top"] if sell else z["bottom"], zlab, color=INK2, fontsize=8.5, va="bottom" if sell else "top", zorder=6)
    # the BOS / CHoCH the zone's move broke (TP1's level)
    if ylo <= z["level"] <= yhi:
        lx0 = max(X(z["level_t"]), -0.5)
        ax.hlines(z["level"], lx0, max(X(z["t_break"]), lx0 + 1), colors=MUTED, linestyles="--", linewidth=1, zorder=1)
        ax.text(lx0 + 0.5, z["level"], f"{z['event']} {fx(z['level'])}", color=MUTED, fontsize=8, va="bottom")
    # trade lines: entry → exit
    risk = abs(x["E"] - x["S"])
    lines = [("Entry", x["E"], ENTRY, "-", f"{'SELL' if sell else 'BUY'} {fx(x['E'])}"),
             ("SL", x["S"], SL, "-", f"SL {fx(x['S'])}  (−1R)")]
    if x["tp1"] is not None:
        lines.append(("TP1", x["tp1"], TP, "--", f"TP1 {fx(x['tp1'])}  (+{abs(x['E'] - x['tp1']) / risk:.1f}R, 50 %)"))
    lines.append(("TP2", x["tp2"], TP, "-", f"TP2 {fx(x['tp2'])}  (+{abs(x['E'] - x['tp2']) / risk:.1f}R)"))
    off = []
    for name, p, col, ls, lab in lines:
        if ylo <= p <= yhi:
            ax.hlines(p, xe, xl, colors=col, linestyles=ls, linewidth=1.6, zorder=5)
            tag(ax, xr + 0.6, p, lab, col)
        else:
            off.append((p, col, lab + ("  ↓" if p < ylo else "  ↑")))
    off.sort(key=lambda o: -abs(o[0] - (ylo + yhi) / 2))           # the farthest at the very edge
    below = [o for o in off if o[0] < ylo]
    above = [o for o in off if o[0] >= ylo]
    off = below + above
    for k, (p, col, lab) in enumerate(off):
        k = below.index((p, col, lab)) if (p, col, lab) in below else above.index((p, col, lab))
        yy = ylo + (yhi - ylo) * (0.04 + 0.05 * k) if p < ylo else yhi - (yhi - ylo) * (0.04 + 0.05 * k)
        tag(ax, xr + 0.6, yy, lab, col)
    # markers
    ax.scatter([xe], [x["E"] if sell else x["E"] - x["spread"]], marker="v" if sell else "^", s=150, color=ENTRY,
               edgecolors=BG, linewidths=1.5, zorder=9)
    if x["t_tp1"]:
        p1 = x["tp1"] - x["spread"] if sell else x["tp1"]
        ax.scatter([X(x["t_tp1"])], [p1], marker="o", s=70, color=TP, edgecolors=BG, linewidths=1.5, zorder=9)
    if x["t_exit"]:
        if x["reason"] == "SL":
            px, col = (x["S"] - x["spread"] if sell else x["S"]), SL
        elif x["reason"] == "BE":
            px, col = (x["E"] - x["spread"] if sell else x["E"]), MUTED
        else:
            px, col = (x["tp2"] - x["spread"] if sell else x["tp2"]), TP
        ax.scatter([X(x["t_exit"])], [px], marker="X", s=120, color=col, edgecolors=BG, linewidths=1.5, zorder=9)
    ax.axvline(X(x["t_touch"]), color=GRID, linewidth=1, zorder=0)
    ax.text(X(x["t_touch"]), yhi, " tap", color=MUTED, fontsize=8, va="top")
    ax.set_xlim(-1, xr + 0.5)
    ax.set_ylim(ylo, yhi)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.yaxis.tick_right()
    ax.tick_params(axis="y", labelright=False, labelleft=True)
    ticks = list(range(0, len(w), max(1, len(w) // 9)))
    ax.set_xticks(ticks, [ist(w[i]["t"]) for i in ticks])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    # header
    res = "win" if x["R"] > 1e-9 else "loss" if x["R"] < -1e-9 else "flat"
    P = x["parts"]
    usd = x.get("usd_001")
    fig.text(0.05, 0.955, f"{c.sym} {c.tf} · trade {n} of {of} · {'SELL' if sell else 'BUY'} · "
             f"{'LIMIT at the zone 50 %' if x['mode'] == 'limit' else 'CONFIRMATION (M5 BOS) entry'} · "
             f"result {x['R']:+.2f}R ({res}{'' if usd is None else f', ${usd:+.2f} at 0.01 lot'})",
             fontsize=14, fontweight="bold", color=INK)
    sc_line = (f"score {x['score']:g}/10 at the tap (return #{x['visit']}): departure {P['departure']} · base {P['time_at_base']} · "
               f"fresh {P['freshness']} · profit margin {P['margin']} · big picture {P['big_picture']} (curve {x['curve_pos']}, H4 "
               f"{ {'buy': 'up', 'sell': 'down'}.get(x['h4'], '-') })" + (" · CHoCH against −0.5" if x.get("counter_choch_t") else ""))
    if x["mode"] == "confirm" and x.get("score_at_entry") is not None:
        sc_line += f"  →  {x['score_at_entry']:g} with the real entry"
    fig.text(0.05, 0.925, sc_line, fontsize=10, color=INK2)
    fig.text(0.05, 0.897, f"tap {ist(x['t_touch'])} · entry {ist(x['t_entry'])} · "
             + (f"TP1 {ist(x['t_tp1'])} · " if x["t_tp1"] else "")
             + f"{ {'SL': 'stopped', 'BE': 'break-even stop', 'TP2': 'TP2 hit', 'open': 'still open'}[x['reason']]} {ist(x['t_exit'])}"
             f" · reward:risk to TP2 {x['rr']:.1f} · spread {x['spread']:.2f} = {x['spread'] / risk:.2f}R · best move for the trade +{x.get('mfe_R', 0):.1f}R"
             " · times IST", fontsize=10, color=INK2)
    fig.text(0.05, 0.02, "▼ / ▲ entry · ● TP1 (half closed, stop to break-even) · × exit, drawn where the bid was when the order filled "
             "(a sell's SL / TP are buys at the ask = bid + spread)", fontsize=9, color=MUTED)
    fig.savefig(path)
    plt.close(fig)


# ── the whole period ─────────────────────────────────────────────────────────

def overview_png(c: Chart, d: Dict, path: str) -> None:
    tr = d["trades"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(16, 9), dpi=100, gridspec_kw={"height_ratios": [3, 2], "hspace": 0.28})
    fig.subplots_adjust(left=0.06, right=0.97, top=0.88, bottom=0.07)
    h1 = learn.to_dicts(learn.load_bars(c.sym, "H1", 10 ** 7))
    h1 = [b for b in h1 if b["t"] >= c.bars[0]["t"]]
    T = lambda t: _dt.datetime.fromtimestamp(t / 1000, _dt.timezone.utc) + IST
    a1.plot([T(b["t"]) for b in h1], [b["c"] for b in h1], color=MUTED, linewidth=0.9)
    for k, x in enumerate(tr, 1):
        sell = x["z"]["side"] == "supply"
        col = TP if x["R"] > 1e-9 else SL if x["R"] < -1e-9 else MUTED
        a1.scatter([T(x["t_entry"])], [x["E"]], marker="v" if sell else "^", s=80, color=col, edgecolors=BG, linewidths=1.2, zorder=5)
        a1.annotate(str(k), (T(x["t_entry"]), x["E"]), xytext=(0, 9 if not sell else -13), textcoords="offset points",
                    color=INK2, fontsize=7.5, ha="center")
    a1.scatter([], [], marker="^", color=TP, label="trade won (▲ buy / ▼ sell)")
    a1.scatter([], [], marker="v", color=SL, label="trade lost")
    a1.legend(loc="upper right", frameon=False, labelcolor=INK2)
    a1.set_title(f"{c.sym} {c.tf}: every trade of the updated supply / demand rules (H1 close line, numbers = trade pictures)",
                 color=INK, fontsize=11, loc="left")
    a1.grid(color=GRID, linewidth=0.6)
    # equity in R, new rules vs the original ticket rule
    for L, col, lab in ((d["original"], MUTED, "original ticket rule (limit at the body edge, SL distal + 0.4 ATR, TP leg extreme)"),
                        (tr, ENTRY, "updated rules (score → limit at 50 % / M5 confirmation, spread-aware SL / TP, TP1 50 % + BE)")):
        done = [x for x in L if x["reason"] != "open"]
        done.sort(key=lambda x: x["t_exit"])
        eq, s = [0.0], 0.0
        ts = [T(c.bars[0]["t"])]
        for x in done:
            s += x["R"]
            eq.append(s)
            ts.append(T(x["t_exit"]))
        a2.step(ts, eq, where="post", color=col, linewidth=2, label=f"{lab}: {s:+.1f}R / {len(done)} trades")
        a2.annotate(f"{s:+.1f}R", (ts[-1], eq[-1]), xytext=(4, 0), textcoords="offset points", color=INK, fontsize=9, va="center")
    a2.axhline(0, color=GRID, linewidth=1)
    a2.set_ylabel("cumulative R")
    a2.legend(loc="lower left", frameon=False, labelcolor=INK2, fontsize=9)
    a2.grid(color=GRID, linewidth=0.6)
    for a in (a1, a2):
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    st = d["stats"]["all"]
    fig.text(0.06, 0.955, f"{c.sym} {c.tf} supply / demand backtest · {ist(d['from'], '%d %b %Y')} – {ist(d['to'], '%d %b %Y')}",
             fontsize=15, fontweight="bold")
    fig.text(0.06, 0.92, f"{d['zones']} valid zones · {d['returns']} returns to a zone · {st.get('n', 0)} trades · "
             f"{st.get('wins', 0)} won · {st.get('total_R', 0):+.1f}R · spread {d['spread_rel'] * 1e4:.1f} bps of price", fontsize=11, color=INK2)
    fig.savefig(path)
    plt.close(fig)


def summary_png(d: Dict, others: Dict[str, Dict], path: str) -> None:
    fig = plt.figure(figsize=(16, 9), dpi=100)
    S = d["stats"]
    fig.text(0.04, 0.95, f"{d['sym']} {d['tf']} — updated supply / demand rules: what was tested and the result",
             fontsize=16, fontweight="bold")
    rules = [
        "Source: Drive › Trade › Crypto strategy › “ETH/USD Supply Zone Setup Evaluation” (31 Oct 2026)",
        "Zones: the VALID supply / demand zones of the /smc chart (supply_demand.py, origin boxes) — your doc's zone 2269.01–2284.38 is one of them",
        f"Score 0–10 (OTA odds enhancers, 2 pts each): departure · time at base · freshness · profit margin (RR to TP2) · big picture (curve + H4)",
        f"   − 0.5 when a CHoCH against the zone closed on {d['tf']}.   ≥ {LIMIT_SCORE:g} → LIMIT at the zone 50 %   ·   {CONFIRM_SCORE:g}–8.5 → wait for an M5 close beyond the latest M5 swing   ·   < {CONFIRM_SCORE:g} → no trade",
        f"Stop: beyond the distal (limit) / the M5 rejection extreme (confirmation) + {SL_BUF_ATR:g} ATR + the spread on a sell (bid / ask, as the doc says)",
        f"Targets: TP1 = 50 % at the BOS the zone's move broke, then stop to break-even;  TP2 = the move's extreme (leg low / high), front-run {TP_CUSHION_ATR:g} ATR + spread",
        f"Added (not in the doc): reward:risk ≥ 2 (your test profile) · a confirmation more than 1 ATR from the zone = ran away (missed) · M5 BOS within 36 M5 candles (V5)",
        f"Fills on M5 candles; a candle that touches stop and target counts the stop; spread {d['spread_rel'] * 1e4:.1f} bps of price (FxPro's median ETH spread 4.44)",
    ]
    for k, r in enumerate(rules):
        fig.text(0.04, 0.89 - k * 0.033, r, fontsize=10.2, color=INK2 if k else INK)
    # results table
    rows = [("updated rules — all", S["all"]), ("   limit entries (score ≥ 9)", S["limit"]), ("   M5 confirmation entries", S["confirm"]),
            ("   sells (supply)", S["sell"]), ("   buys (demand)", S["buy"]), ("original ticket rule (doc's “D-” order)", S["original"])]
    for tf, o in others.items():
        rows.append((f"same rules on {d['sym']} {tf}", o["stats"]["all"]))
    head = ["", "trades", "won", "win %", "total R", "avg R", "profit factor", "max drawdown R"]
    y0 = 0.58
    xs = [0.04, 0.36, 0.43, 0.49, 0.56, 0.64, 0.72, 0.83]
    for x, h in zip(xs, head):
        fig.text(x, y0, h, fontsize=10.5, color=MUTED, fontweight="bold")
    for k, (name, s) in enumerate(rows):
        y = y0 - 0.04 * (k + 1)
        vals = [name, str(s.get("n", 0)), str(s.get("wins", 0)), f"{100 * s.get('win_rate', 0):.0f} %", f"{s.get('total_R', 0):+.1f}",
                f"{s.get('avg_R', 0):+.2f}", "-" if s.get("pf") is None else f"{s['pf']:.2f}", f"{s.get('max_dd_R', 0):.1f}"]
        for j, (x, v) in enumerate(zip(xs, vals)):
            col = INK if j == 0 or j < 4 else (TP if j == 4 and s.get("total_R", 0) > 0 else SL if j == 4 else INK)
            fig.text(x, y, v, fontsize=10.5, color=col if j == 4 else INK)
    yb = y0 - 0.04 * (len(rows) + 1) - 0.02
    why = ", ".join(f"{v} {k}" for k, v in d["skip_why"].items())
    fig.text(0.04, yb, f"Returns not traded ({sum(d['skip_why'].values())}): {why}", fontsize=9.5, color=INK2, wrap=True)
    a = S["all"]
    if a.get("n"):
        notes = [f"What the {a['n']} trades did: {a['mfe_1R']} moved +1R in the trade's favour before their exit, {a['mfe_2R']} reached +2R, {a['mfe_3R']} reached +3R —",
                 f"but TP1 (the broken BOS) sat a median {a['tp1_R_median']}R away and TP2 (the leg extreme) {a['tp2_R_median']}R away, so the far targets were almost never reached.",
                 f"{a['stopped_on_fill_candle']} of {S['limit'].get('n', 0)} limit orders filled and stopped on the same M5 candle: price ran straight through the zone.",
                 "The stops are tight (zone height + 0.2 ATR); the spread alone is 0.2–0.6R of every trade."]
        for k, t in enumerate(notes):
            fig.text(0.04, yb - 0.06 - k * 0.032, t, fontsize=10.5, color=INK)
    fig.savefig(path)
    plt.close(fig)


# ── the zone of the doc, now ─────────────────────────────────────────────────

def live_png(c: Chart, path: str) -> Dict:
    """the newest live supply / demand zone of the chart (the doc's 2269.01-2284.38 on ETHEREUM M30) and what the
    updated rules would do at its first return, scored with the data up to now"""
    zs = [z for z in supply_demand.zones(c.bars, c.m) if z.get("valid") and z.get("live") and z.get("role", "").startswith("origin")]
    last = c.bars[-1]
    price = last["c"]
    near = sorted(zs, key=lambda z: abs(z["mid"] - price))[:1]
    if not near:
        return {}
    z = near[0]
    sell = z["side"] == "sell"
    now = c.close_t[-1]
    k = len(c.T5)
    a = c.atr_at(now)
    s = c.spread(z["proximal"])
    legext = leg_extreme(c, z, k)
    level = c.m["events"][z["event"]]["level"]
    pl = plan_levels(c, z, z["side"], z["mid"], z["distal"], legext, level, a, s)
    sc = score(c, z, z["touches"] + 1, now, pl["rr"])
    mode = "LIMIT at the zone 50 %" if sc["score"] >= LIMIT_SCORE and not sc["counter_choch_t"] else \
        "CONFIRMATION: no resting order — on the tap wait for an M5 close beyond the latest M5 swing" if sc["score"] >= CONFIRM_SCORE else "NO TRADE"
    i0 = max(0, len(c.bars) - 150)
    w = c.bars[i0:]
    t0 = w[0]["t"]
    ms = c.ms
    X = lambda t: (t - t0) / ms
    fig, ax = plt.subplots(figsize=(16, 9), dpi=100)
    fig.subplots_adjust(left=0.05, right=0.74, top=0.82, bottom=0.07)
    candles(ax, w, t0, ms)
    zc = SUPPLY if sell else DEMAND
    xr = len(w) + 0.5
    zx0 = max(X(z["t0"]), -0.5)
    ax.add_patch(Rectangle((zx0, z["bottom"]), xr - zx0, z["top"] - z["bottom"], facecolor=zc, alpha=0.16, edgecolor=zc, linewidth=1.2))
    ax.hlines(z["mid"], zx0, xr, colors=zc, linestyles=(0, (1, 3)), linewidth=1)
    ax.hlines(z["entry"], zx0, xr, colors=MUTED, linestyles=(0, (2, 3)), linewidth=1)
    ax.text(zx0 + 0.5, z["top"] if sell else z["bottom"], f"{'Supply' if sell else 'Demand'} zone {fx(z['bottom'])} – {fx(z['top'])} · base {ist(z['t0'])} IST",
            color=INK2, fontsize=9, va="bottom" if sell else "top")
    tp1 = pl["tp1"]
    levels = [(pl["S"], SL, f"SL (limit case) {fx(pl['S'])}"),
              (z["mid"], ENTRY, f"zone 50 % {fx(z['mid'])}" + (" = limit" if mode.startswith("LIMIT") else " (no limit: score < 9)")),
              (z["entry"], MUTED, f"old order {fx(z['entry'])}: cancel")]
    if tp1 is not None:
        levels.append((tp1, TP, f"TP1 {fx(tp1)} · 50 % (BOS {fx(level)})"))
    levels.append((pl["tp2"], TP, f"TP2 {fx(pl['tp2'])} (leg {'low' if sell else 'high'} {fx(legext)})"))
    lo = min(min(b["l"] for b in w), pl["tp2"])
    hi = max(max(b["h"] for b in w), pl["S"])
    pad = (hi - lo) * 0.05
    ys = []
    for p, col, lab in levels:
        ax.hlines(p, len(w) - 25, xr, colors=col, linewidth=1.4, linestyles="-" if col != MUTED else (0, (2, 3)))
        yy = p
        for q in ys:                                     # keep the tags apart (the old order sits 6 below the 50 %)
            if abs(yy - q) < (hi - lo) * 0.035:
                yy = q - (hi - lo) * 0.035
        ys.append(yy)
        tag(ax, xr + 0.6, yy, lab, col)
    ax.set_xlim(-1, xr + 0.5)
    ax.set_ylim(lo - pad, hi + pad)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ticks = list(range(0, len(w), max(1, len(w) // 9)))
    ax.set_xticks(ticks, [ist(w[i]["t"]) for i in ticks])
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    P = sc["parts"]
    fig.text(0.05, 0.955, f"{c.sym} {c.tf} now ({ist(now)} IST, last close {fx(price)}): the doc's zone under the updated rules",
             fontsize=14, fontweight="bold")
    fig.text(0.05, 0.922, f"score {sc['score']:g}/10 for the first return: departure {P['departure']} · base {P['time_at_base']} · fresh {P['freshness']} · "
             f"profit margin {P['margin']} (RR {pl['rr']:.1f} for a 50 % limit) · big picture {P['big_picture']} (curve {sc['curve_pos']}, H4 "
             f"{ {'buy': 'up', 'sell': 'down'}.get(sc['h4'], '-') })" + (" · CHoCH against −0.5" if sc["counter_choch_t"] else ""),
             fontsize=10.5, color=INK2)
    fig.text(0.05, 0.89, f"→ {mode}.", fontsize=10.5, color=INK)
    fig.text(0.05, 0.862, f"   SL then = the M5 rejection {'high' if sell else 'low'}{' + spread' if sell else ''} + {SL_BUF_ATR:g} ATR; "
             f"TP1 / TP2 as drawn{' (a sell’s SL / TP are buys at the ask, so the spread is inside them)' if sell else ''}.",
             fontsize=10.5, color=INK2)
    fig.savefig(path)
    plt.close(fig)
    return {"zone": [z["bottom"], z["top"]], "score": sc["score"], "parts": P, "mode": mode, "limit": z["mid"], "sl": pl["S"],
            "tp1": tp1, "tp2": pl["tp2"], "rr": pl["rr"], "legext": legext, "level": level, "curve": sc["curve_pos"], "h4": sc["h4"]}


def write_csv(d: Dict, path: str) -> None:
    cols = ["n", "side", "mode", "visit", "score", "zone_bottom", "zone_top", "tap_ist", "entry_ist", "entry", "sl", "tp1", "tp2", "rr_tp2",
            "tp1_ist", "exit_ist", "result", "R", "usd_0.01lot"]
    with open(path, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(cols)
        for k, x in enumerate(d["trades"], 1):
            z = x["z"]
            wr.writerow([k, "SELL" if z["side"] == "supply" else "BUY", x["mode"], x["visit"], x["score"], z["bottom"], z["top"],
                         ist(x["t_touch"], "%Y-%m-%d %H:%M"), ist(x["t_entry"], "%Y-%m-%d %H:%M"), round(x["E"], 2), round(x["S"], 2),
                         "" if x["tp1"] is None else round(x["tp1"], 2), round(x["tp2"], 2), round(x["rr"], 2),
                         ist(x["t_tp1"], "%Y-%m-%d %H:%M") if x["t_tp1"] else "", ist(x["t_exit"], "%Y-%m-%d %H:%M"), x["reason"], x["R"], x.get("usd_001")])


def main() -> int:
    ap = argparse.ArgumentParser(description="pictures of an sd_backtest run")
    ap.add_argument("sym")
    ap.add_argument("tf", nargs="?", default="M30")
    ap.add_argument("--others", default="M15,H1", help="other timeframes whose saved runs go into the summary table")
    a = ap.parse_args()
    with open(os.path.join(OUT_DIR, f"{a.sym}_{a.tf}.json")) as f:
        d = json.load(f)
    others = {}
    for tf in [t for t in a.others.split(",") if t and t != a.tf]:
        try:
            with open(os.path.join(OUT_DIR, f"{a.sym}_{tf}.json")) as f:
                others[tf] = json.load(f)
        except FileNotFoundError:
            pass
    c = Chart(a.sym, a.tf)
    out = os.path.join(OUT_DIR, f"{a.sym}_{a.tf}")
    os.makedirs(out, exist_ok=True)
    for old in os.listdir(out):
        if old.endswith(".png"):
            os.remove(os.path.join(out, old))
    pages = [os.path.join(out, "00_summary.png"), os.path.join(out, "01_overview.png")]
    summary_png(d, others, pages[0])
    overview_png(c, d, pages[1])
    tr = d["trades"]
    for k, x in enumerate(tr, 1):
        p = os.path.join(out, f"trade_{k:02d}_{ist(x['t_entry'], '%Y%m%d_%H%M')}_{'sell' if x['z']['side'] == 'supply' else 'buy'}_"
                              f"{x['mode']}_{x['R']:+.2f}R.png")
        trade_png(c, x, k, len(tr), p)
        pages.append(p)
    live = live_png(c, os.path.join(out, "99_live_setup.png"))
    pages.append(os.path.join(out, "99_live_setup.png"))
    write_csv(d, os.path.join(out, "trades.csv"))
    with PdfPages(os.path.join(out, f"{a.sym}_{a.tf}_sd_backtest.pdf")) as pdf:
        for p in pages:
            img = plt.imread(p)
            fig = plt.figure(figsize=(16, 9), dpi=100)
            fig.figimage(img, 0, 0)
            pdf.savefig(fig)
            plt.close(fig)
    with open(os.path.join(out, "live.json"), "w") as f:
        json.dump(live, f, indent=1)
    print(out, len(pages), "pages")
    print(json.dumps(live, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
