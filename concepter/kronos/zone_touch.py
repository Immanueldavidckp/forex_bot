"""
concepter/kronos/zone_touch.py — will price TOUCH David's S&D zone in the next 50 M15 candles? Kronos says.
(David 2026-11-07; config KRONOS_ZONES; service kronos-zones; page /kzones on the dashboard.)

    cd ~/forex && MT5_NO_LAUNCH=1 ~/opt/kronos-venv/bin/python -m concepter.kronos.zone_touch [--once] [--symbols GOLD,EURUSD]

Read-only (bars in, no orders). Each loop:
  1. once per closed M15 bar: the closed M15 bars of every S&D symbol (engine_data/sdd/state.json "symbols"),
     BARS of them the first time, then the last few merged — the same window the engine and /smc use
  2. sd_david.zones() → the zones that are valid, live and still FRESH (price has not come back to candle A yet)
  3. the symbol whose zone is nearest (in ATR) and whose forecast is older than its last closed bar goes next:
     Kronos-base, PATHS paths × HORIZON bars from the last CONTEXT closed bars. Every path has its own
     high / low / close per bar, so for every fresh zone of that symbol it counts, bar by bar:
        touch   demand: the path's low ≤ A's high (the entry wick); supply: high ≥ A's low
        mid     the same for the dashed 50 % line of candle A
        stop    a CLOSE beyond the far side of candle A (demand below A's low, supply above A's high)
        first   which candle (1..HORIZON) the touch came on; stop_first: the stop came before any touch
  4. zones.json (latest per symbol, for /kzones) and forecasts.jsonl (every forecast, scored later against the real
     candles: did price really touch within HORIZON bars, and on which candle)
"""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import Dict, List

import numpy as np
import pandas as pd

from engine.config import DATA_DIR, KRONOS_ZONES as Z
from engine.major_structure import atr14, major_structure
from engine import sd_david
import mt5_client as mt5c

from .model import COLS, load

SDD_STATE = os.path.join(DATA_DIR, "sdd", "state.json")
OUT = os.path.join(Z["DIR"], "zones.json")
HIST = os.path.join(Z["DIR"], "forecasts.jsonl")
BAR_MS = 15 * 60_000
STEP = pd.Timedelta(minutes=15)
STRUCTURE_N = 5                                   # = sdd_book.STRUCTURE_N
CHART_BARS = 120                                  # real candles kept per symbol for the page's chart
os.makedirs(Z["DIR"], exist_ok=True)


