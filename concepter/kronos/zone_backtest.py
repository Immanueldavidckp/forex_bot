"""
concepter/kronos/zone_backtest.py — Kronos' 50-candle zone-touch forecast tested on PAST candles (David 2026-11-07:
"check the existing candles so I can test this LLM works").

    cd ~/forex && MT5_NO_LAUNCH=1 ~/opt/kronos-venv/bin/python -m concepter.kronos.zone_backtest [--per-symbol 6] [--symbols GOLD,EURUSD]

For every symbol of the S&D engine: the last BARS closed M15 candles from MT5 (with tick volume), every S&D David zone
in them (sd_david.zones, the live rule). For each zone, newest first, up to --per-symbol per symbol, taken round-robin
over the symbols so the page fills evenly:
  t0       = the candle after the BOS candle (the 4th candle of the A-B-C is known by then)
  no peek  = the zones are worked out again on the candles up to t0 ONLY (3000 of them, as live); the zone must exist
             there, valid and still fresh, else it is skipped
  Kronos   = 16 paths × 50 candles from the 512 candles up to t0 (exactly what the live /kzones does)
  real     = the 50 candles that really came after t0: on which candle the wick touched the entry, the 50 % line,
             a close beyond the stop
Baseline: "the nearer the zone, the likelier the touch" (distance in ATR at t0, no model). Kronos is only useful if it
sorts touch / no touch better than that (AUC) and its percentages match the real rates (calibration, Brier score).
Writes engine_data/kronos/zones/backtest.json after every zone; page /kzones shows it.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import Dict, List

import numpy as np

from engine.config import KRONOS_ZONES as Z
from engine.major_structure import atr14, major_structure
from engine import sd_david
import mt5_client as mt5c

from .model import load
from .zone_touch import BAR_MS, STRUCTURE_N, forecast, log, score, symbols

OUT = os.path.join(Z["DIR"], "backtest.json")
FETCH = 8000                     # candles per symbol (~3 months of M15)
WINDOW = Z["BARS"]               # candles the live engine works on (3000)
BEFORE = 80                      # real candles before t0 kept for the chart


def real(z: Dict, fut: List[Dict]) -> Dict:
    buy = z["dir"] == "buy"
    out = {"real_touch": None, "real_mid": None, "real_stop": None}
    for k, b in enumerate(fut, 1):
        if out["real_touch"] is None and ((buy and b["l"] <= z["proximal"]) or (not buy and b["h"] >= z["proximal"])):
            out["real_touch"] = k
        if out["real_mid"] is None and ((buy and b["l"] <= z["mid"]) or (not buy and b["h"] >= z["mid"])):
            out["real_mid"] = k
        if out["real_stop"] is None and ((buy and b["c"] < z["distal"]) or (not buy and b["c"] > z["distal"])):
            out["real_stop"] = k
    t, s = out["real_touch"], out["real_stop"]
    out["real_stop_first"] = s is not None and (t is None or s <= t)
    return out


def auc(score_: List[float], label: List[bool]) -> float | None:
    pos = [s for s, l in zip(score_, label) if l]
    neg = [s for s, l in zip(score_, label) if not l]
    if not pos or not neg:
        return None
    w = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return round(w / (len(pos) * len(neg)), 3)


def summary(rows: List[Dict]) -> Dict:
    if not rows:
        return {"n": 0}
    y = [r["real_touch"] is not None for r in rows]
    p = [r["p_touch"] for r in rows]
    base = sum(y) / len(y)
    brier = sum((a - b) ** 2 for a, b in zip(p, y)) / len(y)
    brier0 = sum((base - b) ** 2 for b in y) / len(y)
    buckets = []
    for lo, hi in ((0, .25), (.25, .5), (.5, .75), (.75, 1.01)):
        b = [r for r in rows if lo <= r["p_touch"] < hi]
        t = [r for r in b if r["real_touch"] is not None]
        buckets.append({"from": lo, "to": min(hi, 1), "n": len(b), "touched": len(t),
                        "kronos": round(sum(r["p_touch"] for r in b) / len(b), 3) if b else None,
                        "rate": round(len(t) / len(b), 3) if b else None})
    both = [r for r in rows if r["real_touch"] is not None and r["first_median"]]
    ym = [r["real_mid"] is not None for r in rows]
    ys = [r["real_stop_first"] for r in rows]
    return {"n": len(rows), "symbols": len({r["symbol"] for r in rows}),
            "real_touch_rate": round(base, 3), "kronos_mean_p": round(sum(p) / len(p), 3),
            "brier": round(brier, 4), "brier_base": round(brier0, 4),
            "auc_kronos": auc(p, y), "auc_distance": auc([-(r["dist_atr"] or 0) for r in rows], y),
            "auc_kronos_mid": auc([r["p_mid"] for r in rows], ym),
            "auc_kronos_stop_first": auc([r["p_stop_first"] for r in rows], ys),
            "real_mid_rate": round(sum(ym) / len(ym), 3), "real_stop_first_rate": round(sum(ys) / len(ys), 3),
            "candle_err_median": int(np.median([abs(r["first_median"] - r["real_touch"]) for r in both])) if both else None,
            "buckets": buckets}


def save(rows: List[Dict], meta: Dict) -> None:
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump({**meta, "at": int(time.time() * 1000), "summary": summary(rows), "zones": rows}, f,
                  separators=(",", ":"))
    os.replace(tmp, OUT)


def candidates(sym: str, bars: List[Dict], per: int) -> List[Dict]:
    """The symbol's zones, newest first, checked with no peek: up to `per` usable ones (with their t0)."""
    H = Z["HORIZON"]
    allz = sd_david.zones(bars, major_structure(bars, STRUCTURE_N), STRUCTURE_N)
    out = []
    for z0 in sorted(allz, key=lambda z: -z["break"]):
        t0 = z0["break"] + 1
        if t0 + H >= len(bars) or t0 < max(Z["CONTEXT"], 600):
            continue
        lo = max(0, t0 + 1 - WINDOW)
        win = bars[lo:t0 + 1]                                   # the candles up to t0 only
        tb = bars[z0["break"]]["t"]
        z = next((x for x in sd_david.zones(win, major_structure(win, STRUCTURE_N), STRUCTURE_N)
                  if win[x["break"]]["t"] == tb), None)
        if z is None or not z["valid"] or z["status"] != "fresh" or not z["live"]:
            continue
        at = atr14(win)[-1]
        out.append({"sym": sym, "t0": t0, "z": z, "atr": at if at == at else None})
        if len(out) >= per:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-symbol", type=int, default=6)
    ap.add_argument("--symbols", default="")
    a = ap.parse_args()
    syms = [s for s in a.symbols.split(",") if s] or symbols()
    now = int(time.time() * 1000)
    bars: Dict[str, List[Dict]] = {}
    for k in range(0, len(syms), 9):
        try:
            got = mt5c.bars_many([(s, Z["TF"], FETCH) for s in syms[k:k + 9]], timeout=300)
        except Exception as e:
            log(f"bars error {type(e).__name__}: {e}")
            continue
        for (s, _), b in got.items():
            bars[s] = [x for x in b if x["t"] + BAR_MS <= now]
    queues = {}
    for s in syms:
        if len(bars.get(s) or []) < 1500:
            continue
        try:
            queues[s] = candidates(s, bars[s], a.per_symbol)
        except Exception as e:
            log(f"{s}: zones error {type(e).__name__}: {e}")
    total = sum(len(q) for q in queues.values())
    log(f"{total} past zones on {len(queues)} symbols to test (≤ {a.per_symbol} each, newest first)")
    meta = {"total": total, "paths": Z["PATHS"], "horizon": Z["HORIZON"], "per_symbol": a.per_symbol,
            "started": now, "done": False}
    try:
        with open(OUT) as f:
            old = json.load(f)
        rows = [r for r in old.get("zones", []) if old.get("horizon") == Z["HORIZON"]]
    except (FileNotFoundError, ValueError):
        rows = []
    have = {r["id"] for r in rows}
    pred = load()
    order = [c for i in range(a.per_symbol) for q in queues.values() if i < len(q) for c in [q[i]]]   # round-robin
    for c in order:
        s, t0, z, b = c["sym"], c["t0"], c["z"], bars[c["sym"]]
        zid = f"{s}-{b[t0 - 1]['t']}"
        if zid in have:
            continue
        t1 = time.time()
        f = forecast(pred, b[:t0 + 1])
        k = score(z, f)
        fut = b[t0 + 1:t0 + 1 + Z["HORIZON"]]
        rr = real(z, fut)
        r = {"id": zid, "symbol": s, "side": z["side"], "dir": z["dir"], "t0": b[t0]["t"],
             "entry": z["proximal"], "mid": z["mid"], "stop": z["distal"], "top": z["top"], "bottom": z["bottom"],
             "last": b[t0]["c"], "dist_atr": round(abs(b[t0]["c"] - z["proximal"]) / c["atr"], 2) if c["atr"] else None,
             **{x: k[x] for x in ("p_touch", "p_mid", "p_stop", "p_stop_first", "first_median")}, **rr,
             "bars": [[x["t"], x["o"], x["h"], x["l"], x["c"]] for x in b[max(0, t0 - BEFORE + 1):t0 + 1 + Z["HORIZON"]]],
             "k0": min(BEFORE, t0 + 1) - 1,
             "fc": {"median": [round(float(x), 8) for x in np.median(f["c"], axis=0)],
                    "q10": [round(float(x), 8) for x in np.percentile(f["c"], 10, axis=0)],
                    "q90": [round(float(x), 8) for x in np.percentile(f["c"], 90, axis=0)]},
             "secs": round(time.time() - t1, 1)}
        rows.append(r)
        have.add(zid)
        save(rows, meta)
        log(f"[{len(rows)}/{total}] {s} {z['side']} @ {z['proximal']:g}: Kronos {r['p_touch']:.0%} touch → "
            f"real {'candle ' + str(rr['real_touch']) if rr['real_touch'] else 'no touch'}")
    meta["done"] = True
    save(rows, meta)
    sm = summary(rows)
    log(f"done: {sm.get('n')} zones, real touch {sm.get('real_touch_rate')}, AUC Kronos {sm.get('auc_kronos')} "
        f"vs distance {sm.get('auc_distance')}, Brier {sm.get('brier')} vs base {sm.get('brier_base')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
