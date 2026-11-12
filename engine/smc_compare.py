"""
engine/smc_compare.py — the /smc page (David 2026-10-28: "use this in our website and show", NOT in MT5): two free
SMC indicators next to the V5 engine on the same bars, all computed here in Python from our own bar files: zones
(top / bottom, from, until mitigated) and confirmations (BOS / CHoCH, sweeps).

  SMC Zones   allanninal/smc-zones (PolyForm-Noncommercial), third_party/smc_zones_ref.py: the author's Python
              reference. On our GOLD M15 bars it reproduced the MT5 indicator's 16 buffers bar for bar (2026-10-28).
              Settings: swing 3, ATR 14, FVG >= 0.2 ATR, an OB ends on a close beyond its far edge, an FVG on a wick
              through it.
  LuxAlgo     Smart Money Concepts [LuxAlgo] (CC BY-NC-SA), third_party/luxalgo_smc.py: a Python port, identical to
              what the MT5 port drew on our GOLD / EURUSD M15 bars (test_smc_compare.py).
  V5 engine   learn.detect_rows on the same bars.
  Structure   David's rule (major_structure.py, 2026-10-28): only the BOS level (the leg's extreme) and the protected
              swing (CHoCH level) exist, so internal breaks are never marked. The page's main layer; the indicators'
              own internal structure is behind the "internal" switch.

Bars: learn.load_bars (engine_data/history + the engine's view file + live.py's file). PDH / PDL = the previous FxPro server day.

    python3 -m engine.smc_compare report [--sym GOLD --tf M15]
"""
from __future__ import annotations

import argparse
import json
import datetime as _dt
import os
import time
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import numpy as np

from . import learn
from . import fib_reject, fib_trend, order_blocks, sd_backtest, sd_classic, sd_david, smc_marks, supply_demand
from . import candles, chart_patterns, elliott, indicators, levels, trendlines, volume_profile, wyckoff
from .config import CHART_EXTRA
from .major_structure import atr14, major_structure
from .config import ENGINE, VIEW_DIR
from .third_party import luxalgo_smc, smc_zones_ref

SERVER_TZ = ZoneInfo(ENGINE["server_tz"])
ZONES_ARGS = dict(swing=3, atr=14, fvg_min=0.20, ob_mit=3, fvg_mit=2, sweep_look=60, sweep_min=0.10)
TFS = ("M5", "M15", "M30", "H1", "H4")
N_BARS = 3000
OB_SHOW, POOLS_SHOW = 3, 3   # live order blocks per side, untaken liquidity pools above / below price (the nearest)
SD_SHOW = supply_demand.SHOW_LIVE   # live supply / demand zones per side (the nearest origin boxes)
STRUCTURE_N = 5       # swing confirmation for David's rule (+ 3 ATR pullback, 0.25 ATR close margin): 14 of his 18 drawn
                      # BOS / CHoCH lines (the engine 13) with half the breaks of the plain swing rule (2026-10-28)
SIDE = {1: "bull", -1: "bear", "buy": "bull", "sell": "bear"}


def available() -> List[str]:
    """Symbols with bars on disk (history or the live view file); GOLD and EURUSD first."""
    syms = set()
    for d in (learn.HIST_DIR, VIEW_DIR):
        try:
            syms |= {f[:-5] for f in os.listdir(d) if f.endswith(".json")}
        except FileNotFoundError:
            pass
    syms |= set(CHART_EXTRA)
    return sorted(syms, key=lambda s: (s not in ("GOLD", "EURUSD"), s != "GOLD", s))


