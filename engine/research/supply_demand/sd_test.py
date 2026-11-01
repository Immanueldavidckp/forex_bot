#!/usr/bin/env python3
"""sd_test.py — which validity criteria make a supply / demand zone hold? (research, 2026-10-30)

Reads /home/david/forex/engine_data/history/<SYM>.json (read-only), builds candidate zones two ways, records the
candidate validity criteria for each, measures the outcome at the FIRST return (closed bars only), and compares the
hold rate with matched random controls and with zones found on shuffled candles. python3 + numpy only.

    python3 sd_test.py [--syms GOLD,EURUSD,...] [--tfs M15,H1] [--out DIR] [--controls 3] [--quick]

Zones
  v5    David's V5 zone: the last opposite candle (<= 5 bars before) a displacement candle (body >= 1.5 x the
        average body of the previous 10). Box = the candle's full wick (smc_marks convention).
  base  the classic S&D base: 1-6 base candles (body <= 50 % of range) between a directional leg-in candle and a
        displacement leg-out that CLOSES beyond the whole base. Distal = the base's extreme wick, proximal = the
        base's extreme body (Seiden / OTA, Set-and-Forget convention).
  Both need the leg-out to close beyond the proximal line and price to leave by >= 1 zone height before the
  first return (a zone price never left is not a zone by anyone's definition).

Outcome at the first return r (first closed bar after the leg-out whose wick reaches the proximal line):
  fail      a bar (r included) CLOSES beyond the distal line
  hold_h    before that, a later bar (r+1 ...) trades >= 1 zone height beyond the proximal line
  hold_2h   ... >= 2 zone heights (an RR-2 trade with the stop at the distal line)
  hold_atr  ... >= 1 ATR(14, at r)
  same-bar target and fail = fail (the bar's path is unknown); unresolved after 200 bars = not held.

Baselines
  ctrl      K random-time controls per zone: same side, same height and same distance from the close in ATR units
            (scaled by ATR at the random bar), same return / departure rules, same outcome rules.
  shuf      the same detection + outcome pipeline on a series of shuffled candles (each bar keeps its own
            open-relative shape, bar order shuffled, closes chained).

Structure (David's major_structure.py, read-only via sys.path) and a 3-bar fractal swing version give the BOS
gate; the rest of the criteria are documented next to the code.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, "/home/david/forex/engine")
from major_structure import major_structure  # noqa: E402  (read-only; no engine imports inside)

HIST = "/home/david/forex/engine_data/history"
SYMS = ["GOLD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "BITCOIN"]
TFS = ["M15", "H1"]
DISP_MULT, BODY_AVG, LOOK = 1.5, 10, 5          # David's V5 values (config.py STRATEGY)
MAX_BASE = 6
HORIZON = 200                                   # bars after the return to resolve hold / fail
MAX_WAIT = 3000                                 # bars to wait for the first return
MIN_DEPART_H = 1.0                              # price must leave by >= 1 zone height
MIN_HEIGHT_ATR = 0.05                           # drop degenerate (doji) zones
FRACTAL_N = 3
BOS_WINDOW = 10                                 # the break must come within 10 bars of the leg-out
FVG_PROTECT, FVG_RUNOFF = 2, 0.5                # David's FVG rule
ROUND = {"GOLD": 10.0, "EURUSD": 0.005, "GBPUSD": 0.005, "AUDUSD": 0.005, "USDJPY": 0.5, "BITCOIN": 1000.0}
IS_FRAC = 0.7


# ----------------------------------------------------------------------------------------------- data

def load(sym: str, tf: str):
    with open(os.path.join(HIST, sym + ".json")) as f:
        rows = json.load(f)["bars"][tf]
    a = np.array([r[:5] for r in rows], dtype=float)
    t, o, h, l, c = a[:, 0].astype(np.int64), a[:, 1], a[:, 2], a[:, 3], a[:, 4]
    ok = (h >= l) & (h > 0)
    return t[ok], o[ok], h[ok], l[ok], c[ok]


def atr14(h, l, c):
    """mean true range of the last 14 bars (expanding at the start), as major_structure.atr14"""
    pc = np.concatenate([[c[0]], c[:-1]])
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    cs = np.concatenate([[0.0], np.cumsum(tr)])
    n = len(tr)
    i = np.arange(n)
    lo = np.maximum(0, i - 13)
    return (cs[i + 1] - cs[lo]) / (i + 1 - lo)


def shuffled_series(o, h, l, c, seed):
    """bar order shuffled, each bar keeps its open-relative shape, closes chained: same marginal candles, no memory"""
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(o))
    rc, rh, rl = (c / o)[idx], (h / o)[idx], (l / o)[idx]
    lr = np.log(rc)
    o2 = o[0] * np.exp(np.concatenate([[0.0], np.cumsum(lr[:-1])]))
    return o2, o2 * rh, o2 * rl, o2 * rc


def fractals(h, l, n=FRACTAL_N):
    """strict swing high / low at p (major_structure._pivot rule), confirmed at bar p+n"""
    N = len(h)
    sh = np.ones(N, bool)
    sl = np.ones(N, bool)
    sh[:n] = sh[N - n:] = False
    sl[:n] = sl[N - n:] = False
    for k in range(1, n + 1):
        sh[n:N - n] &= (h[n:N - n] > h[n - k:N - n - k]) & (h[n:N - n] >= h[n + k:N - n + k])
        sl[n:N - n] &= (l[n:N - n] < l[n - k:N - n - k]) & (l[n:N - n] <= l[n + k:N - n + k])
    return sh, sl


# ----------------------------------------------------------------------------------------------- zones

def _bodies(o, c, k=BODY_AVG):
    body = np.abs(c - o)
    cs = np.concatenate([[0.0], np.cumsum(body)])
    avg = np.full(len(o), np.nan)
    avg[k:] = (cs[k:len(o)] - cs[:len(o) - k]) / k
    return body, avg


def detect_v5(o, h, l, c):
    body, avg = _bodies(o, c)
    N, seen, out = len(o), set(), []
    for d in range(BODY_AVG, N - 1):
        if not (avg[d] > 0 and body[d] >= DISP_MULT * avg[d]):
            continue
        bull = c[d] > o[d]
        j = None
        for i in range(d - 1, max(d - 1 - LOOK, -1), -1):
            if (c[i] < o[i]) if bull else (c[i] > o[i]):
                j = i
                break
        if j is None or (j, bull) in seen:
            continue
        prox, dist = (h[j], l[j]) if bull else (l[j], h[j])
        if (c[d] <= prox) if bull else (c[d] >= prox):
            continue
        seen.add((j, bull))
        out.append(dict(method="v5", side="demand" if bull else "supply", j=j, bs=j, be=d - 1, d=d,
                        prox=float(prox), dist=float(dist), disp=float(body[d] / avg[d]), n_base=int(d - j), typ="V5"))
    return out


def detect_base(o, h, l, c):
    body, avg = _bodies(o, c)
    rng = h - l
    small = body <= 0.5 * rng
    bodyhi, bodylo = np.maximum(o, c), np.minimum(o, c)
    N, seen, out = len(o), set(), []
    for d in range(BODY_AVG + 2, N - 1):
        if not (avg[d] > 0 and body[d] >= DISP_MULT * avg[d]):
            continue
        bull = c[d] > o[d]
        k, i = 0, d - 1
        while i >= 0 and small[i] and k < MAX_BASE:
            k, i = k + 1, i - 1
        if k == 0 or i < 0 or small[i]:
            continue                                   # no base, or no directional leg-in before it
        bs, be = i + 1, d - 1
        if bull:
            dist, prox = l[bs:be + 1].min(), bodyhi[bs:be + 1].max()
            if c[d] <= h[bs:be + 1].max():
                continue
        else:
            dist, prox = h[bs:be + 1].max(), bodylo[bs:be + 1].min()
            if c[d] >= l[bs:be + 1].min():
                continue
        if (bs, bull) in seen:
            continue
        seen.add((bs, bull))
        legin_bull = c[i] > o[i]
        typ = ("R" if legin_bull else "D") + "B" + ("R" if bull else "D")
        out.append(dict(method="base", side="demand" if bull else "supply", j=bs, bs=bs, be=be, d=d,
                        prox=float(prox), dist=float(dist), disp=float(body[d] / avg[d]), n_base=k, typ=typ))
    return out


# ----------------------------------------------------------------------------------------------- outcome

def first_return(demand, prox, start, h, l, maxwait=MAX_WAIT):
    """first bar after start whose wick reaches prox; departure = how far price went away before that"""
    N = len(h)
    end = min(N, start + 1 + maxwait)
    seg = l[start + 1:end] <= prox if demand else h[start + 1:end] >= prox
    hit = np.flatnonzero(seg)
    if len(hit) == 0:
        return None, None
    r = start + 1 + int(hit[0])
    dep = (h[start:r].max() - prox) if demand else (prox - l[start:r].min())
    return r, float(dep)


def outcome(demand, prox, dist, r, h, l, c, atr_r):
    H = abs(prox - dist)
    fail = hold_h = hold_2h = hold_atr = None
    mae = mfe = 0.0
    end = min(len(c), r + HORIZON)
    for i in range(r, end):
        pen = (prox - l[i]) if demand else (h[i] - prox)
        mae = max(mae, pen)
        if (c[i] < dist) if demand else (c[i] > dist):
            fail = i
            break
        if i > r:
            fav = (h[i] - prox) if demand else (prox - l[i])
            mfe = max(mfe, fav)
            if hold_h is None and fav >= H:
                hold_h = i
            if hold_2h is None and fav >= 2 * H:
                hold_2h = i
            if hold_atr is None and fav >= atr_r:
                hold_atr = i
        if hold_2h is not None and hold_atr is not None:
            break
    return dict(fail=fail, hold_h=hold_h is not None, hold_2h=hold_2h is not None, hold_atr=hold_atr is not None,
                hold_idx=hold_h, mae_h=mae / H, mfe_h=mfe / H,
                bars_to_resolve=((hold_h if hold_h is not None else fail if fail is not None else end - 1) - r))


# ----------------------------------------------------------------------------------------------- criteria

def session(t_ms):
    hr = dt.datetime.fromtimestamp(t_ms / 1000, dt.timezone.utc).hour
    return "asia" if hr < 7 else "london" if hr < 12 else "ny_overlap" if hr < 16 else "ny_late" if hr < 21 else "late"


def structure_arrays(t, o, h, l, c):
    bars = [{"t": int(t[i]), "o": float(o[i]), "h": float(h[i]), "l": float(l[i]), "c": float(c[i])} for i in range(len(t))]
    m = major_structure(bars)
    ev = m["events"]
    return (np.array([e["side"] == "buy" for e in ev], bool), np.array([e["origin"]["idx"] for e in ev], int),
            np.array([e["idx"] for e in ev], int), np.array([e["origin"]["price"] for e in ev], float),
            np.array([e["kind"] == "CHoCH" for e in ev], bool))


def unbroken_swing(demand, d, h, l, c, sh, sl, back=100):
    """the nearest confirmed fractal swing beyond the pre-leg-out close that no close has taken since"""
    best = None
    for p in range(d - FRACTAL_N - 1, max(FRACTAL_N, d - back), -1):
        if demand and sh[p] and h[p] > c[d - 1] and h[p] > c[p + 1:d].max():
            best = h[p] if best is None else min(best, h[p])
        elif not demand and sl[p] and l[p] < c[d - 1] and l[p] < c[p + 1:d].min():
            best = l[p] if best is None else max(best, l[p])
    return best


def criteria(z, t, o, h, l, c, A, sh, sl, ev, sym):
    ev_buy, ev_o, ev_x, ev_op, ev_ch = ev
    demand, j, d, r = z["side"] == "demand", z["j"], z["d"], z["r"]
    prox, dist = z["prox"], z["dist"]
    H = abs(prox - dist)
    a = A[d]
    z["height_atr"] = H / a
    z["depart_h"] = z["depart"] / H
    z["depart_atr"] = z["depart"] / a
    z["legout_h"] = (h[d] - l[d]) / H
    z["session"] = session(int(t[j]))
    # David's gate: a major BOS / CHoCH of the zone's side whose move contains the zone candle and whose break
    # comes with the leg-out (<= BOS_WINDOW bars after it) and before the return
    side_ok = ev_buy == demand
    inmove = side_ok & (ev_o <= j) & (ev_x >= d) & (ev_x < r)
    z["bos_major"] = bool(np.any(inmove & (ev_x <= d + BOS_WINDOW)))
    z["bos_major_any"] = bool(np.any(inmove))
    z["bos_move"] = bool(np.any(side_ok & (ev_o <= j) & (ev_x >= j) & (ev_x < r)))   # zone inside any major break's move
    z["choch_major"] = bool(np.any(inmove & ev_ch & (ev_x <= d + BOS_WINDOW)))
    # simple fractal version: the leg-out (3 bars) closes beyond the nearest unbroken 3-bar swing
    lvl = unbroken_swing(demand, d, h, l, c, sh, sl)
    seg = c[d:min(d + 3, r)]
    z["bos_fractal"] = bool(lvl is not None and ((seg.max() > lvl) if demand else (seg.min() < lvl)))
    z["swing_dist_atr"] = None if lvl is None else float(abs(lvl - c[d - 1]) / a)
    # trend and premium / discount from the last major event before the leg-out
    before = np.flatnonzero(ev_x < d)
    if len(before):
        k = before[-1]
        up = bool(ev_buy[k])
        z["trend"] = "up" if up else "down"
        z["with_trend"] = up == demand
        lo, hi = (ev_op[k], h[ev_x[k]:d].max()) if up else (l[ev_x[k]:d].min(), ev_op[k])
        mid = (prox + dist) / 2
        loc = (mid - lo) / (hi - lo) if hi > lo else 0.5
        z["pd_loc"] = float(loc)
        z["pd_ok"] = bool(loc < 0.5) if demand else bool(loc > 0.5)
        z["bars_since_event"] = int(d - ev_x[k])
    else:
        z["trend"], z["with_trend"], z["pd_loc"], z["pd_ok"], z["bars_since_event"] = None, None, None, None, None
    # rolling 100-bar location (a structure-free premium / discount)
    lo, hi = l[max(0, d - 100):d].min(), h[max(0, d - 100):d].max()
    loc = ((prox + dist) / 2 - lo) / (hi - lo) if hi > lo else 0.5
    z["pd100_ok"] = bool(loc < 0.5) if demand else bool(loc > 0.5)
    # FVG of the leg-out (middle candle = the leg-out), David's protect / run-off rule, known by the return
    if demand:
        g_lo, g_hi = h[d - 1], l[d + 1]
    else:
        g_lo, g_hi = h[d + 1], l[d - 1]
    gap = g_hi - g_lo
    z["fvg"] = bool(gap > 0 and d + 1 < r)
    z["fvg_atr"] = float(gap / a) if z["fvg"] else 0.0
    z["fvg_ok"] = False
    if z["fvg"]:
        ft, run = None, 0.0
        for i in range(d + 2, r + 1):
            if (l[i] < g_hi) if demand else (h[i] > g_lo):
                ft = i
                break
            run = max(run, (h[i] - g_hi) if demand else (g_lo - l[i]))
        if ft is None:
            z["fvg_ok"] = True                          # never traded back into before the zone return
        else:
            z["fvg_ok"] = bool(ft - (d + 1) > FVG_PROTECT and run >= FVG_RUNOFF * a)
    # liquidity sweep: the zone / base wick took out the last confirmed fractal swing on its side (<= 30 bars
    # back) and the leg-out closed back beyond it
    bs, be = z["bs"], z["be"]
    z["sweep"] = False
    for p in range(bs - FRACTAL_N - 1, max(FRACTAL_N, bs - 30), -1):
        if demand and sl[p]:
            z["sweep"] = bool(l[bs:be + 1].min() < l[p] and c[d] > l[p])
            break
        if not demand and sh[p]:
            z["sweep"] = bool(h[bs:be + 1].max() > h[p] and c[d] < h[p])
            break
    # round number (Osler): a 00 / 50 style grid level inside the zone or within 0.25 ATR of its mid
    g = ROUND[sym]
    mid = (prox + dist) / 2
    near = round(mid / g) * g
    z["round"] = bool(min(prox, dist) <= near <= max(prox, dist) or abs(near - mid) <= 0.25 * a)
    z["rr_extreme"] = z["depart_h"]                   # the leg's extreme before the return, in zone heights


def opposing_rr(zones, h, l, c):
    """reward-to-risk to the nearest live opposing zone (same method) at the return, in zone heights"""
    by = {}
    for z in zones:
        by.setdefault((z["method"], z["side"]), []).append(z)
    for z in zones:
        opp = by.get((z["method"], "supply" if z["side"] == "demand" else "demand"), [])
        demand, r, prox, H = z["side"] == "demand", z["r"], z["prox"], abs(z["prox"] - z["dist"])
        best = None
        for q in opp:
            if q["d"] >= r:
                continue
            if demand and q["prox"] > prox:
                if q["d"] + 1 < r and c[q["d"] + 1:r].max() > q["dist"]:
                    continue                          # already closed through
                gap = (q["prox"] - prox) / H
            elif not demand and q["prox"] < prox:
                if q["d"] + 1 < r and c[q["d"] + 1:r].min() < q["dist"]:
                    continue
                gap = (prox - q["prox"]) / H
            else:
                continue
            best = gap if best is None else min(best, gap)
        z["rr_opp"] = best


# ----------------------------------------------------------------------------------------------- pipeline

def run_series(t, o, h, l, c, sym, tf, label, with_criteria=True, n_ctrl=3, seed=0):
    A = atr14(h, l, c)
    N = len(c)
    zones = detect_v5(o, h, l, c) + detect_base(o, h, l, c)
    keep = []
    for z in zones:
        H = abs(z["prox"] - z["dist"])
        if H < MIN_HEIGHT_ATR * A[z["d"]]:
            continue
        r, dep = first_return(z["side"] == "demand", z["prox"], z["d"], h, l)
        if r is None or dep < MIN_DEPART_H * H or r + 2 >= N:
            continue
        z["r"], z["depart"], z["wait"] = r, dep, r - z["d"]
        z.update(outcome(z["side"] == "demand", z["prox"], z["dist"], r, h, l, c, A[r]))
        z["is"] = z["d"] < IS_FRAC * N
        # the second return (freshness): after the first hold, the next touch
        z["hold2_h"] = None
        if z["hold_h"]:
            r2, dep2 = first_return(z["side"] == "demand", z["prox"], z["hold_idx"], h, l)
            if r2 is not None and r2 + 2 < N:
                z["hold2_h"] = outcome(z["side"] == "demand", z["prox"], z["dist"], r2, h, l, c, A[r2])["hold_h"]
        keep.append(z)
    zones = keep
    if with_criteria:
        sh, sl = fractals(h, l)
        ev = structure_arrays(t, o, h, l, c)
        for z in zones:
            criteria(z, t, o, h, l, c, A, sh, sl, ev, sym)
        opposing_rr(zones, h, l, c)
    # matched random-time controls
    rng = np.random.default_rng(seed + 17)
    ctrl = []
    for z in zones:
        demand, H = z["side"] == "demand", abs(z["prox"] - z["dist"])
        delta = (c[z["d"]] - z["prox"]) if demand else (z["prox"] - c[z["d"]])
        for _ in range(n_ctrl):
            for _try in range(5):
                d2 = int(rng.integers(50, N - HORIZON - 50))
                s = A[d2] / A[z["d"]]
                H2, dl = H * s, delta * s
                prox2 = c[d2] - dl if demand else c[d2] + dl
                dist2 = prox2 - H2 if demand else prox2 + H2
                r2, dep2 = first_return(demand, prox2, d2, h, l)
                if r2 is None or dep2 < MIN_DEPART_H * H2 or r2 + 2 >= N:
                    continue
                oc = outcome(demand, prox2, dist2, r2, h, l, c, A[r2])
                ctrl.append(dict(method=z["method"], side=z["side"], d=d2, r=r2, wait=r2 - d2, depart_h=dep2 / H2,
                                 height_atr=H2 / A[d2], hold_h=oc["hold_h"], hold_2h=oc["hold_2h"],
                                 hold_atr=oc["hold_atr"], mae_h=oc["mae_h"], mfe_h=oc["mfe_h"],
                                 **{"is": d2 < IS_FRAC * N}))
                break
    for z in zones:
        z.update(sym=sym, tf=tf, series=label, t_j=int(t[z["j"]]), t_d=int(t[z["d"]]), t_r=int(t[z["r"]]))
    for q in ctrl:
        q.update(sym=sym, tf=tf, series=label)
    return zones, ctrl


def job(args):
    sym, tf, n_ctrl, quick = args
    t0 = time.time()
    t, o, h, l, c = load(sym, tf)
    if quick:
        t, o, h, l, c = t[-6000:], o[-6000:], h[-6000:], l[-6000:], c[-6000:]
    zones, ctrl = run_series(t, o, h, l, c, sym, tf, "real", True, n_ctrl, seed=(SYMS.index(sym) if sym in SYMS else 9) * 10 + TFS.index(tf) if tf in TFS else 0)
    o2, h2, l2, c2 = shuffled_series(o, h, l, c, seed=7)
    shuf, _ = run_series(t, o2, h2, l2, c2, sym, tf, "shuf", False, 0)
    print(f"  {sym} {tf}: {len(c)} bars, {len(zones)} zones, {len(ctrl)} controls, {len(shuf)} shuffled zones, "
          f"{time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    return zones, ctrl, shuf


# ----------------------------------------------------------------------------------------------- statistics

def rate(xs):
    xs = np.asarray(xs, float)
    return float(xs.mean()) if len(xs) else float("nan")


def perm_p(a, b, n=4000, seed=1):
    """two-sided permutation p-value for mean(a) - mean(b) (vectorised, chunks of 250 permutations)"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 5 or len(b) < 5:
        return float("nan")
    obs = abs(a.mean() - b.mean())
    pool = np.concatenate([a, b])
    rng = np.random.default_rng(seed)
    cnt, done, na = 0, 0, len(a)
    while done < n:
        k = min(250, n - done)
        m = rng.permuted(np.tile(pool, (k, 1)), axis=1)
        cnt += int(np.sum(np.abs(m[:, :na].mean(1) - m[:, na:].mean(1)) >= obs - 1e-12))
        done += k
    return (cnt + 1) / (n + 1)


