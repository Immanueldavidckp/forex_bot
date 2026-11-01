#!/usr/bin/env python3
"""
signals_proto.py — order-flow signal prototypes on FxPro MT5 ticks (GOLD, EURUSD; M5 / M15), research only.

Volume model (swappable, see classify_ticks): FxPro has no traded volume and no aggressor flag, so the side comes
from the TICK RULE on the bid (Lee & Ready 1991 tick test; MQL5 blog 774467 level 3) applied to CHANGED quotes only
(the aggressor agent's recommendation): bid up = 1 buy unit, bid down = 1 sell unit, unchanged = 0, no carry-forward,
binned at the new bid. The classic carry-forward variant is kept as 'tick_rule_bid'.

Signals (each a deterministic function of the footprint; defaults in P):
  bar_div      bar-level delta divergence     close against the bar delta, |delta| >= div_k x mean |delta| (20 bars)
  cvd_div      CVD divergence at pivots        price HH with CVD LH (bear) / LL with CVD HL (bull), pivot n each side
  absorb       absorption                      vol >= abs_vol x SMA, |delta| >= div_k x mean, but the body goes <= abs_body ATR
                                               with the delta (aggressors got nothing): fade the aggressors
  exhaust      exhaustion                      a new n-bar extreme whose last exh_rows rows hold <= exh_frac of the
                                               bar's mean row volume (thin tip), bar delta with the move
  stack        stacked imbalances              >= stack_n consecutive diagonal imbalances (ratio >= imb_ratio, row volume
                                               >= max(imb_minvol, imb_minvol_frac x mean row)); zone = the rows; dies on a
                                               close through it
  unfin        unfinished auction (proxy)      two consecutive bars share the same high / low within 1 tick at a new
                                               n-bar extreme (flat, repeated extreme) — expected to be revisited.
                                               With the tick rule the exact extreme can only hold one side, so the
                                               footprint form (bid AND ask at the extreme) is undefined here
  dflip        delta flip                      delta sign changes after >= flip_run same-sign bars
  trap         trapped traders                 buy imbalance rows in the top trap_pct of the bar, close below them
  spike        volume spike                    bar volume >= spike_x x SMA(spike_n) — undirected
  bigrow       large print (row)               one row >= bigrow_x x the mean row volume of the last spike_n bars
  init / resp  initiative / responsive         delta sign vs the previous server day's value area (70 % of ticks)
  pocmig       POC migration                   bar POC higher (lower) than the previous bar's for pocmig_n bars
  lvn          single print / LVN in a bar     an inner row <= lvn_frac x mean row with both neighbours >= mean row
  dhl          delta at the high / low         top-row delta <= 0 on a bar that made a new n-bar high (sellers at
                                               the high) / bottom-row delta >= 0 at a new low
  sweep        liquidity sweep + order flow    wick >= sweep_atr ATR beyond the previous n-bar swing / prior day
                                               extreme, close back inside; "confirmed" when the bar delta leans INTO
                                               the sweep (the aggressors who chased it are trapped)
  bos          BOS with strong delta           David's major_structure BOS whose break bar has delta >= div_k x mean and
                                               volume >= 1.2 x SMA  vs  a BOS without

Evaluation: signed forward return (close[t+h] - close[t]) / ATR14[t] x direction, h = 3 / 6 / 12 bars, against the
unconditional mean and a circular-shift permutation of the signal indicator inside each server day (keeps the count
and the clustering; 2000 shifts; two-sided p). Level signals (stack, unfin, lvn) are scored by revisit / hold rate
against a distance-matched baseline (the chance that any bar travels that far within the window).

usage: python3 -I signals_proto.py [--data DIR] [--out DIR] [--selftest]
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import math
import os
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "orderflow_data"))
SERVER_UTC_OFFSET_MS = 7_200_000          # FxPro server clock = EET (UTC+2 since 2026-10-25)
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

P = dict(
    row={"GOLD": 0.10, "EURUSD": 0.00002},  # footprint row (GOLD 10 ticks = 0.10 $, EURUSD 2 points = 0.2 pip)
    tick={"GOLD": 0.01, "EURUSD": 0.00001},
    pivot_n=3, new_n=5, sma_n=20, horizons=(3, 6, 12), perms=2000,
    div_k=1.5,                    # "strong" delta: |delta| >= 1.5 x SMA20 |delta| (CVD Divergence Pro: multiples of average bar delta)
    div_pct=0.10,                 # alternative (NinjaTrader "Delta %"); not used by default — tick counts make it scale with 1/sqrt(N)
    cvd_max_bars=60,              # pivots compared within 60 bars (Institutional Footprint Divergence Engine 40–60)
    abs_vol=1.3, abs_body=0.10,
    exh_rows=2, exh_frac=0.25,
    imb_ratio=3.0, imb_minvol=5, imb_minvol_frac=0.5, stack_n=3, zone_bars=100,   # min row volume = max(5, 0.5 x the bar's mean row)
    unfin_touches=3, revisit_bars=24,
    flip_run=5,
    trap_pct=0.30,
    spike_x=1.5, spike_n=20, bigrow_x=4.0,
    pocmig_n=3,
    lvn_frac=0.15, lvn_nb=0.5,
    sweep_atr=0.10, sweep_n=5,
)


# ----------------------------------------------------------------------------------------------------- ticks
def load_ticks(path: str) -> Dict[str, np.ndarray]:
    a = np.loadtxt(gzip.open(path, "rt"), delimiter=",", skiprows=1, usecols=(0, 1, 2, 3, 6))
    t = a[:, 0] - SERVER_UTC_OFFSET_MS               # UTC ms
    bid, ask, last, flags = a[:, 1], a[:, 2], a[:, 3], a[:, 4].astype(np.int64)
    # one quote update often arrives as two rows (LAST|VOLUME row, then BID|ASK row): keep one
    keep = np.ones(len(t), bool)
    keep[1:] = ~((np.diff(t) == 0) & (np.diff(bid) == 0) & (np.diff(ask) == 0))
    return {"t": t[keep], "bid": bid[keep], "ask": ask[keep], "last": last[keep], "flags": flags[keep]}


def classify_ticks(tk: Dict[str, np.ndarray], method: str = "tick_rule_changed") -> np.ndarray:
    """side per tick: +1 buy, -1 sell, 0 = not counted. Swappable:
    'tick_rule_changed' (default, the aggressor agent's recommendation): bid up = buy, bid down = sell, unchanged = 0
    (no carry-forward), 1 unit per changed tick, binned at the new bid;
    'tick_rule_bid' (classic Lee-Ready: unchanged inherits the previous side); 'tick_rule_mid'; 'quote_rule'."""
    if method == "tick_rule_changed":
        return np.sign(np.diff(tk["bid"], prepend=tk["bid"][0])).astype(np.int8)
    if method == "tick_rule_mid":
        p = (tk["bid"] + tk["ask"]) / 2
    else:
        p = tk["bid"]
    if method == "quote_rule":                     # last >= ask buy, last <= bid sell, else tick rule (MQL5 774467)
        s = np.where(tk["last"] >= tk["ask"], 1, np.where(tk["last"] <= tk["bid"], -1, 0))
        d = np.sign(np.diff(p, prepend=p[0]))
        s = np.where(s == 0, d, s)
    else:
        s = np.sign(np.diff(p, prepend=p[0]))
    s = s.astype(np.int8)
    # unchanged -> previous side (forward fill), first tick -> buy
    idx = np.where(s != 0, np.arange(len(s)), 0)
    idx = np.maximum.accumulate(idx)
    out = s[idx]
    out[out == 0] = 1
    return out


# ------------------------------------------------------------------------------------------------------ bars
class Bars:
    """OHLC (bid) bars with per-bar footprints: rows (price index), buy[], sell[]."""

    def __init__(self, tk: Dict[str, np.ndarray], side: np.ndarray, tf_min: int, row: float, tick: float):
        self.tf, self.row, self.tick = tf_min, row, tick
        ms = tf_min * 60_000
        b = (tk["t"] // ms).astype(np.int64)
        ub, first = np.unique(b, return_index=True)
        n = len(ub)
        self.t = ub * ms                                            # bar open, UTC ms
        bid = tk["bid"]
        ends = np.append(first[1:], len(bid))
        self.o = bid[first]
        self.c = bid[ends - 1]
        self.h = np.maximum.reduceat(bid, first)
        self.l = np.minimum.reduceat(bid, first)
        self.vol = np.add.reduceat((side != 0).astype(float), first)      # units = classified ticks
        self.delta = np.add.reduceat(side.astype(float), first)
        # gaps (weekend / feed holes): bars are only those with ticks; the next bar after a gap is flagged
        self.gap_before = np.r_[True, np.diff(self.t) != ms]
        # per-tick row index
        r = np.floor(bid / row + 1e-9).astype(np.int64)
        self.rlo = np.minimum.reduceat(r, first)
        self.rhi = np.maximum.reduceat(r, first)
        self.fp_buy: List[np.ndarray] = []
        self.fp_sell: List[np.ndarray] = []
        self.maxd = np.zeros(n); self.mind = np.zeros(n)
        self.d_sh = np.zeros(n); self.d_sl = np.zeros(n)          # NinjaTrader Delta SH / SL
        self.touch_h = np.zeros(n); self.touch_l = np.zeros(n)   # ticks printed exactly at the bar high / low
        self.poc = np.zeros(n)
        for i in range(n):
            a, e = first[i], ends[i]
            rr = r[a:e] - self.rlo[i]
            sd = side[a:e]
            nb = np.bincount(rr[sd > 0], minlength=self.rhi[i] - self.rlo[i] + 1).astype(float)
            ns = np.bincount(rr[sd < 0], minlength=self.rhi[i] - self.rlo[i] + 1).astype(float)
            self.fp_buy.append(nb); self.fp_sell.append(ns)
            cum = np.cumsum(sd)
            self.maxd[i], self.mind[i] = cum.max(), cum.min()
            bb = bid[a:e]
            ih = np.flatnonzero(bb == self.h[i])[-1]; il = np.flatnonzero(bb == self.l[i])[-1]
            self.d_sh[i] = cum[-1] - cum[ih]; self.d_sl[i] = cum[-1] - cum[il]
            self.touch_h[i] = ((bb == self.h[i]) & (sd != 0)).sum(); self.touch_l[i] = ((bb == self.l[i]) & (sd != 0)).sum()
            tot = nb + ns
            self.poc[i] = (self.rlo[i] + int(np.argmax(tot))) * row + row / 2
        self.n = n
        self.cvd = np.cumsum(self.delta)
        self.atr = atr14(self.h, self.l, self.c)
        self.day = ((self.t + SERVER_UTC_OFFSET_MS) // 86_400_000).astype(np.int64)   # FxPro server day
        self.sma_vol = sma(self.vol, P["sma_n"])
        self.up = self.c > self.o

    def ist(self, i: int) -> str:
        return dt.datetime.fromtimestamp(self.t[i] / 1000, IST).strftime("%m-%d %H:%M IST")

    def row_price(self, i: int, k: int) -> float:
        return (self.rlo[i] + k) * self.row


def atr14(h, l, c) -> np.ndarray:
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.r_[c[0], c[:-1]]), np.abs(l - np.r_[c[0], c[:-1]])))
    tr[0] = h[0] - l[0]
    out = np.empty(len(tr))
    for i in range(len(tr)):
        w = tr[max(0, i - 13): i + 1]
        out[i] = w.mean()
    return out


def sma(x, n) -> np.ndarray:
    out = np.empty(len(x))
    for i in range(len(x)):
        out[i] = x[max(0, i - n + 1): i + 1].mean()
    return out


def pivots(x: np.ndarray, n: int, high: bool) -> np.ndarray:
    """indices of n-bar pivots (strictly beyond the n before, not exceeded by the n after), major_structure._pivot"""
    out = []
    for p in range(n, len(x) - n):
        v = x[p]
        ok = True
        for k in range(1, n + 1):
            a, b = x[p - k], x[p + k]
            if (high and (a >= v or b > v)) or (not high and (a <= v or b < v)):
                ok = False; break
        if ok:
            out.append(p)
    return np.array(out, dtype=int)


# ---------------------------------------------------------------------------------------- footprint rules
def imbalances(buy: np.ndarray, sell: np.ndarray, ratio: float, minvol: float) -> Tuple[np.ndarray, np.ndarray]:
    """diagonal bid/ask imbalance per row (JOAT / ATAS / LuxAlgo): buy[k] vs sell[k-1] (one row lower),
    sell[k] vs buy[k+1] (one row higher). Returns boolean arrays (buy_imb, sell_imb)."""
    n = len(buy)
    bi = np.zeros(n, bool); si = np.zeros(n, bool)
    for k in range(n):
        if k >= 1 and buy[k] >= minvol and buy[k] >= ratio * max(sell[k - 1], 1.0) and (sell[k - 1] > 0 or buy[k] >= ratio * 1):
            bi[k] = True
        if k + 1 < n and sell[k] >= minvol and sell[k] >= ratio * max(buy[k + 1], 1.0):
            si[k] = True
    return bi, si


def stacks(flags: np.ndarray, n: int) -> List[Tuple[int, int]]:
    """runs of >= n consecutive True: list of (first_row, last_row)"""
    out, start = [], None
    for k, f in enumerate(np.r_[flags, False]):
        if f and start is None:
            start = k
        elif not f and start is not None:
            if k - start >= n:
                out.append((start, k - 1))
            start = None
    return out


# ------------------------------------------------------------------------------------------------- signals
def detect(B: Bars) -> Dict[str, List[Dict]]:
    """every signal as {i, dir (+1 bull / -1 bear / 0), level?, note}"""
    S: Dict[str, List[Dict]] = {k: [] for k in ("bar_div", "cvd_div", "absorb", "exhaust", "stack", "unfin", "dflip", "trap",
                                                 "spike", "bigrow", "init", "resp", "pocmig", "lvn", "dhl", "sweep",
                                                 "sweep_conf", "sweep_unconf")}
    n, pn = B.n, P["pivot_n"]
    dpct = np.where(B.vol > 0, B.delta / np.maximum(B.vol, 1), 0.0)
    mad = sma(np.abs(B.delta), P["sma_n"])
    dk = B.delta / np.maximum(np.r_[mad[0], mad[:-1]], 1)      # delta in multiples of the mean |delta| of the 20 bars before
    body = B.c - B.o
    nn = P["new_n"]
    hi_new = np.array([i >= nn and B.h[i] > B.h[i - nn:i].max() for i in range(n)])
    lo_new = np.array([i >= nn and B.l[i] < B.l[i - nn:i].min() for i in range(n)])
    mean_row_hist = np.array([np.mean([B.vol[j] / (B.rhi[j] - B.rlo[j] + 1) for j in range(max(0, i - P["spike_n"] + 1), i + 1)]) for i in range(n)])

    for i in range(1, n):
        if B.gap_before[i] or B.atr[i] <= 0:
            continue
        buy, sell = B.fp_buy[i], B.fp_sell[i]
        tot = buy + sell
        nrows = len(tot)
        mean_row = B.vol[i] / nrows
        # bar-level delta divergence (LuxAlgo delta-divergence: bar closes up on negative delta / down on positive)
        if B.up[i] and dk[i] <= -P["div_k"]:
            S["bar_div"].append(dict(i=i, dir=+1, note=f"up close, delta {dpct[i]:+.0%} = {dk[i]:+.1f}x mean|delta| (sellers absorbed)"))
        elif (not B.up[i]) and body[i] < 0 and dk[i] >= P["div_k"]:
            S["bar_div"].append(dict(i=i, dir=-1, note=f"down close, delta {dpct[i]:+.0%} = {dk[i]:+.1f}x mean|delta| (buyers absorbed)"))
        # absorption: heavy volume, strong one-sided delta, no price progress with the delta
        if B.vol[i] >= P["abs_vol"] * B.sma_vol[i - 1] and abs(dk[i]) >= P["div_k"] and \
                body[i] * np.sign(dpct[i]) <= P["abs_body"] * B.atr[i]:
            S["absorb"].append(dict(i=i, dir=int(-np.sign(dpct[i])), note=f"vol {B.vol[i]/B.sma_vol[i-1]:.1f}x, delta {dpct[i]:+.0%}, body {body[i]/B.atr[i]:+.2f} ATR"))
        # exhaustion: thin tip at a new extreme, delta with the move
        k = P["exh_rows"]
        if hi_new[i] and nrows > 2 * k and tot[-k:].max() <= P["exh_frac"] * mean_row and B.delta[i] > 0:
            S["exhaust"].append(dict(i=i, dir=-1, note=f"top {k} rows <= {P['exh_frac']:.0%} of mean row at a new high"))
        if lo_new[i] and nrows > 2 * k and tot[:k].max() <= P["exh_frac"] * mean_row and B.delta[i] < 0:
            S["exhaust"].append(dict(i=i, dir=+1, note=f"bottom {k} rows <= {P['exh_frac']:.0%} of mean row at a new low"))
        # imbalances, stacks, traps, delta at the high / low
        bi, si = imbalances(buy, sell, P["imb_ratio"], max(P["imb_minvol"], P["imb_minvol_frac"] * mean_row))
        for a, b in stacks(bi, P["stack_n"]):
            S["stack"].append(dict(i=i, dir=+1, lo=B.row_price(i, a), hi=B.row_price(i, b + 1), note=f"{b-a+1} buy imbalances {B.row_price(i,a):.5g}-{B.row_price(i,b+1):.5g}"))
        for a, b in stacks(si, P["stack_n"]):
            S["stack"].append(dict(i=i, dir=-1, lo=B.row_price(i, a), hi=B.row_price(i, b + 1), note=f"{b-a+1} sell imbalances {B.row_price(i,a):.5g}-{B.row_price(i,b+1):.5g}"))
        rng = B.h[i] - B.l[i]
        if rng > 0:
            top = B.h[i] - P["trap_pct"] * rng; bot = B.l[i] + P["trap_pct"] * rng
            rows_bi = [k2 for k2 in range(nrows) if bi[k2] and B.row_price(i, k2) >= top]
            if rows_bi and B.c[i] < B.row_price(i, min(rows_bi)) and B.c[i] <= B.l[i] + 0.5 * rng:
                S["trap"].append(dict(i=i, dir=-1, note=f"{len(rows_bi)} buy imbalance rows in the top {P['trap_pct']:.0%}, close below them"))
            rows_si = [k2 for k2 in range(nrows) if si[k2] and B.row_price(i, k2 + 1) <= bot]
            if rows_si and B.c[i] > B.row_price(i, max(rows_si) + 1) and B.c[i] >= B.h[i] - 0.5 * rng:
                S["trap"].append(dict(i=i, dir=+1, note=f"{len(rows_si)} sell imbalance rows in the bottom {P['trap_pct']:.0%}, close above them"))
        if hi_new[i] and (buy[-1] - sell[-1]) <= 0 and tot[-1] >= P["imb_minvol"]:
            S["dhl"].append(dict(i=i, dir=-1, note=f"top row delta {buy[-1]-sell[-1]:+.0f} at a new high"))
        if lo_new[i] and (buy[0] - sell[0]) >= 0 and tot[0] >= P["imb_minvol"]:
            S["dhl"].append(dict(i=i, dir=+1, note=f"bottom row delta {buy[0]-sell[0]:+.0f} at a new low"))
        # unfinished auction proxy: the exact extreme was printed >= k times at a new n-bar extreme
        # (LuxAlgo unfinished-auction candle form: flat, repeated highs at the same tick) two consecutive bars share the
        # extreme within 1 tick and it is the extreme of the new_n bars before
        if i >= nn + 1 and abs(B.h[i] - B.h[i - 1]) <= B.tick and B.h[i - 1] >= B.h[i - 1 - nn:i - 1].max():
            S["unfin"].append(dict(i=i, dir=0, level=max(B.h[i], B.h[i - 1]), side=+1, note=f"flat high {B.h[i]:.5g} on 2 bars ({int(B.touch_h[i])}+{int(B.touch_h[i-1])} ticks)"))
        if i >= nn + 1 and abs(B.l[i] - B.l[i - 1]) <= B.tick and B.l[i - 1] <= B.l[i - 1 - nn:i - 1].min():
            S["unfin"].append(dict(i=i, dir=0, level=min(B.l[i], B.l[i - 1]), side=-1, note=f"flat low {B.l[i]:.5g} on 2 bars ({int(B.touch_l[i])}+{int(B.touch_l[i-1])} ticks)"))
        # delta flip after a run
        r = P["flip_run"]
        if i >= r and np.sign(B.delta[i]) != 0 and all(np.sign(B.delta[j]) == -np.sign(B.delta[i]) for j in range(i - r, i)):
            S["dflip"].append(dict(i=i, dir=int(np.sign(B.delta[i])), note=f"delta {B.delta[i]:+.0f} after {r} bars of the other sign"))
        # volume spike / big row
        if B.vol[i] >= P["spike_x"] * B.sma_vol[i - 1]:
            S["spike"].append(dict(i=i, dir=0, note=f"vol {B.vol[i]/B.sma_vol[i-1]:.1f}x SMA{P['spike_n']}"))
        if tot.max() >= P["bigrow_x"] * mean_row_hist[i - 1]:
            kk = int(np.argmax(tot))
            S["bigrow"].append(dict(i=i, dir=0, level=B.row_price(i, kk) + B.row / 2, note=f"row {B.row_price(i,kk):.5g} = {tot.max()/mean_row_hist[i-1]:.1f}x mean row"))
        # POC migration
        m = P["pocmig_n"]
        if i >= m and not B.gap_before[i - m + 1:i + 1].any():
            if all(B.poc[j] > B.poc[j - 1] for j in range(i - m + 1, i + 1)):
                S["pocmig"].append(dict(i=i, dir=+1, note=f"POC up {m} bars"))
            elif all(B.poc[j] < B.poc[j - 1] for j in range(i - m + 1, i + 1)):
                S["pocmig"].append(dict(i=i, dir=-1, note=f"POC down {m} bars"))
        # LVN / single print inside the bar (MQL5 17518 single-print test, neighbours above the mean)
        for k2 in range(1, nrows - 1):
            if 2 <= k2 <= nrows - 3 and tot[k2] <= P["lvn_frac"] * mean_row and tot[k2 - 1] >= P["lvn_nb"] * mean_row and tot[k2 + 1] >= P["lvn_nb"] * mean_row:
                S["lvn"].append(dict(i=i, dir=0, level=B.row_price(i, k2) + B.row / 2, note=f"row {B.row_price(i,k2):.5g} = {tot[k2]:.0f} ticks vs mean {mean_row:.0f}"))
                break
        # liquidity sweep of the previous n-bar swing high / low (also the prior server day's extreme)
        j0 = max(0, i - 40)
        ph = pivots(B.h[j0:i + 1], P["sweep_n"], True) + j0
        pl = pivots(B.l[j0:i + 1], P["sweep_n"], False) + j0
        ph = ph[ph < i - P["sweep_n"]]; pl = pl[pl < i - P["sweep_n"]]
        if len(ph):
            lvl = B.h[ph[-1]]
            if B.h[i] >= lvl + P["sweep_atr"] * B.atr[i] and B.c[i] < lvl and B.h[i - 1] < lvl:
                conf = B.delta[i] > 0
                e = dict(i=i, dir=-1, level=lvl, note=f"swept swing high {lvl:.5g}, delta {dpct[i]:+.0%}")
                S["sweep"].append(e); S["sweep_conf" if conf else "sweep_unconf"].append(e)
        if len(pl):
            lvl = B.l[pl[-1]]
            if B.l[i] <= lvl - P["sweep_atr"] * B.atr[i] and B.c[i] > lvl and B.l[i - 1] > lvl:
                conf = B.delta[i] < 0
                e = dict(i=i, dir=+1, level=lvl, note=f"swept swing low {lvl:.5g}, delta {dpct[i]:+.0%}")
                S["sweep"].append(e); S["sweep_conf" if conf else "sweep_unconf"].append(e)

    # CVD divergence at price pivots (regular only; pivots within cvd_max_bars)
    for high in (True, False):
        pv = pivots(B.h if high else B.l, pn, high)
        for a, b in zip(pv[:-1], pv[1:]):
            if b - a > P["cvd_max_bars"] or B.gap_before[a:b + 1].any():
                continue
            if high and B.h[b] > B.h[a] and B.cvd[b] < B.cvd[a]:
                S["cvd_div"].append(dict(i=b + pn, dir=-1, note=f"HH {B.h[a]:.5g}->{B.h[b]:.5g}, CVD {B.cvd[a]:.0f}->{B.cvd[b]:.0f}"))
            if (not high) and B.l[b] < B.l[a] and B.cvd[b] > B.cvd[a]:
                S["cvd_div"].append(dict(i=b + pn, dir=+1, note=f"LL {B.l[a]:.5g}->{B.l[b]:.5g}, CVD {B.cvd[a]:.0f}->{B.cvd[b]:.0f}"))
    # initiative / responsive vs the previous server day's value area (70 % of ticks, CBOT two-row step)
    va = value_areas(B)
    for i in range(n):
        d = B.day[i]
        if d - 1 not in va or B.delta[i] == 0:
            continue
        vah, val = va[d - 1]
        s = int(np.sign(B.delta[i]))
        if (s > 0 and B.c[i] > vah) or (s < 0 and B.c[i] < val):
            S["init"].append(dict(i=i, dir=s, note=f"{'buying above VAH' if s>0 else 'selling below VAL'} ({vah:.5g}/{val:.5g})"))
        elif (s > 0 and B.c[i] < val) or (s < 0 and B.c[i] > vah):
            S["resp"].append(dict(i=i, dir=s, note=f"{'buying below VAL' if s>0 else 'selling above VAH'} ({vah:.5g}/{val:.5g})"))
    return S


def value_areas(B: Bars) -> Dict[int, Tuple[float, float]]:
    out = {}
    for d in np.unique(B.day):
        idx = np.flatnonzero(B.day == d)
        if len(idx) < 50:
            continue
        lo = min(B.rlo[idx]); hi = max(B.rhi[idx])
        prof = np.zeros(hi - lo + 1)
        for i in idx:
            prof[B.rlo[i] - lo: B.rhi[i] - lo + 1] += B.fp_buy[i] + B.fp_sell[i]
        poc = int(np.argmax(prof)); a = b = poc; got = prof[poc]; target = 0.70 * prof.sum()
        while got < target and (a > 0 or b < len(prof) - 1):
            up = prof[b + 1: b + 3].sum() if b < len(prof) - 1 else -1
            dn = prof[max(0, a - 2): a].sum() if a > 0 else -1
            if up >= dn:
                got += up; b = min(len(prof) - 1, b + 2)
            else:
                got += dn; a = max(0, a - 2)
        out[int(d)] = ((hi if False else (lo + b + 1)) * B.row, (lo + a) * B.row)
    return out


# ---------------------------------------------------------------------------------------------- evaluation
def fwd_returns(B: Bars, h: int) -> np.ndarray:
    r = np.full(B.n, np.nan)
    for i in range(B.n - h):
        if not B.gap_before[i + 1:i + h + 1].any() and B.atr[i] > 0:
            r[i] = (B.c[i + h] - B.c[i]) / B.atr[i]
    return r


def perm_test(B: Bars, idx: np.ndarray, dirs: np.ndarray, r: np.ndarray, perms: int, rng: np.random.Generator) -> Tuple[float, float, float]:
    """mean signed return of the signal vs circular shifts of the indicator inside each server day"""
    ok = ~np.isnan(r[idx])
    idx, dirs = idx[ok], dirs[ok]
    if len(idx) < 3:
        return float("nan"), float("nan"), float("nan")
    obs = float(np.mean(dirs * r[idx]))
    days = B.day
    null = np.empty(perms)
    for q in range(perms):
        tot, cnt = 0.0, 0
        for d in np.unique(days[idx]):
            di = np.flatnonzero(days == d)
            m = idx[days[idx] == d]; dd = dirs[days[idx] == d]
            pos = np.searchsorted(di, m)
            sh = rng.integers(len(di))
            newi = di[(pos + sh) % len(di)]
            v = r[newi]; okv = ~np.isnan(v)
            tot += float(np.sum(dd[okv] * v[okv])); cnt += int(okv.sum())
        null[q] = tot / max(cnt, 1)
    p = float((np.abs(null) >= abs(obs)).mean())
    return obs, float(null.std()), p


def level_test(B: Bars, events: List[Dict], window: int, rng: np.random.Generator) -> Dict:
    """revisit rate of a level within `window` bars vs a distance-matched baseline"""
    hits, base = [], []
    for e in events:
        i, lvl = e["i"], e["level"]
        if i + 1 >= B.n:
            continue
        d = lvl - B.c[i]
        j1 = min(B.n, i + 1 + window)
        if B.gap_before[i + 1:j1].any():
            continue
        if d >= 0:
            hit = bool((B.h[i + 1:j1] >= lvl).any())
        else:
            hit = bool((B.l[i + 1:j1] <= lvl).any())
        hits.append(hit)
        # baseline: how often does any bar travel |d| in that direction within the window
        dist = abs(d) / B.atr[i]
        cnt = tot = 0
        for k in range(0, B.n - window - 1, 3):
            if B.gap_before[k + 1:k + 1 + window].any() or B.atr[k] <= 0:
                continue
            tot += 1
            if d >= 0:
                cnt += bool((B.h[k + 1:k + 1 + window] >= B.c[k] + dist * B.atr[k]).any())
            else:
                cnt += bool((B.l[k + 1:k + 1 + window] <= B.c[k] - dist * B.atr[k]).any())
        base.append(cnt / max(tot, 1))
    if not hits:
        return dict(n=0)
    hits = np.array(hits, float); base = np.array(base)
    obs = hits.mean(); exp = base.mean()
    # bootstrap of the baseline Bernoulli draws
    sims = np.array([(rng.random(len(base)) < base).mean() for _ in range(2000)])
    p = float((np.abs(sims - exp) >= abs(obs - exp)).mean())
    return dict(n=len(hits), hit=round(float(obs), 3), base=round(float(exp), 3), p=round(p, 3))


def zone_test(B: Bars, zones: List[Dict], rng: np.random.Generator) -> Dict:
    """stacked-imbalance zone as S/R: first retest inside zone_bars; held = price bounced >= 0.5 ATR away from
    the zone before any close through it. Baseline: the same test on random price bands of the same width at
    the same distance from the close."""
    def run(lo, hi, i, side):
        j1 = min(B.n, i + 1 + P["zone_bars"])
        for j in range(i + 1, j1):
            if B.gap_before[j]:
                return None
            if side > 0:        # support: a close below = through
                if B.c[j] < lo:
                    return False
                if B.l[j] <= hi:
                    for k in range(j, min(j1, j + 12)):
                        if B.c[k] < lo:
                            return False
                        if B.h[k] >= hi + 0.5 * B.atr[i]:
                            return True
                    return False
            else:
                if B.c[j] > hi:
                    return False
                if B.h[j] >= lo:
                    for k in range(j, min(j1, j + 12)):
                        if B.c[k] > hi:
                            return False
                        if B.l[k] <= lo - 0.5 * B.atr[i]:
                            return True
                    return False
        return None
    res, base = [], []
    for z in zones:
        i, lo, hi, side = z["i"], z["lo"], z["hi"], z["dir"]
        if i + 1 >= B.n or (i + 1 < B.n and ((side > 0 and B.c[i + 1] < lo) or (side < 0 and B.c[i + 1] > hi))):
            continue   # ATAS imbalance-levels: a level the very next candle takes out is noise
        r = run(lo, hi, i, side)
        if r is None:
            continue
        res.append(r)
        off = (lo - B.c[i]) if side > 0 else (hi - B.c[i])
        w = hi - lo
        bs = []
        for _ in range(20):
            k = int(rng.integers(1, B.n - P["zone_bars"] - 2))
            sc = B.atr[k] / B.atr[i] if B.atr[i] > 0 else 1
            if side > 0:
                l2 = B.c[k] + off * sc; h2 = l2 + w * sc
            else:
                h2 = B.c[k] + off * sc; l2 = h2 - w * sc
            rb = run(l2, h2, k, side)
            if rb is not None:
                bs.append(rb)
        base.append(np.mean(bs) if bs else np.nan)
    if not res:
        return dict(n=0)
    res = np.array(res, float); base = np.array(base, float)
    ok = ~np.isnan(base)
    if not ok.any():
        return dict(n=int(len(res)), held=round(float(res.mean()), 3))
    bb = base[ok]; obs = res[ok].mean(); exp = bb.mean()
    sims = np.array([(rng.random(len(bb)) < bb).mean() for _ in range(2000)])
    p = float((np.abs(sims - exp) >= abs(obs - exp)).mean())
    return dict(n=int(len(res)), held=round(float(obs), 3), base=round(float(exp), 3), p=round(p, 3))


def evaluate(B: Bars, S: Dict[str, List[Dict]], rng: np.random.Generator) -> Dict:
    R = {h: fwd_returns(B, h) for h in P["horizons"]}
    out = {}
    per100 = 100.0 / max(B.n, 1)
    for name, ev in S.items():
        row = dict(n=len(ev), per100bars=round(len(ev) * per100, 1))
        if ev and all(e["dir"] != 0 for e in ev):
            idx = np.array([e["i"] for e in ev]); dirs = np.array([e["dir"] for e in ev], float)
            for h in P["horizons"]:
                obs, sd, p = perm_test(B, idx, dirs, R[h], P["perms"], rng)
                row[f"h{h}"] = dict(mean_atr=round(obs, 3), null_sd=round(sd, 3), p=round(p, 3))
        elif ev:
            idx = np.array([e["i"] for e in ev])
            for h in P["horizons"]:   # undirected: absolute move vs all bars
                v = R[h][idx]; v = v[~np.isnan(v)]
                allv = R[h][~np.isnan(R[h])]
                row[f"h{h}"] = dict(abs_mean=round(float(np.abs(v).mean()), 3) if len(v) else None, all_abs_mean=round(float(np.abs(allv).mean()), 3))
        out[name] = row
    out["unfin"]["revisit"] = level_test(B, S["unfin"], P["revisit_bars"], rng)
    nn = P["new_n"]
    fin = [dict(i=i, level=B.h[i]) for i in range(nn + 1, B.n) if B.h[i] > B.h[i - nn:i].max() and B.h[i] - B.h[i - 1] >= 0.3 * B.atr[i]] + \
          [dict(i=i, level=B.l[i]) for i in range(nn + 1, B.n) if B.l[i] < B.l[i - nn:i].min() and B.l[i - 1] - B.l[i] >= 0.3 * B.atr[i]]
    out["unfin"]["finished_control"] = level_test(B, fin, P["revisit_bars"], rng)
    out["lvn"]["revisit"] = level_test(B, S["lvn"], P["revisit_bars"], rng)
    out["bigrow"]["revisit"] = level_test(B, S["bigrow"], P["revisit_bars"], rng)
    out["stack"]["zone"] = zone_test(B, S["stack"], rng)
    return out


# ----------------------------------------------------------------------------------- David's BOS + delta
def bos_test(B: Bars, rng: np.random.Generator) -> Optional[Dict]:
    try:
        sys.path.insert(0, "/home/david/forex")
        from engine.major_structure import major_structure   # read-only use
    except Exception as ex:  # pragma: no cover
        return {"error": repr(ex)}
    bars = [dict(t=int(B.t[i] // 1000), o=float(B.o[i]), h=float(B.h[i]), l=float(B.l[i]), c=float(B.c[i])) for i in range(B.n)]
    m = major_structure(bars, n=5, pullback_atr=3.0, margin_atr=0.25)
    strong, weak = [], []
    for e in m["events"]:
        i = e["idx"]; d = +1 if e["side"] == "buy" else -1
        dp = B.delta[i] / max(B.vol[i], 1)
        rec = dict(i=i, dir=d, note=f"{e['kind']} {e['side']} delta {dp:+.0%} vol {B.vol[i]/B.sma_vol[max(i-1,0)]:.1f}x")
        mad = sma(np.abs(B.delta), P["sma_n"])[max(i - 1, 0)]
        (strong if (B.delta[i] * d >= P["div_k"] * mad and B.vol[i] >= 1.2 * B.sma_vol[max(i - 1, 0)]) else weak).append(rec)
    out = {"events": len(m["events"])}
    R = {h: fwd_returns(B, h) for h in P["horizons"]}
    for nm, ev in (("strong_delta", strong), ("weak_delta", weak)):
        row = dict(n=len(ev))
        if len(ev) >= 3:
            idx = np.array([e["i"] for e in ev]); dirs = np.array([e["dir"] for e in ev], float)
            for h in P["horizons"]:
                obs, sd, p = perm_test(B, idx, dirs, R[h], P["perms"], rng)
                row[f"h{h}"] = dict(mean_atr=round(obs, 3), p=round(p, 3))
        row["examples"] = [f"{B.ist(e['i'])} {e['note']}" for e in ev[:4]]
        out[nm] = row
    return out


# ------------------------------------------------------------------------------------------------ selftest
def selftest() -> None:
    """reproduce published worked examples on toy inputs"""
    # 1) ATAS 'how to find and trade imbalance': 116 bids vs 26 asks = 446 %, 86 vs 8 = 1075 % -> both >= 300 %
    assert round(116 / 26 * 100) == 446 and round(86 / 8 * 100) == 1075
    # 2) JOAT diagonal rule: buy[k] >= ratio x sell[k-1]; sell[k] >= ratio x buy[k+1]; stacked >= 3 consecutive rows
    buy = np.array([0, 30, 40, 50, 10, 5], float)     # rows low -> high
    sell = np.array([5, 5, 5, 5, 40, 60], float)
    bi, si = imbalances(buy, sell, 3.0, 5)
    assert bi.tolist() == [False, True, True, True, False, False], bi
    assert si.tolist() == [False, False, False, False, True, False], si   # sell[4]=40 vs buy[5]=5 -> 8x; sell[5] has no row above
    assert stacks(bi, 3) == [(1, 3)] and stacks(si, 3) == []
    # 3) LuxAlgo delta divergence (bearish: later high higher, delta/CVD at that high lower) on a toy series
    h = np.array([1, 2, 3, 2, 1, 2, 3.5, 2, 1], float)
    cvd = np.array([0, 5, 10, 8, 6, 7, 9, 8, 7], float)
    pv = pivots(h, 2, True)
    assert pv.tolist() == [2, 6] and h[6] > h[2] and cvd[6] < cvd[2]
    # 4) Cont-Kukanov-Stoikov OFI e_n on a toy L1 sequence: bid size up at same price -> +dq; bid price up -> +q_new;
    #    ask price down -> -q_new ; ask size up at same price -> -dq
    def e_n(pb0, qb0, pa0, qa0, pb1, qb1, pa1, qa1):
        return (qb1 if pb1 >= pb0 else 0) - (qb0 if pb1 <= pb0 else 0) - (qa1 if pa1 <= pa0 else 0) + (qa0 if pa1 >= pa0 else 0)
    assert e_n(10, 100, 11, 100, 10, 150, 11, 100) == 50          # bid queue grew by 50
    assert e_n(10, 100, 11, 100, 10.5, 70, 11, 100) == 70          # new better bid of 70
    assert e_n(10, 100, 11, 100, 10, 100, 10.5, 40) == -40         # new better ask of 40
    assert e_n(10, 100, 11, 100, 10, 100, 11, 160) == -60          # ask queue grew by 60
    # 5) tick rule on changed quotes (default): up = buy, down = sell, unchanged = 0; classic variant carries forward
    tk = {"bid": np.array([1.0, 1.0, 1.1, 1.1, 1.0, 1.0, 1.2]), "ask": np.zeros(7), "last": np.zeros(7)}
    assert classify_ticks(tk).tolist() == [0, 0, 1, 0, -1, 0, 1]
    assert classify_ticks(tk, "tick_rule_bid").tolist() == [1, 1, 1, 1, -1, -1, 1]
    # 6) NinjaTrader Delta SH / SL on a toy bar: delta since the LAST touch of the high / low
    side = np.array([1, 1, 1, -1, -1, 1, -1, -1], int)             # bid path 1,2,3,2,1,2,1,0 : high at tick 2, low at tick 7
    cum = np.cumsum(side)
    assert cum[-1] - cum[2] == -3 and cum[-1] - cum[7] == 0
    # 7) with the tick rule the exact high can only hold buy ticks: the auction is ALWAYS 'finished' at tick size
    bid = np.array([1.00, 1.01, 1.02, 1.01, 1.02, 1.01, 1.00])
    s = classify_ticks({"bid": bid, "ask": bid, "last": bid})
    assert (s[bid == bid.max()] > 0).all() and (s[bid == bid.min()] <= 0).all()
    print("selftest ok: ATAS imbalance %, JOAT diagonal + stack, LuxAlgo divergence, CKS OFI, tick rule, NT Delta SH/SL, finished-auction property")


# ---------------------------------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=DATA)
    ap.add_argument("--out", default=HERE)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--method", default="tick_rule_changed")
    ap.add_argument("--perms", type=int, default=P["perms"])
    ap.add_argument("--imb-minvol-frac", type=float, default=P["imb_minvol_frac"], help="0 = absolute imb_minvol only (the common vendor default)")
    ap.add_argument("--name", default="proto_results.json")
    args = ap.parse_args()
    P["imb_minvol_frac"] = args.imb_minvol_frac
    if args.selftest:
        selftest(); return
    P["perms"] = args.perms
    rng = np.random.default_rng(7)
    results = {"params": {k: v for k, v in P.items()}, "method": args.method, "symbols": {}}
    for sym in ("GOLD", "EURUSD"):
        tk = load_ticks(os.path.join(args.data, f"{sym}_ticks.csv.gz"))
        side = classify_ticks(tk, args.method)
        print(f"\n=== {sym}: {len(tk['t'])} ticks after de-dup, {np.mean(side != 0):.1%} changed the bid, buy share of those {np.mean(side > 0) / max(np.mean(side != 0), 1e-9):.1%}", flush=True)
        for tf in (5, 15):
            B = Bars(tk, side, tf, P["row"][sym], P["tick"][sym])
            S = detect(B)
            ev = evaluate(B, S, rng)
            days = {}
            for name, lst in S.items():
                for e in lst:
                    d = dt.datetime.fromtimestamp(B.t[e["i"]] / 1000, IST).strftime("%m-%d")
                    days.setdefault(name, {}).setdefault(d, 0)
                    days[name][d] += 1
            ex = {name: [f"{B.ist(e['i'])} {'bull' if e['dir']>0 else 'bear' if e['dir']<0 else '-'} {e['note']}" for e in lst[:3]] for name, lst in S.items()}
            bos = bos_test(B, rng)
            key = f"{sym}_M{tf}"
            results["symbols"][key] = dict(bars=B.n, days=int(len(np.unique(B.day))), signals=ev, per_day=days, examples=ex, bos=bos,
                                           finished_at_tick={"highs_with_1_touch": float(np.mean(B.touch_h == 1)), "lows_with_1_touch": float(np.mean(B.touch_l == 1))})
            print(f"--- {key}: {B.n} bars, ATR median {np.median(B.atr):.5g}")
            for name, row in ev.items():
                line = f"{name:12s} n={row['n']:4d} /100bars={row['per100bars']:5.1f}"
                for h in P["horizons"]:
                    r = row.get(f"h{h}")
                    if r and "mean_atr" in r:
                        line += f" | h{h} {r['mean_atr']:+.2f}ATR p={r['p']:.2f}"
                    elif r:
                        line += f" | h{h} |r| {r['abs_mean']} vs {r['all_abs_mean']}"
                for k in ("revisit", "finished_control", "zone"):
                    if k in row:
                        line += f" | {k} {row[k]}"
                print(line)
            print("BOS:", json.dumps(bos)[:400])
    with open(os.path.join(args.out, args.name), "w") as f:
        json.dump(results, f, indent=1, default=float)
    print("\nwritten", os.path.join(args.out, args.name))


if __name__ == "__main__":
    main()
