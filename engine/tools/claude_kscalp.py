"""
engine/tools/claude_kscalp.py — Claude's 15-minute scalp ON KRONOS' OUTPUT (David 2026-11-08: "every 15m candle predict
the direction, buy or sell, get the minimum profit then exit; choose how far it may go — an FVG may reverse it — capture
0.02 / 0.05 / 0.07 then exit; you use the Kronos output, not the Kronos trade").

    MT5_NO_LAUNCH=1 python3 -m engine.tools.claude_kscalp          # loop; magic 24102099 (shows on /kronos as Claude's)

Each new M15 forecast in engine_data/kronos/signals.json (the GPU writes one per symbol per closed bar):
  direction  Kronos: P(up) ≥ 0.56 → buy, ≤ 0.44 → sell; 0.44–0.56 = coin flip, no trade
  reach      how far Kronos' paths go that way: the median close at the end of the 8 bars (buy) and its best
             (max of the median path); the 10 % / 90 % closes give the adverse side
  obstacle   the nearest thing in the way on the M15 chart (my read): an unfilled FVG edge, a fresh S&D David zone edge,
             the last 20-bar swing high / low. Price tends to stall / reverse there, so the target stops short of it
  target     min(obstacle − 1 spread, Kronos median reach); must be ≥ 3 spreads, else no trade (the spread would eat it)
  stop       the adverse 10 % (buy) / 90 % (sell) close over the 8 bars, at least 3 spreads and the broker's stops level
  exit       the target, the stop, the next forecast flipping against the trade (P(up) crosses 0.5 the other way),
             or 8 bars (2 h) — "get the minimum profit then exit"
  size       0.01 lot, one scalp per symbol; a symbol that already has a Claude position (either rule) is skipped
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Dict, List, Optional

sys.path.insert(0, os.path.expanduser("~/forex"))
import mt5_client as mt5c                                     # noqa: E402
from engine.config import DATA_DIR, KRONOS                    # noqa: E402
from engine.major_structure import atr14, major_structure     # noqa: E402
from engine import sd_david                                    # noqa: E402
from engine.trade_checks import chk, g                         # noqa: E402

MAGIC = KRONOS["CLAUDE_MAGIC"]
LOTS = 0.01
P_BUY, P_SELL = 0.56, 0.44
MIN_TARGET_SPREADS, MIN_STOP_SPREADS = 3, 3
HOLD_BARS = 8
SIGNALS = os.path.join(KRONOS["DIR"], "signals.json")
LOG = os.path.join(DATA_DIR, "kronos", "claude_crypto.log")
NOTES = os.path.join(DATA_DIR, "kronos", "claude_notes.json")
STATE = os.path.join(DATA_DIR, "kronos", "kscalp_state.json")
FX = {"AUDUSD", "CADCHF", "CADJPY", "CHFJPY", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURUSD", "GBPCAD", "GBPCHF",
      "GBPJPY", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY", "GOLD"}


def log(msg):
    line = f"[kscalp {time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def jload(p, default):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default


def jsave(p, d):
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, p)


def fvg_edges(bars: List[Dict]) -> List[tuple]:
    """Unfilled 3-candle gaps in the last 60 bars → [(kind, near_edge, far_edge)], kind 'bull' (gap below price) / 'bear'."""
    out = []
    N = len(bars)
    for i in range(max(2, N - 60), N):
        a, c = bars[i - 2], bars[i]
        if c["l"] > a["h"]:                                    # bull gap a.h .. c.l
            lo, hi = a["h"], c["l"]
            if all(b["l"] > lo for b in bars[i + 1:]):          # not filled since
                out.append(("bull", hi, lo))
        elif c["h"] < a["l"]:
            lo, hi = c["h"], a["l"]
            if all(b["h"] < hi for b in bars[i + 1:]):
                out.append(("bear", lo, hi))
    return out


def obstacle(bars: List[Dict], side: str, price: float) -> Optional[tuple]:
    """The nearest level in the trade's way: (what, level). Buy → things above price; sell → below."""
    cands = obstacles(bars, side, price)
    return min(cands, key=lambda c: abs(c[1] - price)) if cands else None


def obstacles(bars: List[Dict], side: str, price: float) -> List[tuple]:
    """Every level in the trade's way: [(what, level)]."""
    cands = []
    for kind, near, far in fvg_edges(bars):
        if side == "buy" and kind == "bear" and near > price:
            cands.append(("bear FVG", near))
        if side == "sell" and kind == "bull" and near < price:
            cands.append(("bull FVG", near))
    try:
        zs = sd_david.zones(bars, major_structure(bars, 5), 5)
        for z in zs:
            if not (z["valid"] and z["live"]):
                continue
            if side == "buy" and z["side"] == "supply" and z["proximal"] > price:
                cands.append(("supply zone", z["proximal"]))
            if side == "sell" and z["side"] == "demand" and z["proximal"] < price:
                cands.append(("demand zone", z["proximal"]))
    except Exception:
        pass
    sw = bars[-21:-1]
    hi, lo = max(b["h"] for b in sw), min(b["l"] for b in sw)
    if side == "buy" and hi > price:
        cands.append(("20-bar high", hi))
    if side == "sell" and lo < price:
        cands.append(("20-bar low", lo))
    return cands