def log(msg: str) -> None:
    print(f"[kzones {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def symbols() -> List[str]:
    try:
        with open(SDD_STATE) as f:
            return list(json.load(f)["symbols"])
    except Exception:
        return ["GOLD", "EURUSD", "GBPUSD", "USDJPY", "BITCOIN", "ETHEREUM"]


def fetch(bars: Dict[str, List[Dict]], syms: List[str], now: int) -> None:
    wants = [(s, Z["TF"], Z["BARS"] if len(bars.get(s) or []) < Z["BARS"] // 2 else 20) for s in syms]
    got = {}
    for k in range(0, len(wants), 18):            # a few bridge calls, not one huge one
        try:
            got.update(mt5c.bars_many(wants[k:k + 18], timeout=240))
        except Exception as e:
            log(f"bars error {type(e).__name__}: {e}")
    for s in syms:
        new = [b for b in got.get((s, Z["TF"]), []) if b["t"] + BAR_MS <= now]          # closed bars only
        if new:
            old = [b for b in bars.get(s, []) if b["t"] < new[0]["t"]]
            bars[s] = (old + new)[-Z["BARS"]:]


def fresh_zones(bars: List[Dict]) -> List[Dict]:
    zs = sd_david.zones(bars, major_structure(bars, STRUCTURE_N), STRUCTURE_N)
    return [z for z in zs if z["valid"] and z["live"] and z["status"] == "fresh"]


def forecast(pred, bars: List[Dict]) -> Dict[str, np.ndarray]:
    """→ {"h","l","c"}: arrays (PATHS, HORIZON) of Kronos-base paths from the last CONTEXT closed bars."""
    w = bars[-Z["CONTEXT"]:]
    df = pd.DataFrame([[b["o"], b["h"], b["l"], b["c"], b.get("v") or 0.0] for b in w], columns=COLS,
                      index=pd.to_datetime([b["t"] for b in w], unit="ms"))
    n, H = Z["PATHS"], Z["HORIZON"]
    ys = pd.Series(pd.date_range(df.index[-1] + STEP, periods=H, freq=STEP))
    res = pred.predict_batch([df] * n, [pd.Series(df.index)] * n, [ys] * n, pred_len=H, T=1.0, top_p=0.9,
                             sample_count=1, verbose=False)
    return {k: np.array([r[col].to_numpy() for r in res], dtype=np.float64)
            for k, col in (("h", "high"), ("l", "low"), ("c", "close"))}


def _first(hit: np.ndarray) -> np.ndarray:
    """(paths, bars) bool → the first bar (1-based) per path, 0 = never."""
    any_ = hit.any(axis=1)
    return np.where(any_, hit.argmax(axis=1) + 1, 0)


def score(z: Dict, f: Dict[str, np.ndarray]) -> Dict:
    buy = z["dir"] == "buy"
    entry, stop, mid = z["proximal"], z["distal"], z["mid"]
    touch = f["l"] <= entry if buy else f["h"] >= entry
    half = f["l"] <= mid if buy else f["h"] >= mid
    stopc = f["c"] < stop if buy else f["c"] > stop
    ft, fm, fs = _first(touch), _first(half), _first(stopc)
    n = len(ft)
    got = ft[ft > 0]
    return {"p_touch": round(float((ft > 0).mean()), 4), "p_mid": round(float((fm > 0).mean()), 4),
            "p_stop": round(float((fs > 0).mean()), 4),
            "p_stop_first": round(float(((fs > 0) & ((ft == 0) | (fs <= ft))).mean()), 4),
            "first_median": int(np.median(got)) if len(got) else None,
            "first_each": [int(x) for x in ft], "paths": n}


def zone_row(sym: str, z: Dict, bars: List[Dict], atr: float) -> Dict:
    last = bars[-1]["c"]
    return {"id": f"{sym}-{bars[z['break']]['t']}", "symbol": sym, "side": z["side"], "dir": z["dir"],
            "t_a": bars[z["a"]]["t"], "t_break": bars[z["break"]]["t"], "top": z["top"], "bottom": z["bottom"],
            "mid": z["mid"], "entry": z["proximal"], "stop": z["distal"],
            "t1": (z.get("targets") or [{}])[0].get("price"),
            "fvg": z["fvg"], "dist_atr": round(abs(last - z["proximal"]) / atr, 2) if atr else None}


def real_touch(rec: Dict, bars: List[Dict]) -> Dict:
    """A logged forecast against the real candles after its bar: touched? on which candle? stop first?"""
    i = next((k for k, b in enumerate(bars) if b["t"] == rec["bar_t"]), None)
    if i is None:
        return {}
    after = bars[i + 1:i + 1 + rec["horizon"]]
    buy = rec["dir"] == "buy"
    out = {"seen": len(after)}
    for k, b in enumerate(after, 1):
        if "real_stop" not in out and ((buy and b["c"] < rec["stop"]) or (not buy and b["c"] > rec["stop"])):
            out["real_stop"] = k
        if (buy and b["l"] <= rec["entry"]) or (not buy and b["h"] >= rec["entry"]):
            out["real_touch"] = k
            break
    out["done"] = "real_touch" in out or len(after) >= rec["horizon"]
    return out


def scoreboard(bars: Dict[str, List[Dict]]) -> Dict:
    """Every logged forecast that is over (touched, or HORIZON candles passed) → hit table by Kronos' P(touch)."""
    try:
        with open(HIST) as f:
            recs = [json.loads(l) for l in f if l.strip()]
    except FileNotFoundError:
        recs = []
    # one score per zone per hour is enough: a zone forecast every bar would count the same outcome many times
    seen, rows = set(), []
    for r in recs:
        key = (r["id"], r["bar_t"] // 3_600_000)
        if key in seen or r["symbol"] not in bars:
            continue
        seen.add(key)
        rt = real_touch(r, bars[r["symbol"]])
        if rt.get("done"):
            rows.append({**r, **rt})
    buckets = []
    for lo, hi in ((0, .25), (.25, .5), (.5, .75), (.75, 1.01)):
        b = [x for x in rows if lo <= x["p_touch"] < hi]
        t = [x for x in b if x.get("real_touch")]
        buckets.append({"from": lo, "to": min(hi, 1), "n": len(b), "touched": len(t),
                        "rate": round(len(t) / len(b), 3) if b else None})
    recent = sorted(rows, key=lambda x: -x["bar_t"])[:60]
    keep = ("id", "symbol", "side", "bar_t", "entry", "stop", "p_touch", "p_mid", "first_median", "real_touch", "real_stop")
    return {"n": len(rows), "buckets": buckets, "recent": [{k: x.get(k) for k in keep} for x in recent],
            "logged": len(recs)}


def save(state: Dict) -> None:
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, separators=(",", ":"))
    os.replace(tmp, OUT)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="one pass over every symbol with a fresh zone, then stop")
    ap.add_argument("--symbols", default="", help="comma list (default: the S&D engine's symbols)")
    a = ap.parse_args()
    pred = load()
    log(f"Kronos-base on {pred.device}: {Z['PATHS']} paths × {Z['HORIZON']} M15 bars per symbol with a fresh S&D David zone")
    try:
        with open(OUT) as f:
            state = json.load(f)
    except (FileNotFoundError, ValueError):
        state = {}
    state.setdefault("symbols", {})
    bars: Dict[str, List[Dict]] = {}
    slot, done_once = None, set()
    while True:
        syms = [s for s in a.symbols.split(",") if s] or symbols()
        now = int(time.time() * 1000)
        if now // BAR_MS != slot and now % BAR_MS > 10_000:
            fetch(bars, syms, now)
            slot = now // BAR_MS
            todo = []
            for s in syms:
                b = bars.get(s) or []
                if len(b) < Z["CONTEXT"] + 10:
                    continue
                try:
                    zs = fresh_zones(b)
                except Exception as e:
                    log(f"{s}: zones error {type(e).__name__}: {e}")
                    continue
                at = atr14(b)[-1]
                at = at if at == at else None
                rows = [zone_row(s, z, b, at) for z in zs]
                old = state["symbols"].get(s) or {}
                # keep the last forecast's numbers for zones that are still fresh; zones that are gone drop off
                prev = {r["id"]: r for r in old.get("zones", [])}
                for r in rows:
                    for k in ("p_touch", "p_mid", "p_stop", "p_stop_first", "first_median", "first_each", "paths"):
                        if k in prev.get(r["id"], {}):
                            r[k] = prev[r["id"]][k]
                state["symbols"][s] = {**{k: v for k, v in old.items() if k not in ("zones", "bars")},
                                       "zones": rows, "last_t": b[-1]["t"], "last": b[-1]["c"], "atr": at,
                                       "bars": [[x["t"], x["o"], x["h"], x["l"], x["c"]] for x in b[-CHART_BARS:]]}
                if rows:
                    todo.append((min(r["dist_atr"] or 99 for r in rows), s))
            state["queue"] = [s for _, s in sorted(todo)]
            state["scoreboard"] = scoreboard(bars)
            state["at"] = now
            save(state)
            log(f"bars in: {len(todo)} symbols with a fresh zone, {sum(len(state['symbols'][s]['zones']) for _, s in todo)} zones")
        # next: the nearest zone whose forecast is older than its symbol's last closed bar
        nxt = next((s for s in state.get("queue", []) if state["symbols"][s].get("fc_bar_t") != state["symbols"][s]["last_t"]
                    and not (a.once and s in done_once)), None)
        if nxt is None:
            if a.once and slot is not None:
                log("--once: every symbol done")
                return 0
            time.sleep(5)
            continue
        e = state["symbols"][nxt]
        t0 = time.time()
        try:
            f = forecast(pred, bars[nxt])
        except Exception as ex:
            log(f"{nxt}: forecast error {type(ex).__name__}: {ex}")
            e["fc_bar_t"] = e["last_t"]
            continue
        secs = round(time.time() - t0, 1)
        done_once.add(nxt)
        e.update(fc_bar_t=e["last_t"], fc_made=int(time.time() * 1000), fc_secs=secs,
                 fc={"median": [round(float(x), 8) for x in np.median(f["c"], axis=0)],
                     "q10": [round(float(x), 8) for x in np.percentile(f["c"], 10, axis=0)],
                     "q90": [round(float(x), 8) for x in np.percentile(f["c"], 90, axis=0)],
                     "low10": [round(float(x), 8) for x in np.percentile(f["l"], 10, axis=0)],
                     "high90": [round(float(x), 8) for x in np.percentile(f["h"], 90, axis=0)]})
        zs = fresh_zones(bars[nxt])
        byid = {f"{nxt}-{bars[nxt][z['break']]['t']}": z for z in zs}
        with open(HIST, "a") as h:
            for r in e["zones"]:
                z = byid.get(r["id"])
                if z is None:
                    continue
                r.update(score(z, f))
                h.write(json.dumps({"id": r["id"], "symbol": nxt, "side": r["side"], "dir": r["dir"],
                                    "bar_t": e["last_t"], "horizon": Z["HORIZON"], "entry": r["entry"],
                                    "stop": r["stop"], "mid": r["mid"], "p_touch": r["p_touch"], "p_mid": r["p_mid"],
                                    "p_stop": r["p_stop"], "first_median": r["first_median"],
                                    "made_ms": e["fc_made"]}) + "\n")
        state["at"] = int(time.time() * 1000)
        save(state)
        best = max(e["zones"], key=lambda r: r.get("p_touch", 0))
        log(f"{nxt}: {len(e['zones'])} zone(s) in {secs}s; best {best['side']} @ {best['entry']:g}: "
            f"P(touch in {Z['HORIZON']}) {best.get('p_touch', 0):.0%}, P(50%) {best.get('p_mid', 0):.0%}")


if __name__ == "__main__":
    raise SystemExit(main())
