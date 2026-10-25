"""
engine/backtest.py — the V5 engine replayed on FxPro's history (engine.history), every setup recorded with
what it looked like on the chart and how it ended, so the worthless supply/demand / FVG / BOS setups can be
found from data (David 2026-10-25: "it has to avoid the worthless ones, for that we have to train").

    python3 -m engine.backtest run [--tfs M15,M30,H1] [--symbols A,B]   → engine_data/backtest/setups.jsonl
    python3 -m engine.backtest report                                    → engine_data/backtest/report.txt / .json

The live code does the deciding: strategy.structure / bos_setups / pullback / bias / stop_price /
opposite_levels / final_target / pretrade / strength / layer_price, Book.refuse's broker checks and the real
Book.trail for the stop management (Mode A break-even, Mode B Target 1 + trailing, the R locks). On purpose
different from live, kept small:
  - the structure runs once over the whole history, swings expiring after the live bar window
  - a pullback fills at the entry level (or the M5 open when price gapped through it), not the tick seen
    within a minute; sells fill at the bid, buys at the ask (bid + that bar's spread), stops trigger on the
    closing side; when one M5 bar holds both the stop and the target, the stop counts
  - no slots or equity changes: every setup is judged on its own, 2.5 % normal + 1.5 % layer of fixed equity
Every touched setup is kept, also those the live engine refuses (no target → a 3R what-if target), so the
filters themselves can be judged.
"""
from __future__ import annotations

import argparse
import bisect
import datetime as _dt
import json
import math
import os
import time
from collections import Counter, defaultdict
from multiprocessing import Pool
from typing import Dict, List, Optional

from . import book as B
from . import strategy as V
from .config import DATA_DIR, ENGINE, STRATEGY as S
from .feed import TF_MIN
from .history import HIST_DIR

OUT_DIR = os.path.join(DATA_DIR, "backtest")
SETUPS_FILE = os.path.join(OUT_DIR, "setups.jsonl")
HORIZON = 2000                                 # M5 bars (≈ 7 days) the excursion is followed for
TREND_SIDE = {"bullish": "buy", "bearish": "sell"}


# ── the live Book's pieces, run without MT5 or files ──
class _MT5:
    def sltp(self, ticket, sl=0.0, tp=0.0):
        return {"ok": True}


class _Feed:
    def __init__(self, info: Dict):
        self.info, self.cur = info, []

    def completed(self, sym, tf, at_ms=None):
        return self.cur


class _Book:
    """What Book.trail / Book.refuse read from self."""
    def __init__(self, sym: str, info: Dict):
        self.feed = _Feed({sym: info})

    def free_slots(self) -> int:
        return 1


def _quiet() -> None:
    B.journal = lambda *a, **k: None
    B.log = lambda *a, **k: None
    B.mt5c = _MT5()


# ── bars ──
def load(path: str) -> Dict:
    with open(path) as f:
        d = json.load(f)
    bars = {}
    for tf, rows in d["bars"].items():
        sps = sorted(r[5] for r in rows if r[5] > 0)
        med = sps[len(sps) // 2] if sps else 0.0
        bars[tf] = [{"t": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4], "sp": r[5] if r[5] > 0 else med} for r in rows]
    return {**d, "bars": bars}


class Series:
    """One timeframe with its bar start times, for 'the bars completed by time now' windows."""
    def __init__(self, tf: str, bars: List[Dict]):
        self.tf, self.bars, self.ms = tf, bars, TF_MIN[tf] * 60_000
        self.T = [b["t"] for b in bars]

    def done(self, now: int) -> int:
        """Number of bars that had closed by `now`."""
        return bisect.bisect_right(self.T, now - self.ms)

    def window(self, now: int, n: int) -> List[Dict]:
        i = self.done(now)
        return self.bars[max(0, i - n):i]


def _side_trend(label: str, side: str) -> str:
    s = TREND_SIDE.get(label)
    return "with" if s == side else "against" if s else "unclear"


def _ratio(a, b) -> Optional[float]:
    return round(a / b, 3) if a is not None and b else None