def smc_zones(rows: List[list]) -> Dict:
    """allanninal's SMC Zones on [t_ms, o, h, l, c] rows (the last row = the forming bar, never used)."""
    a = np.array([r[1:5] for r in rows], dtype=float)
    t_s = np.array([r[0] // 1000 for r in rows])
    _, zones, breaks, sweeps = smc_zones_ref.smc_zones(t_s, a[:, 0], a[:, 1], a[:, 2], a[:, 3], **ZONES_ARGS)
    T = [r[0] for r in rows]
    return {"params": ZONES_ARGS,
            "zones": [{"kind": z["kind"].upper(), "side": SIDE[z["dir"]], "top": float(z["top"]), "bottom": float(z["bot"]),
                       "t0": T[z["t0"]], "t_born": T[z["born"]], "t_end": T[z["end"]] if z["end"] is not None else None,
                       "touches": z["touches"]} for z in zones],
            "breaks": [{"kind": "CHoCH" if b["choch"] else "BOS", "side": SIDE[b["dir"]], "level": float(b["level"]),
                        "t_from": T[b["frm"]], "t": T[b["at"]]} for b in breaks],
            "sweeps": [{"side": SIDE[s["dir"]], "level": float(s["level"]), "t_from": T[s["frm"]], "t": T[s["at"]]}
                       for s in sweeps]}


def lux(rows: List[list]) -> Dict:
    d = luxalgo_smc.smc([r[0] for r in rows], *([r[k] for r in rows] for k in (1, 2, 3, 4)))
    d["obs"] = [{**ob, "kind": "OB"} for ob in d["obs"]]
    d["fvgs"] = [{"kind": "FVG", "side": f["side"], "top": f["hi"], "bottom": f["lo"], "t0": f["t0"], "t1": f["t1"],
                  "t_born": f["t_born"], "t_end": f["t_end"]} for f in d["fvgs"]]
    return d


def prev_day(rows: List[list]) -> Dict:
    """High / low of the previous FxPro server day (LuxAlgo's PDH / PDL) and the bars they were made on."""
    day = lambda ms: _dt.datetime.fromtimestamp(ms / 1000, SERVER_TZ).date()
    last = day(rows[-1][0])
    prev = [r for r in rows if day(r[0]) < last]
    if not prev:
        return {}
    d0 = day(prev[-1][0])
    bars = [r for r in prev if day(r[0]) == d0]
    hi, lo = max(bars, key=lambda r: r[2]), min(bars, key=lambda r: r[3])
    return {"PDH": hi[2], "PDH_t": hi[0], "PDL": lo[3], "PDL_t": lo[0], "day": d0.isoformat()}


def load(sym: str, tf: str, n: int = N_BARS) -> Dict:
    """Everything the /smc page draws for one chart — closed bars only (the page draws the forming one from live.py)."""
    rows = learn.load_bars(sym, tf, n)
    if len(rows) < 60:
        return {"sym": sym, "tf": tf, "bars": rows, "error": f"only {len(rows)} {tf} bars for {sym}"}
    bars = learn.to_dicts(rows)
    m = major_structure(bars, STRUCTURE_N)
    mk = smc_marks.marks(bars, m)
    return {"sym": sym, "tf": tf, "bars": [r[:5] for r in rows], "major": major(rows, bars, m, mk), "zones": smc_zones(rows),
            "lux": lux(rows), "levels": prev_day(rows), "v5": learn.detect_rows(rows, tf, sym), "ta": concepts(bars, m, mk, tf),
            "sd": supply_demand.page(bars, m), "sdbt": sd_backtest.saved(sym, tf), "kcbz": kcbz_saved(sym, tf),
            "sdc": sdc_page(bars, m), "obr": obr_page(bars, m), "sdd": sdd_page(bars, m), **fib_page(bars, sym)}



def _T(bars, i):
    return None if i is None else bars[min(i, len(bars) - 1)]["t"]


def sdc_page(bars: List[Dict], m: Dict) -> List[Dict]:
    """supply / demand the S&D school's way (sd_classic.py, research 2026-11-01) for the page"""
    T = lambda i: _T(bars, i)
    return [{"side": z["side"], "kind": z["kind"], "role": z["role"], "top": z["top"], "bottom": z["bottom"],
             "proximal": z["proximal"], "proximal_wick": z["proximal_wick"], "distal": z["distal"], "t0": T(z["base"][0]),
             "t_dep": T(z["d"]), "t_valid": T(z["valid_idx"]), "t_end": T(z["end_idx"]), "status": z["status"],
             "touches": z["touches"], "t_touch": T(z["touch_idx"]), "t_broken": T(z["broken_idx"]),
             "t_superseded": T(z["superseded_idx"]), "score": z["score"], "parts": z["parts"], "bos": z["bos"],
             "base_n": z["base_n"], "single": z["single"], "height_atr": z["height_atr"], "run_h": z["run_h"],
             "live": z["live"]} for z in sd_classic.zones(bars, m)]


def sdd_page(bars: List[Dict], m: Dict) -> List[Dict]:
    """David's supply / demand, the class rule (sd_david.py): BOS → A-B-C gap in the BOS move → candle A is the zone"""
    T = lambda i: _T(bars, i)
    return [{"side": z["side"], "valid": z["valid"], "why": z["why"], "top": z["top"], "bottom": z["bottom"],
             "mid": z["mid"], "proximal": z["proximal"], "distal": z["distal"], "bos_level": z["bos_level"],
             "t_level": T(z["level_idx"]), "t_origin": T(z["origin"]), "t_break": T(z["break"]),
             "t0": T(z["a"]), "t_c": T(z["a"] + 2) if z["a"] is not None else None,
             "fvg": z["fvg"], "fib_ext": z.get("fib_ext"), "targets": z.get("targets"),
             "status": z["status"], "t_touch": T(z["touch_idx"]), "t_broken": T(z["broken_idx"]),
             "t_superseded": T(z["superseded_idx"]), "t_end": T(z["end_idx"]), "live": z["live"]}
            for z in sd_david.zones(bars, m)]


def fib_page(bars: List[Dict], sym: str = "") -> Dict:
    """the class's Fib rules as they are TRADED (fib_reject.py: the live versions + the reject checklist) on their own
    swing structure: "fbt" = FIB GO WITH TREND, "fbr" = FIB RETRACEMENT, "fbs" = that structure's BOS / CHoCH. A setup
    the checklist refuses has status "rejected" (the spread warning needs the live spread: only the engine checks it)."""
    T = lambda i: _T(bars, i)
    st = fib_trend.swing_structure(bars, fib_trend.STRUCTURE_N)
    keep = ("side", "swing", "status", "why", "H", "L", "levels", "entry", "sl", "tp", "rr", "exit", "result", "warnings", "rejected")

    def row(z, **more):
        d = dict({k: z.get(k) for k in keep}, t_bos=T(z["bos_idx"]), t_h=T(z["h_idx"]), t_l=T(z["l_idx"]),
                 t_entry=T(z["entry_idx"]), t_exit=T(z["exit_idx"]), t_wend=T(min(z["w_end"], len(bars) - 1)),
                 live=z["w_end"] >= len(bars), **more)
        if z.get("rejected"):
            d["would"] = z["status"]                                # what it did anyway: the checklist's own scorecard
            d["status"], d["why"] = "rejected", "; ".join(z["warnings"])
        return d

    tr = [row(z, mark=z.get("mark"), t_choch=T(z["choch_idx"]), t_cross=T(z["cross_idx"]), t_cross_back=T(z["cross_back_idx"]),
              t_touch=T(z.get("touch_idx"))) for z in fib_reject.judged("trend", sym, bars, st)]
    rt = [row(z, entry_level=z["entry_level"]) for z in fib_reject.judged("retrace", sym, bars, st)]
    ev = [{"kind": e["kind"], "side": e["side"], "level": e["level"], "t_level": T(e["level_idx"]), "t": T(e["idx"])}
          for e in st["events"]]
    return {"fbt": tr, "fbr": rt, "fbs": ev}


def obr_page(bars: List[Dict], m: Dict) -> List[Dict]:
    """order blocks the ICT / SMC-indicator way (order_blocks.py, research 2026-11-01) for the page"""
    T = lambda i: _T(bars, i)
    return [{"side": o["side"], "kind": o["kind"], "of": f"{o['event_kind']} {o['dir']}", "n": o["n"], "top": o["top"],
             "bottom": o["bottom"], "body_top": o["body_top"], "body_bottom": o["body_bottom"], "mean": o["mean"],
             "t0": T(o["idx"]), "t_last": T(o["idx_last"]), "t_break": T(o["break_idx"]), "t_end": T(o["end_idx"]),
             "t_touch": T(o["touch_idx"]), "t_mean": T(o["mean_idx"]), "t_invalid": T(o["invalid_idx"]),
             "t_dead": T(o["dead_idx"]), "flip": o["flip"], "status": o["status"], "score": o["score"],
             "parts": o["parts"], "swept": o["swept"], "fvg": o["fvg"], "extreme": o["extreme"], "live": o["live"]}
            for o in order_blocks.blocks(bars, m)]


KCBZ_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine_data", "backtest",
                        "kronos_claude_bos_zone")


def kcbz_saved(sym: str, tf: str) -> Optional[Dict]:
    """the Kronos + Claude BOS → zone backtest (concepter/backtests/kronos_claude_bos_zone.py), or None"""
    try:
        with open(os.path.join(KCBZ_DIR, f"chart_{sym}_{tf}.json")) as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return None


def major(rows: List[list], bars=None, m=None, mk=None) -> Dict:
    """David's structure: BOS at the leg's extreme, CHoCH only at the protected swing, nothing internal — and the
    marks hung on it (smc_marks.py): FVG clusters of the major breaks, the premium / discount range."""
    bars = bars or learn.to_dicts(rows)
    m = m or major_structure(bars, STRUCTURE_N)
    mk = mk or smc_marks.marks(bars, m)
    T = lambda i: None if i is None else bars[min(i, len(bars) - 1)]["t"]
    lv = lambda q: q and {"price": q["price"], "t": q["t"], "kind": q["kind"]}
    end = lambda f: f["inverted_idx"] if f["inverted_idx"] is not None else f["filled_idx"]
    r = mk["range"]
    return {"n": STRUCTURE_N, "trend": m["trend"], "protected": lv(m["protected"]), "bos_level": lv(m["bos_level"]),
            "points": [{"t": q["t"], "price": q["price"], "kind": q["kind"]} for q in m["points"]],
            "breaks": [{"kind": e["kind"], "side": SIDE[e["side"]], "level": e["level"], "t_from": e["level_t"], "t": e["t"],
                        "origin": e["origin"]["price"], "origin_t": e["origin"]["t"]} for e in m["events"]],
            "fvgs": [{"side": f["side"], "top": f["top"], "bottom": f["bottom"], "t0": T(f["idx"] - 1), "t_mid": T(f["idx"]),
                      "status": f["status"], "live": f["live"], "invalid": f["invalid"], "superseded": f["superseded"],
                      "atr": f["atr_mult"], "of": f"{f['event_kind']} {f['side']}", "t_touch": T(f["touched_idx"]),
                      "t_ce": T(f["ce_idx"]), "t_end": T(end(f)), "inverted": f["inverted_idx"] is not None}
                     for f in mk["fvgs"]],
            "obs": [{"side": o["side"], "top": o["top"], "bottom": o["bottom"], "mid": o["mid"], "t0": T(o["idx"]),
                     "t_break": T(o["break_idx"]), "of": f"{o['event_kind']} {o['side']}", "status": o["status"], "live": o["live"],
                     "has_fvg": o["has_fvg"], "t_touch": T(o["touch_idx"]), "t_mean": T(o["mean_idx"]),
                     "t_invalid": T(o["invalid_idx"]), "t_breaker": T(o["breaker_idx"]), "t_dead": T(o["dead_idx"])} for o in mk["obs"]],
            "pools": [{"kind": q["kind"], "side": "high" if q["high"] else "low", "level": q["level"], "zone": q["zone"],
                       "touches": q["touches"], "t_first": T(q["first"]), "t_born": T(q["born"]), "status": q["status"],
                       "t_broken": T(q["broken_idx"]),
                       "sweeps": [{"t": T(w["start"]), "t_end": T(w["end"]), "extreme": w["extreme"], "kind": w["kind"], "bos": w["bos"]}
                                  for w in q["sweeps"]]} for q in mk["pools"]],
            "range": r and {k: r[k] for k in ("trend", "high", "low", "eq", "ote", "price", "pos", "zone", "in_ote")}
                         | {"t0": T(r["from_idx"])}}


CANDLE_BARS = 600         # candle patterns of the newest 600 bars
REVERSAL_BARS = 10        # a reversal pattern's candles must make the high / low of the 10 bars before it
PATTERNS_SHOW = 12        # the newest chart patterns


def _candles(bars: List[Dict], mk: Dict, A: List[float], tf: str) -> List[Dict]:
    """TA-Lib's 61 patterns on the newest bars; "at" = the live SMC marks of the pattern's own side its candles
    touched then — a bullish pattern in a bull OB / FVG or at sell-side liquidity (a low), a bearish one in a bear
    OB / FVG or at buy-side liquidity (a high), the pool within 0.25 ATR: where a candle pattern means something"""
    a = np.array([[b["o"], b["h"], b["l"], b["c"]] for b in bars], dtype=float)
    P = candles.patterns(a[:, 0], a[:, 1], a[:, 2], a[:, 3])
    n, first = len(bars), max(0, len(bars) - CANDLE_BARS)
    if bars and bars[-1]["t"] + learn.TF_MS[tf] > time.time() * 1000:
        n -= 1                                                    # the forming candle is not read (it would repaint)
    zones = [(o["break_idx"], next((x for x in (o["invalid_idx"],) if x is not None), n), o["bottom"], o["top"],
              f"{'Bull' if o['side'] == 'bull' else 'Bear'} OB", 1 if o["side"] == "bull" else -1) for o in mk["obs"]]
    zones += [(f["idx"] + 1, next((x for x in (f["inverted_idx"], f["filled_idx"]) if x is not None), n), f["bottom"], f["top"],
               f"{'Bull' if f['side'] == 'bull' else 'Bear'} FVG", 1 if f["side"] == "bull" else -1) for f in mk["fvgs"]]
    pools = [(q["born"], q["broken_idx"] if q["broken_idx"] is not None else (q["sweeps"][0]["start"] if q["sweeps"] else n),
              q["level"], _pool_label({"kind": q["kind"], "touches": q["touches"]}), -1 if q["high"] else 1) for q in mk["pools"]]
    DIR = {"bullish": 1, "bearish": -1, "neutral": 0}
    out = []
    for name, v in P.items():
        info = candles.INFO[name]
        for i in np.nonzero(v[first:n])[0] + first:
            b, val = bars[i], int(v[i])
            sd = DIR.get(info["direction"], 1 if val > 0 else -1)   # GRAVESTONEDOJI is bearish but reports +100
            # the patterns that end on this candle: the pattern's candles overlap the level
            lo, hi = min(bars[j]["l"] for j in range(max(0, i - info["candles"] + 1), i + 1)), \
                max(bars[j]["h"] for j in range(max(0, i - info["candles"] + 1), i + 1))
            at = [lb for s0, s1, bot, top, lb, z in zones if z == sd and s0 <= i <= s1 and lo <= top and hi >= bot]
            at += [lb for s0, s1, lv, lb, z in pools if z == sd and s0 <= i <= s1 and lo - 0.25 * A[i] <= lv <= hi + 0.25 * A[i]]
            j0 = i - info["candles"] + 1                          # a reversal needs a move to reverse (Nison, Bulkowski):
            prior = bars[max(0, j0 - REVERSAL_BARS):max(0, j0)]   # its candles make the extreme of the 10 bars before
            turn = bool(prior) and (lo <= min(x["l"] for x in prior) if sd > 0 else hi >= max(x["h"] for x in prior) if sd < 0 else False)
            out.append({"t": b["t"], "n": name, "v": val, **({"at": sorted(set(at))} if at else {}), **({"turn": True} if turn else {})})
    return sorted(out, key=lambda c: c["t"])


def concepts(bars: List[Dict], m: Dict, mk: Dict, tf: str) -> Dict:
    """rows 2–8 of the concept table (levels, candles, trend lines, chart patterns, Fibonacci / ATR / RSI / MACD /
    VWAP, volume profile, Wyckoff / Elliott), times instead of bar numbers"""
    A = atr14(bars)
    n = len(bars)
    T = lambda i: None if i is None else bars[min(max(i, 0), n - 1)]["t"] + (max(i - (n - 1), 0) * (bars[-1]["t"] - bars[-2]["t"]))
    rnd = lambda xs, k=6: [None if x is None else float(f"{x:.{k}g}") for x in xs]   # significant digits
    lv = levels.levels(bars, m, A, tf)
    sw = lambda ws: [{"t": T(w["start"]), "t_end": T(w["end"]), "extreme": w["extreme"], "kind": w["kind"]} for w in ws]
    sessions = [{"key": x["key"], "label": x["label"], "date": x["date"], "t0": T(x["first"]), "t1": T(x["last"]),
                 "final": x["final"], "high": x["high"], "high_t": T(x["high_idx"]), "low": x["low"], "low_t": T(x["low_idx"]),
                 "high_status": x.get("high_status"), "low_status": x.get("low_status"),
                 "high_sweeps": sw(x.get("high_sweeps", [])), "low_sweeps": sw(x.get("low_sweeps", [])),
                 "t_high_broken": T(x.get("high_broken_idx")), "t_low_broken": T(x.get("low_broken_idx")),
                 "judas": x.get("judas") and {"side": x["judas"]["side"], "t": T(x["judas"]["start"]), "extreme": x["judas"]["extreme"]}}
                for x in lv["sessions"]]
    pb = lv["pullback"]
    tl = trendlines.trendlines(bars, m, A)
    line = lambda ln: {"side": ln["side"], "status": ln["status"], "t1": T(ln["b1"]), "p1": ln["p1"], "t2": T(ln["b2"]), "p2": ln["p2"],
                       "slope": ln["slope"], "touches": [T(i) for i in ln["touches"]], "t_known": T(ln["known"]),
                       "t_end": T(ln["end"]), "t_break": T(ln["break_idx"]), "held": ln.get("held"), "t_back": T(ln.get("back_idx")),
                       "confirmed": ln["confirmed"], "offset": ln["offset"]}
    rg = tl["regression"]
    cps = chart_patterns.patterns(bars, A, tf)[-PATTERNS_SHOW:]
    ind = indicators.indicators(bars, m)
    fb, fe, vw = ind["fib"], ind["fib_ext"], ind["vwap"]
    vp = volume_profile.profiles(bars, m, tf)
    prof = lambda p: p and {**{k: p[k] for k in ("row", "low", "rows", "poc", "vah", "val", "hvn", "lvn")}, "t0": T(p["from_idx"]),
                            "t1": T(p["to_idx"]), "day": p.get("day"), "developing": p.get("developing"), "naked": p.get("naked"),
                            "t_tested": T(p.get("tested_idx")), "t_accepted": T(p.get("accepted_idx"))}
    wy = wyckoff.wyckoff(bars, m, A, tf)
    ew = elliott.elliott(bars, m["points"], A)
    pts = lambda P: [{"t": T(q["idx"]), "price": q["price"], "label": q["label"]} for q in P]
    return {
        "levels": {"sessions": sessions, "killzones": [{**k, "t0": T(k["first"]), "t1": T(k["last"])} for k in lv["killzones"]],
                   "opens": [{"label": o["label"], "t": T(o["idx"]), "price": o["price"]} for o in lv["opens"]],
                   "pullback": pb and {**{k: pb[k] for k in ("trend", "origin", "extreme", "deepest", "now", "class", "levels")},
                                       "t_origin": T(pb["origin_idx"]), "t_extreme": T(pb["extreme_idx"]), "t_deepest": T(pb["deepest_idx"])},
                   "pullbacks": [{**p, "t": p["t"]} for p in lv["pullbacks"][-8:]]},
        "candles": _candles(bars, mk, A, tf),
        "candle_info": {k: {f: v[f] for f in ("label", "kind", "direction", "candles", "notes")} for k, v in candles.INFO.items()},
        "trend": {"shown": [line(ln) for ln in tl["shown"]],
                  "regression": rg and {"t_from": T(rg["from_idx"]), "p_from": rg["at_from"], "t_to": T(rg["to_idx"]), "p_to": rg["at_to"],
                                        "sigma": rg["sigma"], "k": rg["k"], "r": rg["r"], "trend_channel": rg["trend_channel"]}},
        "patterns": [{**{k: r.get(k) for k in ("pattern", "side", "status", "height", "target", "target_realistic", "stop", "fail_rate",
                                               "confirm_price", "break", "atr")},
                      "points": pts(r["points"]), "lines": [{"kind": x["kind"], "t1": T(x["i1"]), "p1": x["p1"], "slope": x["slope"]} for x in r["lines"]],
                      "t_first": T(r["first_idx"]), "t_known": T(r["known_idx"]), "t_confirm": T(r["confirm_idx"]), "t_end": T(r["end_idx"]),
                      "t_invalid": T(r["invalid_idx"]), "pole": r.get("pole") and {"t0": T(r["pole"]["i0"]), "p0": r["pole"]["p0"]}} for r in cps],
        "ind": {"atr": {"wilder": ind["atr"]["wilder"][-1], "mt5": ind["atr"]["mt5"][-1]}, "rsi": rnd(ind["rsi"], 3),
                "macd": {k: rnd(ind["macd"][k]) for k in ("macd", "signal")},                 # histogram = macd − signal
                "divergences": [{**{k: d[k] for k in ("osc", "kind", "side", "price", "prev_price", "osc_val", "prev_osc")},
                                 "t": T(d["idx"]), "t_prev": T(d["prev_idx"]), "t_known": T(d["known"]), "t_invalid": T(d["invalid_idx"])}
                                for d in ind["divergences"] if d["idx"] >= n - CANDLE_BARS],
                "fib": fb and {**{k: fb[k] for k in ("trend", "one", "zero", "retrace", "targets")}, "t_one": T(fb["one_idx"]), "t_zero": T(fb["zero_idx"])},
                "fib_ext": fe and {**{k: fe[k] for k in ("side", "A", "B", "C", "levels")}, "t_A": T(fe["A_idx"]), "t_B": T(fe["B_idx"]), "t_C": T(fe["C_idx"])},
                "vwap": vw and {"session": rnd(vw["session"]["vwap"]), "sd": rnd(vw["session"]["sd"]), "week": rnd(vw["week"]),
                                "starts": [T(i) for i in vw["starts"]],
                                "anchored": vw["anchored"] and rnd(vw["anchored"]), "t_anchor": T(vw["anchored_idx"])}},
        "profile": {"volume": vp["volume"], "row": vp["row"], "days": [prof(p) for p in vp["days"]], "leg": prof(vp["leg"])},
        "wyckoff": {"volume": wy["volume"], "ranges": [{**{k: r[k] for k in ("kind", "phase", "status", "why", "schematic", "provisional", "low", "high")},
                                                        "t0": T(r["from_idx"]), "t1": T(r["to_idx"]),
                                                        "events": [{**{k: e.get(k) for k in ("label", "price", "climax", "grade", "heavy", "strong", "vol")},
                                                                    "t": T(e["idx"])} for e in r["events"]]} for r in wy["ranges"]]},
        "elliott": {"counts": [{**{k: c[k] for k in ("pattern", "side", "stage", "score", "ratios", "invalidation", "rule", "targets", "provisional", "notes")},
                                "points": pts(c["points"])} for c in ew["counts"]],
                    "abc": ew["abc"] and {**{k: ew["abc"].get(k) for k in ("pattern", "side", "stage", "score", "b_retrace", "c_vs_a", "invalidation", "rule", "targets", "provisional")},
                                          "points": pts(ew["abc"]["points"])}},
    }


POOL_NAME = {"major high": "swing high", "major low": "swing low"}


def _pool_label(q: Dict) -> str:
    return f"{q['kind']} ×{q['touches']}" if q["kind"] in ("EQH", "EQL") else POOL_NAME.get(q["kind"], q["kind"])


def _merge_pools(pools) -> List[Dict]:
    """one entry per price: an EQH that is also the swing high and the PDH is one pool, labelled with all three"""
    by: Dict[float, Dict] = {}
    for q in pools:
        k = round(q["level"], 8)
        if k in by:
            by[k]["label"] += " · " + _pool_label(q)
            by[k]["t_first"] = min(by[k]["t_first"], q["t_first"])
        else:
            by[k] = {**q, "label": _pool_label(q)}
    return list(by.values())


def _merge_sweeps(pools: List[Dict]) -> List[Dict]:
    by: Dict[tuple, Dict] = {}
    for q in pools:
        for w in q["sweeps"]:
            k = (w["t"], round(q["level"], 8))
            if k in by:
                by[k]["label"] += " · " + _pool_label(q)
            else:
                by[k] = {**w, "side": q["side"], "level": q["level"], "label": _pool_label(q)}
    return sorted(by.values(), key=lambda w: w["t"])


def summary(d: Dict, near: int = 8, last: int = 8) -> Dict:
    """Per tool: the zones still live nearest to price, and the latest confirmations."""
    price = d["bars"][-1][4]
    dist = lambda z: 0.0 if z["bottom"] <= price <= z["top"] else min(abs(z["top"] - price), abs(z["bottom"] - price))
    L = d["lux"]
    lux_live = [z for z in L["obs"] if z["t_end"] is None and z.get("shown")] + [z for z in L["fvgs"] if z["t_end"] is None]
    v5 = d["v5"]
    M, S = d["major"], d["sd"]
    return {
        "price": price, "t_last": d["bars"][-1][0], "levels": d["levels"],
        "major": {"trend": M["trend"], "protected": M["protected"], "bos_level": M["bos_level"], "breaks": M["breaks"][-last:],
                  "range": M["range"], "fvgs_live": sorted((f for f in M["fvgs"] if f["live"]), key=dist)[:near],
                  "fvgs_recent": M["fvgs"][-4:],
                  "obs_live": [o for sd in ("bull", "bear") for o in
                               sorted((o for o in M["obs"] if o["live"] and o["side"] == sd), key=dist)[:OB_SHOW]],
                  "breakers": sorted((o for o in M["obs"] if o["status"] == "breaker"), key=dist)[:2],
                  "pools_above": sorted(_merge_pools(q for q in M["pools"] if q["status"] == "untaken" and q["level"] > price),
                                        key=lambda q: q["level"])[:POOLS_SHOW],
                  "pools_below": sorted(_merge_pools(q for q in M["pools"] if q["status"] == "untaken" and q["level"] <= price),
                                        key=lambda q: -q["level"])[:POOLS_SHOW],
                  "sweeps": _merge_sweeps(M["pools"])[-6:]},
        "sd": {"live": [z for side in ("supply", "demand") for z in
                        sorted((z for z in S["zones"] if z["live"] and z["side"] == side and z["role"].startswith("origin")),
                               key=dist)[:SD_SHOW]],
               "n_live": sum(1 for z in S["zones"] if z["live"]),
               "n_origin": sum(1 for z in S["zones"] if z["live"] and z["role"].startswith("origin")),
               "valid": S["valid"], "candidates": S["candidates"], "filtered": S["filtered"]},
        "zones": {"live": sorted((z for z in d["zones"]["zones"] if z["t_end"] is None), key=dist)[:near],
                  "breaks": d["zones"]["breaks"][-last:], "sweeps": d["zones"]["sweeps"][-4:],
                  "n_live": sum(1 for z in d["zones"]["zones"] if z["t_end"] is None)},
        "lux": {"live": sorted(lux_live, key=dist)[:near],
                "breaks": [b for b in L["breaks"] if b["scope"] == "swing"][-4:] + [b for b in L["breaks"] if b["scope"] == "internal"][-last:],
                "zones": L["zones"], "trailing": L["trailing"], "trend": {k: SIDE.get(v, "–") for k, v in L["trend"].items()}},
        "v5": {"trend": v5.get("trend"), "zones": sorted(v5["zones"], key=lambda z: z["t"])[-6:],
               "fvgs": sorted(v5["fvgs"], key=lambda z: z["t"])[-6:],
               "breaks": [{**e, "side": SIDE.get(e["side"], e["side"])} for e in v5["events"][-last:]]},
    }


_CACHE: Dict[tuple, tuple] = {}
CACHE_S = 30          # the internet copy serves this page too: one computation per chart per 30 s, whoever asks


FULL_BARS = 100000    # "whole history": every bar on disk (M15 / M30 ≈ 100,000 since 2026-11-03 → ~1.5 min to compute, kept 10 min)
FULL_CACHE_S = 600


def page(sym: str, tf: str, n: int = N_BARS) -> Dict:
    hit = _CACHE.get((sym, tf, n))
    if hit and time.time() - hit[0] < (CACHE_S if n <= N_BARS else FULL_CACHE_S):
        return hit[1]
    d = load(sym, tf, n)
    if "error" not in d:
        d["summary"] = summary(d)
    if len(_CACHE) > 64:
        _CACHE.clear()
    _CACHE[(sym, tf, n)] = (time.time(), d)
    return d


def _ist(ms: int) -> str:
    return (_dt.datetime.fromtimestamp(ms / 1000, _dt.timezone.utc) + _dt.timedelta(hours=5, minutes=30)).strftime("%m-%d %H:%M")


def report(sym: str, tf: str) -> str:
    d = page(sym, tf)
    if "error" in d:
        return f"== {sym} {tf}: {d['error']}"
    s, out = d["summary"], []
    out.append(f"== {sym} {tf}  last bar {_ist(s['t_last'])} IST  price {s['price']:g}")
    M = s["major"]
    out.append(f"  Structure (David's rule): trend {M['trend']}  protected {M['protected'] and M['protected']['price']}"
               f"  BOS level {M['bos_level'] and M['bos_level']['price']}")
    for b in M["breaks"]:
        out.append(f"    {_ist(b['t'])}  {b['kind']:<5} {b['side']:<4} level {b['level']:g}")
    SD = s["sd"]
    out.append(f"  Supply / demand (David's gate: {SD['valid']} of {SD['candidates']} candidates valid, {SD['n_live']} live"
               f" — the {SD['n_origin']} origin boxes below; the rest are nested inside the same breaks, the page draws the origin)")
    for z in SD["live"]:
        out.append(f"    {z['side']:<6} {z['kind'].split(' ')[0]:<4} {z['bottom']:g} – {z['top']:g}  entry {z['entry']:g}"
                   f"  {z['status']:<7} checklist {z['score']}/10  base from {_ist(z['t0'])}, {z['event']} {_ist(z['t_break'])}")
    for name, k in (("SMC Zones", "zones"), ("LuxAlgo", "lux")):
        out.append(f"  {name}: zones live nearest price")
        for z in s[k]["live"]:
            out.append(f"    {z['kind']:<4} {z['side']:<4} {z.get('scope', ''):<8} {z['bottom']:g} – {z['top']:g}  from {_ist(z['t0'])}")
        out.append(f"  {name}: last confirmations")
        for b in sorted(s[k]["breaks"], key=lambda b: b["t"]):
            out.append(f"    {_ist(b['t'])}  {b['kind']:<5} {b['side']:<4} {b.get('scope', ''):<8} level {b['level']:g}")
    T = d["ta"]
    pb, I = T["levels"]["pullback"], T["ind"]
    out.append("  Concepts (rows 2–8):")
    if pb:
        out.append(f"    pullback of the {pb['trend']} leg {pb['origin']:g} → {pb['extreme']:g}: deepest {pb['deepest'] * 100:.1f} % ({pb['class']}),"
                   f" close {pb['now'] * 100:.1f} %")
    for x in [x for x in T["levels"]["sessions"] if x["final"]][-3:]:
        out.append(f"    {x['label']:<11} {x['date']}  H {x['high']:g} {x['high_status']}  L {x['low']:g} {x['low_status']}")
    key = [c for c in T["candles"] if c.get("at") and c.get("turn") and T["candle_info"][c["n"]]["kind"] == "reversal"][-3:]
    for c in key:
        out.append(f"    {_ist(c['t'])}  {T['candle_info'][c['n']]['label']} ({'bull' if c['v'] > 0 else 'bear'}) at {', '.join(c['at'])}")
    for p in T["patterns"][-3:]:
        out.append(f"    {p['pattern']} {p['side']} {p['status']} (known {_ist(p['t_known'])})")
    rsi = I["rsi"][-1]
    out.append(f"    ATR Wilder {I['atr']['wilder']:g} / MT5 {I['atr']['mt5']:g} · RSI {rsi if rsi is None else round(rsi, 1)}"
               + (f" · VWAP {I['vwap']['session'][-1]:g}" if I["vwap"] else " · no tick volume: no VWAP"))
    for r in T["wyckoff"]["ranges"][:1]:
        out.append(f"    Wyckoff {r['kind']} phase {r['phase']} {r['status']} {r['low']:g} – {r['high']:g}")
    for c in T["elliott"]["counts"][:1]:
        out.append(f"    Elliott {c['pattern']} {c['side']} {c['stage']} score {c['score']} invalid beyond {c['invalidation']:g}")
    out.append("  V5 engine: last breaks")
    for e in s["v5"]["breaks"]:
        out.append(f"    {_ist(e['t'])}  {e['kind']:<5} {e['side']:<4} level {e['level']:g}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="SMC Zones / LuxAlgo / V5 on the same bars")
    ap.add_argument("cmd", choices=["report"])
    ap.add_argument("--sym", default="GOLD")
    ap.add_argument("--tf", default="M15")
    a = ap.parse_args()
    print(report(a.sym, a.tf))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
