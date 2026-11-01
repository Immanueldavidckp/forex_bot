"""
engine/sd_backtest.py — David's UPDATED supply / demand rules run end to end over one chart's history (David
2026-10-31: "i have updated the supply and demand in the drive … apply in the existing chart and do the back test").
The update is his Drive file Trade/Crypto strategy/"ETH／USD Supply Zone Setup Evaluation" (2026-10-31 18:29), the
audit of the ETHEREUM M30 sell limit 2270.36 / SL 2286.50 / TP 2174.00 placed that afternoon. Every VALID zone of
the /smc supply / demand layer (supply_demand.py, the origin boxes the page draws), every return to it, its score,
the entry type, entry / SL / TP1 / TP2 and the result.

The rules as the file states them ([ours] = a number the file leaves open):

  score 0-10   Sam Seiden / OTA odds enhancers, 2 points each
                 departure      2 = explosive: leg-out body >= EXPLOSIVE_MULT (2.0) x the 10 before [ours] AND a run of
                                >= 2 zone heights within 10 bars (the file's ETH zone: 3.16 x, 3.92 heights);
                                1 = the 1.5 x every valid zone has
                 time at base   1-3 candles 2, 4-5 1, more 0
                 freshness      1st return 2, 2nd 1, 3rd 0 (a 4th = spent, never traded)
                 profit margin  reward : risk to TP2 (spread inside both) >= 3 -> 2, >= 2 -> 1, else 0
                 big picture    the zone in its half of the last 200 bars' range (supply upper / demand lower) AND
                                the H4 major trend the same way -> 2; the right half only -> 1; the wrong half -> 0
                                (the file gave the ETH zone 0 with H4 down but low in the curve)
               - 0.5 when a CHoCH against the zone has closed on this timeframe since the zone's break (the file's
                 bullish M30 CHoCH 2244.81 under a supply)
  entry type   >= 9 and no CHoCH against: resting LIMIT at the zone's 50 % ("raised from the 2270.36 body edge to
               2276.23, the 70.5 % OTE / zone midpoint")
               7 - 8.5, or >= 9 with a CHoCH against (Moreno #8: a structure break against a set-and-forget entry
               invalidates it): CONFIRMATION — after the tap an M5 candle closes beyond the latest confirmed M5 swing
               (the V5 entry BOS: strategy.entry_bos on strategy.structure(M5), the engine's own rule) within
               m5_confirm_max_bars (36) M5 candles and before a close through the zone; the score is taken again
               with the real entry / stop and must still be >= 7
               < 7: no trade
  stop         the structural high / low (limit: the zone's distal wick; confirmation: the M5 rejection high / low
               since the tap) + SL_BUF_ATR (0.2) x ATR [ours; the file used 2.12-4.68 = 0.26-0.6 ATR on ETH] + the
               spread for a sell (its stop is a buy at the ask)
  targets      TP2 = the move's extreme (supply: the leg low since the leg-out; demand: the leg high) front-run by
               TP_CUSHION_ATR (0.1) x ATR [ours; the file 0.77] + the spread for a sell (its TP is a buy at the ask);
               TP1 = TP1_PART (50 %) at the BOS / CHoCH level the zone's move broke (same cushion), then the stop to
               break-even. TP1 is skipped when that level is not between the entry and TP2.
  costs        FxPro's spread as a share of price (symbol_cost.json median; ETHEREUM 4.44 at ~2244 = 0.198 %, the
               file's 19.8 bps); the chart is the bid: a sell fills at the bid and exits at the ask, a buy fills at
               the ask and exits at the bid
  fills        managed on M5 bars; a candle that reaches the stop and a target counts the stop; a limit's own fill
               candle can stop it out but not take profit; one trade per zone at a time; trades on different zones
               may overlap (counted, not netted)
  baseline     "original ticket": the rule of the 13:45 trade the file graded D- — every zone's first return, sell /
               buy limit at the body edge, stop distal + 0.4 ATR with no spread, one target at the leg extreme with
               no spread and no cushion, no score

    python3 -m engine.sd_backtest ETHEREUM M30        -> engine_data/sd_backtest/ETHEREUM_M30.json + a printed summary
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import time
from typing import Dict, List, Optional

import numpy as np

from . import learn, supply_demand
from .config import DATA_DIR, STRATEGY
from .major_structure import atr14, major_structure

OUT_DIR = os.path.join(DATA_DIR, "sd_backtest")
TF_MS = learn.TF_MS
STRUCTURE_N = 5                         # smc_compare.STRUCTURE_N: the /smc page's major structure
LIMIT_SCORE, CONFIRM_SCORE, COUNTER_PENALTY = 9.0, 7.0, 0.5
EXPLOSIVE_MULT = 2.0
SL_BUF_ATR, TP_CUSHION_ATR = 0.2, 0.1
TP1_PART = 0.5
CURVE_BARS = 200
MAX_VISITS = 3
BASE_SL_ATR = 0.4                       # the original ticket's stop buffer
MIN_RR = 2.0                            # David's filter profile "test": RR >= 2 to the target (the rubric alone takes 0.8)
MAX_CHASE_ATR = 1.0                     # [ours] a confirmation close further than this from the proximal = ran away, missed
CONFIRM_MAX = int(STRATEGY.get("m5_confirm_max_bars", 36))
RULES = {"limit_score": LIMIT_SCORE, "confirm_score": CONFIRM_SCORE, "counter_penalty": COUNTER_PENALTY,
         "explosive_mult": EXPLOSIVE_MULT, "sl_buf_atr": SL_BUF_ATR, "tp_cushion_atr": TP_CUSHION_ATR,
         "tp1_part": TP1_PART, "curve_bars": CURVE_BARS, "min_rr": MIN_RR, "max_chase_atr": MAX_CHASE_ATR, "max_visits": MAX_VISITS, "m5_confirm_max_bars": CONFIRM_MAX}


# ── data ─────────────────────────────────────────────────────────────────────

def spread_rel(sym: str, m5: List[Dict]) -> float:
    """the spread as a share of price: symbol_cost.json's median spread over the median M5 close of the last 30 days"""
    try:
        with open(os.path.join(DATA_DIR, "symbol_cost.json")) as f:
            sp = float(json.load(f)[sym]["median_spread"])
    except (FileNotFoundError, KeyError, ValueError):
        sp = 0.0
    ref = float(np.median([b["c"] for b in m5[-8640:]]))
    return sp / ref if ref > 0 else 0.0


