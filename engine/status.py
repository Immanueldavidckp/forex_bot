"""
engine/status.py — one answer to "where is every symbol in the strategy right now" (David 2026-10-30,
looking at /smc: "show the status like what all are the chart approaching our trading strategy, then what
all are in trade P/L loss, and in chart SL TP").

Three things, all built from the files the engine already writes (state.json, overview.json, pnl.json), so
the dashboard never has to touch MT5:

  APPROACHING  every live setup, ordered by how near price is to its entry. A V5 setup walks
               BOS/CHoCH -> POI (supply/demand or mitigation block) -> FVG -> price returns to the FVG
               -> M5 BOS confirms -> the nine gates -> order. The step it is on is its status; the
               distance to the entry is how close it is to the next one.
  IN TRADE     every open position with its live P&L, its stop and target, and how far it has travelled
               in R (so a trade sitting at +0.4R is not mistaken for a winner).
  LEVELS       the SL / TP / entry of each live setup and open trade, for drawing on the chart.

Nothing here decides anything; it only reports.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .config import OVERVIEW_FILE, PNL_FILE, STATE_FILE, VIEW_DIR

# the steps of a V5 setup, in the order they happen; the index is used to sort and to show progress
STEPS = ["waiting pullback", "waiting M5 BOS", "signal", "entered"]
LIVE = ("waiting pullback", "waiting M5 BOS")
STEP_TEXT = {
    "waiting pullback": "structure + FVG are set; waiting for price to come back to the entry",
    "waiting M5 BOS": "price retraced into the FVG; waiting for an M5 close beyond the last M5 swing",
    "signal": "every rule passed — order would go now (watch mode if trading is off)",
    "entered": "in trade",
}


def _load(path: str) -> Dict:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def _atr(bars: List, period: int = 14) -> Optional[float]:
    """ATR(14) straight off a view file's [t, o, h, l, c, ...] bars."""
    if not bars or len(bars) < period + 1:
        return None
    tr = []
    for i in range(1, len(bars)):
        h, l = float(bars[i][2]), float(bars[i][3])
        pc = float(bars[i - 1][4])
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    tail = tr[-period:]
    return sum(tail) / len(tail) if tail else None


def _num(x) -> Optional[float]:
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def approaching(state: Dict, ov: Dict) -> List[Dict]:
    """every setup still alive, nearest to its entry first.

    The live plan (entry / stop / target / RR) is the `preview` the engine writes into each symbol's view
    file, not state.json -- a waiting setup has no committed plan yet, only the one it would trade with now.
    Each row also carries whether the cost gate would let it through, so a symbol the engine will never
    trade is not shown as if it were about to fire.
    """
    from . import profit as PR
    costs = PR.load_costs()
    price_of = {s["symbol"]: _num(s.get("price")) for s in (ov.get("symbols") or [])}
    out = []
    for fn in sorted(os.listdir(VIEW_DIR)) if os.path.isdir(VIEW_DIR) else []:
        if not fn.endswith(".json"):
            continue
        v = _load(os.path.join(VIEW_DIR, fn))
        sym = v.get("symbol") or fn[:-5]
        px = price_of.get(sym)
        if px is None:
            bars = (v.get("bars") or {}).get("M5") or []
            px = _num(bars[-1][4]) if bars else None
        c = costs.get(sym) or {}
        dear = c.get("tradeable") is False
        for r in (v.get("setups") or []):
            st = r.get("status")
            if st not in LIVE and st != "signal":
                continue
            plan = r.get("preview") or r.get("plan") or {}
            tgt = plan.get("target") or {}
            entry = _num(plan.get("entry")) or _num(r.get("entry"))
            # the engine writes a preview only for its trade timeframes (M15 / M30), so H4 and M5 setups
            # get their ATR from the view's own bars rather than showing no distance at all
            atr = _num(plan.get("atr")) or _atr((v.get("bars") or {}).get(r.get("tf")) or [])
            dist = abs(px - entry) if (px is not None and entry is not None) else None
            out.append({
                "symbol": sym, "tf": r.get("tf"), "side": r.get("side"), "status": st,
                "step": STEPS.index(st) if st in STEPS else None, "step_text": STEP_TEXT.get(st, st),
                "entry": entry, "price": px, "distance": dist,
                "distance_atr": round(dist / atr, 2) if (dist is not None and atr) else None,
                "distance_pct": round(100 * dist / px, 3) if (dist is not None and px) else None,
                "stop": _num(plan.get("stop")), "target": _num(tgt.get("price")),
                # a setup on a chart-only timeframe has no committed plan yet; its zone's far edge is where
                # the stop will go (V5: "this setup's zone + buffer"), so it is shown as provisional
                "stop_provisional": _num(r.get("invalidation")) if plan.get("stop") is None else None,
                "target_label": tgt.get("label"), "rr": _num(tgt.get("rr")),
                "sl_atr_x": _num(plan.get("sl_atr_x")),
                "blocked": plan.get("why") or None,
                "tradeable": not dear,
                "cost_why": (f"{sym} costs {c['spread_atr']:.0%} of an ATR to trade "
                             f"(limit {PR.P['MAX_SPREAD_ATR']:.0%})") if dear and c.get("spread_atr") else None,
                "entry_type": r.get("entry_type"), "id": r.get("id"), "kind": r.get("kind"),
            })
    # what the engine can actually trade first, then the nearest to firing
    out.sort(key=lambda d: (not d["tradeable"], -(d["step"] or 0),
                            d["distance_atr"] if d["distance_atr"] is not None else 9e9))
    return out