def plan(sym: str, sg: Dict, bars: List[Dict], info: Dict, tick: Dict) -> Dict:
    p = sg["p_up"]
    if P_SELL < p < P_BUY:
        return {"skip": f"P(up) {p:.0%} is a coin flip"}
    side = "buy" if p >= P_BUY else "sell"
    bid, ask = float(tick["bid"]), float(tick["ask"])
    sp = max(ask - bid, 0.0)
    pt = float(info["point"])
    gap = float(info.get("trade_stops_level") or 0) * pt
    dg = int(info["digits"])
    med, q10, q90 = sg["median"], sg["q10"], sg["q90"]
    entry = ask if side == "buy" else bid
    if side == "buy":
        reach = max(med) - entry
        adverse = entry - min(q10)
    else:
        reach = entry - min(med)
        adverse = max(q90) - entry
    if reach <= 0:
        return {"skip": f"Kronos median does not go {side} from here"}
    ob = obstacle(bars, side, entry)
    tgt_dist = reach
    why_t = f"Kronos median reach {reach:.{dg}f}"
    if ob is not None and abs(ob[1] - entry) - sp < tgt_dist:
        tgt_dist = abs(ob[1] - entry) - sp
        why_t = f"{ob[0]} at {ob[1]:.{dg}f} (1 spread short of it)"
    if tgt_dist < MIN_TARGET_SPREADS * sp or tgt_dist <= gap:
        return {"skip": f"target {tgt_dist:.{dg}f} is under {MIN_TARGET_SPREADS} spreads ({sp:.{dg}f}) — {why_t}"}
    stop_dist = max(adverse, MIN_STOP_SPREADS * sp, gap + pt)
    tp = entry + tgt_dist if side == "buy" else entry - tgt_dist
    sl = entry - stop_dist if side == "buy" else entry + stop_dist
    allob = sorted(obstacles(bars, side, entry), key=lambda c: abs(c[1] - entry))
    sl_src = {adverse: f"Kronos {'10' if side == 'buy' else '90'} % close", MIN_STOP_SPREADS * sp: f"the {MIN_STOP_SPREADS}-spread floor",
              gap + pt: "the broker's stops level"}[stop_dist]
    agree = p if side == "buy" else 1 - p
    sp_txt = (lambda x: f"{x / sp:.1f} spreads" if sp else "spread 0 (broker quote bid = ask)")
    checks = [
        chk("Setup", "Kronos direction", f"P(up) {p:.0%} → {side} ({agree:.0%} of {sg.get('paths', 16)} paths)",
            f"buy ≥ {P_BUY:.0%} · sell ≤ {P_SELL:.0%} · between = coin flip", True),
        chk("Setup", "Kronos median reach", f"{g(reach)} {'up' if side == 'buy' else 'down'} in {len(med)} bars",
            "the median path must go the trade's way", reach > 0),
        chk("Setup", "Obstacles in the way (M15)", " · ".join(f"{w} {g(lv)}" for w, lv in allob[:4]) or "none",
            "unfilled FVG edge, fresh S&D David zone, 20-bar swing: the target stops 1 spread short of the nearest", None),
        chk("Entry", "Target", f"{g(tgt_dist)} ({sp_txt(tgt_dist)}) ← {why_t}", f"≥ {MIN_TARGET_SPREADS} spreads and outside the stops level", True),
        chk("Risk", "Stop", f"{g(stop_dist)} ({sp_txt(stop_dist)}) ← {sl_src}", f"Kronos adverse close, ≥ {MIN_STOP_SPREADS} spreads, outside the stops level", True),
        chk("Risk", "Spread", f"{g(sp)}", "counted in the target / stop above", None),
        chk("Risk", "Broker stops level", f"{g(gap)}", "target and stop outside it", True),
    ]
    t0 = sg["bar_t"] + 900_000
    ts = [t0 + i * 900_000 for i in range(1, len(med) + 1)]
    marks = [{"type": "path", "label": "Kronos median (10–90 % band)", "t": [t0] + ts, "p": [entry] + list(med), "color": "#b388ff",
              "band": [[entry] + list(q10), [entry] + list(q90)]}]
    for w, lv in allob[:4]:
        marks.append({"type": "line", "label": w, "price": lv, "t0": bars[-60]["t"] if len(bars) >= 60 else bars[0]["t"], "t1": ts[-1],
                      "color": "#f5c542", "dash": [3, 3]})
    return {"side": side, "entry": entry, "sl": round(sl, dg), "tp": round(tp, dg), "risk": stop_dist,
            "target": tgt_dist, "spread": sp, "p_up": p, "checks": checks, "marks": marks,
            "why": f"Kronos P(up) {p:.0%} → {side}; target {why_t}; stop = Kronos {'10' if side == 'buy' else '90'} % close"}