def m5_events(sym: str, m5: List[Dict]) -> List[Dict]:
    """strategy.structure(M5) events (the V5 entry BOS), cached per symbol + last bar: ~45 s for 99,000 bars"""
    from .strategy import structure
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{sym}_M5_events.json")
    key = [len(m5), m5[0]["t"], m5[-1]["t"]]
    try:
        with open(path) as f:
            d = json.load(f)
        if d["key"] == key:
            return d["events"]
    except (FileNotFoundError, ValueError, KeyError):
        pass
    ev = [{"side": e["side"], "kind": e["kind"], "idx": e["idx"], "t": e["t"], "level": e["level"]} for e in structure(m5)["events"]]
    with open(path, "w") as f:
        json.dump({"key": key, "events": ev}, f)
    return ev


class Chart:
    def __init__(self, sym: str, tf: str):
        self.sym, self.tf, self.ms = sym, tf, TF_MS[tf]
        self.bars = learn.to_dicts(learn.load_bars(sym, tf, 10 ** 7))
        self.m5 = learn.to_dicts(learn.load_bars(sym, "M5", 10 ** 7))
        h4 = learn.to_dicts(learn.load_bars(sym, "H4", 10 ** 7))
        self.A = atr14(self.bars)
        self.close_t = [b["t"] + self.ms for b in self.bars]
        self.m = major_structure(self.bars, STRUCTURE_N)
        hm = major_structure(h4, STRUCTURE_N)
        self.h4_t = [h4[e["idx"]]["t"] + TF_MS["H4"] for e in hm["events"]]
        self.h4_side = [e["side"] for e in hm["events"]]
        self.choch = [(e["side"], e["idx"], self.close_t[e["idx"]]) for e in self.m["events"] if e["kind"] == "CHoCH"]
        m5 = self.m5
        self.T5 = [b["t"] for b in m5]
        self.H5 = np.array([b["h"] for b in m5])
        self.L5 = np.array([b["l"] for b in m5])
        self.C5 = [b["c"] for b in m5]
        self.Hl, self.Ll = self.H5.tolist(), self.L5.tolist()
        self.sp = spread_rel(sym, m5)
        ev = m5_events(sym, m5)
        self.ev5 = {s: sorted(e["idx"] for e in ev if e["side"] == s) for s in ("buy", "sell")}
        self.gap5 = max(1, 3 * self.ms // TF_MS["M5"])          # supply_demand.VISIT_GAP trade-TF bars outside

    def i5(self, t: int) -> int:
        """the first M5 bar opening at or after t"""
        return bisect.bisect_left(self.T5, t)

    def closed_before(self, t: int) -> int:
        """number of trade-TF bars closed by time t"""
        return bisect.bisect_right(self.close_t, t)

    def atr_at(self, t: int) -> float:
        j = self.closed_before(t)
        return self.A[max(0, j - 1)]

    def h4_trend(self, t: int) -> Optional[str]:
        j = bisect.bisect_right(self.h4_t, t)
        return self.h4_side[j - 1] if j else None

    def spread(self, price: float) -> float:
        return self.sp * price


# ── one trade ────────────────────────────────────────────────────────────────

def manage(c: Chart, side: str, E: float, S: float, tp1: Optional[float], tp2: float, s: float, j0: int,
           fill_bar: bool) -> Dict:
    """walk M5 from bar j0; prices are ORDER prices (sell: entry bid, stop / targets ask; buy: entry ask, stop /
    targets bid) and the chart is the bid. fill_bar = j0 is the limit's own fill candle (stop only)."""
    sell = side == "sell"
    risk = abs(E - S)
    slT = S - s if sell else S
    tp1T = None if tp1 is None else (tp1 - s if sell else tp1)
    tp2T = tp2 - s if sell else tp2
    beT = E - s if sell else E
    pnl = (lambda x: E - x) if sell else (lambda x: x - E)
    H, L = c.Hl, c.Ll
    stop, half, R, t1, best = slT, False, 0.0, None, 0.0      # best = the max favourable excursion in R (MFE)
    for j in range(j0, len(H)):
        if (H[j] >= stop) if sell else (L[j] <= stop):
            R += (1 - TP1_PART if half else 1.0) * pnl(E if half else S) / risk
            return {"exit_j": j, "reason": "BE" if half else "SL", "R": R, "tp1_j": t1, "mfe": best}
        if j == j0 and fill_bar:
            continue
        best = max(best, pnl(L[j] + s if sell else H[j]) / risk)
        if not half and tp1T is not None and ((L[j] <= tp1T) if sell else (H[j] >= tp1T)):
            R += TP1_PART * pnl(tp1) / risk
            half, stop, t1 = True, beT, j
        if (L[j] <= tp2T) if sell else (H[j] >= tp2T):
            R += (1 - TP1_PART if half else 1.0) * pnl(tp2) / risk
            return {"exit_j": j, "reason": "TP2", "R": R, "tp1_j": t1, "mfe": best}
    last = c.C5[-1] + (s if sell else 0.0)                    # still open: marked at the last close
    R += (1 - TP1_PART if half else 1.0) * pnl(last) / risk
    return {"exit_j": None, "reason": "open", "R": R, "tp1_j": t1, "mfe": best}


# ── the zones ────────────────────────────────────────────────────────────────

def plan_levels(c: Chart, z: Dict, side: str, E: float, hi_lo: float, legext: float, level: float, a: float, s: float) -> Dict:
    """stop beyond hi_lo (the distal or the M5 rejection extreme), TP2 at the leg extreme, TP1 at the broken level"""
    sell = side == "sell"
    buf, cush = SL_BUF_ATR * a, TP_CUSHION_ATR * a
    S = hi_lo + s + buf if sell else hi_lo - buf
    tp2 = legext + s + cush if sell else legext - cush
    tp1 = level + s + cush if sell else level - cush
    risk = abs(E - S)
    # targets are hit on the bid: a sell's at tp - s, a buy's at tp
    tp2_bid = tp2 - s if sell else tp2
    tp1_bid = tp1 - s if sell else tp1
    entry_bid = E if sell else E - s
    room = (entry_bid - tp2_bid) if sell else (tp2_bid - entry_bid)
    if not ((tp2_bid < tp1_bid < entry_bid) if sell else (entry_bid < tp1_bid < tp2_bid)):
        tp1 = None
    rr = abs(E - tp2) / risk if risk > 0 and room > 0 else 0.0
    return {"E": E, "S": S, "tp1": tp1, "tp2": tp2, "risk": risk, "rr": rr, "room": room > 0}


def margin_pts(rr: float) -> int:
    return 2 if rr >= 3 else 1 if rr >= 2 else 0


def score(c: Chart, z: Dict, visit: int, t: int, rr: float) -> Dict:
    side = z["side"]
    p = {"departure": 2 if (z["disp_mult"] >= EXPLOSIVE_MULT and (z["run_zone_heights"] or 0) >= 2) else 1,
         "time_at_base": 2 if z["base_n"] <= 3 else 1 if z["base_n"] <= 5 else 0,
         "freshness": {1: 2, 2: 1}.get(visit, 0),
         "margin": margin_pts(rr)}
    j = c.closed_before(t)
    w = c.bars[max(0, j - CURVE_BARS):j]
    lo, hi = min(b["l"] for b in w), max(b["h"] for b in w)
    pos = (z["mid"] - lo) / (hi - lo) if hi > lo else 0.5
    curve_ok = pos >= 0.5 if side == "sell" else pos <= 0.5
    htf = c.h4_trend(t)
    p["big_picture"] = (2 if htf == side else 1) if curve_ok else 0
    counter = next((ti for sd, ix, ti in c.choch if sd != side and ix > z["break_idx"] and ti <= t), None)
    tot = sum(p.values()) - (COUNTER_PENALTY if counter else 0.0)
    return {"score": tot, "parts": p, "curve_pos": round(pos, 2), "h4": htf, "counter_choch_t": counter}


def leg_extreme(c: Chart, z: Dict, k: int) -> float:
    """the move's extreme from the leg-out candle to M5 bar k (exclusive): supply -> the low, demand -> the high"""
    i0 = c.i5(c.bars[z["d"]]["t"])
    return float(c.L5[i0:k].min()) if z["side"] == "sell" else float(c.H5[i0:k].max())


def zone_info(c: Chart, z: Dict) -> Dict:
    T = c.bars
    f = z.get("fvg")
    return {"side": supply_demand.SIDE[z["side"]], "kind": z["kind"], "top": z["top"], "bottom": z["bottom"],
            "mid": z["mid"], "entry_line": z["entry"], "t0": z["t0"], "t_out": T[z["d"]]["t"], "t_break": z["t_break"],
            "event": z["event_kind"], "level": c.m["events"][z["event"]]["level"],
            "level_t": c.m["events"][z["event"]]["level_t"], "disp": z["disp_mult"], "base_n": z["base_n"],
            "run_zh": z["run_zone_heights"], "height_atr": z["height_atr"],
            "fvg": {"bottom": f["bottom"], "top": f["top"], "t": T[f["idx"]]["t"]} if f else None}


def visit_end(c: Chart, inzone, k: int, k_end: int) -> int:
    """the visit that is on at M5 bar k ends gap5 candles after its last candle in the box"""
    last_in = k
    while True:
        w = inzone[last_in + 1:min(last_in + 1 + c.gap5, k_end)]
        if not w.any():
            return min(last_in + c.gap5, k_end)
        last_in = last_in + 1 + int(np.flatnonzero(w)[-1])


def run_zone(c: Chart, z: Dict, zid: int, trades: List[Dict], skips: List[Dict], base: List[Dict]) -> None:
    side, sell = z["side"], z["side"] == "sell"
    prox, dist, mid = z["proximal"], z["distal"], z["mid"]
    level = c.m["events"][z["event"]]["level"]
    known = max(z["break_idx"], z["d"] + supply_demand.RUN_BARS - 1)
    if known >= len(c.bars):
        return
    t_known = c.close_t[known]
    brk = next((i for i in range(known + 1, len(c.bars)) if (c.bars[i]["c"] > dist if sell else c.bars[i]["c"] < dist)), None)
    t_broken = c.close_t[brk] if brk is not None else None
    k_end = c.i5(t_broken) if t_broken is not None else len(c.T5)       # no new entry from the break on
    inzone = (c.H5 >= prox) if sell else (c.L5 <= prox)
    zi = zone_info(c, z)
    pos, visit = c.i5(t_known), 0
    while pos < k_end:
        nz = np.flatnonzero(inzone[pos:k_end])
        if not len(nz):
            return
        k = pos + int(nz[0])                                         # the tap: first M5 candle back at the proximal
        visit += 1
        v_end = visit_end(c, inzone, k, k_end)                       # the visit lasts until gap5 candles outside
        if visit > MAX_VISITS:
            return
        t = c.T5[k]
        a = c.atr_at(t)
        s = c.spread(prox)
        legext = leg_extreme(c, z, k)
        rec = {"zone": zid, "z": zi, "visit": visit, "t_touch": t, "atr": a, "spread": s, "legext": legext}
        if visit == 1:                                               # the original ticket's rule (baseline)
            Eb = z["entry"]
            Sb = dist + BASE_SL_ATR * a if sell else dist - BASE_SL_ATR * a
            fill = next((j for j in range(k, v_end) if (c.Hl[j] >= Eb if sell else c.Ll[j] <= Eb - s)), None)
            okb = (legext < Eb) if sell else (legext > Eb)
            if fill is not None and okb:
                r = manage(c, side, Eb, Sb, None, legext, s, fill, True)
                base.append({**rec, "mode": "original", "E": Eb, "S": Sb, "tp1": None, "tp2": legext,
                             "j_entry": fill, "t_entry": c.T5[fill], **_exit(c, r)})
        # the updated rules: score with the limit geometry, then the entry type
        pl = plan_levels(c, z, side, mid, dist, legext, level, a, s)
        sc = score(c, z, visit, t, pl["rr"])
        rec.update(score=sc["score"], parts=sc["parts"], curve_pos=sc["curve_pos"], h4=sc["h4"], counter_choch_t=sc["counter_choch_t"])
        nxt = v_end
        if not pl["room"]:
            skips.append({**rec, "why": "price already beyond TP2 (no room)"})
        elif sc["score"] >= LIMIT_SCORE and not sc["counter_choch_t"] and pl["rr"] < MIN_RR:
            skips.append({**rec, "mode": "limit", "why": f"reward:risk {pl['rr']:.1f} < {MIN_RR:g}"})
        elif sc["score"] >= LIMIT_SCORE and not sc["counter_choch_t"]:
            fill = next((j for j in range(k, v_end) if (c.Hl[j] >= mid if sell else c.Ll[j] <= mid - s)), None)
            if fill is None:
                skips.append({**rec, "mode": "limit", "why": "limit at the 50 % not reached on this return"})
            else:
                r = manage(c, side, pl["E"], pl["S"], pl["tp1"], pl["tp2"], s, fill, True)
                trades.append({**rec, "mode": "limit", "E": pl["E"], "S": pl["S"], "tp1": pl["tp1"], "tp2": pl["tp2"],
                               "rr": pl["rr"], "j_entry": fill, "t_entry": c.T5[fill], **_exit(c, r)})
                nxt = _after(c, inzone, v_end, r, k_end)
        elif sc["score"] >= CONFIRM_SCORE:
            evs = c.ev5[side]
            q = bisect.bisect_right(evs, k)
            e = evs[q] if q < len(evs) else None
            if e is None or e > k + CONFIRM_MAX or e >= k_end:
                why = "zone closed through before the M5 BOS" if e is not None and e >= k_end and e <= k + CONFIRM_MAX \
                    else f"no M5 entry BOS within {CONFIRM_MAX} M5 candles"
                skips.append({**rec, "mode": "confirm", "why": why})
                nxt = max(v_end, k + CONFIRM_MAX)
            else:
                se = c.spread(c.C5[e])
                E = c.C5[e] if sell else c.C5[e] + se
                ext = float(c.H5[k:e + 1].max()) if sell else float(c.L5[k:e + 1].min())
                p2 = plan_levels(c, z, side, E, ext, legext, level, a, se)
                sc2 = score(c, z, visit, t, p2["rr"])
                rec.update(score_at_entry=sc2["score"], parts_at_entry=sc2["parts"], j_bos=e)
                chase = ((prox - c.C5[e]) if sell else (c.C5[e] - prox)) / a if a > 0 else 0.0
                if chase > MAX_CHASE_ATR:
                    skips.append({**rec, "mode": "confirm", "t_bos": c.T5[e], "E": E,
                                  "why": f"M5 BOS {chase:.1f} ATR away from the zone: ran away (missed)"})
                    nxt = max(v_end, e + 1)
                elif not p2["room"] or p2["rr"] < MIN_RR:
                    skips.append({**rec, "mode": "confirm", "t_bos": c.T5[e], "E": E,
                                  "why": f"after the M5 BOS reward:risk {p2['rr']:.1f} < {MIN_RR:g}"})
                    nxt = max(v_end, e + 1)
                elif sc2["score"] < CONFIRM_SCORE:
                    skips.append({**rec, "mode": "confirm", "t_bos": c.T5[e], "E": E,
                                  "why": f"after the M5 BOS reward:risk {p2['rr']:.1f} -> score {sc2['score']:g} < {CONFIRM_SCORE:g}"})
                    nxt = max(v_end, e + 1)
                else:
                    r = manage(c, side, E, p2["S"], p2["tp1"], p2["tp2"], se, e + 1, False)
                    trades.append({**rec, "mode": "confirm", "E": E, "S": p2["S"], "tp1": p2["tp1"], "tp2": p2["tp2"],
                                   "rr": p2["rr"], "spread": se, "j_entry": e, "t_entry": c.T5[e], **_exit(c, r)})
                    nxt = _after(c, inzone, v_end, r, k_end)
        else:
            skips.append({**rec, "why": f"score {sc['score']:g} < {CONFIRM_SCORE:g}: no trade"})
        pos = _resume(c, inzone, nxt, k_end)


def _after(c: Chart, inzone, v_end: int, r: Dict, k_end: int) -> int:
    """past the trade's exit (the visit it ended in is closed by _resume)"""
    return len(c.T5) if r["exit_j"] is None else max(v_end, r["exit_j"] + 1)


def _resume(c: Chart, inzone, x: int, k_end: int) -> int:
    """a new return starts only after price has been out of the box gap5 candles: if bar x still belongs to a visit
    (a candle in the box within gap5 before it), skip to that visit's end"""
    if x >= k_end:
        return x
    lo = max(0, x - c.gap5)
    w = np.flatnonzero(inzone[lo:x + 1])
    return max(x, visit_end(c, inzone, lo + int(w[-1]), k_end)) if len(w) else x


def _exit(c: Chart, r: Dict) -> Dict:
    T = lambda j: None if j is None else c.T5[j]
    return {"reason": r["reason"], "R": round(r["R"], 3), "t_exit": T(r["exit_j"]), "t_tp1": T(r["tp1_j"]),
            "mfe_R": round(r["mfe"], 2)}


# ── the whole chart ─────────────────────────────────────────────────────────

def stats(tr: List[Dict]) -> Dict:
    done = [x for x in tr if x["reason"] != "open"]
    R = [x["R"] for x in done]
    if not R:
        return {"n": 0, "open": len(tr)}
    eq = np.cumsum(R)
    dd = float(np.max(np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:] - eq)) if len(eq) else 0.0
    wins, losses = [r for r in R if r > 1e-9], [r for r in R if r < -1e-9]
    return {"n": len(R), "open": len(tr) - len(done), "wins": len(wins), "losses": len(losses), "be": len(R) - len(wins) - len(losses),
            "win_rate": round(len(wins) / len(R), 3), "total_R": round(float(sum(R)), 2), "avg_R": round(float(np.mean(R)), 3),
            "pf": round(sum(wins) / -sum(losses), 2) if losses else None, "max_dd_R": round(dd, 2),
            "tp2": sum(1 for x in done if x["reason"] == "TP2"), "sl": sum(1 for x in done if x["reason"] == "SL"),
            "mfe_1R": sum(1 for x in done if x.get("mfe_R", 0) >= 1), "mfe_2R": sum(1 for x in done if x.get("mfe_R", 0) >= 2),
            "mfe_3R": sum(1 for x in done if x.get("mfe_R", 0) >= 3),
            "stopped_on_fill_candle": sum(1 for x in done if x["reason"] == "SL" and x["t_exit"] == x["t_entry"]),
            "tp1_R_median": round(float(np.median([abs(x["E"] - x["tp1"]) / abs(x["E"] - x["S"]) for x in done if x.get("tp1")])), 1)
            if any(x.get("tp1") for x in done) else None,
            "tp2_R_median": round(float(np.median([abs(x["E"] - x["tp2"]) / abs(x["E"] - x["S"]) for x in done])), 1),
            "be_after_tp1": sum(1 for x in done if x["reason"] == "BE")}


