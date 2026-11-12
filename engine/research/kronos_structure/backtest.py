"""
engine/research/kronos_structure/backtest.py — does David's M15 structure (BOS / CHoCH, engine/major_structure.py)
fix Kronos' trades? (David 2026-11-12: "kronos failing because of trend, add the trend analysis in the 15 min and
add the CHOCH and BOS ... do the backtest with few chart")

Every recorded live forecast (engine_data/kronos/signals.jsonl: 16 paths, 8 bars, M15) is replayed on the broker's
M15 bars with the live rule's levels: entry at the next bar's open (ask for a buy), stop 1 ATR(14) capped at $2,
target 2 × the stop distance or 2 ATR (the larger), out at the close of bar 8. Bars are bid prices; the symbol's
spread now is charged on every trade. A bar that touches stop and target counts as the stop. Result in R.

Structure at the forecast bar, from ONE forward pass (the pass only ever uses closed bars, so no look-ahead):
trend = side of the last event; last event kind (BOS / CHoCH) and its age in bars; where price sits in the leg
(0 = at the protected level, 1 = at the leg's extreme). H1 the same way.

    cd ~/forex && DISPLAY=:99 MT5_NO_LAUNCH=1 PYTHONPATH=. ~/opt/kronos-venv/bin/python engine/research/kronos_structure/backtest.py
"""
from __future__ import annotations

import bisect
import collections
import json
import os
import re
import sys
import time

import mt5_client as m
from engine.config import KRONOS as K
from engine import kronos_book as KB
from engine.kronos_book import lot_for, money_per_move
from engine.major_structure import atr14, major_structure

SYMS = (sys.argv[1].split(",") if len(sys.argv) > 1 else
        ["GOLD", "BITCOIN", "ETHEREUM", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
         "EURJPY", "GBPJPY", "EURGBP", "EURCHF", "EURCAD", "GBPCHF"])
BAR = 900_000


def klass(s: str) -> str:
    return "gold" if s == "GOLD" else "crypto" if s in ("BITCOIN", "ETHEREUM") else "forex"


def state_at(events, bars, i):
    """structure known at the close of bar i: (side, kind, age, pos) of the last event with idx ≤ i"""
    k = bisect.bisect_right([e["idx"] for e in events], i) - 1
    if k < 0:
        return None
    e = events[k]
    prot = e["origin"]["price"]
    seg = bars[e["origin"]["idx"]:i + 1]
    ext = max(b["h"] for b in seg) if e["side"] == "buy" else min(b["l"] for b in seg)
    pos = (bars[i]["c"] - prot) / (ext - prot) if ext != prot else 1.0
    n_bos = 0                                         # BOS in a row on this side (how old the trend is)
    for q in events[k::-1]:
        if q["side"] != e["side"]:
            break
        n_bos += q["kind"] == "BOS"
    return {"side": e["side"], "kind": e["kind"], "age": i - e["idx"], "pos": pos, "n_bos": n_bos}


def simulate(bars, A, i, side, info, spread):
    """→ R after spread, or None when the live rule would refuse (spread over 30 % of the stop / no bars)"""
    if i + 1 + K["HOLD_BARS"] >= len(bars):
        return None
    sg = 1 if side == "buy" else -1
    sl_d = K["SL_ATR"] * A[i]
    mpm = money_per_move(info) * lot_for(info)
    if K.get("MAX_RISK_USD") and mpm > 0:
        sl_d = min(sl_d, K["MAX_RISK_USD"] / mpm)
    tp_d = max(K["TP_ATR"] * A[i], (K.get("MIN_RR") or 2.0) * sl_d)
    if sl_d <= 0 or spread > K["MAX_SPREAD_SL"] * sl_d:
        return None
    o = bars[i + 1]["o"]
    entry = o + spread if sg > 0 else o               # buy at the ask, sell at the bid
    sl, tp = entry - sg * sl_d, entry + sg * tp_d
    for b in bars[i + 1:i + 1 + K["HOLD_BARS"]]:
        lo, hi = (b["l"], b["h"]) if sg > 0 else (b["l"] + spread, b["h"] + spread)   # a sell closes at the ask
        if (lo <= sl) if sg > 0 else (hi >= sl):
            return -1.0
        if (hi >= tp) if sg > 0 else (lo <= tp):
            return tp_d / sl_d
    c = bars[i + K["HOLD_BARS"]]["c"] + (0 if sg > 0 else spread)
    return sg * (c - entry) / sl_d