# ── outcomes ──
def fixed_outcome(side: str, entry: float, stop: float, tp: float, m5: List[Dict], j: int) -> Dict:
    """Stop / target only, from the touch bar on; the excursion keeps being followed after the target until
    the stop or HORIZON bars (so any other R target can be read off mfe_r)."""
    sell, risk = side == "sell", abs(entry - stop)
    res, mfe, mfe_k = None, 0.0, 0
    for k in range(j, min(len(m5), j + HORIZON)):
        b = m5[k]
        if (b["h"] + b["sp"] >= stop) if sell else (b["l"] <= stop):
            if res is None:
                res = {"r": -1.0, "exit": "sl", "bars": k - j}
            break
        if k > j:
            fav = (entry - (b["l"] + b["sp"])) if sell else (b["h"] - entry)
            if fav > mfe:
                mfe, mfe_k = fav, k - j
            if res is None and ((b["l"] + b["sp"] <= tp) if sell else (b["h"] >= tp)):
                res = {"r": round(abs(tp - entry) / risk, 3), "exit": "tp", "bars": k - j}
    return {**(res or {"r": None, "exit": "open", "bars": None}), "mfe_r": round(mfe / risk, 3), "mfe_bars": mfe_k}


def managed_outcome(sym: str, info: Dict, side: str, tf: str, entry: float, stop: float, tp: float, layer: Optional[float],
                    m5: List[Dict], j: int, cancel_t: Optional[int]) -> Dict:
    """The live management (Book.trail) bar by bar: exits on the stop as it stood after the previous bar, the
    layer fills when price reaches it (Mode B), an unfilled layer dies when the setup's timeframe closes beyond
    the zone. → % of equity (2.5 % normal + 1.5 % layer risk) and the same in normal-R."""
    sell, sg = side == "sell", -1 if side == "sell" else 1
    bk = _Book(sym, info)
    t = {"id": "bt", "symbol": sym, "tf": tf, "side": side, "entry": entry, "stop0": stop, "stop": stop, "tp": tp,
         "opened_ms": m5[j]["t"] + 60_000, "mode": "A", "best": entry, "tp1": None, "tp1_hit": False, "be_done": False, "locked_r": 0.0}
    risk = abs(entry - stop)
    lay = "pending" if layer else None
    moves = 0
    for k in range(j, len(m5)):
        b, sp = m5[k], m5[k]["sp"]
        if lay == "pending":
            if cancel_t is not None and b["t"] >= cancel_t:
                lay = "cancelled"
            elif (b["h"] >= layer) if sell else (b["l"] + sp <= layer):
                lay = "filled"
                t["mode"], t["tp1"] = "B", entry + float(S["tp1_fraction"]) * (tp - entry)
        st = t["stop"]
        gap_sl = (b["o"] + sp >= st) if sell else (b["o"] <= st)
        hit_sl = (b["h"] + sp >= st) if sell else (b["l"] <= st)
        hit_tp = k > j and ((b["l"] + sp <= tp) if sell else (b["h"] >= tp))
        if hit_sl or hit_tp:
            px = (b["o"] + sp if sell else b["o"]) if gap_sl else st if hit_sl else tp
            pct = float(S["normal_risk_pct"]) * sg * (px - entry) / risk
            if lay == "filled":
                pct += float(S["layer_risk_pct"]) * sg * (px - layer) / abs(layer - stop)
            return {"pct": round(pct, 3), "r": round(pct / float(S["normal_risk_pct"]), 3), "exit": "sl" if hit_sl else "tp",
                    "stop_moved": moves, "final_stop": st, "layer": lay, "bars": k - j, "exit_t": b["t"]}
        bk.feed.cur = m5[max(0, j - 1, k - 60):k + 1]   # trail reads the last M5 swing and bar; `best` is kept in t
        before = t["stop"]
        B.Book.trail(bk, t, [{"ticket": 1, "price_current": b["c"] + (sp if sell else 0), "tp": tp}])
        moves += t["stop"] != before
    return {"pct": None, "r": None, "exit": "open", "stop_moved": moves, "final_stop": t["stop"], "layer": lay, "bars": None, "exit_t": None}