def run(sym: str, tf: str) -> Dict:
    t0 = time.time()
    c = Chart(sym, tf)
    zs = [z for z in supply_demand.zones(c.bars, c.m) if z.get("valid") and z.get("role", "").startswith("origin")]
    trades, skips, base = [], [], []
    for i, z in enumerate(zs):
        run_zone(c, z, i, trades, skips, base)
    for L in (trades, skips, base):
        L.sort(key=lambda x: x.get("t_entry") or x["t_touch"])
    usd = float(json.load(open(os.path.join(learn.HIST_DIR, f"{sym}.json")))["info"].get("trade_contract_size", 1.0)) * 0.01
    for x in trades + base:
        x["usd_001"] = round((x["R"] * abs(x["E"] - x["S"])) * usd, 4)
    out = {"sym": sym, "tf": tf, "made": int(time.time()), "rules": RULES, "spread_rel": c.sp,
           "from": c.bars[0]["t"], "to": c.bars[-1]["t"] + c.ms, "bars": len(c.bars), "zones": len(zs),
           "returns": len(trades) + len(skips),
           "stats": {"all": stats(trades), "limit": stats([x for x in trades if x["mode"] == "limit"]),
                     "confirm": stats([x for x in trades if x["mode"] == "confirm"]),
                     "sell": stats([x for x in trades if x["z"]["side"] == "supply"]),
                     "buy": stats([x for x in trades if x["z"]["side"] == "demand"]),
                     "fvg": stats([x for x in trades if x["z"]["fvg"]]),
                     "no_fvg": stats([x for x in trades if not x["z"]["fvg"]]),
                     "original": stats(base)},
           "skip_why": _count(skips), "trades": trades, "skips": skips, "original": base, "secs": round(time.time() - t0, 1)}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, f"{sym}_{tf}.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"))
    return out