def main() -> int:
    off = m.detect_offset("BITCOIN")
    data = m.bars_many([(s, "M15", 4000) for s in SYMS] + [(s, "H1", 1500) for s in SYMS], timeout=400, offset=off)
    infos = {s: r.get("result") for s, r in zip(SYMS, m.call([{"op": "info", "symbol": s} for s in SYMS], timeout=120))}
    sigs = collections.defaultdict(dict)
    with open(os.path.join(K["DIR"], "signals.jsonl")) as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d["symbol"] in SYMS:
                sigs[d["symbol"]][d["bar_t"]] = d
    rows = []
    for s in SYMS:
        B, H, info = data.get((s, "M15")), data.get((s, "H1")), infos.get(s)
        if not B or not H or not info:
            print(f"{s}: no bars / info", file=sys.stderr)
            continue
        spread = float(info.get("spread") or 0) * float(info.get("point") or 0)
        A, ev, hev = atr14(B), major_structure(B)["events"], major_structure(H)["events"]
        idx = {b["t"]: i for i, b in enumerate(B)}
        ht = [b["t"] for b in H]
        for bar_t, d in sorted(sigs[s].items()):
            i = idx.get(bar_t)
            if i is None or i < 600:
                continue
            st = state_at(ev, B, i)
            hi = bisect.bisect_right(ht, bar_t + BAR - 3_600_000) - 1      # the last H1 bar closed by the entry
            hs = state_at(hev, H, hi) if hi >= 0 else None
            p_up = float(d["p_up"])
            agree, move = max(p_up, 1 - p_up), float(d["median"][-1]) - float(d["last"])
            kside = "buy" if p_up >= K["P_MIN"] else "sell" if p_up <= 1 - K["P_MIN"] else None
            if kside and ((move > 0) != (kside == "buy") or abs(move) < K["MIN_MOVE_SPREAD_X"] * spread):
                kside = None
            r = {"s": s, "t": bar_t, "st": st, "h1": hs, "kside": kside, "agree": agree}
            r["Rk"] = simulate(B, A, i, kside, info, spread) if kside else None
            # the live rule's own view: kronos_book.structure() on the CONTEXT bars the engine holds
            r["live"] = KB.structure([[x["t"], x["o"], x["h"], x["l"], x["c"]] for x in B[i + 1 - K["CONTEXT"]:i + 1]]) if kside else None
            r["Rst"] = simulate(B, A, i, st["side"], info, spread) if st else None    # control: the trend alone
            rows.append(r)
    ts = sorted(r["t"] for r in rows)
    print(f"{len(rows)} forecasts on {len({r['s'] for r in rows})} symbols, {time.strftime('%m-%d', time.gmtime(ts[0] / 1000))} → "
          f"{time.strftime('%m-%d', time.gmtime(ts[-1] / 1000))}; Kronos signals (≥ {K['P_MIN']:.0%}): {sum(1 for r in rows if r['Rk'] is not None)}")
    mid = ts[len(ts) // 2]

    def show(name, G, key="Rk"):
        G = [r for r in G if r.get(key) is not None]
        if not G:
            return print(f"  {name:58} n   0")
        x = [r[key] for r in G]
        a, b = [r[key] for r in G if r["t"] < mid], [r[key] for r in G if r["t"] >= mid]
        av = lambda v: f"{sum(v) / len(v):+.2f}" if v else "  -  "
        print(f"  {name:58} n {len(x):4}  won {100 * sum(v > 0 for v in x) / len(x):3.0f}%  avg {av(x)} R  sum {sum(x):+7.1f} R"
              f"   1st half {av(a)} (n {len(a)})  2nd half {av(b)} (n {len(b)})")

    KS = [r for r in rows if r["kside"] and r["st"]]
    W = lambda r: r["st"]["side"] == r["kside"]
    HW = lambda r: r["h1"] and r["h1"]["side"] == r["kside"]
    print("\n== 1. Kronos alone vs Kronos + M15 structure")
    show("Kronos alone (the live rule)", KS)
    show("Kronos WITH the M15 trend", [r for r in KS if W(r)])
    show("Kronos AGAINST the M15 trend", [r for r in KS if not W(r)])
    show("Kronos with M15 AND H1 trend", [r for r in KS if W(r) and HW(r)])
    show("Kronos with H1 trend only", [r for r in KS if HW(r)])
    show("Kronos against M15 and H1", [r for r in KS if not W(r) and not HW(r)])
    print("\n== 2. control: the M15 trend with NO Kronos (does Kronos add anything?)")
    show("trend alone, every forecast bar", [r for r in rows if r["st"]], "Rst")
    show("trend alone, Kronos undecided (< 75 %)", [r for r in rows if r["st"] and not r["kside"]], "Rst")
    show("trend alone, Kronos agrees", [r for r in KS if W(r)], "Rst")
    show("trend alone, Kronos disagrees", [r for r in KS if not W(r)], "Rst")
    for side in ("buy", "sell"):
        S = [r for r in KS if r["kside"] == side]
        print(f"\n== 3. {side.upper()}S — Kronos {side} and where the M15 structure is")
        show(f"all Kronos {side}s", S)
        show(f"M15 trend {'up' if side == 'buy' else 'down'} (with)", [r for r in S if W(r)])
        show("  last event BOS", [r for r in S if W(r) and r["st"]["kind"] == "BOS"])
        show("  last event CHoCH (trend just turned)", [r for r in S if W(r) and r["st"]["kind"] == "CHoCH"])
        show("  event fresh (≤ 12 bars = 3 h)", [r for r in S if W(r) and r["st"]["age"] <= 12])
        show("  event 13–48 bars old", [r for r in S if W(r) and 12 < r["st"]["age"] <= 48])
        show("  event older than 48 bars (12 h)", [r for r in S if W(r) and r["st"]["age"] > 48])
        show("  price in the pullback (lower 60 % of the leg)", [r for r in S if W(r) and r["st"]["pos"] < 0.6])
        show("  price near the leg's extreme (top 40 %)", [r for r in S if W(r) and r["st"]["pos"] >= 0.6])
        show("  1st BOS of the trend or the CHoCH", [r for r in S if W(r) and r["st"]["n_bos"] <= 1])
        show("  2 or more BOS in a row (old trend)", [r for r in S if W(r) and r["st"]["n_bos"] >= 2])
        show("  with M15 + H1, in the pullback", [r for r in S if W(r) and HW(r) and r["st"]["pos"] < 0.6])
        show("  with M15 + H1, near the extreme", [r for r in S if W(r) and HW(r) and r["st"]["pos"] >= 0.6])
        show(f"M15 trend against the {side}", [r for r in S if not W(r)])
        show("  against, last event CHoCH", [r for r in S if not W(r) and r["st"]["kind"] == "CHoCH"])
        show("  against, last event BOS", [r for r in S if not W(r) and r["st"]["kind"] == "BOS"])
    print("\n== 4. by market: Kronos with the M15 trend / against")
    for c in ("forex", "gold", "crypto"):
        show(f"{c} with", [r for r in KS if klass(r["s"]) == c and W(r)])
        show(f"{c} against", [r for r in KS if klass(r["s"]) == c and not W(r)])
    print("\n== 5. by symbol: Kronos alone → with the M15 trend")
    for s in SYMS:
        show(f"{s} alone", [r for r in KS if r["s"] == s])
        show(f"{s} with M15 trend", [r for r in KS if r["s"] == s and W(r)])
    print("\n== 6. Kronos agreement, with the M15 trend")
    for lo, hi in ((0.75, 0.82), (0.82, 0.94), (0.94, 1.01)):
        show(f"{lo:.0%}–{min(hi, 1):.0%} with", [r for r in KS if W(r) and lo <= r["agree"] < hi])
        show(f"{lo:.0%}–{min(hi, 1):.0%} against", [r for r in KS if not W(r) and lo <= r["agree"] < hi])
    print("\n== 7. the live rule (kronos_book.decide): M15 trend from the engine's 512 bars, buys only in the pullback")
    ok = lambda r: r["live"] and r["live"]["side"] == r["kside"] and (r["kside"] == "sell" or r["live"]["pos"] <= KB.BUY_PULLBACK_MAX)
    show("before: Kronos alone", KS)
    show("after: trades the new rule takes", [r for r in KS if ok(r)])
    show("after: trades the new rule refuses", [r for r in KS if not ok(r)])
    show("  taken sells", [r for r in KS if ok(r) and r["kside"] == "sell"])
    show("  taken buys", [r for r in KS if ok(r) and r["kside"] == "buy"])
    days = len({r["t"] // 86400_000 for r in KS}) or 1
    print(f"  per day: before {len([r for r in KS if r['Rk'] is not None]) / days:.0f} trades, after "
          f"{len([r for r in KS if ok(r) and r['Rk'] is not None]) / days:.0f} trades ({days} days with forecasts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