# ── the replay of one symbol ──
def replay(path: str, tfs: List[str]) -> Dict:
    _quiet()
    d = load(path)
    sym, info, market = d["symbol"], d["info"], d["market"]
    ser = {tf: Series(tf, d["bars"][tf]) for tf in d["bars"]}
    m5s = ser["M5"]
    m5 = m5s.bars
    point = float(info["point"])
    start = max(ser[tf].bars[0]["t"] + n * ser[tf].ms for tf, n in ENGINE["bars"].items() if tf in ser)
    out: List[Dict] = []
    counts: Counter = Counter()
    for tf in tfs:
        s = ser[tf]
        bars = s.bars
        st = V.structure(bars, window=ENGINE["bars"][tf])
        evs = st["events"]
        ev_t = [e["t"] for e in evs]
        streak, prev = [], None
        for e in evs:                               # breaks in a row on the same side before this one
            streak.append(streak[-1] + 1 if prev == e["side"] and streak else 0)
            prev = e["side"]
        ev_pos = {e["t"]: i for i, e in enumerate(evs)}
        sw = {k: [x for x in st["swings"] if x["kind"] == k] for k in ("high", "low")}
        sw_idx = {k: [x["idx"] for x in v] for k, v in sw.items()}
        cands = [c for c in V.bos_setups(bars, st, tf, sym, max_age=len(bars) + 1) if c["complete"]]
        for c in cands:                             # the setup exists for the engine once its last piece has closed
            k = c["formed_idx"] if c["zone"] else max(c["formed_idx"], c["mb"]["idx"] + 2)
            c["known_t"] = bars[min(k, len(bars) - 1)]["t"] + s.ms
        newer = {side: sorted((c["bos"]["t"], c["known_t"]) for c in cands if c["side"] == side) for side in ("buy", "sell")}
        age = int(S["setup_max_age_bars"])
        for c in cands:
            if c["known_t"] < start:
                continue
            counts[f"{tf} setups"] += 1
            side, sell = c["side"], c["side"] == "sell"
            expire = bars[min(len(bars) - 1, c["bos"]["idx"] + age)]["t"] + s.ms
            j = None
            for q in range(bisect.bisect_left(m5s.T, c["known_t"]), len(m5)):
                if m5[q]["t"] >= expire:
                    break
                if (m5[q]["h"] >= c["entry"]) if sell else (m5[q]["l"] <= c["entry"]):
                    j = q
                    break
            nw = [kt for bt, kt in newer[side] if bt > c["bos"]["t"]]
            nk = min(nw) if nw else None
            if nk is not None and (j is None and nk < expire or j is not None and m5[j]["t"] >= nk):
                counts[f"{tf} superseded"] += 1
                continue
            if j is None:
                counts[f"{tf} never came back"] += 1
                continue
            out.append(evaluate(sym, info, market, tf, c, j, ser, st, evs, ev_t, streak, ev_pos, sw, sw_idx, point))
            counts[f"{tf} touched"] += 1
    return {"symbol": sym, "records": out, "counts": dict(counts),
            "from": start, "to": m5[-1]["t"]}