def _count(skips: List[Dict]) -> Dict:
    d: Dict[str, int] = {}
    for x in skips:
        w = x["why"]
        k = "score < 7: no trade" if w.startswith("score") else "ran away before the M5 BOS (> 1 ATR)" if "ran away" in w \
            else "reward:risk < 2" if "reward:risk" in w else w.split(" -> ")[0]
        d[k] = d.get(k, 0) + 1
    return dict(sorted(d.items(), key=lambda kv: -kv[1]))


def saved(sym: str, tf: str) -> Optional[Dict]:
    """the last run for the /smc page (trades only), or None"""
    try:
        with open(os.path.join(OUT_DIR, f"{sym}_{tf}.json")) as f:
            d = json.load(f)
    except (FileNotFoundError, ValueError):
        return None
    keep = ("mode", "visit", "score", "parts", "t_touch", "t_entry", "E", "S", "tp1", "tp2", "rr", "t_tp1", "t_exit",
            "reason", "R", "usd_001", "spread", "counter_choch_t", "h4", "curve_pos", "mfe_R")
    return {"made": d["made"], "rules": d["rules"], "stats": d["stats"], "from": d["from"], "to": d["to"],
            "trades": [{**{k: x.get(k) for k in keep}, "z": x["z"]} for x in d["trades"]]}


def main() -> int:
    ap = argparse.ArgumentParser(description="backtest David's updated supply / demand rules on one chart")
    ap.add_argument("sym")
    ap.add_argument("tf", nargs="?", default="M30")
    a = ap.parse_args()
    d = run(a.sym, a.tf)
    for k, v in d["stats"].items():
        print(f"{k:9s} {v}")
    print("not traded:", d["skip_why"])
    print(f"{d['zones']} zones, {d['returns']} returns, {d['secs']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
