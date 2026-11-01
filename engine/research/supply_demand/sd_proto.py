#!/usr/bin/env python3
"""
sd_proto.py — supply & demand METHOD prototype for David's /smc page ("only the valid ones"), 2026-10-30.

Spec (see report.md for the sources behind every number; David's rules win where they define a thing):

  candles      base candle      body <= BASE_BODY_PCT (0.5) x range                      (eltrader, CienF-OTC, AW S&D, cmike444)
               leg-out candle   body >= DISP_MULT (1.5) x mean body of the DISP_AVG_BARS (10) before   (David V5 §4 / new rules §11)
                                scored, not filtered: body >= 0.5 x range ("decisive"), >= 0.7 "explosive" (cmike444, eltrader)
  formation    base = the run of base candles (1..MAX_BASE = 3, Svopex default; cmike/AW allow 6) immediately before the
               leg-out candle; David's zone candle (the LAST OPPOSITE-colour candle <= LOOKBACK 5 bars before the leg-out,
               V5 §3) must be inside the box: if it sits just before the base run, the run is extended to it; if there are
               no base candles at all the zone is that single candle ("single-candle" kind = the OB of smc_marks).
               leg-in = net close-to-close move over LEG_BARS (5) bars before the base, >= LEG_MIN_ATR (0.5) ATR:
               rally/drop -> kind RBR / DBD (continuation), RBD / DBR (reversal); flat leg-in -> "xBR" / "xBD".
  box          distal   = wick extreme of the base (demand: lowest low; supply: highest high)   (LuxAlgo, eltrader, David V5 wick)
               proximal = wick edge (David's V5 / smc_marks OB convention, LuxAlgo "widest honest zone") PLUS the body edge
                          of the base as the dashed ENTRY line (OTA/eltrader/cmike444 "proximal = bodies")
               height   > MAX_HEIGHT_ATR (1.5) ATR(14) -> refined to David's single candle; still too tall -> filtered
                          (cmike444 MAX_ZONE_ATR 1.5; Supply Demand Zones Pro 1.0; AW clips)
  validity     HARD (David): the leg-out must be the displacement of a MAJOR BOS / CHoCH (major_structure.py):
               origin <= base < leg-out candle <= break candle, same side, and price must not come back to the box's
               proximal (wick) edge between the leg-out and the break ("move strongly away": new rules §9-10, LuxAlgo
               "departures that break a prior swing carry more weight", cmike444 freshness).
               Zones that fail the gate are returned with valid=False and the reason (the page hides them).
               Of the zones of one break the EARLIEST clean one is the origin (Seiden: "the origin of the move") ->
               primary; later ones are "nested" (shown smaller / on request).
  score 0-10   departure  : body mult >= 1.5 -> 1, >= 2.5 -> 2 ; run from proximal >= 2 zone heights within 10 bars -> +1
                            (AW "Min departure 2 zone heights / 1.5 ATR within 10 bars"; OTA "strength of the move")
               fvg        : a 3-candle gap in the leg-out -> +1 (David §12 REQUIRES it for a trade: flag `setup_ready`)
               time@base  : 1 candle -> 2, 2-3 -> 1, more -> 0 (OTA "time at the level: less is more"; crosstrade 1-3 bars)
               freshness  : fresh 2, 1 test 1, else 0 (Seiden SFO 2005: first revisit is the highest odds)
               trend      : the major trend at the break agrees with the zone side -> +1 (OTA "big picture")
               curve      : demand in the lower half / supply in the upper half of the last 200 bars' range -> +1 (OTA curve)
               margin     : distance to the nearest opposing live zone >= 3 x zone height -> +1 (eltrader: OTA 3:1 minimum)
  life cycle   known from the break candle on (before it the zone is not valid): fresh -> tested (a wick reaches the
               proximal line; depth to the 50 % line = "mean", to the distal = "full") -> spent after SPENT_TOUCHES (3)
               separate visits (crosstrade / eltrader "classic school: 3 or more tests") -> broken (a CLOSE beyond the
               distal line; Supply Demand Zones Pro / AW / therighttrader "close through the distal edge is a break";
               a wick is a fake break) -> flipped (after a break, price comes back to the box from the other side:
               AW / Flux "flip", ICT breaker). superseded = a CHoCH closed against the zone side after it (smc_marks).
               A visit ends when price has been outside the box for VISIT_GAP (3) bars (AW "bars outside to end a visit").

    zones(bars, m) -> list of zone dicts (see _finish for the fields)
    bars  [{t, o, h, l, c}, ...]      m = major_structure(bars, 5)
python3 + numpy only; major_structure.py is imported read-only from ~/forex/engine.
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
import time
from typing import Dict, List, Optional

import numpy as np

sys.path.insert(0, "/home/david/forex/engine")
from major_structure import _pivot, atr14, major_structure  # noqa: E402  (read-only)

BASE_BODY_PCT = 0.5
DISP_MULT, DISP_AVG_BARS = 1.5, 10          # David
LOOKBACK = 5                                # David zone_lookback_bars
MAX_BASE = 3
LEG_BARS, LEG_MIN_ATR = 5, 0.5
MAX_HEIGHT_ATR = 1.5
RUN_BARS, RUN_ZONE_HEIGHTS = 10, 2.0
SPENT_TOUCHES, VISIT_GAP = 3, 3
CURVE_BARS = 200
MARGIN_RR = 3.0
SIDE = {"buy": "demand", "sell": "supply"}


def _body(b):
    return abs(b["c"] - b["o"])


def _is_base(b):
    r = b["h"] - b["l"]
    return r > 0 and _body(b) <= BASE_BODY_PCT * r


def _opp(b, side):
    return b["c"] < b["o"] if side == "buy" else b["c"] > b["o"]


def _same(b, side):
    return b["c"] > b["o"] if side == "buy" else b["c"] < b["o"]


def _gap(bars, i, side):
    """the 3-candle gap whose middle candle is i (bars i-1, i, i+1)"""
    if i < 1 or i + 1 >= len(bars):
        return None
    a, c = bars[i - 1], bars[i + 1]
    if side == "buy" and c["l"] > a["h"]:
        return (a["h"], c["l"])
    if side == "sell" and c["h"] < a["l"]:
        return (c["h"], a["l"])
    return None


def _candidate(bars, A, d, side, mult):
    """the zone box of leg-out candle d; None with a reason if no box can be made"""
    n = len(bars)
    # base run: consecutive base candles immediately before d
    b0 = d
    while b0 - 1 >= 0 and d - b0 < MAX_BASE and _is_base(bars[b0 - 1]):
        b0 -= 1
    base = list(range(b0, d))
    # David's candle: the last opposite-colour candle within LOOKBACK before d
    j = next((i for i in range(d - 1, max(d - 1 - LOOKBACK, -1), -1) if _opp(bars[i], side)), None)
    kind_note = ""
    if base:
        if j is not None and j < b0 and b0 - j == 1:
            base = [j] + base                      # the opposite candle sits just before the base run: include it
        elif j is not None and j < b0:
            kind_note = "opposite candle further back than the base run (kept the base)"
        elif j is None:
            kind_note = "no opposite candle within lookback (base only)"
    else:
        if j is None:
            return None, "no base candle and no opposite candle before the leg-out"
        base = [j]
        kind_note = "single-candle"
    if len(base) > MAX_BASE + 1:
        return None, f"base run {len(base)} > {MAX_BASE}"
    z = _box(bars, base, side)
    a = A[d - 1] if d > 0 else A[d]
    refined = False
    if a > 0 and (z["top"] - z["bottom"]) > MAX_HEIGHT_ATR * a:
        if j is not None and len(base) > 1:
            base, refined = [j], True
            z = _box(bars, base, side)
        if (z["top"] - z["bottom"]) > MAX_HEIGHT_ATR * a:
            return None, f"box taller than {MAX_HEIGHT_ATR} ATR after refinement ({((z['top'] - z['bottom']) / a):.2f})"
    # leg-in
    li = base[0]
    leg_in = "flat"
    if li - LEG_BARS >= 0 and a > 0:
        mv = bars[li - 1]["c"] - bars[li - 1 - LEG_BARS]["c"] if li - 1 - LEG_BARS >= 0 else 0.0
        if abs(mv) >= LEG_MIN_ATR * a:
            leg_in = "rally" if mv > 0 else "drop"
    out = "rally" if side == "buy" else "drop"
    kind = {"rally": "R", "drop": "D", "flat": "x"}[leg_in] + "B" + ("R" if out == "rally" else "D")
    if kind_note == "single-candle":
        kind += " (single-candle)"
    elif refined:
        kind += " (refined to the opposite candle)"
    z.update(side=side, kind=kind, kind_note=kind_note, base=base, base_n=len(base), leg_in=leg_in, d=d,
             disp_mult=round(mult, 2), disp_body_pct=round(_body(bars[d]) / max(bars[d]["h"] - bars[d]["l"], 1e-12), 2),
             atr=a, height_atr=round((z["top"] - z["bottom"]) / a, 2) if a > 0 else None, refined=refined)
    # leg-out stats: run beyond the proximal within RUN_BARS; FVG in the leg-out (middle candle d-1..d+2)
    prox = z["top"] if side == "buy" else z["bottom"]
    run = 0.0
    for k in range(d, min(n, d + RUN_BARS)):
        run = max(run, (bars[k]["h"] - prox) if side == "buy" else (prox - bars[k]["l"]))
    h = z["top"] - z["bottom"]
    z["run_atr"] = round(run / a, 2) if a > 0 else None
    z["run_zone_heights"] = round(run / h, 2) if h > 0 else None
    gaps = [(_gap(bars, i, side), i) for i in range(max(d, 1), min(d + 3, n - 1))]
    gaps = [(g, i) for g, i in gaps if g]
    z["fvg"] = {"idx": gaps[0][1], "bottom": gaps[0][0][0], "top": gaps[0][0][1]} if gaps else None
    return z, None


def _box(bars, base, side):
    hi = max(bars[i]["h"] for i in base)
    lo = min(bars[i]["l"] for i in base)
    body_hi = max(max(bars[i]["o"], bars[i]["c"]) for i in base)
    body_lo = min(min(bars[i]["o"], bars[i]["c"]) for i in base)
    if side == "buy":
        return {"top": hi, "bottom": lo, "proximal": hi, "distal": lo, "entry": body_hi, "mid": (hi + lo) / 2}
    return {"top": hi, "bottom": lo, "proximal": lo, "distal": hi, "entry": body_lo, "mid": (hi + lo) / 2}


def _track(bars, z, start, events):
    """life cycle from bar `start` (the break candle + 1) on"""
    side, top, bot, mid = z["side"], z["top"], z["bottom"], z["mid"]
    bull = side == "buy"
    prox, dist = z["proximal"], z["distal"]
    inside = lambda b: (b["l"] <= prox) if bull else (b["h"] >= prox)
    z.update(status="fresh", touches=0, touch_idx=None, mean_idx=None, full_idx=None, broken_idx=None,
             flipped_idx=None, spent_idx=None, max_depth=0.0, superseded_idx=None, visits=[])
    in_visit, last_in = False, None
    for i in range(start, len(bars)):
        b = bars[i]
        if z["status"] in ("broken", "flipped", "dead"):
            if z["status"] == "broken" and ((b["h"] >= dist) if bull else (b["l"] <= dist)):
                z["status"], z["flipped_idx"] = "flipped", i      # back at the box from the other side: flip zone
            elif z["status"] == "flipped" and ((b["c"] > prox) if bull else (b["c"] < prox)):
                z["status"], z["dead_idx"] = "dead", i             # closed back through the flip zone: gone
            continue
        if (b["c"] < dist) if bull else (b["c"] > dist):
            z["status"], z["broken_idx"] = "broken", i
            continue
        if inside(b):
            depth = ((prox - b["l"]) if bull else (b["h"] - prox)) / max(top - bot, 1e-12)
            z["max_depth"] = max(z["max_depth"], min(depth, 1.0))
            if not in_visit:
                in_visit = True
                z["touches"] += 1
                z["visits"].append(i)
                if z["touch_idx"] is None:
                    z["touch_idx"], z["status"] = i, "tested"
            if z["mean_idx"] is None and ((b["l"] <= mid) if bull else (b["h"] >= mid)):
                z["mean_idx"] = i
            if z["full_idx"] is None and ((b["l"] <= dist) if bull else (b["h"] >= dist)):
                z["full_idx"] = i
            last_in = i
            if z["touches"] >= SPENT_TOUCHES and z["status"] != "spent":
                z["status"], z["spent_idx"] = "spent", i
        elif in_visit and last_in is not None and i - last_in >= VISIT_GAP:
            in_visit = False
    z["superseded_idx"] = next((e["idx"] for e in events if e["kind"] == "CHoCH" and e["side"] != side and e["idx"] >= start), None)
    z["live"] = z["status"] in ("fresh", "tested") and z["superseded_idx"] is None


def _score(bars, z, m, zones_so_far):
    s, parts = 0, {}
    dep = (2 if z["disp_mult"] >= 2.5 else 1) + (1 if (z["run_zone_heights"] or 0) >= RUN_ZONE_HEIGHTS else 0)
    parts["departure"] = dep
    parts["fvg"] = 1 if z["fvg"] else 0
    parts["time_at_base"] = 2 if z["base_n"] == 1 else 1 if z["base_n"] <= 3 else 0
    parts["freshness"] = 2 if z["touches"] == 0 else 1 if z["touches"] == 1 else 0
    e = m["events"][z["event"]]
    parts["trend"] = 1 if e["kind"] == "BOS" else 0        # a BOS continues the major trend; a CHoCH starts a new one
    x = e["idx"]
    lo = min(b["l"] for b in bars[max(0, x - CURVE_BARS):x + 1])
    hi = max(b["h"] for b in bars[max(0, x - CURVE_BARS):x + 1])
    pos = (z["mid"] - lo) / (hi - lo) if hi > lo else 0.5
    parts["curve"] = 1 if (pos <= 0.5 if z["side"] == "buy" else pos >= 0.5) else 0
    z["curve_pos"] = round(pos, 2)
    h = z["top"] - z["bottom"]
    opp = [q for q in zones_so_far if q["valid"] and q["side"] != z["side"] and q["break_idx"] <= x
           and ((q["bottom"] > z["top"]) if z["side"] == "buy" else (q["top"] < z["bottom"]))]
    if opp:
        dist = min(abs(q["proximal"] - z["proximal"]) for q in opp)
        z["margin_rr"] = round(dist / h, 1) if h > 0 else None
        parts["margin"] = 1 if h > 0 and dist / h >= MARGIN_RR else 0
    else:
        z["margin_rr"], parts["margin"] = None, 1
    z["score_parts"] = parts
    z["score"] = sum(parts.values())


def zones(bars: List[Dict], m: Optional[Dict] = None, n: int = 5) -> List[Dict]:
    m = m or major_structure(bars, n)
    A = atr14(bars)
    N = len(bars)
    bodies = np.array([_body(b) for b in bars])
    avg = np.full(N, np.nan)
    for i in range(DISP_AVG_BARS, N):
        avg[i] = bodies[i - DISP_AVG_BARS:i].mean()
    out: List[Dict] = []
    ev = m["events"]
    for k, e in enumerate(ev):
        side, o, x = e["side"], e["origin"]["idx"], e["idx"]
        prim_done = False
        cands = []
        for d in range(max(o + 1, DISP_AVG_BARS), x + 1):
            if not _same(bars[d], side) or not (avg[d] > 0) or bodies[d] < DISP_MULT * avg[d]:
                continue
            z, why = _candidate(bars, A, d, side, bodies[d] / avg[d])
            if z is None:
                cands.append({"event": k, "d": d, "valid": False, "why": why, "side": side})
                continue
            if z["base"][0] < o:
                z.update(valid=False, why="base before the move's origin")
            else:
                prox = z["proximal"]
                back = next((i for i in range(d + 1, x + 1) if (bars[i]["l"] <= prox if side == "buy" else bars[i]["h"] >= prox)), None)
                if back is not None:
                    z.update(valid=False, why=f"price came back to the box at bar {back} before the break (not a clean departure)")
                else:
                    z.update(valid=True, why=None)
            cands.append(z)
        # overlapping boxes of the SAME break are one zone: keep the earlier (the origin), merge the later into it
        # (LuxAlgo scoring page: "overlapping zones either merge or the best-formed candidate is kept"; AW "Keep strongest")
        kept: List[Dict] = []
        for z in cands:
            if z["valid"]:
                hit = next((q for q in kept if z["bottom"] < q["top"] and z["top"] > q["bottom"]), None)
                if hit:
                    z.update(valid=False, why="overlaps an earlier box of the same break (merged into it)", merged_into=hit["d"])
                    hit["merged"] = hit.get("merged", 0) + 1
                else:
                    kept.append(z)
        good = kept
        for z in cands:
            z.update(event=k, event_kind=e["kind"], break_idx=x, origin_idx=o, t0=bars[z["base"][0]]["t"] if z.get("base") else bars[z["d"]]["t"],
                     t_break=bars[x]["t"], gate="major " + e["kind"] + " " + SIDE[side])
            if z["valid"]:
                # origin = the earliest clean zone of the break (Seiden: the origin of the move) = the page's primary box;
                # last = the one nearest the break (= David's OB in smc_marks); nested = in between
                z["role"] = ("origin" if z is good[0] else "") + ("+last" if z is good[-1] else "") or "nested"
                z["role"] = z["role"].lstrip("+")
                _track(bars, z, x + 1, ev)
                _score(bars, z, m, out)
            out.append(z)
    # candidates outside every major break: displacement candles whose leg-out broke no major level
    covered = set()
    for z in out:
        covered.add(z["d"])
    for d in range(DISP_AVG_BARS, N):
        if d in covered or not (avg[d] > 0) or bodies[d] < DISP_MULT * avg[d]:
            continue
        side = "buy" if bars[d]["c"] > bars[d]["o"] else "sell"
        z, why = _candidate(bars, A, d, side, bodies[d] / avg[d])
        if z is None:
            out.append({"d": d, "side": side, "valid": False, "why": why, "event": None, "t0": bars[d]["t"]})
        else:
            z.update(valid=False, why="no major BOS / CHoCH from this leg-out (David §9-10: INVALID, do not mark)",
                     event=None, t0=bars[z["base"][0]]["t"])
            out.append(z)
    out.sort(key=lambda z: z["d"])
    return out


# ----------------------------------------------------------------------------------------------- reporting helpers
def ist(ms):
    return (_dt.datetime.fromtimestamp(ms / 1000, _dt.timezone.utc) + _dt.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %H:%M")


def load(sym, tf, last=3000):
    d = json.load(open(f"/home/david/forex/engine_data/history/{sym}.json"))
    rows = d["bars"][tf][-last:]
    return [{"t": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4]} for r in rows]


def summary(sym, tf, bars, zs, m):
    N = len(bars)
    valid = [z for z in zs if z["valid"]]
    inval = [z for z in zs if not z["valid"]]
    why = {}
    for z in inval:
        key = z["why"].split(" at bar")[0].split(" (")[0] if z["why"] else "?"
        why[key] = why.get(key, 0) + 1
    lines = [f"== {sym} {tf}: {N} bars  {ist(bars[0]['t'])} .. {ist(bars[-1]['t'])} IST, {len(m['events'])} major events "
             f"({sum(e['kind']=='BOS' for e in m['events'])} BOS / {sum(e['kind']=='CHoCH' for e in m['events'])} CHoCH)",
             f"   displacement candidates {len(zs)} ({100*len(zs)/N:.1f} per 100 bars); VALID {len(valid)} "
             f"({100*len(valid)/N:.2f} per 100 bars): origin (primary box) {sum(z['role'].startswith('origin') for z in valid)}, "
             f"last (= OB) {sum(z['role'].endswith('last') for z in valid)}, nested {sum(z['role']=='nested' for z in valid)}",
             f"   kinds of valid: " + ", ".join(f"{k} {v}" for k, v in sorted(_count(z['kind'].split(' ')[0] for z in valid).items())),
             f"   single-candle (no base) among valid: {sum('single' in z['kind'] for z in valid)}, refined: {sum(z['refined'] for z in valid)}",
             f"   status now: " + ", ".join(f"{k} {v}" for k, v in sorted(_count(z['status'] for z in valid).items())),
             f"   live (fresh/tested, not superseded by a CHoCH): {sum(z['live'] for z in valid)}; fresh but superseded: "
             f"{sum(z['status']=='fresh' and z['superseded_idx'] is not None for z in valid)}  with FVG in the leg-out: {sum(bool(z['fvg']) for z in valid)}",
             f"   score of valid: mean {np.mean([z['score'] for z in valid]):.1f}, >=7: {sum(z['score']>=7 for z in valid)}, <=4: {sum(z['score']<=4 for z in valid)}",
             "   filtered: " + "; ".join(f"{k}: {v}" for k, v in sorted(why.items(), key=lambda kv: -kv[1]))]
    return "\n".join(lines)


def _count(it):
    c = {}
    for v in it:
        c[v] = c.get(v, 0) + 1
    return c


def examples(bars, zs, k=4):
    valid = [z for z in zs if z["valid"] and z["role"].startswith("origin")]
    pick = valid[-k:]
    out = []
    for z in pick:
        out.append(f"   {SIDE[z['side']]:6s} {z['kind']:<32s} base {ist(z['t0'])} IST x{z['base_n']}  box {z['bottom']:.5g}-{z['top']:.5g} "
                   f"(entry {z['entry']:.5g}, {z['height_atr']} ATR)  leg-out x{z['disp_mult']} body {int(100*z['disp_body_pct'])}%  "
                   f"run {z['run_zone_heights']} boxes  FVG {'yes' if z['fvg'] else 'no'}  {z['gate']} @ {ist(z['t_break'])}  "
                   f"status {z['status']} (touches {z['touches']}, depth {int(100*z['max_depth'])}%)  score {z['score']} {z['score_parts']}")
    return "\n".join(out)


if __name__ == "__main__":
    for sym in ("GOLD", "EURUSD"):
        for tf in ("M15", "H1"):
            bars = load(sym, tf)
            t0 = time.perf_counter()
            m = major_structure(bars, 5)
            t1 = time.perf_counter()
            zs = zones(bars, m)
            t2 = time.perf_counter()
            print(summary(sym, tf, bars, zs, m))
            print(f"   timing: structure {1000*(t1-t0):.0f} ms, zones {1000*(t2-t1):.0f} ms")
            print(examples(bars, zs))
            print()