def evaluate(sym, info, market, tf, c, j, ser, st, evs, ev_t, streak, ev_pos, sw, sw_idx, point) -> Dict:
    side, sell = c["side"], c["side"] == "sell"
    m5, s = ser["M5"].bars, ser[tf]
    hit = m5[j]
    now = hit["t"]                                 # the engine sees the bars that closed before the touch bar
    h1 = ser["H1"].window(now, ENGINE["bars"]["H1"])
    h4 = ser["H4"].window(now, ENGINE["bars"]["H4"])
    tfb = s.window(now, ENGINE["bars"][tf])
    m15 = ser["M15"].window(now, ENGINE["bars"]["M15"])
    m5w = ser["M5"].window(now, ENGINE["bars"]["M5"])
    bias = V.trade_bias(h4, h1)                    # David 2026-10-25: the H4 and the H1 bias must agree (as live)
    aligned = bias["bias"] == side
    e = c["entry"]
    bid = max(e, hit["o"]) if sell else min(e, hit["o"])
    ask = bid + hit["sp"]
    entry = bid if sell else ask
    stop = V.stop_price(c, point)
    levels = V.opposite_levels(side, (tf, tfb), ("H1", h1), ("H4", h4))
    tgt = V.final_target(side, entry, stop, levels)
    atr15 = V.sl_atr(m15)
    why = V.pretrade(c, entry, stop, tgt, atr15)
    bk = _Book(sym, info)
    if not why:
        why = B.Book.refuse(bk, sym, side, entry, stop, tgt["price"], bid, ask)
    risk = abs(entry - stop)
    # the strength of the pullback and the layer, as Book.signal works them out
    cur = s.done(now)
    kind = "high" if side == "buy" else "low"
    p = bisect.bisect_left(sw_idx[kind], c["bos"]["idx"])
    peak = sw[kind][p] if p < len(sw[kind]) and sw[kind][p]["confirmed"] <= cur - 1 else None
    if peak:
        end_t = peak["t"]
    else:
        rng = range(c["bos"]["idx"], max(c["bos"]["idx"] + 1, cur))
        end_t = s.bars[(max if side == "buy" else min)(rng, key=lambda i: s.bars[i]["h" if side == "buy" else "l"])]["t"]
    x = len(m5w) - 1
    r = next((k for k, bb in enumerate(m5w) if bb["t"] > end_t), max(0, x - 6))
    strength = V.strength(m5w, min(r, x), x, side) if x >= 0 else {"level": "weak", "score": 0}
    lay = V.layer_price(side, entry, stop, strength["level"]) if risk else None
    gap = B.stops_gap(info)
    layer_px = lay["price"] if lay and abs(lay["price"] - bid if sell else ask - lay["price"]) >= gap else None
    # features: what the setup looked like on the chart
    atr_tf = V.tools.atr(tfb[-57:], 14)
    poi, f = c["poi"], c["fvg"]
    i0 = ev_pos.get(c["bos"]["t"], 0)
    later = evs[i0 + 1:bisect.bisect_right(ev_t, now - s.ms)]
    hs, ls = [x for x in bias["swings"] if x["kind"] == "high"], [x for x in bias["swings"] if x["kind"] == "low"]
    rng_pos = None
    if hs and ls and hs[-1]["price"] > ls[-1]["price"]:
        H, L = hs[-1]["price"], ls[-1]["price"]
        rng_pos = round(((entry - L) if side == "buy" else (H - entry)) / (H - L), 3)
    near_zone = poi["top"] if side == "buy" else poi["bottom"]
    feats = {
        "kind": c["kind"], "disp_x": (c["zone"] or {}).get("displacement", {}).get("x"),
        "zone_atr": _ratio(poi["top"] - poi["bottom"], atr_tf), "fvg_n": len(c["fvgs"]), "fvg_pick": c["fvg_pick"],
        "fvg_atr": _ratio(f["top"] - f["bottom"], atr_tf),
        "move_atr": _ratio(abs(c["bos"]["close"] - c["bos"]["origin"]["price"]), atr_tf),
        "break_atr": _ratio(abs(c["bos"]["close"] - c["bos"]["level"]), atr_tf),
        "bos_streak": streak[i0] if i0 < len(streak) else 0,
        "choch_against": sum(1 for x in later if x["side"] != side and x["kind"] == "CHoCH"),
        "bos_against": sum(1 for x in later if x["side"] != side and x["kind"] == "BOS"),
        "sl_atr": _ratio(risk, atr15), "sl_pct": round(100 * risk / entry, 4) if entry else None,
        "spread_frac": _ratio(hit["sp"], risk), "atr_pct": round(100 * atr15 / entry, 4) if atr15 and entry else None,
        "rr": tgt["rr"], "tgt_tf": (tgt["label"] or "").split(" ")[0] if tgt["price"] is not None else None,
        "h4": _side_trend(V.trend_label(h4)["trend"], side), "tf_trend": _side_trend(V.trend_label(tfb)["trend"], side),
        "range_pos": rng_pos, "entry_zone_r": _ratio(abs(entry - near_zone), risk),
        "age_bars": max(0, cur - 1 - c["formed_idx"]), "wait_m5": j - bisect.bisect_left(ser["M5"].T, c["known_t"]),
        "strength": strength["level"], "strength_score": strength.get("score"), "leg_running": peak is None,
        "hour": _dt.datetime.fromtimestamp(now / 1000, _dt.timezone.utc).hour,
        "dow": _dt.datetime.fromtimestamp(now / 1000, _dt.timezone.utc).weekday(),
    }
    rec = {"id": c["id"], "symbol": sym, "market": market, "tf": tf, "side": side, "live_tf": tf in ENGINE["trade_tfs"],
           "touch_t": now, "bos_t": c["bos"]["t"], "bos_level": c["bos"]["level"], "bos_level_t": c["bos"]["level_t"], "origin_t": c["bos"]["origin"]["t"],
           "poi": {k: poi[k] for k in ("t", "top", "bottom")}, "fvg": {k: f[k] for k in ("t", "top", "bottom")},
           "entry_level": e, "entry": entry, "stop": stop, "tp": tgt["price"], "tp_label": tgt["label"],
           "aligned": aligned, "aligned_h1": bias["h1"]["bias"] == side, "bias_why": bias.get("why"),
           "why": why if aligned else f"against the bias ({bias.get('why')})",
           "traded": aligned and not why, "layer": layer_px, "feats": feats}
    if not risk or (sell and stop <= entry) or (not sell and stop >= entry):
        return {**rec, "fixed": None, "managed": None}
    tp = tgt["price"] if tgt["price"] is not None else (entry - 3 * risk if sell else entry + 3 * risk)   # what-if for refused ones
    rec["tp_used"] = tp
    rec["fixed"] = fixed_outcome(side, entry, stop, tp, m5, j)
    if aligned:
        inv = c["invalidation"]
        q = s.done(now + s.ms)                      # the setup timeframe bar holding the touch and the ones after it
        cancel_t = next((s.bars[i]["t"] + s.ms for i in range(max(0, q - 1), min(len(s.bars), q + 400))
                         if (s.bars[i]["c"] > inv if sell else s.bars[i]["c"] < inv)), None)
        rec["managed"] = managed_outcome(sym, info, side, tf, entry, stop, tp, layer_px, m5, j, cancel_t)
    return rec


