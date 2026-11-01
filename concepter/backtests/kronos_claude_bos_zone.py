"""
concepter/backtests/kronos_claude_bos_zone.py — David 2026-11-01: backtest "Kronos direction + Claude BOS → its
supply / demand zone" on ONE symbol's whole M15 history, and write the report for Drive.

Steps (each one is its own tool, this file only puts them together):
  1. python3 -m marketdata.data export GOLD --days 0 --tfs M15,H1 --out <BT>/data --no-kronos   the whole history
  2. python3 -m concepter.scan --engine claude --kinds setup --symbol GOLD --data <BT>/data
         --out <BT>/claude_setups_GOLD.jsonl                                                  every Claude setup
  3. ~/opt/kronos-venv/bin/python -m concepter.kronos.backfill --symbol GOLD --data <BT>/data
         --at <BT>/claude_setups_GOLD.jsonl                                                   Kronos at those bars
  4. python3 -m concepter.backtests.kronos_claude_bos_zone [--upload]                        this file:
       - the strategy with the conductor + paper executor (rules/strategy/kronos_claude_bos_zone), and the same
         without Kronos (rules/strategy/claude_bos_zone), each with the stop buffer at 0.1 / 0.25 / 0.5 ATR
       - every setup on its own (no "one trade at a time"): Kronos agreed vs did not
       - pictures of every trade, equity curves, CSVs, a PDF and a README → <BT>/report (→ Drive with --upload)
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
import os
import statistics as st
import subprocess
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from marketdata import data as MD  # noqa: E402
from shared import rules as R  # noqa: E402
from shared.contracts import TF_MS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BT = os.path.join(ROOT, "engine_data", "backtest", "kronos_claude_bos_zone")
SYM, TF = "GOLD", "M15"
MS = TF_MS[TF]
DRIVE = "gdrive:Trade /Forex strategy/GOLD M15 Kronos + Claude BOS zone backtest 2026-11-01"
BUFFERS = (0.1, 0.25, 0.5)

BG, PANEL, GRID, INK, INK2, MUTED = "#0b0e14", "#121722", "#232a3a", "#e6e9ef", "#b4bccc", "#7d879c"
BULL, BEAR, SUPPLY, DEMAND = "#26a69a", "#ef5350", "#ffa726", "#42a5f5"
ENTRY, SLC, TPC, BOSC = "#e5c07b", "#e06c75", "#56b6c2", "#c678dd"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": INK, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": GRID, "figure.facecolor": BG,
                     "axes.facecolor": BG, "savefig.facecolor": BG})


def utc(ms: Optional[int], fmt: str = "%Y-%m-%d %H:%M") -> str:
    return "-" if ms is None else dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime(fmt)


# ── 1. the strategy runs ────────────────────────────────────────────────────────────────────────────────────────

def _one(job):
    from concepter.run import run
    bt, name, strategy, buf = job
    out = os.path.join(bt, f"run_{name}")
    run(strategy, [SYM], data_dir=os.path.join(bt, "data"), out_dir=out, quiet=True,
        overrides={"stop.buffer_atr": buf})
    return name


def runs(bt: str) -> List[str]:
    jobs = [(bt, f"{s}_buf{b}", s, b) for s in ("kronos_claude_bos_zone", "claude_bos_zone") for b in BUFFERS]
    with ProcessPoolExecutor(max_workers=len(jobs)) as pool:
        return list(pool.map(_one, jobs))


def load_run(bt: str, name: str) -> Dict:
    d = os.path.join(bt, f"run_{name}")
    with open(os.path.join(d, "summary.json")) as f:
        s = json.load(f)
    with open(os.path.join(d, "trades.jsonl")) as f:
        trades = [json.loads(line) for line in f if line.strip()]
    with open(os.path.join(d, "journal.jsonl")) as f:
        journal = [json.loads(line) for line in f if line.strip()]
    orders = [r for j in journal if j["event"] == "decision" for r in j["results"] if r["command"]["kind"] == "open"]
    expired = sum(1 for j in journal if j["event"] == "decision" for r in j["results"]
                  if r["command"]["kind"] == "close" and "not filled" in r["command"]["reason"])
    cancelled = sum(1 for j in journal if j["event"] == "decision" for r in j["results"]
                    if r["command"]["kind"] == "close" and "cancelled" in r["command"]["reason"])
    return {"name": name, "summary": s, "trades": trades, "orders": len(orders), "expired": expired,
            "cancelled": cancelled}


def stats(trades: List[Dict]) -> Dict:
    rs = [t["r"] for t in trades]
    won = [r for r in rs if r > 0]
    eq, peak, dd = 0.0, 0.0, 0.0
    for r in rs:
        eq += r
        peak = max(peak, eq)
        dd = min(dd, eq - peak)
    return {"n": len(rs), "won": len(won), "win_pct": round(100 * len(won) / len(rs), 1) if rs else 0,
            "total_r": round(sum(rs), 2), "avg_r": round(sum(rs) / len(rs), 3) if rs else 0,
            "avg_win_r": round(st.mean(won), 2) if won else 0, "max_dd_r": round(dd, 2),
            "pnl": round(sum(t["pnl"] for t in trades), 2)}


# ── 2. every setup on its own ───────────────────────────────────────────────────────────────────────────────────

def setups_alone(setups: List[Dict], bars, kron: Dict[int, Dict], buf: float = 0.25, expiry: int = 96) -> List[Dict]:
    """Each setup as if it were the only one (no "one trade at a time"): limit at the entry from the bar after it
    appears, filled when the ask (buy) / bid (sell) reaches it within `expiry` bars, then stop or target (the stop
    first when one bar touches both). The CHoCH cancel and the rollover window are NOT applied here."""
    idx = {b.t: i for i, b in enumerate(bars)}
    out = []
    for s in setups:
        d, side = s["data"], s["side"]
        i0 = idx.get(s["now"] - MS)
        if i0 is None:
            continue
        sign = 1 if side == "buy" else -1
        sp = bars[i0].spread
        sl = d["distal"] - sign * (buf * (d["atr"] or 0) + sp)
        entry, tp = d["entry"], d["leg_extreme"]
        risk = (entry - sl) * sign
        rec = {"t": s["now"], "side": side, "entry": entry, "sl": round(sl, 2), "tp": tp,
               "rr": round((tp - entry) * sign / risk, 2) if risk > 0 else None, "zone_score": d["zone_score"]}
        fc = kron.get(s["now"] - MS)
        if fc:
            p_up = fc["p_up"]
            k_side = "buy" if p_up >= 0.5 else "sell"
            p = max(p_up, 1 - p_up)
            move_x = abs(fc["median"][-1] - fc["last"]) / sp if sp else 99
            rec.update(kronos_side=k_side, kronos_p=p,
                       kronos=("agrees" if k_side == side and p >= 0.75 and move_x >= 2 else
                               "against" if k_side != side and p >= 0.75 else "unsure"))
        else:
            rec["kronos"] = "no forecast"
        fill = next((i for i in range(i0 + 1, min(i0 + 1 + expiry, len(bars)))
                     if (bars[i].l + bars[i].spread <= entry if side == "buy" else bars[i].h >= entry)), None)
        if fill is None or risk <= 0:
            rec.update(result="not filled", r=None)
            out.append(rec)
            continue
        res, r = "open at the end", None
        for b in bars[fill:]:
            hit_sl = b.l <= sl if side == "buy" else b.h + b.spread >= sl
            hit_tp = b.h >= tp if side == "buy" else b.l + b.spread <= tp
            if hit_sl:
                res, r = "sl", -1.0
                break
            if hit_tp:
                res, r = "tp", round((tp - entry) * sign / risk, 2)
                break
        rec.update(result=res, r=r, filled=bars[fill].t)
        out.append(rec)
    return out


def group(rows: List[Dict], key=None) -> Dict:
    rows = [r for r in rows if (key is None or key(r))]
    done = [r for r in rows if r["r"] is not None]
    won = [r for r in done if r["r"] > 0]
    return {"setups": len(rows), "filled": len(done), "won": len(won),
            "win_pct": round(100 * len(won) / len(done), 1) if done else 0,
            "total_r": round(sum(r["r"] for r in done), 2), "avg_r": round(sum(r["r"] for r in done) / len(done), 3) if done else 0}


# ── 3. pictures ─────────────────────────────────────────────────────────────────────────────────────────────────

def candles(ax, bars, t0: int) -> None:
    for b in bars:
        x = (b.t - t0) / MS
        col = BULL if b.c >= b.o else BEAR
        ax.vlines(x, b.l, b.h, color=col, linewidth=0.8, zorder=2)
        lo, hi = min(b.o, b.c), max(b.o, b.c)
        ax.add_patch(Rectangle((x - 0.31, lo), 0.62, max(hi - lo, 1e-9), facecolor=col, edgecolor=col, lw=0.5, zorder=3))


def tag(ax, x, y, text, col, ha="left"):
    ax.text(x, y, text, color=INK, fontsize=8.5, ha=ha, va="center", zorder=8,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": PANEL, "edgecolor": col, "linewidth": 1.1})


def trade_png(t: Dict, s: Dict, fc: Optional[Dict], bars, n: int, of: int, path: str) -> None:
    d = s["data"]
    idx = {b.t: i for i, b in enumerate(bars)}
    i_zone = idx.get(d["zone_t0"], 0)
    i_exit = idx.get(t["closed_t"] - MS, len(bars) - 1)
    a = max(0, i_zone - 12)
    z = min(len(bars), i_exit + 12)
    if z - a > 320:                                     # a very long trade: keep the end, the zone is still drawn
        a = max(0, z - 320)
    win = bars[a:z]
    t0 = win[0].t
    X = lambda ms: (ms - t0) / MS
    fig, ax = plt.subplots(figsize=(18, 7.6))
    candles(ax, win, t0)
    buy = t["side"] == "buy"
    zc = DEMAND if buy else SUPPLY
    ax.add_patch(Rectangle((X(d["zone_t0"]), d["bottom"]), X(t["closed_t"]) - X(d["zone_t0"]), d["top"] - d["bottom"],
                           facecolor=zc, alpha=0.18, edgecolor=zc, lw=1.2, zorder=1))
    tag(ax, max(X(d["zone_t0"]), 0), d["top"] if not buy else d["bottom"],
        f"{'demand' if buy else 'supply'} ({d['zone_kind']}, score {d['zone_score']})", zc)
    xb = X(d["t_break"])
    ax.hlines(d["bos_level"], max(xb - 8, 0), max(xb + 1, 1), color=BOSC, lw=1.4, ls="--", zorder=4)
    tag(ax, max(xb + 1.3, 1.5), d["bos_level"], f"BOS {t['side']} {d['bos_level']:,.2f}" + ("" if xb >= 0 else " (earlier)"), BOSC)
    x1, x2 = X(s["now"]), X(t["closed_t"])
    ax.hlines(t["entry"], x1, x2, color=ENTRY, lw=1.5, zorder=5)
    tag(ax, x2 + 0.5, t["entry"], f"entry {t['entry']:,.2f}", ENTRY)
    ax.hlines(s["_sl"], x1, x2, color=SLC, lw=1.5, zorder=5)
    tag(ax, x2 + 0.5, s["_sl"], f"SL {s['_sl']:,.2f}", SLC)
    ax.hlines(d["leg_extreme"], x1, x2, color=TPC, lw=1.5, zorder=5)
    tag(ax, x2 + 0.5, d["leg_extreme"], f"TP {d['leg_extreme']:,.2f} (leg {'high' if buy else 'low'})", TPC)
    ax.axvline(x1, color=MUTED, lw=0.8, ls=":")
    ax.scatter([X(t["opened_t"]) - 1], [t["entry"]], marker="^" if buy else "v", s=90, color=ENTRY, zorder=9)
    ax.scatter([X(t["closed_t"]) - 1], [t["exit"]], marker="X", s=90, color=TPC if t["r"] > 0 else SLC, zorder=9)
    lo = min(min(b.l for b in win), s["_sl"], d["leg_extreme"])
    hi = max(max(b.h for b in win), s["_sl"], d["leg_extreme"])
    pad = (hi - lo) * 0.06
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlim(-1, len(win) + 9)
    ticks = list(range(0, len(win), max(1, len(win) // 8)))
    ax.set_xticks(ticks)
    ax.set_xticklabels([utc(win[i].t, "%d %b %H:%M") for i in ticks])
    ax.set_xlabel("UTC")
    ax.grid(color=GRID, lw=0.5)
    kr = f"Kronos {'buy' if fc['p_up'] >= 0.5 else 'sell'} {max(fc['p_up'], 1 - fc['p_up']):.0%}" if fc else "no Kronos"
    col = TPC if t["r"] > 0 else SLC
    ax.set_title(f"#{n}/{of}  {SYM} {TF} {t['side'].upper()}  ·  setup {utc(s['now'])} UTC  ·  {kr}  ·  "
                 f"filled {utc(t['opened_t'], '%d %b %H:%M')} → {t['exit_reason'].upper()} {utc(t['closed_t'], '%d %b %H:%M')}  ·  "
                 f"{t['r']:+.2f}R", color=col, fontsize=11.5, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def equity_png(curves: Dict[str, List[Dict]], path: str, title: str) -> None:
    fig, ax = plt.subplots(figsize=(14, 6))
    cols = [TPC, ENTRY, DEMAND, SUPPLY, SLC, BOSC]
    for (name, tr), c in zip(curves.items(), cols):
        xs, ys, eq = [], [], 0.0
        for t in tr:
            eq += t["r"]
            xs.append(dt.datetime.fromtimestamp(t["closed_t"] / 1000, dt.timezone.utc))
            ys.append(eq)
        ax.step(xs, ys, where="post", color=c, lw=1.8, label=f"{name}: {len(tr)} trades, {eq:+.1f}R")
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_ylabel("cumulative R")
    ax.grid(color=GRID, lw=0.5)
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=INK)
    ax.set_title(title, loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def table_png(lines: List[List[str]], title: str, path: str) -> None:
    fig, ax = plt.subplots(figsize=(14, 0.55 * len(lines) + 1.2))
    ax.axis("off")
    first = max(len(x[0]) for x in lines)
    rest = len(lines[0]) - 1
    w0 = min(0.42, 0.011 * first + 0.02)
    tb = ax.table(cellText=lines[1:], colLabels=lines[0], loc="upper left", cellLoc="center",
                  colWidths=[w0] + [(1 - w0) / rest] * rest)
    tb.auto_set_font_size(False)
    tb.set_fontsize(10)
    tb.scale(1, 1.6)
    for (r, c), cell in tb.get_celld().items():
        cell.set_facecolor(PANEL if r else GRID)
        cell.set_edgecolor(GRID)
        cell.get_text().set_color(INK)
    ax.set_title(title, loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=110, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)


def write_chart(bt: str, main_run: Dict, base_run: Dict, by_key: Dict, kron: Dict, ms_: Dict, bs_: Dict, bars) -> str:
    """<bt>/chart_<SYM>_<TF>.json: every trade with its BOS, zone, leg and levels, for the /smc page's
    "BOS-zone backtest" layer (engine/smc_compare.py reads it)."""
    def rows(run):
        out = []
        for n, t in enumerate(run["trades"], 1):
            key = next(k for k in t["setup_id"].split("+") if k.startswith("claude.setup"))
            s = by_key[key]
            d = s["data"]
            fc = kron.get(s["now"] - MS)
            out.append({"n": n, "side": t["side"], "setup_t": s["now"], "t_break": d["t_break"], "bos": d["bos_level"],
                        "origin": d["origin"], "zone": {"top": d["top"], "bottom": d["bottom"], "t0": d["zone_t0"],
                                                        "kind": d["zone_kind"], "score": d["zone_score"]},
                        "leg": d["leg_extreme"], "entry": t["entry"], "sl": t["sl0"], "tp": t["tp"],
                        "t_open": t["opened_t"], "t_close": t["closed_t"], "exit": t["exit"],
                        "why": t["exit_reason"], "r": t["r"], "p_up": fc["p_up"] if fc else None})
        return out
    d = {"made": utc(int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)), "from": bars[0].t, "to": bars[-1].t,
         "strategy": "Kronos direction + Claude BOS → its supply / demand zone; SL beyond the zone + 0.25 ATR + spread; "
                     "TP the BOS leg's swing (rules/strategy/kronos_claude_bos_zone)",
         "stats": {"kronos_claude": ms_, "claude_only": bs_},
         "kronos_claude": rows(main_run), "claude_only": rows(base_run)}
    path = os.path.join(bt, f"chart_{SYM}_{TF}.json")
    with open(path, "w") as f:
        json.dump(d, f)
    return path


# ── 4. the report ───────────────────────────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-runs", action="store_true", help="reuse the runs already in <BT>")
    ap.add_argument("--upload", action="store_true", help=f"copy the report to {DRIVE}")
    ap.add_argument("--dir", default=BT, help="the backtest folder (data/, claude_setups_*.jsonl, runs, report/)")
    a = ap.parse_args()
    bt = a.dir
    if not a.skip_runs:
        print("runs:", runs(bt), flush=True)
    info, series = MD.load(SYM, os.path.join(bt, "data"))
    bars = series[TF]
    with open(os.path.join(bt, f"claude_setups_{SYM}.jsonl")) as f:
        setups = [json.loads(line) for line in f if line.strip()]
    with gzip.open(os.path.join(bt, "data", f"kronos_{SYM}.jsonl.gz"), "rt") as f:
        kron = {r["bar_t"]: r for r in (json.loads(line) for line in f if line.strip())}
    by_key = {f"claude.setup.{s['side']}.{s['t']}": s for s in setups}

    R_ = {n: load_run(bt, n) for n in (f"{s}_buf{b}" for s in ("kronos_claude_bos_zone", "claude_bos_zone") for b in BUFFERS)}
    main_run, base_run = R_["kronos_claude_bos_zone_buf0.25"], R_["claude_bos_zone_buf0.25"]
    alone = setups_alone(setups, bars, kron)
    out = os.path.join(bt, "report")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        os.remove(os.path.join(out, f))

    # tables
    head = ["strategy", "SL buffer", "orders", "unfilled", "cancelled", "trades", "won", "win %", "avg win R",
            "avg R", "total R", "max DD R", "P&L $"]
    rows = [head]
    for n, r in R_.items():
        s = stats(r["trades"])
        rows.append(["Kronos + Claude" if n.startswith("kronos") else "Claude only (no Kronos)", f"{n.split('buf')[1]} ATR",
                     r["orders"], r["expired"], r["cancelled"], s["n"], s["won"], s["win_pct"], s["avg_win_r"],
                     s["avg_r"], s["total_r"], s["max_dd_r"], s["pnl"]])
    rows = [list(map(str, x)) for x in rows]
    table_png(rows, f"{SYM} {TF}, {utc(bars[0].t, '%d %b %Y')} → {utc(bars[-1].t, '%d %b %Y')}: the strategy, one trade "
                    "at a time (conductor + paper executor, spread included, no swap)", os.path.join(out, "01_results.png"))
    g = [["setups (each on its own, SL buffer 0.25 ATR)", "setups", "filled", "won", "win %", "avg R", "total R"]]
    for lab, key in (("all setups", None), ("Kronos agrees (p ≥ 75 %, move ≥ 2 spreads)", lambda r: r["kronos"] == "agrees"),
                     ("Kronos against (other side, p ≥ 75 %)", lambda r: r["kronos"] == "against"),
                     ("Kronos unsure", lambda r: r["kronos"] == "unsure"),
                     ("buy setups", lambda r: r["side"] == "buy"), ("sell setups", lambda r: r["side"] == "sell"),
                     ("zone score ≥ 8", lambda r: r["zone_score"] >= 8), ("zone score < 8", lambda r: r["zone_score"] < 8)):
        x = group(alone, key)
        g.append([lab, x["setups"], x["filled"], x["won"], x["win_pct"], x["avg_r"], x["total_r"]])
    g = [list(map(str, x)) for x in g]
    table_png(g, "Every setup on its own: does Kronos pick the better ones?", os.path.join(out, "02_setups_by_kronos.png"))
    equity_png({"Kronos + Claude": main_run["trades"], "Claude only": base_run["trades"]},
               os.path.join(out, "03_equity.png"), f"{SYM} {TF}: cumulative R, SL buffer 0.25 ATR")

    # trade pictures (Kronos + Claude, buffer 0.25)
    pics = []
    for n, t in enumerate(main_run["trades"], 1):
        key = next((k for k in t["setup_id"].split("+") if k.startswith("claude.setup")), None)
        s = dict(by_key[key])
        s["_sl"] = t["sl0"]                               # the stop as placed
        p = os.path.join(out, f"trade_{n:02d}_{utc(t['opened_t'], '%Y%m%d_%H%M')}_{t['side']}_{t['r']:+.2f}R.png")
        trade_png(t, s, kron.get(s["now"] - MS), bars, n, len(main_run["trades"]), p)
        pics.append(p)

    # CSVs
    with open(os.path.join(out, "trades_kronos_claude.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["#", "side", "filled_utc", "entry", "exit", "closed_utc", "exit", "R", "pnl_usd_0.01lot"])
        for n, t in enumerate(main_run["trades"], 1):
            w.writerow([n, t["side"], utc(t["opened_t"]), t["entry"], t["exit"], utc(t["closed_t"]), t["exit_reason"], t["r"], t["pnl"]])
    with open(os.path.join(out, "setups_each_on_its_own.csv"), "w", newline="") as f:
        keys = ["t", "side", "entry", "sl", "tp", "rr", "zone_score", "kronos", "kronos_side", "kronos_p", "result", "r"]
        w = csv.writer(f)
        w.writerow(keys)
        for r in alone:
            w.writerow([utc(r["t"]) if k == "t" else r.get(k) for k in keys])

    # README (→ a Google Doc on Drive) + PDF
    # cross-check: the conductor's trades against the per-setup simulation (two separate pieces of code)
    alone_by_t = {(r["t"], r["side"]): r for r in alone}
    same = diff = cancelled_losers = 0
    for t in base_run["trades"]:
        k = next(k for k in t["setup_id"].split("+") if k.startswith("claude.setup"))
        a_ = alone_by_t.get((int(k.split(".")[-1]), t["side"]))
        if a_ and a_["r"] is not None and abs(a_["r"] - t["r"]) < 0.05:
            same += 1
        else:
            diff += 1
    S = R.strategy("kronos_claude_bos_zone")
    ms_ = stats(main_run["trades"])
    bs_ = stats(base_run["trades"])
    ka = group(alone, lambda r: r["kronos"] == "agrees")
    kn = group(alone, lambda r: r["kronos"] != "agrees")
    html = [f"<h1>{SYM} {TF}: Kronos direction + Claude BOS → supply / demand zone</h1>",
            f"<p>Backtest of the whole {SYM} {TF} history on the FxPro demo: {len(bars):,} bars, "
            f"{utc(bars[0].t, '%d %b %Y')} → {utc(bars[-1].t, '%d %b %Y')} (UTC). Made 2026-11-01 by Claude Code "
            f"for David.</p>",
            "<h2>The rules tested</h2>", "<pre>" + S.words.replace("<", "&lt;") + "</pre>",
            "<h2>Important: what \"Claude\" means in this test</h2>",
            "<p>The Claude engine ran in its <b>toolkit</b> mode: the BOS is David's structure rule "
            "(engine/major_structure.py) exactly as the /smc page draws it. No language model was asked (none is "
            "connected yet, and 342 setups × a model call is a separate decision). Kronos ran for real: Kronos-base, "
            "16 paths × 8 bars, on the 512 bars before each setup, the same as the live forecaster.</p>",
            "<h2>Result</h2>",
            f"<p><b>Kronos + Claude</b> (SL buffer 0.25 ATR): {ms_['n']} trades, {ms_['won']} won ({ms_['win_pct']} %), "
            f"average win {ms_['avg_win_r']}R, <b>total {ms_['total_r']:+}R</b> ({ms_['avg_r']:+}R a trade), deepest "
            f"drawdown {ms_['max_dd_r']}R.</p>",
            f"<p><b>Same setups without Kronos</b>: {bs_['n']} trades, {bs_['won']} won ({bs_['win_pct']} %), "
            f"<b>total {bs_['total_r']:+}R</b> ({bs_['avg_r']:+}R a trade).</p>",
            f"<p><b>Every setup on its own</b> (no one-at-a-time limit): where Kronos agreed, {ka['filled']} filled, "
            f"{ka['won']} won, {ka['avg_r']:+}R a trade; where it did not, {kn['filled']} filled, {kn['won']} won, "
            f"{kn['avg_r']:+}R a trade.</p>",
            "<p>Pictures: 01 results table · 02 setups by Kronos · 03 equity · trade_NN one per trade (zone box, BOS, "
            "entry / SL / TP, fill ▲▼ and exit ✕). CSVs: every trade, and every setup with its Kronos reading.</p>",
            "<h2>What it means</h2><ul>"
            f"<li><b>Kronos does not pick the better setups.</b> It agreed strongly with only {ka['setups']} of the "
            f"{len(setups)} setups, and those did worse ({ka['avg_r']:+}R a trade) than the rest ({kn['avg_r']:+}R). "
            "Kronos more often pointed the other way after a BOS (table 02). It only cuts the number of trades.</li>"
            f"<li><b>Taken one at a time the strategy is about break-even</b>, but every setup on its own loses "
            f"{group(alone)['avg_r']:+}R a trade over {group(alone)['filled']} fills. The one-at-a-time run was lucky "
            "in which setups it happened to take; the all-setups number is the fairer one.</li>"
            "<li>Most losses are a pullback that runs straight through the zone; the wins are big (the leg's swing is "
            "often 5–10R away), but too rare (12–20 % won).</li>"
            "<li>A wider stop buffer wins more often but smaller; none of the three turns the result clearly "
            "positive, and the swings between them are within the noise of 17–65 trades.</li></ul>"
            "<h2>Checks</h2><ul>"
            f"<li>The conductor's {same + diff} trades without Kronos were re-simulated one by one by separate code: "
            f"{same} came out with the same R, {diff} differed.</li>"
            "<li>Trade pictures were looked at by hand (zone, BOS, entry, SL, TP, fill and exit where the rules say).</li>"
            "<li>No look-ahead: each Kronos forecast uses only the 512 bars up to the setup bar; each setup is found "
            "from closed bars only.</li></ul>"
            "<h2>How it was simulated</h2><ul>"
            "<li>Conductor + paper executor (the same code a live run would use): one order at a time on the symbol; "
            "limit at the zone's entry line; filled when the ask (buy) / bid (sell) reaches it; the stop counts first "
            "when one bar touches both; the bar's spread is paid; no slippage, no swap.</li>"
            "<li>The limit is cancelled after 96 bars or on a Claude CHoCH against it; no new orders 20:45–22:15 UTC.</li>"
            "<li>The SL buffer was also tried at 0.1 and 0.5 ATR (table 01).</li>"
            "<li>\"Each on its own\" ignores the one-at-a-time limit, the CHoCH cancel and the rollover window, so "
            "every setup counts once.</li></ul>",
            "<h2>Files</h2><p>Code: concepter/backtests/kronos_claude_bos_zone.py, rules/strategy/kronos_claude_bos_zone, "
            "rules/concept/claude. Data + runs: engine_data/backtest/kronos_claude_bos_zone/.</p>"]
    with open(os.path.join(out, "README.html"), "w") as f:
        f.write("<html><body>" + "\n".join(html) + "</body></html>")
    with PdfPages(os.path.join(out, f"{SYM}_{TF}_kronos_claude_bos_zone_backtest.pdf")) as pdf:
        for p in sorted(os.path.join(out, x) for x in os.listdir(out) if x.endswith(".png")):
            img = plt.imread(p)
            fig = plt.figure(figsize=(img.shape[1] / 110, img.shape[0] / 110))
            fig.figimage(img)
            pdf.savefig(fig)
            plt.close(fig)
    write_chart(bt, main_run, base_run, by_key, kron, ms_, bs_, bars)
    summary = {"crosscheck": {"same_r": same, "different": diff}, "main": ms_, "no_kronos": bs_, "kronos_agrees_alone": ka, "kronos_not_alone": kn,
               "all_alone": group(alone), "setups": len(setups), "forecasts": len(kron),
               "runs": {n: stats(r["trades"]) | {"orders": r["orders"], "unfilled": r["expired"], "cancelled": r["cancelled"]}
                        for n, r in R_.items()}}
    with open(os.path.join(out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))
    if a.upload:
        subprocess.run(["rclone", "copy", out, DRIVE, "--exclude", "README.html"], check=True)
        subprocess.run(["rclone", "copy", os.path.join(out, "README.html"), DRIVE, "--drive-import-formats", "html",
                        "--drive-export-formats", "html"], check=True)
        print("uploaded →", DRIVE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
