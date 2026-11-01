"""
ports.py — line-by-line Python (numpy only) ports of six public supply & demand tools, 2026-10-30.

All ports take parallel float arrays o, h, l, c (oldest first; chronological index i = 0 .. n-1) and an optional
volume array v, and return a list of zone dicts:
    {tool, side ('supply'|'demand'), top, bottom, idx (the bar the zone is anchored to), known_idx (the bar on
     which the tool first draws it), ...tool-specific status fields}

Sources (code read, not descriptions):
  shved      MQL5 CodeBase 14545 (MT4 original by "Shved", 2016) and 29395 (MT5 port by Behzad.mvr, v1.7, 2023)
             https://www.mql5.com/en/code/14545   https://www.mql5.com/en/code/29395
  cmike      npm @cmike444/supply-and-demand-zones 1.3.1 (MIT), github.com/cmike444/SupplyAndDemand
             https://unpkg.com/@cmike444/supply-and-demand-zones@1.3.1/dist/lib/identifyZones.js (+ rallyBaseDrop.js …)
  svopex     TradingView "Svopex S&D Scan" (open source, Pine v6) https://www.tradingview.com/script/Jywsoivw-Svopex-S-D-Scan/
  flux       TradingView "Supply and Demand Zones | Flux Charts" (4,305 boosts) https://www.tradingview.com/script/ZUAYemgd-Supply-and-Demand-Zones-Flux-Charts/
  bigbeluga  TradingView "Supply and Demand Zones [BigBeluga]" (11,359 boosts) https://www.tradingview.com/script/I0o8N7VW-Supply-and-Demand-Zones-BigBeluga/
  sdzpro     TradingView "Supply Demand Zones PRO" by ProjectSyndicate (5,819 boosts) https://www.tradingview.com/script/h0jxhmgn-Supply-Demand-Zones-Pro/
The Pine sources were fetched from pine-facade.tradingview.com/pine-facade/get/<PUB id>/last; copies are in dl/tv/.
Each port notes where the original is ambiguous ("AMBIGUOUS:").
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np


# ----------------------------------------------------------------------------------------------------------------
# shared helpers
# ----------------------------------------------------------------------------------------------------------------
def true_range(h, l, c):
    tr = h - l
    tr[1:] = np.maximum(tr[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    return tr


def atr_rma(h, l, c, n):
    """Wilder / RMA ATR, the way MetaTrader iATR and Pine ta.atr compute it (first value = simple mean)."""
    tr = true_range(h, l, c)
    out = np.empty_like(tr)
    out[: n] = np.cumsum(tr[: n]) / np.arange(1, n + 1)
    for i in range(n, len(tr)):
        out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


def atr_sma(h, l, c, n):
    """simple mean of the last n true ranges (major_structure.atr14 style)"""
    tr = true_range(h, l, c)
    cs = np.cumsum(np.insert(tr, 0, 0.0))
    out = np.empty_like(tr)
    for i in range(len(tr)):
        a = max(0, i + 1 - n)
        out[i] = (cs[i + 1] - cs[a]) / (i + 1 - a)
    return out


def pivot_high(h, left, right, strict_left=True):
    """Pine ta.pivothigh(high, left, right) — index p is a pivot if high[p] is greater than the `left` bars before and
    greater than the `right` bars after. AMBIGUOUS: Pine's tie rule is undocumented; this uses strict > on both
    sides (strict_left=False allows ties on the left, the MQL Fractal() convention)."""
    n = len(h)
    out = np.zeros(n, dtype=bool)
    for p in range(left, n - right):
        v = h[p]
        lft = h[p - left:p]
        rgt = h[p + 1:p + right + 1]
        if (np.all(lft < v) if strict_left else np.all(lft <= v)) and np.all(rgt < v):
            out[p] = True
    return out


def pivot_low(l, left, right, strict_left=True):
    n = len(l)
    out = np.zeros(n, dtype=bool)
    for p in range(left, n - right):
        v = l[p]
        lft = l[p - left:p]
        rgt = l[p + 1:p + right + 1]
        if (np.all(lft > v) if strict_left else np.all(lft >= v)) and np.all(rgt > v):
            out[p] = True
    return out


# ----------------------------------------------------------------------------------------------------------------
# 1. Shved Supply and Demand (MT4 14545 / MT5 29395)
# ----------------------------------------------------------------------------------------------------------------
SHVED_STRENGTH = {0: "weak", 1: "turncoat", 2: "untested", 3: "verified", 4: "proven"}


def shved_fractal_period(tf_minutes: int, factor: float) -> int:
    """Fractal(): P = timeframe*factor; if timeframe > P: P = timeframe; P = P/timeframe*2 + ceil(P/timeframe/2)
    (all integer arithmetic in MQL) -> fast factor 3 -> 7 bars each side, slow factor 6 -> 15, on EVERY timeframe."""
    P = int(tf_minutes * factor)
    if tf_minutes > P:
        P = tf_minutes
    q = P // tf_minutes
    return q * 2 + math.ceil((q // 2))


def shved_fractals(h, l, P):
    """Fractal(UP_POINT,P,shift): older P bars must be <= High[shift] (fails on >), newer P bars must be < (fails on
    >=). Needs P bars on both sides. Returns (up, dn) boolean arrays in chronological index."""
    up = pivot_high(h, P, P, strict_left=False)
    dn = pivot_low(l, P, P, strict_left=False)
    return up, dn


def shved(o, h, l, c, v=None, tf_minutes=15, back_limit=1000, fuzz=0.75, fast=3.0, slow=6.0, merge=True,
          extend=True, show_weak=False, show_untested=True, show_turncoat=True, asof: Optional[int] = None,
          include_busted=False, **_):
    """FindZones() of shved_supply_and_demand_v1_7.mq5 lines 268-578, evaluated at bar `asof` (default: last bar),
    the way the indicator redraws on every new bar. cnt = 0 (no history mode). Returns the zones drawn at asof."""
    n = len(c)
    end = n - 1 if asof is None else asof               # series index 0 == chronological `end`
    A7 = atr_rma(h, l, c, 7)
    Pf, Ps = shved_fractal_period(tf_minutes, fast), shved_fractal_period(tf_minutes, slow)
    # FastFractals(): computed for shift in (limit .. 2]; Fractal() also needs shift >= P and shift <= Bars-P-1
    fup, fdn = shved_fractals(h[: end + 1], l[: end + 1], Pf)
    sup, sdn = shved_fractals(h[: end + 1], l[: end + 1], Ps)
    fup[end - 1:] = False; fdn[end - 1:] = False             # FastUpPts[0] = FastUpPts[1] = 0
    sup[end - 1:] = False; sdn[end - 1:] = False
    shift = min(n - 1, back_limit)
    temp = []                                             # dicts hi, lo, turn, hits, start, strength
    busted = []
    # for(ii=shift; ii>cnt+5; ii--): series ii -> chronological k = end - ii
    for ii in range(shift, 5, -1):
        k = end - ii
        if k < 0:
            continue
        atr = A7[k]
        fu = atr / 2 * fuzz
        for kind in ("up", "dn"):
            if kind == "up":
                if not fup[k]:
                    continue
                is_weak = not sup[k]
                hival = h[k] + (fu if extend else 0.0)
                loval = max(min(c[k], h[k] - fu), h[k] - fu * 2)
            else:
                if not fdn[k]:
                    continue
                is_weak = not sdn[k]
                loval = l[k] - (fu if extend else 0.0)
                hival = min(max(c[k], l[k] + fu), l[k] + fu * 2)
            turned = False; hasturned = False; is_bust = False; bustcount = 0; testcount = 0
            # for(i=ii-1; i>=cnt; i--): newer bars, chronological j = k+1 .. end
            for j in range(k + 1, end + 1):
                # a touch = a later FAST fractal of the zone's kind (opposite kind once turned) inside the zone
                if kind == "up":
                    touch = (not turned and fup[j] and loval <= h[j] <= hival) or (turned and fdn[j] and loval <= l[j] <= hival)
                else:
                    touch = (turned and fup[j] and loval <= h[j] <= hival) or (not turned and fdn[j] and loval <= l[j] <= hival)
                if touch:
                    # "just make sure its been 10+ candles since the prev one": for(jj=i+1; jj<i+11) = the 10 OLDER bars
                    touch_ok = True
                    for jj in range(j - 1, max(j - 11, -1), -1):  # the 10 OLDER bars, the zone's own fractal bar included
                        if kind == "up":                            # (so a touch < 10 bars after the zone bar never counts)
                            t2 = (not turned and fup[jj] and loval <= h[jj] <= hival) or (turned and fdn[jj] and loval <= l[jj] <= hival)
                        else:
                            t2 = (turned and fup[jj] and loval <= h[jj] <= hival) or (not turned and fdn[jj] and loval <= l[jj] <= hival)
                        if t2:
                            touch_ok = False
                            break
                    if touch_ok:
                        bustcount = 0
                        testcount += 1
                # bust: a WICK through the far side
                if kind == "up":
                    bust = (not turned and h[j] > hival) or (turned and l[j] < loval)
                else:
                    bust = (turned and h[j] > hival) or (not turned and l[j] < loval)
                if bust:
                    bustcount += 1
                    if bustcount > 1 or is_weak:
                        is_bust = True
                        break
                    turned = not turned
                    hasturned = True
                    testcount = 0
            if is_bust:
                if include_busted:                      # not in the original: busted zones are simply not drawn
                    busted.append({"tool": "shved", "side": "supply" if kind == "up" else "demand", "kind": kind,
                                   "top": hival, "bottom": loval, "idx": k, "known_idx": k + Pf, "strength": "busted",
                                   "bust_idx": j, "hits": testcount, "turned": hasturned, "weak": is_weak, "shown": False})
                continue
            if testcount > 3:
                strength = 4
            elif testcount > 0:
                strength = 3
            elif hasturned:
                strength = 1
            elif not is_weak:
                strength = 2
            else:
                strength = 0
            temp.append({"hi": hival, "lo": loval, "turn": hasturned, "hits": testcount, "start": k,
                         "strength": strength, "kind": kind, "merged_from": 1})
    if merge:
        merge_count, iterations = 1, 0
        while merge_count > 0 and iterations < 3:
            merge_count = 0
            iterations += 1
            flag = [False] * len(temp)
            pairs = []
            for i in range(len(temp) - 1):
                if temp[i]["hits"] == -1 or flag[i]:
                    continue
                for j in range(i + 1, len(temp)):
                    if temp[j]["hits"] == -1 or flag[j]:
                        continue
                    a, b = temp[i], temp[j]
                    if (b["lo"] <= a["hi"] <= b["hi"]) or (b["lo"] <= a["lo"] <= b["hi"]) or \
                       (a["lo"] <= b["hi"] <= a["hi"]) or (a["lo"] <= b["lo"] <= a["hi"]):
                        pairs.append((i, j)); flag[i] = flag[j] = True; merge_count += 1
            for i, j in pairs:
                t, s = temp[i], temp[j]
                t["hi"] = max(t["hi"], s["hi"]); t["lo"] = min(t["lo"], s["lo"])
                t["hits"] += s["hits"]
                t["start"] = min(t["start"], s["start"])        # MathMax of series shifts = the OLDER bar
                t["strength"] = max(t["strength"], s["strength"])
                t["merged_from"] += s["merged_from"]
                if t["hits"] > 3:
                    t["strength"] = 4
                if t["hits"] == 0 and not t["turn"]:
                    t["hits"] = 1
                    if t["strength"] < 3:
                        t["strength"] = 3
                if not t["turn"] or not s["turn"]:
                    t["turn"] = False
                if t["turn"]:
                    t["hits"] = 0
                s["hits"] = -1
    zones = []
    for z in temp:
        if z["hits"] < 0:
            continue
        if z["hi"] < c[end]:
            ztype = "support"
        elif z["lo"] > c[end]:
            ztype = "resist"
        else:                                               # price inside: the first earlier close outside decides
            ztype = "support"
            for j in range(end - 1, max(end - shift, -1), -1):
                if c[j] < z["lo"]:
                    ztype = "resist"; break
                if c[j] > z["hi"]:
                    ztype = "support"; break
        st = SHVED_STRENGTH[z["strength"]]
        shown = not ((st == "weak" and not show_weak) or (st == "untested" and not show_untested) or (st == "turncoat" and not show_turncoat))
        zones.append({"tool": "shved", "side": "supply" if ztype == "resist" else "demand", "kind": z["kind"],
                      "top": z["hi"], "bottom": z["lo"], "idx": z["start"], "known_idx": z["start"] + Pf,
                      "strength": st, "hits": z["hits"], "turned": z["turn"], "merged_from": z["merged_from"],
                      "shown": shown, "weak": z["strength"] == 0})
    return zones + busted


# ----------------------------------------------------------------------------------------------------------------
# 2. cmike444 supply-and-demand-zones (rally-base-drop family, Sam Seiden style)
# ----------------------------------------------------------------------------------------------------------------
CM = dict(EXPLOSIVE=0.7, DECISIVE=0.5, MIN_BASE=1, MAX_BASE=6, MIN_ZONE_CANDLES=5, ATR_PERIOD=14,
          MAX_ZONE_ATR=1.5, MAX_BASE_GAP_ATR=0.5, MIN_EXPLOSIVE_ATR=1.5)


def _cm_atr(o, h, l, c, i, period=14):
    """atr(candles.slice(max(0, i-14), i)): the 14 candles BEFORE i; TR needs a previous candle so <= 13 TRs."""
    a = max(0, i - period)
    seg_h, seg_l, seg_c = h[a:i], l[a:i], c[a:i]
    if len(seg_h) == 0:
        return 0.0
    if len(seg_h) == 1:
        return float(seg_h[0] - seg_l[0])
    tr = np.maximum(seg_h[1:] - seg_l[1:], np.maximum(np.abs(seg_h[1:] - seg_c[:-1]), np.abs(seg_l[1:] - seg_c[:-1])))
    tr = tr[-period:]
    return float(tr.mean())


def cmike(o, h, l, c, v=None, **_):
    n = len(c)
    body = np.abs(c - o)
    rng = h - l
    bull = c > o
    bear = c < o
    ratio = np.where(rng > 0, body / np.where(rng > 0, rng, 1.0), 0.0)
    decisive = (body > 0) & (ratio > CM["DECISIVE"])
    indecisive = (body == 0) | (ratio <= CM["DECISIVE"])      # isIndecisiveCandle: body 0 -> true

    def run_end(start, cond, max_count=None):
        k, cnt = start, 0
        while k < n and cond(k) and (max_count is None or cnt < max_count):
            k += 1; cnt += 1
        return k

    def explosive(k, min_atr):
        if body[k] == 0:
            return False
        if min_atr > 0 and rng[k] < min_atr:
            return False
        return ratio[k] >= CM["EXPLOSIVE"]

    def valid_base(b0, b1, atr):
        if atr <= 0:
            return True
        for k in range(b0 + 1, b1):                      # gaps between base candles only
            if abs(o[k] - c[k - 1]) > CM["MAX_BASE_GAP_ATR"] * atr:
                return False
        if h[b0:b1].max() - l[b0:b1].min() > CM["MAX_ZONE_ATR"] * atr:
            return False
        return True

    def pattern(i, leg_in_bull, leg_out_bull, atr):
        """rallyBaseDrop / dropBaseDrop / dropBaseRally / rallyBaseRally with the slice starting at i"""
        if n - i < CM["MIN_ZONE_CANDLES"]:
            return None
        leg_in = (lambda k: decisive[k] and bull[k]) if leg_in_bull else (lambda k: decisive[k] and bear[k])
        in_end = run_end(i, leg_in)
        if in_end == i:
            return None
        base_end = run_end(in_end, lambda k: indecisive[k], CM["MAX_BASE"])
        if base_end - in_end < CM["MIN_BASE"]:
            return None
        min_atr = CM["MIN_EXPLOSIVE_ATR"] * atr
        leg_out = (lambda k: explosive(k, min_atr) and bull[k]) if leg_out_bull else (lambda k: explosive(k, min_atr) and bear[k])
        out_end = run_end(base_end, leg_out)
        if out_end == base_end:
            return None
        if not valid_base(in_end, base_end, atr):
            return None
        bo, bc = o[in_end:base_end], c[in_end:base_end]
        if leg_out_bull:
            prox = float(np.maximum(bo, bc).max()); dist = float(l[i:out_end].min()); side = "demand"
        else:
            prox = float(np.minimum(bo, bc).min()); dist = float(h[i:out_end].max()); side = "supply"
        dep = slice(base_end, out_end)
        strong = (decisive[dep] & (bull[dep] if leg_out_bull else bear[dep])) | \
                 ((ratio[dep] >= CM["EXPLOSIVE"]) & (body[dep] > 0) & (bull[dep] if leg_out_bull else bear[dep]))
        count_f = strong.mean()
        range_f = min(rng[dep].mean() / atr, 1.0) if atr > 0 else 0.5
        if v is not None:
            avg_dep = v[dep].mean(); avg_base = v[in_end:base_end].mean()
            r = avg_dep / avg_base if avg_base > 0 else 1.0
            vol_f = r / (r + 1)
        else:
            vol_f = 0.5
        bc_n = base_end - in_end
        time_f = 1.0 if bc_n <= 3 else 0.5 if bc_n <= 6 else 0.0
        conf = (count_f + range_f + vol_f + time_f) / 4
        return {"tool": "cmike", "side": side, "top": max(prox, dist), "bottom": min(prox, dist), "proximal": prox,
                "distal": dist, "idx": in_end, "base_end": base_end - 1, "known_idx": out_end - 1,
                "start": i, "end": out_end - 1, "type": ("R" if leg_in_bull else "D") + "B" + ("R" if leg_out_bull else "D"),
                "dep_conf": conf, "base_n": bc_n}

    zones = []
    i = 0
    gmin, gmax = l.min(), h.max()
    pr = gmax - gmin
    while i < n:
        atr = _cm_atr(o, h, l, c, i, CM["ATR_PERIOD"])
        z = None
        for leg_in_bull, leg_out_bull in ((True, False), (False, False), (False, True), (True, True)):  # RBD, DBD, DBR, RBR
            z = pattern(i, leg_in_bull, leg_out_bull, atr)
            if z:
                break
        if z is None:
            i += 1
            continue
        post = slice(z["end"] + 1, n)
        entered = (h[post] >= z["proximal"]).any() if z["side"] == "supply" else (l[post] <= z["proximal"]).any()
        fresh_f = 0.5 if entered else 1.0
        pos = (z["proximal"] - gmin) / pr if pr > 0 else 0.5
        pos_f = pos if z["side"] == "supply" else 1 - pos
        tf_f = 0.5                                      # timeframeFactor needs timestamps; 15m ~ 0.26, 1h ~ 0.48
        conf = (z["dep_conf"] * 3 + pos_f + fresh_f + tf_f) / 6
        stop = abs(z["proximal"] - z["distal"])
        ext = l[: z["end"] + 1].min() if z["side"] == "supply" else h[: z["end"] + 1].max()   # as coded: ALL candles <= end
        rr = min(abs(ext - z["proximal"]) / stop / 5, 1.0) if stop > 0 else 0.0
        z["confidence"] = (conf * 6 + rr) / 7
        z["fresh"] = not entered
        zones.append(z)
        i = z["end"] + 1                                 # i += endIdx; continue; (then the for's i++)
    # filterFreshZones: a demand whose proximal is above a supply's proximal conflicts; the older one goes
    stale = set()
    for d in [z for z in zones if z["side"] == "demand"]:
        for s in [z for z in zones if z["side"] == "supply"]:
            if d["proximal"] > s["proximal"]:
                if d["end"] < s["end"]:
                    stale.add(id(d))
                elif s["end"] < d["end"]:
                    stale.add(id(s))
                else:
                    stale.add(id(d))
    for z in zones:
        z["stale"] = id(z) in stale
    return zones


# ----------------------------------------------------------------------------------------------------------------
# 3. Svopex S&D Scan (base candles + explosive body, ATR units)
# ----------------------------------------------------------------------------------------------------------------
def svopex(o, h, l, c, v=None, base_max=3, base_body_pct=0.5, expl_mult=1.5, atr_len=14, max_zones=20,
           use_wicks=True, break_pct=0, **_):
    """f_detect() + f_track() + f_break() of Svopex S&D Scan. NOTE the default break_pct = 0 means
    thr = bot + 0 -> a supply zone is removed the first time a bar's high reaches its BOTTOM edge (first touch),
    so with defaults every zone is 'fresh or gone'. break_pct=100 = removed when the far edge is exceeded."""
    n = len(c)
    atr = atr_rma(h, l, c, atr_len)
    body = np.abs(c - o)
    hi_src = h if use_wicks else np.maximum(o, c)
    lo_src = l if use_wicks else np.minimum(o, c)
    zones, sup, dem = [], [], []
    base_count, base_h, base_l, base_t = 0, np.nan, np.nan, -1
    pct = break_pct / 100.0
    for i in range(n):
        is_base = body[i] < base_body_pct * atr[i]
        up = (c[i] - o[i]) > expl_mult * atr[i]
        dn = (o[i] - c[i]) > expl_mult * atr[i]
        sig = 0
        if is_base:
            if base_count == 0:
                base_h, base_l, base_t = h[i], l[i], i
            else:
                base_h, base_l = max(base_h, h[i]), min(base_l, l[i])
            base_count += 1
        elif 1 <= base_count <= base_max and up:
            sig = 2
            z = {"tool": "svopex", "side": "demand", "top": base_h, "bottom": base_l, "idx": base_t, "base_n": base_count,
                 "known_idx": i + 1, "expl_idx": i, "removed_idx": None, "touched_idx": None}
            zones.append(z); dem.append(z)
            if len(dem) > max_zones: dem.pop(0)
            base_count = 0
        elif 1 <= base_count <= base_max and dn:
            sig = 1
            z = {"tool": "svopex", "side": "supply", "top": base_h, "bottom": base_l, "idx": base_t, "base_n": base_count,
                 "known_idx": i + 1, "expl_idx": i, "removed_idx": None, "touched_idx": None}
            zones.append(z); sup.append(z)
            if len(sup) > max_zones: sup.pop(0)
            base_count = 0
        else:
            base_count = 0
        # f_all() hands sig[1]/zone[1] on: the zone exists from bar i+1; f_break runs on every confirmed bar
        for arr in (sup, dem):
            for z in list(arr):
                if z["known_idx"] > i:
                    continue
                hgt = z["top"] - z["bottom"]
                if z["side"] == "supply":
                    if z["touched_idx"] is None and hi_src[i] >= z["bottom"] and lo_src[i] <= z["top"]:
                        z["touched_idx"] = i
                    if hi_src[i] >= z["bottom"] + hgt * pct:
                        z["removed_idx"] = i; arr.remove(z)
                else:
                    if z["touched_idx"] is None and hi_src[i] >= z["bottom"] and lo_src[i] <= z["top"]:
                        z["touched_idx"] = i
                    if lo_src[i] <= z["top"] - hgt * pct:
                        z["removed_idx"] = i; arr.remove(z)
    return zones


# ----------------------------------------------------------------------------------------------------------------
# 4. Flux Charts — Supply and Demand Zones
# ----------------------------------------------------------------------------------------------------------------
def flux(o, h, l, c, v=None, pivot_len=30, lookback=2000, cooldown=3, hold_bars=10, wick_avg_bars=5, **_):
    n = len(c)
    ph = pivot_high(h, pivot_len, pivot_len)
    pl = pivot_low(l, pivot_len, pivot_len)
    zones = []

    def bounds(p, is_supply):
        ks = range(p, p - wick_avg_bars, -1)            # the pivot bar and the 4 before it (barsBack + k)
        ks = [k for k in ks if k >= 0]
        if is_supply:
            avg = np.mean([h[k] - max(o[k], c[k]) for k in ks])
            return h[p], h[p] - avg
        avg = np.mean([min(o[k], c[k]) - l[k] for k in ks])
        return l[p] + avg, l[p]

    def overlap(top, bot, i):
        for z in zones:
            if z["active"] and i - z["idx"] <= lookback and bot <= z["top"] and top >= z["bottom"]:
                return True
        return False

    for i in range(n):
        p = i - pivot_len
        if p >= pivot_len:
            for is_sup, flag in ((True, ph), (False, pl)):
                if flag[p]:
                    t, b = bounds(p, is_sup)
                    if not overlap(t, b, i):
                        zones.append({"tool": "flux", "side": "supply" if is_sup else "demand", "top": t, "bottom": b,
                                      "idx": p, "known_idx": i, "is_supply": is_sup, "orig_supply": is_sup, "active": True,
                                      "pending": False, "retests": 0, "breakouts": 0, "last_retest": -1,
                                      "retest_bars": [], "breakout_bars": [], "flip_idx": None, "first_break_idx": None})
        # updateZones on the confirmed bar i
        for z in zones:
            if z["known_idx"] > i:
                continue
            if z["active"] and i - z["idx"] > lookback:
                z["active"] = False
            if not z["active"]:
                continue
            through = (z["is_supply"] and c[i] > z["top"]) or (not z["is_supply"] and c[i] < z["bottom"])
            back = (z["is_supply"] and c[i] < z["bottom"]) or (not z["is_supply"] and c[i] > z["top"])
            flipped = handled = False
            if z["pending"] and through:
                z["breakouts"] += 1; z["breakout_bars"].append(i)
                z["is_supply"] = not z["is_supply"]; flipped = True
                if z["flip_idx"] is None: z["flip_idx"] = i
                z["pending"] = False; handled = True
            if z["pending"] and back:
                z["retests"] += 1; z["last_retest"] = i; z["retest_bars"].append(i)
                z["pending"] = False; handled = True
            if not handled and not z["pending"] and through:
                z["pending"] = True
                if z["first_break_idx"] is None: z["first_break_idx"] = i
            if z["active"] and not flipped and not z["pending"] and not handled and i > z["idx"] and i - z["last_retest"] >= cooldown:
                reacted = (h[i] >= z["bottom"] and c[i] < z["bottom"]) if z["is_supply"] else (l[i] <= z["top"] and c[i] > z["top"])
                if reacted:
                    z["retests"] += 1; z["last_retest"] = i; z["retest_bars"].append(i)
    for z in zones:                                     # computeHoldStats at the last bar
        hits = resolved = 0
        for rb in z["retest_bars"]:
            if (n - 1) - rb >= hold_bars:
                resolved += 1
                if not any(rb < bb <= rb + hold_bars for bb in z["breakout_bars"]):
                    hits += 1
        z["held"], z["resolved"] = hits, resolved
        z["quality"] = (hits + 1.0) / (resolved + 2.0)
    return zones


# ----------------------------------------------------------------------------------------------------------------
# 5. BigBeluga — Supply and Demand Zones
# ----------------------------------------------------------------------------------------------------------------
def bigbeluga(o, h, l, c, v, atr_len=200, cooldown=15, max_boxes=5, **_):
    """3 consecutive same-colour candles with the PREVIOUS bar's volume above the 1000-bar average; the box sits on
    the last opposite-colour candle within 6 bars: supply = [low_i, low_i + 2*ATR200], demand = [high_i - 2*ATR200,
    high_i]. Deleted on a close beyond the far edge; 'mitigated' (dashed) when, 35+ bars old, a bar straddles the
    near edge. Only 5 boxes per side are kept; an overlapping box is removed."""
    n = len(c)
    atr2 = atr_rma(h, l, c, atr_len) * 2
    bear = c < o; bull = c > o
    extra = np.zeros(n, dtype=bool)
    for i in range(n):
        a = max(0, i - 999)
        extra[i] = v[i] > v[a:i + 1].mean()
    zones = []
    live = {"supply": [], "demand": []}
    cnt = {"supply": 0, "demand": 0}
    for i in range(n):
        for side, same, opp in (("supply", bear, bull), ("demand", bull, bear)):
            if i >= 2 and same[i] and same[i - 1] and same[i - 2] and extra[i - 1] and cnt[side] == 0:
                for k in range(0, 6):
                    j = i - k
                    if j < 0:
                        break
                    if opp[j]:
                        cnt[side] = 1
                        if side == "supply":
                            z = {"top": l[j] + atr2[i], "bottom": l[j]}
                        else:
                            z = {"top": h[j], "bottom": h[j] - atr2[i]}
                        z.update({"tool": "bigbeluga", "side": side, "idx": j, "known_idx": i, "deleted_idx": None,
                                  "mitigated_idx": None, "removed_overlap": False, "evicted": False})
                        zones.append(z); live[side].append(z)
                        break
            if cnt[side] >= 1:
                cnt[side] += 1
            if cnt[side] >= cooldown:
                cnt[side] = 0
        for side in ("supply", "demand"):
            arr = live[side]
            for z in list(arr):
                # NOTE the original's age gate `(b.get_right() - b.get_left() - 15) > 20` is always true because
                # set_right(bar_index + 100) runs just before it -> the dashed "mitigated" style needs no age.
                if side == "supply":
                    if c[i] > z["top"]:
                        z["deleted_idx"] = i; arr.remove(z); continue
                    if h[i] > z["bottom"] and l[i] < z["bottom"] and z["mitigated_idx"] is None:
                        z["mitigated_idx"] = i
                else:
                    if c[i] < z["bottom"]:
                        z["deleted_idx"] = i; arr.remove(z); continue
                    if l[i] < z["top"] and h[i] > z["top"] and z["mitigated_idx"] is None:
                        z["mitigated_idx"] = i
            # overlap: box i goes when another box's near edge lies strictly inside it
            removed = True
            while removed:
                removed = False
                for a in arr:
                    for b in arr:
                        if a is b:
                            continue
                        edge = b["top"] if side == "supply" else b["bottom"]
                        if a["bottom"] < edge < a["top"]:
                            a["removed_overlap"] = True; a["deleted_idx"] = i; arr.remove(a); removed = True
                            break
                    if removed:
                        break
            if len(arr) > max_boxes:
                z = arr.pop(0); z["evicted"] = True; z["deleted_idx"] = i
    return zones


# ----------------------------------------------------------------------------------------------------------------
# 6. Supply Demand Zones PRO (ProjectSyndicate)
# ----------------------------------------------------------------------------------------------------------------
def sdzpro(o, h, l, c, v=None, swing_len=12, max_h_atr=1.0, min_h_atr=1.0, force_h_atr=1.0, min_dist=44,
           atr_len=20, hours=None, invalidation="Close", **_):
    """pivot candle (12/12) box = that candle's high..low, forced to >= 1 ATR(20) and clamped to <= 1 ATR around
    its mid (so with defaults EVERY zone is exactly 1 ATR tall); min 44 bars between zones per side; overlapping
    unbroken zones of the same side merge (union); retest = a bar entering the box; broken = a close beyond the
    far edge; strength = 8 - 0.8*retests - min(age/500, 2). `hours`: optional array of exchange-time hours; a
    pivot confirmed at hour 22-23 is skipped ("Other" session)."""
    n = len(c)
    atr = atr_rma(h, l, c, atr_len)
    ph = pivot_high(h, swing_len, swing_len)
    pl = pivot_low(l, swing_len, swing_len)
    zones = []
    last = {"supply": 0, "demand": 0}
    for i in range(n):
        p = i - swing_len
        if p >= swing_len:
            for side, flag in (("supply", ph), ("demand", pl)):
                if not flag[p]:
                    continue
                if hours is not None and hours[i] >= 22:
                    continue
                if i - last[side] < min_dist:
                    continue
                top, bot = h[p], l[p]
                mid = (top + bot) / 2
                hgt = top - bot
                if hgt < atr[i] * force_h_atr:
                    hgt = atr[i] * force_h_atr; top, bot = mid + hgt / 2, mid - hgt / 2
                if hgt > atr[i] * max_h_atr:
                    hgt = atr[i] * max_h_atr; top, bot = mid + hgt / 2, mid - hgt / 2
                if hgt < atr[i] * min_h_atr:
                    continue
                merged = False
                for z in reversed(zones[-10:]):
                    if z["side"] == side and not z["broken"] and top >= z["bottom"] and bot <= z["top"]:
                        z["top"], z["bottom"] = max(top, z["top"]), min(bot, z["bottom"])
                        z["merged"] += 1; merged = True
                        break
                if not merged:
                    zones.append({"tool": "sdzpro", "side": side, "top": top, "bottom": bot, "idx": p, "known_idx": i,
                                  "retests": 0, "in_zone": False, "broken": False, "broken_idx": None, "merged": 0})
                    last[side] = i
        for z in zones:
            if z["known_idx"] > i or z["broken"]:
                continue
            inz = h[i] >= z["bottom"] and l[i] <= z["top"]
            if inz and not z["in_zone"]:
                z["retests"] += 1; z["in_zone"] = True
            elif not inz:
                z["in_zone"] = False
            lvl = (c[i] if invalidation == "Close" else h[i]) if z["side"] == "supply" else (c[i] if invalidation == "Close" else l[i])
            if (z["side"] == "supply" and lvl > z["top"]) or (z["side"] == "demand" and lvl < z["bottom"]):
                z["broken"] = True; z["broken_idx"] = i
    for z in zones:
        age = (n - 1) - z["idx"]
        z["strength"] = int(max(0, min(10, 8.0 - z["retests"] * 0.8 - min(age / 500.0, 2.0))))
    return zones


TOOLS = {"shved": shved, "cmike": cmike, "svopex": svopex, "flux": flux, "bigbeluga": bigbeluga, "sdzpro": sdzpro}