def overrides(pairs: List[str]) -> Dict:
    """--set key=value (a STRATEGY input, e.g. swing_length=5) → {key: value} with the input's own type."""
    out = {}
    for p in pairs or []:
        k, v = p.split("=", 1)
        if k not in S:
            raise SystemExit(f"--set {k}: not a STRATEGY input")
        out[k] = type(S[k])(json.loads(v)) if not isinstance(S[k], bool) else v.lower() in ("1", "true", "yes")
    return out


def cmd_run(a) -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    tfs = a.tfs.split(",")
    sets = overrides(a.set)
    out_file = os.path.join(OUT_DIR, f"setups{'_' + a.out if a.out else ''}.jsonl")
    paths = sorted(os.path.join(HIST_DIR, x) for x in os.listdir(HIST_DIR) if x.endswith(".json"))
    if a.symbols:
        want = set(a.symbols.split(","))
        paths = [p for p in paths if os.path.basename(p)[:-5] in want]
    t0 = time.time()
    total, counts = 0, Counter()
    with Pool(min(a.jobs, len(paths))) as pool, open(out_file, "w") as out:
        for res in pool.imap_unordered(_job, [(p, tfs, sets) for p in paths]):
            if "error" in res:
                print(f"{res['symbol']}: ERROR {res['error']}", flush=True)
                continue
            for r in res["records"]:
                out.write(json.dumps(r, separators=(",", ":")) + "\n")
            total += len(res["records"])
            counts.update(res["counts"])
            tr = [r for r in res["records"] if r["traded"] and r.get("fixed") and r["fixed"]["r"] is not None]
            print(f"{res['symbol']:12s} {len(res['records']):5d} touched, {len(tr):4d} traded, fixed {sum(r['fixed']['r'] for r in tr):+7.1f}R "
                  f"({time.time() - t0:.0f} s)", flush=True)
    with open(out_file.replace(".jsonl", "_counts.json"), "w") as f:
        json.dump({"tfs": tfs, "set": sets, "counts": dict(counts), "records": total, "at": int(time.time())}, f, indent=1)
    print(f"{total} touched setups → {out_file}")
    return 0


def _job(arg):
    path, tfs, sets = arg
    S.update(sets)                                 # the worker's own copy of the strategy inputs
    try:
        return replay(path, tfs)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"symbol": os.path.basename(path)[:-5], "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="replay the V5 engine on FxPro's history")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--tfs", default="M15,M30,H1")
    r.add_argument("--symbols", default="")
    r.add_argument("--jobs", type=int, default=12)
    r.add_argument("--set", action="append", help="override a STRATEGY input for this run, e.g. --set swing_length=5")
    r.add_argument("--out", default="", help="name suffix: setups_<out>.jsonl")
    rp = sub.add_parser("report")
    rp.add_argument("--out", default="", help="which run: setups_<out>.jsonl")
    a = ap.parse_args()
    if a.cmd == "report":
        from .bt_report import main as report
        return report(a.out)
    return cmd_run(a)


if __name__ == "__main__":
    raise SystemExit(main())