def main():
    syms = [s for s in jload(os.path.join(DATA_DIR, "sdd", "state.json"), {}).get("symbols", []) if s not in FX]
    st = jload(STATE, {"seen": {}, "open": {}})
    log(f"kscalp on: {len(syms)} crypto symbols, Kronos P(up) ≥ {P_BUY:.0%} / ≤ {P_SELL:.0%}, {LOTS} lot, {HOLD_BARS} bars max")
    infos: Dict[str, Dict] = {}
    while True:
        try:
            sigs = jload(SIGNALS, {})
            pos = {p["symbol"]: p for p in mt5c.positions(magic=MAGIC)}
            now = time.time() * 1000
            # 1. manage: flip or time exit (TP / SL sit at the broker)
            for sym, o in list(st["open"].items()):
                p = pos.get(sym)
                if p is None or p["ticket"] != o["ticket"]:
                    log(f"{sym} #{o['ticket']}: gone (TP / SL / hand) — dropped")
                    st["open"].pop(sym)
                    continue
                sg = sigs.get(sym) or {}
                flip = sg.get("bar_t") and sg["bar_t"] > o["bar_t"] and ((o["side"] == "buy" and sg["p_up"] <= P_SELL)
                                                                           or (o["side"] == "sell" and sg["p_up"] >= P_BUY))
                age_bars = (now - o["bar_t"]) / 900_000
                if flip or age_bars >= HOLD_BARS + 1:
                    res = mt5c.close(o["ticket"], comment="kscalp flip" if flip else "kscalp time")
                    log(f"{sym} #{o['ticket']}: closed ({'Kronos flipped to P(up) %.0f%%' % (100 * sg['p_up']) if flip else f'{HOLD_BARS} bars'}) "
                        f"P&L {p['profit']:+.2f} → {res.get('comment')}")
                    st["open"].pop(sym)
            # 2. new forecasts → new scalps
            todo = [s for s in syms if s in sigs and st["seen"].get(s) != sigs[s]["bar_t"]
                    and now - sigs[s]["made_ms"] < 600_000]
            if todo:
                need = [s for s in todo if s not in infos]
                if need:
                    for s, r in zip(need, mt5c.call([{"op": "info", "symbol": s} for s in need], timeout=120)):
                        if "result" in r:
                            infos[s] = r["result"]
                ticks = {s: r.get("result") for s, r in zip(todo, mt5c.call([{"op": "tick", "symbol": s} for s in todo], timeout=120))}
                bars = mt5c.bars_many([(s, "M15", 120) for s in todo], timeout=240)
                notes = jload(NOTES, {})
                for s in todo:
                    sg = sigs[s]
                    st["seen"][s] = sg["bar_t"]
                    if s in pos:
                        continue                                   # a Claude trade (either rule) is on this symbol
                    if s not in infos or not ticks.get(s) or (s, "M15") not in bars:
                        log(f"{s}: no data"); continue
                    r = plan(s, sg, bars[(s, "M15")], infos[s], ticks[s])
                    if "skip" in r:
                        log(f"{s}: skip — {r['skip']}"); continue
                    res = mt5c.order(s, r["side"], LOTS, sl=r["sl"], tp=r["tp"], magic=MAGIC, comment="claude kscalp",
                                     deviation=int(max(50, 2 * r["spread"] / float(infos[s]["point"]))))
                    ok = res.get("ok") or res.get("retcode") == 10009
                    dg = int(infos[s]["digits"])
                    log(f"{s}: {r['side']} {LOTS} @ {res.get('price', r['entry'])} SL {r['sl']} TP {r['tp']} "
                        f"(target {r['target']:.{dg}f} = {r['target'] / r['spread'] if r['spread'] else 0:.1f} spreads, risk {r['risk']:.{dg}f}) — "
                        f"{r['why']} → {'OK ticket ' + str(res.get('order')) if ok else 'REFUSED ' + str(res.get('comment'))}")
                    if ok:
                        t = res.get("order")
                        st["open"][s] = {"ticket": t, "side": r["side"], "bar_t": sg["bar_t"], "entry": res.get("price", r["entry"])}
                        notes[str(t)] = {"symbol": s, "side": r["side"], "why": r["why"], "entry": res.get("price", r["entry"]),
                                         "sl": r["sl"], "tp": r["tp"], "atr15": r["risk"], "risk": r["risk"],
                                         "opened": int(now), "plan": f"scalp: TP {r['tp']} / SL {r['sl']} / Kronos flips / {HOLD_BARS} bars",
                                         "rule": "kscalp", "rule_tf": "M15", "marks": r["marks"],
                                         "checks": r["checks"] + [
                                             chk("Guard", "One trade per symbol", "no Claude position here", "either Claude rule", True),
                                             chk("Guard", "Fresh forecast", f"{(now - sg['made_ms']) / 60000:.1f} min old", "< 10 min", True),
                                             chk("Guard", "Exit plan", f"TP / SL at the broker · Kronos flips · {HOLD_BARS} bars", "checked every 20 s", None)]}
                jsave(NOTES, notes)
            jsave(STATE, st)
        except Exception as e:
            log(f"error {type(e).__name__}: {e}")
        time.sleep(20)


if __name__ == "__main__":
    os.environ.setdefault("MT5_NO_LAUNCH", "1")
    main()