def in_trade(state: Dict, ov: Dict) -> List[Dict]:
    """open positions with live P&L and how far they have run in R."""
    trades = {t.get("symbol"): t for t in (ov.get("trades") or [])}
    out = []
    for p in (ov.get("positions") or []):
        sym = p.get("symbol")
        op, cur = _num(p.get("price_open")), _num(p.get("price_current"))
        sl, tp = _num(p.get("sl")), _num(p.get("tp"))
        buy = int(p.get("type", 0)) == 0
        risk = abs(op - sl) if (op is not None and sl) else None
        moved = ((cur - op) if buy else (op - cur)) if (op is not None and cur is not None) else None
        t = trades.get(sym) or {}
        out.append({
            "symbol": sym, "ticket": p.get("ticket"), "side": "buy" if buy else "sell",
            "volume": _num(p.get("volume")), "entry": op, "price": cur, "sl": sl, "tp": tp,
            "pnl": _num(p.get("profit")), "comment": p.get("comment"),
            "risk": risk, "moved": moved,
            "r_now": round(moved / risk, 2) if (risk and moved is not None) else None,
            "to_sl": abs(cur - sl) if (cur is not None and sl) else None,
            "to_tp": abs(tp - cur) if (cur is not None and tp) else None,
            "tf": t.get("tf"), "setup": t.get("setup") or t.get("id"),
        })
    out.sort(key=lambda d: (d["pnl"] if d["pnl"] is not None else 0))
    return out


def levels(sym: str, state: Dict, ov: Dict) -> List[Dict]:
    """entry / SL / TP lines to draw on one symbol's chart."""
    out = []
    for a in approaching(state, ov):
        if a["symbol"] != sym:
            continue
        for key, kind in (("entry", "entry"), ("stop", "sl"), ("stop_provisional", "sl"), ("target", "tp")):
            if a.get(key) is not None:
                out.append({"price": a[key], "kind": kind, "side": a["side"], "tf": a["tf"],
                            "status": a["status"], "id": a["id"], "live": True})
    for t in in_trade(state, ov):
        if t["symbol"] != sym:
            continue
        for key, kind in (("entry", "entry"), ("sl", "sl"), ("tp", "tp")):
            if t.get(key):
                out.append({"price": t[key], "kind": kind, "side": t["side"], "tf": t.get("tf"),
                            "status": "entered", "id": t["ticket"], "live": False, "pnl": t["pnl"]})
    return out


def build(sym: str = "") -> Dict:
    state, ov, pnl = _load(STATE_FILE), _load(OVERVIEW_FILE), _load(PNL_FILE)
    ap, it = approaching(state, ov), in_trade(state, ov)
    acct = ov.get("account") or {}
    return {
        "at": ov.get("at"), "trading": ov.get("trading"), "profile": ov.get("filter_profile"),
        "approaching": ap, "in_trade": it,
        "counts": {"approaching": len(ap), "ready": sum(1 for a in ap if a["status"] == "signal"),
                   "in_trade": len(it)},
        "open_pnl": round(sum(t["pnl"] for t in it if t["pnl"] is not None), 2),
        "equity": _num(acct.get("equity")), "balance": _num(acct.get("balance")),
        "run": {"n": (pnl.get("all") or {}).get("n"), "total": (pnl.get("all") or {}).get("total"),
                "mean": (pnl.get("all") or {}).get("mean"), "lo": (pnl.get("all") or {}).get("lo"),
                "hi": (pnl.get("all") or {}).get("hi"), "verdict": pnl.get("all_verdict")},
        "levels": levels(sym, state, ov) if sym else [],
    }


if __name__ == "__main__":
    import argparse
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--symbol", default="")
    ap_.add_argument("--json", action="store_true")
    a = ap_.parse_args()
    d = build(a.symbol)
    if a.json:
        print(json.dumps(d, indent=1))
        raise SystemExit(0)
    c = d["counts"]
    print(f"trading {'ON' if d['trading'] else 'off'} · profile {d['profile']} · equity {d['equity']}")
    print(f"\nAPPROACHING ({c['approaching']} live, {c['ready']} ready to fire)")
    print(f"  {'symbol':<11}{'tf':<5}{'side':<6}{'step':<22}{'entry':>12}{'price':>12}{'away':>8}{'RR':>6}  note")
    for r in d["approaching"][:30]:
        away = (f"{r['distance_atr']:.2f}A" if r["distance_atr"] is not None
                else (f"{r['distance_pct']:.2f}%" if r["distance_pct"] is not None else "—"))
        note = "TOO DEAR — will be refused" if not r["tradeable"] else (r["blocked"][:40] if r["blocked"] else "")
        print(f"  {r['symbol']:<11}{str(r['tf']):<5}{str(r['side']):<6}{r['status']:<22}"
              f"{r['entry'] if r['entry'] is not None else 0:>12.5f}{r['price'] if r['price'] is not None else 0:>12.5f}"
              f"{away:>8}{r['rr'] if r['rr'] is not None else 0:>6.2f}  {note}")
    print(f"\nIN TRADE ({c['in_trade']}, open P&L ${d['open_pnl']:+.2f})")
    for t in d["in_trade"]:
        print(f"  {t['symbol']:<10}{t['side']:<6}{t['volume']} @ {t['entry']:g}  now {t['price']:g}  "
              f"SL {t['sl'] or 0:g}  TP {t['tp'] or 0:g}  P&L ${t['pnl'] or 0:+.2f}  ({t['r_now']}R)")
    r = d["run"]
    if r.get("n"):
        print(f"\nRUN SO FAR: {r['n']} closed, net ${r['total']:+.2f}, per trade ${r['mean']:+.4f} -> {r['verdict']}")