def boot_ci(a, b, n=4000, seed=2):
    """95 % bootstrap CI of mean(a) - mean(b)"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 5 or len(b) < 5:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    ia = rng.integers(0, len(a), (n, len(a)))
    ib = rng.integers(0, len(b), (n, len(b)))
    diff = a[ia].mean(1) - b[ib].mean(1)
    return (float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5)))


def pct(x):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.1f}"


def pp(x):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:+.1f}"


def fmt_p(p):
    return "n/a" if p is None or (isinstance(p, float) and math.isnan(p)) else ("<0.001" if p < 0.001 else f"{p:.3f}")


CRITERIA = [
    ("bos_major", "BOS gate (David's major structure, break within 10 bars)", lambda z: z["bos_major"]),
    ("bos_major_any", "major BOS before the return (any delay)", lambda z: z["bos_major_any"]),
    ("bos_move", "zone inside any major break's move", lambda z: z["bos_move"]),
    ("choch_major", "the break is a CHoCH", lambda z: z["choch_major"]),
    ("bos_fractal", "BOS gate (3-bar fractal swing)", lambda z: z["bos_fractal"]),
    ("disp>=2", "displacement >= 2 x avg body", lambda z: z["disp"] >= 2.0),
    ("disp>=3", "displacement >= 3 x avg body", lambda z: z["disp"] >= 3.0),
    ("fvg", "FVG in the leg-out", lambda z: z["fvg"]),
    ("fvg>=0.3atr", "FVG >= 0.3 ATR", lambda z: z["fvg_atr"] >= 0.3),
    ("fvg_ok", "FVG kept (David: untouched 2 candles, 0.5 ATR run)", lambda z: z["fvg_ok"]),
    ("base<=2", "base <= 2 candles (V5: opposite candle <= 2 bars before)", lambda z: z["n_base"] <= 2),
    ("base>=3", "base >= 3 candles", lambda z: z["n_base"] >= 3),
    ("depart>=3h", "departure >= 3 zone heights before the return", lambda z: z["depart_h"] >= 3),
    ("depart>=2atr", "departure >= 2 ATR before the return", lambda z: z["depart_atr"] >= 2),
    ("legout>=2h", "leg-out candle range >= 2 zone heights", lambda z: z["legout_h"] >= 2),
    ("height<=0.5atr", "zone height <= 0.5 ATR", lambda z: z["height_atr"] <= 0.5),
    ("height>1atr", "zone height > 1 ATR", lambda z: z["height_atr"] > 1),
    ("with_trend", "with the major trend", lambda z: z["with_trend"] is True),
    ("against_trend", "against the major trend", lambda z: z["with_trend"] is False),
    ("pd_ok", "demand in discount / supply in premium (major range)", lambda z: z["pd_ok"] is True),
    ("pd100_ok", "... of the last 100 bars' range", lambda z: z["pd100_ok"]),
    ("sweep", "liquidity sweep just before the leg-out", lambda z: z["sweep"]),
    ("round", "round-number level in / at the zone", lambda z: z["round"]),
    ("rr_opp>=2", "RR >= 2 to the nearest live opposing zone", lambda z: z["rr_opp"] is not None and z["rr_opp"] >= 2),
    ("no_opp", "no live opposing zone above / below", lambda z: z["rr_opp"] is None),
    ("wait<=50", "returned within 50 bars", lambda z: z["wait"] <= 50),
    ("wait>200", "returned after > 200 bars", lambda z: z["wait"] > 200),
    ("asia", "formed in Asia (00-07 UTC)", lambda z: z["session"] == "asia"),
    ("london", "formed in London (07-12 UTC)", lambda z: z["session"] == "london"),
    ("ny_overlap", "formed in London/NY overlap (12-16 UTC)", lambda z: z["session"] == "ny_overlap"),
]
COMBOS = [
    ("gate+fvg", "BOS gate + FVG", lambda z: z["bos_major"] and z["fvg"]),
    ("gate+fvg_ok", "BOS gate + FVG kept", lambda z: z["bos_major"] and z["fvg_ok"]),
    ("gate+trend", "BOS gate + with trend", lambda z: z["bos_major"] and z["with_trend"] is True),
    ("gate+pd", "BOS gate + discount/premium", lambda z: z["bos_major"] and z["pd_ok"] is True),
    ("gate+sweep", "BOS gate + sweep", lambda z: z["bos_major"] and z["sweep"]),
    ("gate+fvg+trend", "BOS gate + FVG + with trend", lambda z: z["bos_major"] and z["fvg"] and z["with_trend"] is True),
    ("gate+fvg+pd", "BOS gate + FVG + discount/premium", lambda z: z["bos_major"] and z["fvg"] and z["pd_ok"] is True),
    ("gate+depart3", "BOS gate + departure >= 3 h", lambda z: z["bos_major"] and z["depart_h"] >= 3),
    ("fractal+fvg", "fractal BOS + FVG", lambda z: z["bos_fractal"] and z["fvg"]),
    ("fvg+depart3", "FVG + departure >= 3 h", lambda z: z["fvg"] and z["depart_h"] >= 3),
    ("sweep+fvg", "sweep + FVG", lambda z: z["sweep"] and z["fvg"]),
    ("sweep+bos_any", "sweep + major BOS before return", lambda z: z["sweep"] and z["bos_major_any"]),
    ("trend+pd", "with trend + discount/premium", lambda z: z["with_trend"] is True and z["pd_ok"] is True),
    ("nogate", "NO major BOS (David: invalid)", lambda z: not z["bos_major"]),
]


def crit_table(zones, metric="hold_h"):
    """per criterion: n, hold rate with / without, lift, permutation p, IS lift, OOS lift"""
    lines = ["| criterion | n with | hold with % | hold without % | lift pp | p | IS lift pp | OOS lift pp |",
             "|---|---|---|---|---|---|---|---|"]
    out = {}
    for key, name, fn in CRITERIA + COMBOS:
        m = np.array([bool(fn(z)) for z in zones])
        y = np.array([z[metric] for z in zones], float)
        a, b = y[m], y[~m]
        isd = np.array([z["is"] for z in zones])
        li = rate(y[m & isd]) - rate(y[~m & isd])
        lo = rate(y[m & ~isd]) - rate(y[~m & ~isd])
        p = perm_p(a, b)
        out[key] = dict(name=name, n=int(m.sum()), with_=rate(a), without=rate(b), lift=rate(a) - rate(b), p=p,
                        is_lift=li, oos_lift=lo)
        lines.append(f"| {name} | {m.sum()} | {pct(rate(a))} | {pct(rate(b))} | {pp(rate(a) - rate(b))} | {fmt_p(p)} | "
                     f"{pp(li)} | {pp(lo)} |")
    return "\n".join(lines), out


def overview_table(groups):
    """groups: list of (label, zones, ctrl, shuf)"""
    lines = ["| set | zones | hold 1h % | ctrl 1h % | lift pp [95 % CI] | shuf 1h % | hold 1 ATR % | ctrl 1 ATR % | "
             "hold 2h % | ctrl 2h % | median wait | MAE h | closed thru % |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for label, zs, cs, ss in groups:
        if not zs:
            continue
        y = [z["hold_h"] for z in zs]
        yc = [q["hold_h"] for q in cs]
        ci = boot_ci(y, yc)
        lines.append(f"| {label} | {len(zs)} | {pct(rate(y))} | {pct(rate(yc))} | {pp(rate(y) - rate(yc))} "
                     f"[{pp(ci[0])}, {pp(ci[1])}] | {pct(rate([z['hold_h'] for z in ss]))} | "
                     f"{pct(rate([z['hold_atr'] for z in zs]))} | {pct(rate([q['hold_atr'] for q in cs]))} | "
                     f"{pct(rate([z['hold_2h'] for z in zs]))} | {pct(rate([q['hold_2h'] for q in cs]))} | "
                     f"{int(np.median([z['wait'] for z in zs]))} | {np.median([z['mae_h'] for z in zs]):.2f} | "
                     f"{pct(rate([z['fail'] is not None for z in zs]))} |")
    return "\n".join(lines)


def freshness_table(zones):
    lines = ["| set | first return hold % | zones that held then returned | second return hold % |", "|---|---|---|---|"]
    for label, zs in zones:
        sec = [z["hold2_h"] for z in zs if z["hold2_h"] is not None]
        lines.append(f"| {label} | {pct(rate([z['hold_h'] for z in zs]))} | {len(sec)} | {pct(rate(sec))} |")
    return "\n".join(lines)


def strat_table(zones, ctrl, key, buckets, name):
    """hold rate by a continuous variable's bucket, zones vs controls"""
    lines = [f"| {name} | zones n | zones hold % | ctrl n | ctrl hold % | lift pp |", "|---|---|---|---|---|---|"]
    for lo, hi in buckets:
        zs = [z["hold_h"] for z in zones if lo <= z[key] < hi]
        cs = [q["hold_h"] for q in ctrl if lo <= q[key] < hi]
        lines.append(f"| {lo}-{hi} | {len(zs)} | {pct(rate(zs))} | {len(cs)} | {pct(rate(cs))} | {pp(rate(zs) - rate(cs))} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--syms", default=",".join(SYMS))
    ap.add_argument("--tfs", default=",".join(TFS))
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--controls", type=int, default=3)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--procs", type=int, default=6)
    a = ap.parse_args()
    syms, tfs = a.syms.split(","), a.tfs.split(",")
    jobs = [(s, tf, a.controls, a.quick) for s in syms for tf in tfs]
    print(f"running {len(jobs)} symbol/timeframe jobs", file=sys.stderr)
    with Pool(min(a.procs, len(jobs))) as pool:
        res = pool.map(job, jobs)
    zones = [z for r in res for z in r[0]]
    ctrl = [q for r in res for q in r[1]]
    shuf = [z for r in res for z in r[2]]
    with open(os.path.join(a.out, "zones.json"), "w") as f:
        json.dump({"zones": zones, "controls": ctrl, "shuffled": shuf}, f)

    md = [f"# sd_test.py results ({dt.date.today()})", "",
          f"zones {len(zones)}, controls {len(ctrl)}, shuffled-series zones {len(shuf)}; horizon {HORIZON} bars, "
          f"max wait {MAX_WAIT}, min departure {MIN_DEPART_H} h, in-sample = first {int(IS_FRAC * 100)} % of bars", ""]
    sel = lambda L, **kw: [z for z in L if all(z.get(k) == v for k, v in kw.items())]
    fx = lambda L: [z for z in L if z["sym"] != "BITCOIN"]
    for method in ("v5", "base"):
        md += [f"## Overview — {method} zones", ""]
        groups = [(f"ALL FX+GOLD {method}", fx(sel(zones, method=method)), fx(sel(ctrl, method=method)), fx(sel(shuf, method=method)))]
        for tf in tfs:
            groups.append((f"FX+GOLD {method} {tf}", fx(sel(zones, method=method, tf=tf)), fx(sel(ctrl, method=method, tf=tf)),
                           fx(sel(shuf, method=method, tf=tf))))
        for s in syms:
            for tf in tfs:
                groups.append((f"{s} {tf} {method}", sel(zones, method=method, sym=s, tf=tf), sel(ctrl, method=method, sym=s, tf=tf),
                               sel(shuf, method=method, sym=s, tf=tf)))
        md += [overview_table(groups), ""]
        md += [f"### In-sample / out-of-sample — {method}", ""]
        groups = []
        for lab, flag in (("IS", True), ("OOS", False)):
            groups.append((f"FX+GOLD {method} {lab}", fx(sel(zones, method=method, **{"is": flag})),
                           fx(sel(ctrl, method=method, **{"is": flag})), fx(sel(shuf, method=method, **{"is": flag}))))
            for tf in tfs:
                groups.append((f"FX+GOLD {method} {tf} {lab}", fx(sel(zones, method=method, tf=tf, **{"is": flag})),
                               fx(sel(ctrl, method=method, tf=tf, **{"is": flag})), fx(sel(shuf, method=method, tf=tf, **{"is": flag}))))
        md += [overview_table(groups), ""]
        md += [f"### Base type — {method}", ""]
        if method == "base":
            groups = [(f"{typ} {tf}", fx(sel(zones, method=method, typ=typ, tf=tf)), fx(sel(ctrl, method=method, tf=tf)),
                       fx(sel(shuf, method=method, tf=tf))) for typ in ("RBR", "DBR", "DBD", "RBD") for tf in tfs]
            md += [overview_table(groups), ""]
        md += [f"### Freshness — {method} (first vs second return, FX+GOLD)", ""]
        md += [freshness_table([(f"{method} {tf}", fx(sel(zones, method=method, tf=tf))) for tf in tfs]
                               + [(f"{method} {s} {tf}", sel(zones, method=method, sym=s, tf=tf)) for s in syms for tf in tfs]), ""]
        md += [f"### Hold rate by age / height / departure — {method} FX+GOLD (zones vs matched controls)", ""]
        zz, cc = fx(sel(zones, method=method)), fx(sel(ctrl, method=method))
        md += [strat_table(zz, cc, "wait", [(1, 10), (10, 30), (30, 100), (100, 300), (300, 3001)], "bars to return"), "",
               strat_table(zz, cc, "height_atr", [(0, 0.5), (0.5, 1), (1, 2), (2, 100)], "height / ATR"), "",
               strat_table(zz, cc, "depart_h", [(1, 2), (2, 3), (3, 5), (5, 10), (10, 1000)], "departure / height"), ""]
        for tf in tfs:
            md += [f"### Criteria — {method} {tf}, FX+GOLD pooled (hold = 1 zone height before a close beyond distal)", ""]
            md += [crit_table(fx(sel(zones, method=method, tf=tf)))[0], ""]
            md += [f"### Criteria — {method} {tf}, FX+GOLD pooled, hold = 1 ATR", ""]
            md += [crit_table(fx(sel(zones, method=method, tf=tf)), "hold_atr")[0], ""]
            md += [f"### Criteria — {method} {tf}, FX+GOLD pooled, hold = 2 zone heights (RR 2)", ""]
            md += [crit_table(fx(sel(zones, method=method, tf=tf)), "hold_2h")[0], ""]
        for s in syms:
            for tf in tfs:
                md += [f"### Criteria — {method} {s} {tf}", "", crit_table(sel(zones, method=method, sym=s, tf=tf))[0], ""]
    with open(os.path.join(a.out, "tables.md"), "w") as f:
        f.write("\n".join(md))
    print("\n".join(md[:40]))


if __name__ == "__main__":
    main()
