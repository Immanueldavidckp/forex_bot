"""
engine/tools/claude_crypto.py — Claude's own crypto trades on the FxPro demo (David 2026-11-07: "take all the entries you
can, 0.01 lot, then monitor when to exit"). Magic 24102099 (KRONOS["CLAUDE_MAGIC"], shown on /kronos).

    MT5_NO_LAUNCH=1 python3 -m engine.tools.claude_crypto scan      # every crypto symbol: trend, pullback, zone, spread → trades
    MT5_NO_LAUNCH=1 python3 -m engine.tools.claude_crypto watch     # loop: break-even at +1R, trail 1 ATR after +1.5R, 12 h time exit

The rule (Claude's read, written down so it is the same on every symbol):
  trend    H1: close above the 24-bar mean AND the last 12 H1 lows rising → up; below AND highs falling → down; else none
  pullback price has come back against the trend ≥ 0.4 ATR(H1) from the last 12 h extreme but < 1.5 ATR (not at the extreme,
           not a reversal)
  zone     a fresh S&D David zone (zones.json) on the trend side within 2 ATR(M15): the stop goes beyond it
  stop     beyond the last 6 H1 swing (max high / min low) or the zone, + spread; target 2 R
  skip     spread > 25 % of the risk, risk < the broker's stops level, already in this symbol
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/forex"))
import mt5_client as mt5c                                     # noqa: E402
from engine.config import DATA_DIR, KRONOS                    # noqa: E402
from engine.trade_checks import chk, g                        # noqa: E402

MAGIC = KRONOS["CLAUDE_MAGIC"]
LOTS = 0.01
FX = {"AUDUSD", "CADCHF", "CADJPY", "CHFJPY", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURUSD", "GBPCAD", "GBPCHF",
      "GBPJPY", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY", "GOLD"}
LOG = os.path.join(DATA_DIR, "kronos", "claude_crypto.log")
NOTES = os.path.join(DATA_DIR, "kronos", "claude_notes.json")


def log(msg):
    line = f"[claude {time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def atr(bars, n=14):
    tr = [max(b["h"] - b["l"], abs(b["h"] - p["c"]), abs(b["l"] - p["c"])) for p, b in zip(bars, bars[1:])]
    return sum(tr[-n:]) / n


def symbols():
    with open(os.path.join(DATA_DIR, "sdd", "state.json")) as f:
        return [s for s in json.load(f)["symbols"] if s not in FX]


def read(sym, h1, m15, zones, info, tick):
    """→ a trade dict or {"skip": why}."""
    if len(h1) < 30:
        return {"skip": "few bars"}
    c = h1[-1]["c"]
    mean = sum(b["c"] for b in h1[-24:]) / 24
    lows, highs = [b["l"] for b in h1[-12:]], [b["h"] for b in h1[-12:]]
    rising = min(lows[6:]) > min(lows[:6]) and max(highs[6:]) > max(highs[:6])
    falling = max(highs[6:]) < max(highs[:6]) and min(lows[6:]) < min(lows[:6])
    a1, a15 = atr(h1), atr(m15)
    if c > mean and rising:
        side = "buy"
    elif c < mean and falling:
        side = "sell"
    else:
        return {"skip": "no H1 trend"}
    ext = max(highs) if side == "buy" else min(lows)
    pull = (ext - c) if side == "buy" else (c - ext)
    momentum = pull < 0.4 * a1          # at the extreme: allowed as a momentum entry (David: every entry possible), smaller target
    if pull > 1.5 * a1:
        return {"skip": f"pullback too deep ({pull / a1:.1f} ATR)"}
    bid, ask = float(tick["bid"]), float(tick["ask"])
    sp = max(ask - bid, 0.0)
    pt = float(info["point"])
    gap = float(info.get("trade_stops_level") or 0) * pt
    swing = min(b["l"] for b in h1[-6:]) if side == "buy" else max(b["h"] for b in h1[-6:])
    zone = None
    for z in zones:
        if z["side"] == ("demand" if side == "buy" else "supply") and abs(z["entry"] - c) <= 2 * a15:
            zone = z
    rr = 1.5 if momentum else 2.0
    if side == "buy":
        sl = min(swing, zone["stop"] if zone else swing) - sp - 0.1 * a15
        entry = ask
        sl = min(sl, entry - 5 * sp, entry - gap - pt)      # the stop at least 5 spreads away (cost ≤ 20 % of the risk)
        risk = entry - sl
        tp = entry + rr * risk
    else:
        sl = max(swing, zone["stop"] if zone else swing) + sp + 0.1 * a15
        entry = bid
        sl = max(sl, entry + 5 * sp, entry + gap + pt)
        risk = sl - entry
        tp = entry - rr * risk
    if risk <= max(gap, 0):
        return {"skip": f"risk {risk:g} inside the stops level {gap:g}"}
    if sp > 0.25 * risk:
        return {"skip": f"spread {sp:g} is {sp / risk:.0%} of the risk {risk:g}"}
    dg = int(info["digits"])
    # what set the stop: the swing / zone, the 5-spread floor or the broker's stops level (the furthest one wins)
    base = (min(swing, zone["stop"] if zone else swing) - sp - 0.1 * a15) if side == "buy" else \
        (max(swing, zone["stop"] if zone else swing) + sp + 0.1 * a15)
    src = {abs(entry - base): (f"S&D zone stop {g(zone['stop'])}" if zone and (zone["stop"] < swing if side == "buy" else zone["stop"] > swing)
                               else f"6-bar H1 swing {'low' if side == 'buy' else 'high'} {g(swing)}") + " + spread + 0.1 ATR(M15)",
           5 * sp: "the 5-spread floor", gap + pt: "the broker's stops level"}
    why_sl = src[max(src)]
    lo_a, lo_b, hi_a, hi_b = min(lows[:6]), min(lows[6:]), max(highs[:6]), max(highs[6:])
    t_end = h1[-1]["t"] + 3_600_000
    checks = [
        chk("Setup", "H1 close vs 24-bar mean", f"close {g(c)} {'above' if c > mean else 'below'} mean {g(mean)}",
            "buy: above · sell: below", True),
        chk("Setup", "H1 swings, last 12 bars (6 vs 6)", f"lows {g(lo_a)} → {g(lo_b)} · highs {g(hi_a)} → {g(hi_b)}",
            "buy: lows AND highs rising · sell: both falling", True),
        chk("Entry", "Distance from the 12-bar extreme", f"{pull / a1:.2f} ATR(H1) from {g(ext)} → {'momentum' if momentum else 'pullback'}",
            "0.4–1.5 ATR = pullback (TP 2 R) · under 0.4 = momentum at the extreme (TP 1.5 R) · over 1.5 = skip", True),
        chk("Setup", "S&D David zone on the trend side", f"{zone['side']} {g(zone['entry'])}, stop {g(zone['stop'])}" if zone else "none within 2 ATR(M15)",
            "optional: when there is one within 2 ATR(M15), the stop goes beyond it", None),
        chk("Risk", "Stop", f"{g(round(sl, dg))} ← {why_sl}", "beyond the 6-bar swing / zone + spread, ≥ 5 spreads, outside the stops level", True),
        chk("Risk", "Spread vs risk", f"{g(sp)} = {sp / risk:.0%} of the risk {g(risk)}", "≤ 25 %", True),
        chk("Risk", "Broker stops level", f"risk {g(risk)} vs level {g(gap)}", "the stop outside it", True),
        chk("Risk", "Target", f"{rr:g} R → {g(round(tp, dg))}", "2 R pullback · 1.5 R momentum", True),
    ]
    marks = [
        {"type": "line", "label": "24-bar H1 mean", "price": mean, "t0": h1[-24]["t"], "t1": t_end, "color": "#ffb74d", "dash": [5, 3]},
        {"type": "line", "label": f"12-bar H1 {'high' if side == 'buy' else 'low'} (the extreme)", "price": ext, "t0": h1[-12]["t"],
         "t1": t_end, "color": "#9aa4b8", "dash": [2, 3]},
        {"type": "line", "label": f"6-bar H1 swing {'low' if side == 'buy' else 'high'}", "price": swing, "t0": h1[-6]["t"],
         "t1": t_end, "color": "#ce93d8", "dash": [2, 3]},
        {"type": "box", "label": "first 6 H1 bars", "t0": h1[-12]["t"], "t1": h1[-6]["t"], "top": hi_a, "bottom": lo_a, "color": "120,130,150"},
        {"type": "box", "label": "last 6 H1 bars", "t0": h1[-6]["t"], "t1": t_end, "top": hi_b, "bottom": lo_b,
         "color": "38,166,154" if side == "buy" else "239,83,80"},
    ]
    if zone:
        marks.append({"type": "box", "label": f"S&D David {zone['side']} zone", "t0": zone.get("t_a"), "t1": None,
                      "top": zone.get("top", max(zone["entry"], zone["stop"])), "bottom": zone.get("bottom", min(zone["entry"], zone["stop"])),
                      "color": "76,175,80" if zone["side"] == "demand" else "239,83,80"})
    return {"side": side, "entry": entry, "sl": round(sl, dg), "tp": round(tp, dg), "risk": risk, "spread": sp,
            "atr15": a15, "atr1": a1, "pull": round(pull / a1, 2), "zone": zone["entry"] if zone else None,
            "checks": checks, "marks": marks,
            "why": f"H1 {side} trend, {'momentum' if momentum else 'pullback'} {pull / a1:.1f} ATR" + (f", S&D {zone['side']} {zone['entry']:g}" if zone else "")}


def scan():
    syms = symbols()
    with open(os.path.join(DATA_DIR, "kronos", "zones", "zones.json")) as f:
        Z = json.load(f)["symbols"]
    have = {p["symbol"] for p in mt5c.positions(magic=MAGIC)}
    infos = {s: r.get("result") for s, r in zip(syms, mt5c.call([{"op": "info", "symbol": s} for s in syms], timeout=120))}
    ticks = {s: r.get("result") for s, r in zip(syms, mt5c.call([{"op": "tick", "symbol": s} for s in syms], timeout=120))}
    bars = mt5c.bars_many([(s, tf, n) for s in syms for tf, n in (("H1", 60), ("M15", 40))], timeout=240)
    try:
        with open(NOTES) as f:
            notes = json.load(f)
    except Exception:
        notes = {}
    placed = []
    for s in syms:
        if s in have:
            log(f"{s}: already in"); continue
        if not infos.get(s) or not ticks.get(s) or (s, "H1") not in bars:
            log(f"{s}: no data"); continue
        r = read(s, bars[(s, "H1")], bars[(s, "M15")], [z for z in Z.get(s, {}).get("zones", [])], infos[s], ticks[s])
        if "skip" in r:
            log(f"{s}: skip — {r['skip']}"); continue
        res = mt5c.order(s, r["side"], LOTS, sl=r["sl"], tp=r["tp"], magic=MAGIC, comment="claude crypto",
                         deviation=int(max(50, 0.2 * r["atr15"] / float(infos[s]["point"]))))
        ok = res.get("ok") or res.get("retcode") == 10009
        log(f"{s}: {r['side']} {LOTS} @ {res.get('price', r['entry'])} SL {r['sl']} TP {r['tp']} risk {r['risk']:.6g} — "
            f"{r['why']} → {'OK ticket ' + str(res.get('order')) if ok else 'REFUSED ' + str(res.get('comment'))}")
        if ok:
            placed.append(s)
            notes[str(res.get("order"))] = {"symbol": s, "side": r["side"], "why": r["why"], "entry": res.get("price", r["entry"]),
                                            "sl": r["sl"], "tp": r["tp"], "atr15": r["atr15"], "risk": r["risk"],
                                            "opened": int(time.time() * 1000), "plan": "BE at +1R, trail 1 ATR after +1.5R, 12 h time exit",
                                            "rule": "trend", "rule_tf": "H1", "marks": r["marks"],
                                            "checks": r["checks"] + [
                                                chk("Guard", "One trade per symbol", "no Claude trade open here", "one at a time", True),
                                                chk("Guard", "24 h loss cap", f"Claude P&L 24 h ${os.environ['CLAUDE_PNL24']}" if os.environ.get("CLAUDE_PNL24") else "scan run by hand",
                                                    "no new entries below −$40 (claude_night.sh)", True if os.environ.get("CLAUDE_PNL24") else None),
                                                chk("Guard", "Exit plan", "BE at +1 R · trail 1 ATR(M15) after +1.5 R · 12 h time exit", "the watcher, every 5 min", None)]}
    with open(NOTES, "w") as f:
        json.dump(notes, f, indent=1)
    log(f"scan done: {len(placed)} new trade(s): {', '.join(placed) or '-'}")


def watch(every=300, hold_h=12.0):
    known = {}                                   # ticket → symbol of the positions seen last round (broker exits are logged)
    while True:
        try:
            pos = mt5c.positions(magic=MAGIC)
            now_t = {p["ticket"]: p["symbol"] for p in pos}
            for t, sym in list(known.items()):
                if t in now_t:
                    continue
                try:                             # the broker closed it (SL / TP / by hand): find the closing deal
                    outs = [d for d in mt5c.deals(position=t) if d.get("entry") == 1]
                    if outs:
                        d = outs[-1]
                        how = {4: "stop", 5: "target"}.get(d.get("reason"), "closed")
                        pnl = d.get("profit", 0) + d.get("commission", 0) + d.get("swap", 0)
                        log(f"{sym} #{t}: → closed at the broker ({how} {d.get('price')}) P&L {pnl:+.2f}")
                    else:
                        log(f"{sym} #{t}: gone from the book (no closing deal found yet)")
                except Exception as e:
                    log(f"{sym} #{t}: gone; deal lookup failed {type(e).__name__}: {e}")
            known = now_t
            try:
                with open(NOTES) as f:
                    notes = json.load(f)
            except Exception:
                notes = {}
            now = time.time()
            for p in pos:
                sym, t = p["symbol"], p["ticket"]
                n = notes.get(str(t)) or notes.get(str(p.get("identifier"))) or {}
                buy = p["type"] == 0
                px = float(p["price_current"]); op = float(p["price_open"]); sl = float(p["sl"] or 0)
                risk = n.get("risk") or abs(op - sl) or 1
                a = n.get("atr15") or risk
                r = (px - op) / risk if buy else (op - px) / risk
                age_h = (now - n.get("opened", now * 1000) / 1000) / 3600 if n else 0
                want = None
                if r >= 1.5:
                    want = px - a if buy else px + a
                elif r >= 1.0:
                    want = op + 0.05 * risk if buy else op - 0.05 * risk
                if want is not None:                     # the broker refuses a stop inside its stops level: clamp to it
                    info = mt5c.info(sym); dg = int(info["digits"]); pt = float(info["point"])
                    gap = float(info.get("trade_stops_level") or 0) * pt
                    if gap:
                        want = min(want, px - gap - pt) if buy else max(want, px + gap + pt)
                if want is not None and ((buy and want > sl) or (not buy and (sl == 0 or want < sl))):
                    res = mt5c.sltp(t, sl=round(want, dg), tp=float(p["tp"] or 0))
                    log(f"{sym} #{t}: +{r:.2f}R → SL {round(want, dg)} ({'trail' if r >= 1.5 else 'break-even'}) {res.get('comment')}")
                elif age_h >= hold_h:
                    res = mt5c.close(t, comment="claude time exit")
                    log(f"{sym} #{t}: {age_h:.1f} h old at {r:+.2f}R → closed (time exit) {res.get('comment')}")
            log(f"watch: {len(pos)} open, " + ", ".join(f"{p['symbol']} {float(p['profit']):+.2f}" for p in pos))
        except Exception as e:
            log(f"watch error {type(e).__name__}: {e}")
        time.sleep(every)


if __name__ == "__main__":
    os.environ.setdefault("MT5_NO_LAUNCH", "1")
    {"scan": scan, "watch": watch}[sys.argv[1]]()
