"""
engine/trade_checks.py — "why did this trade happen": every check a strategy made before its entry, with the value it saw
and the rule it compared it to, plus the chart marks it used (David 2026-11-09: "if I click any trade it has to show
the full chart, why that trade happened, what all are the things it checked and what all are the confirmations").

Each strategy RECORDS its checks at the entry (claude_crypto, claude_kscalp, kronos_book, sdd_book → "checks" / "marks"
next to the trade). For trades placed before that existed, the dashboard REBUILDS them here from the saved candles
(explain()); a rebuilt list says so in its "source", and values the rule saw live (the spread, the broker's stops
level) that were not saved are marked "not recorded".

    check = {"group": "Setup" | "Entry" | "Risk" | "Guard", "name", "value", "need", "ok": True | False | None}
    mark  = {"type": "line",  "label", "price", "t0", "t1", "color", "dash"?}      times in ms (UTC)
            {"type": "box",   "label", "t0", "t1", "top", "bottom", "color"}
            {"type": "vline", "label", "t", "color"}
            {"type": "path",  "label", "t": [...], "p": [...], "color", "band": [[lo...], [hi...]]?}
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .config import DATA_DIR

BUY, SELL, INFO, ZONE_D, ZONE_S, KRON = "#26a69a", "#ef5350", "#9aa4b8", "76,175,80", "239,83,80", "#b388ff"


def chk(group: str, name: str, value, need: str, ok: Optional[bool]) -> Dict:
    return {"group": group, "name": name, "value": value if isinstance(value, str) else f"{value:g}", "need": need, "ok": ok}


def g(x, dg: int = 6) -> str:
    """A price, short: 5 significant digits for big numbers, the instrument's digits otherwise."""
    if x is None:
        return "–"
    return f"{x:.{dg}g}" if abs(x) < 1 else f"{x:.{max(2, dg - len(str(int(abs(x)))))}f}"


# ── rebuilding a trade that was placed before its checks were recorded ──────────────────────────────────────────────

def _bars(sym: str, tf: str) -> List[Dict]:
    """The view's recent bars (engine_data/view/<SYM>.json, seconds) as the engine's bar dicts (ms)."""
    try:
        with open(os.path.join(DATA_DIR, "view", f"{sym}.json")) as f:
            rows = (json.load(f).get("bars") or {}).get(tf) or []
    except (OSError, ValueError):
        return []
    return [{"t": r[0] * 1000, "o": r[1], "h": r[2], "l": r[3], "c": r[4]} for r in rows]


def _until(bars: List[Dict], ms: int, tf_ms: int) -> List[Dict]:
    """The bars that were CLOSED at ms (no peek at the bar the trade opened in)."""
    return [b for b in bars if b["t"] + tf_ms <= ms]


def _rebuild_claude(row: Dict) -> Dict:
    from .tools import claude_crypto as cc
    sym, ms = row["symbol"], row.get("opened_ms") or 0
    H1all, M15all = _bars(sym, "H1"), _bars(sym, "M15")
    h1, m15 = _until(H1all, ms, 3_600_000), _until(M15all, ms, 900_000)
    if len(h1) < 30 or len(m15) < 20:
        return {}
    e = float(row["entry"])
    # the live scan read the bars still FORMING at the entry (MT5 returns them last): rebuild them from the closed M15
    # bars inside the H1 bar + the entry price as its close, so the rebuilt read is what the rule saw
    h1_start = next((b["t"] for b in H1all if b["t"] <= ms < b["t"] + 3_600_000), None)
    if h1_start is not None:
        part = [b for b in m15 if b["t"] >= h1_start]
        h1.append({"t": h1_start, "o": part[0]["o"] if part else e, "h": max([b["h"] for b in part] + [e]),
                   "l": min([b["l"] for b in part] + [e]), "c": e})
    m15.append({"t": ms - ms % 900_000, "o": e, "h": e, "l": e, "c": e})
    r = cc.read(sym, h1[-60:], m15[-40:], [], {"point": 1e-8, "digits": 8, "trade_stops_level": 0}, {"bid": e, "ask": e})
    if "skip" in r:
        return {"checks": [chk("Setup", "Rebuilt from the candles", r["skip"], "the rule on the closed H1 bars at the entry",
                               None)], "source": "rebuilt"}
    keep = [c for c in r["checks"] if c["group"] in ("Setup", "Entry")]
    keep.append(chk("Risk", "Stop and target (as placed)", f"SL {g(row.get('sl'))} · TP {g(row.get('tp'))}",
                    "beyond the 6-bar H1 swing / zone + spread, ≥ 5 spreads; 2 R (1.5 R momentum)", None))
    keep.append(chk("Risk", "Spread at entry", "not recorded (trade older than the checklist)", "≤ 25 % of the risk", None))
    return {"checks": keep, "marks": r["marks"], "tf": "H1", "source": "rebuilt"}


def _rebuild_kscalp(row: Dict) -> Dict:
    from .tools import claude_kscalp as ks
    sym, ms = row["symbol"], row.get("opened_ms") or 0
    sg = None
    try:
        with open(os.path.join(DATA_DIR, "kronos", "signals.jsonl")) as f:
            for line in f:
                if f'"{sym}"' not in line:
                    continue
                x = json.loads(line)
                if x.get("symbol") == sym and x["bar_t"] + 900_000 <= ms and (sg is None or x["bar_t"] > sg["bar_t"]):
                    sg = x
    except OSError:
        return {}
    bars = _until(_bars(sym, "M15"), ms, 900_000)
    if sg is None or len(bars) < 30:
        return {}
    e = float(row["entry"])
    r = ks.plan(sym, sg, bars[-120:], {"point": 1e-8, "digits": 8, "trade_stops_level": 0}, {"bid": e, "ask": e})
    if "skip" in r:
        return {"checks": [chk("Setup", "Rebuilt from the forecast + candles", r["skip"], "", None)], "source": "rebuilt"}
    keep = [c for c in r["checks"] if c["name"] not in ("Spread", "Broker stops level", "Target", "Stop")]
    keep.append(chk("Risk", "Stop and target (as placed)", f"SL {g(row.get('sl'))} · TP {g(row.get('tp'))}",
                    "target short of the nearest obstacle, ≥ 3 spreads; stop = Kronos adverse close", None))
    keep.append(chk("Risk", "Spread at entry", "not recorded (trade older than the checklist)", "", None))
    return {"checks": keep, "marks": r["marks"], "tf": "M15", "source": "rebuilt"}


def _rebuild_kronos(row: Dict) -> Dict:
    from .config import KRONOS as K
    m = row.get("meta") or {}
    p = m.get("p_up")
    if p is None:
        return {}
    agree = max(p, 1 - p)
    side = row["side"]
    e, sl, tp = row.get("entry"), row.get("sl"), row.get("tp")
    a = abs(e - sl) / K["SL_ATR"] if e is not None and sl is not None else None
    med = m.get("median_end")
    out = [chk("Setup", "Kronos paths agreeing", f"{agree:.0%} of {K['PATHS']} paths {'up' if side == 'buy' else 'down'}",
               f"≥ {K['P_MIN']:.0%}", agree >= K["P_MIN"])]
    if med is not None and e is not None:
        out.append(chk("Setup", "Median path ends", f"{g(med)} ({'above' if med > e else 'below'} the entry {g(e)})",
                       f"on the {side} side", (med > e) == (side == "buy")))
    out += [chk("Risk", "Stop", f"{K['SL_ATR']:g} ATR(M15) = {g(a)}" if a else "–", f"{K['SL_ATR']:g} ATR", None),
            chk("Risk", "Target", f"{K['TP_ATR']:g} ATR = {g(abs(tp - e)) if tp is not None and e is not None else '–'}",
                f"{K['TP_ATR']:g} ATR (2 R)", None),
            chk("Risk", "Spread vs stop", "not recorded (trade older than the checklist)", f"≤ {K['MAX_SPREAD_SL']:.0%}", None),
            chk("Guard", "Exit plan", f"{K['HOLD_BARS']} bars (2 h) time exit", "TP / SL at the broker", None)]
    marks = []
    bt = m.get("bar_t")
    if bt:
        try:
            with open(os.path.join(DATA_DIR, "kronos", "signals.jsonl")) as f:
                sg = next((x for x in map(json.loads, (ln for ln in f if f'"{row["symbol"]}"' in ln and str(bt) in ln))
                           if x.get("symbol") == row["symbol"] and x.get("bar_t") == bt), None)
            if sg:
                from .kronos_book import kronos_marks
                marks = kronos_marks(sg, e)
        except (OSError, ValueError):
            pass
    return {"checks": out, "marks": marks, "tf": "M15", "source": "rebuilt"}


def _rebuild_sdd(row: Dict) -> Dict:
    m = row.get("meta") or {}
    if m.get("t_a") is None:
        return {}
    from . import sd_david
    from .major_structure import major_structure
    sym, ms = row["symbol"], row.get("placed_ms") or row.get("opened_ms") or 0
    bars = _until(_bars(sym, "M15"), ms, 900_000)
    z = None
    if len(bars) > 30:
        try:
            z = next((x for x in sd_david.zones(bars, major_structure(bars, 5), 5)
                      if x.get("valid") and bars[x["break"]]["t"] == m.get("t_break")), None)
        except Exception:
            z = None
    if z is None:                                   # the zone is older than the saved candles: what the order kept
        zone = m.get("zone")
        z = {"side": zone, "dir": row["side"], "top": m.get("zone_top"), "bottom": m.get("zone_bottom"),
             "proximal": m.get("zone_top") if zone == "demand" else m.get("zone_bottom"),
             "distal": m.get("zone_bottom") if zone == "demand" else m.get("zone_top"), "fvg": None, "status": "fresh",
             "event": None, "bos_level": None}
        r = sdd_checks(z, None, {"price": row.get("entry"), "sl": row.get("sl"), "tp": row.get("tp"), "rr": m.get("rr"),
                                 "spread": None}, t_a=m.get("t_a"), t_break=m.get("t_break"))
    else:
        r = sdd_checks(z, bars, {"price": row.get("entry"), "sl": row.get("sl"), "tp": row.get("tp"), "rr": m.get("rr"),
                                 "spread": None})
    r["source"] = "rebuilt"
    return r


def explain(row: Dict) -> Dict:
    """→ {"checks", "marks", "tf", "source": "recorded" | "rebuilt" | "none"} for one /api/trades row."""
    m = row.get("meta") or {}
    if m.get("checks"):
        return {"checks": m["checks"], "marks": m.get("marks") or [], "tf": m.get("rule_tf") or "M15", "source": "recorded"}
    out: Dict = {}
    try:
        if row["strategy"] == "Claude":
            out = _rebuild_kscalp(row) if m.get("rule") == "kscalp" else _rebuild_claude(row)
        elif row["strategy"] == "Kronos":
            out = _rebuild_kronos(row)
        elif row["strategy"] == "S&D David":
            out = _rebuild_sdd(row)
    except Exception as e:                          # a rebuild is a nice-to-have: never break the page
        out = {"checks": [chk("Setup", "Rebuild failed", f"{type(e).__name__}: {e}", "", None)], "source": "rebuilt"}
    if not out:
        return {"checks": [], "marks": [], "tf": "M15", "source": "none"}
    out.setdefault("marks", [])
    out.setdefault("tf", "M15")
    return out


# ── S&D David: shared by sdd_book (recorded at the order) and the rebuild above ─────────────────────────────────────

def sdd_checks(z: Dict, bars: Optional[List[Dict]], lv: Dict, t_a: Optional[int] = None, t_break: Optional[int] = None,
               gap: Optional[float] = None, max_spread_risk: Optional[float] = None) -> Dict:
    """One S&D David zone + its order levels → checks + marks. bars = the M15 bars the zone was found on (None: the
    zone's own fields only)."""
    from .config import SDD as S
    buy = z["dir"] == "buy"
    t = (lambda i: bars[i]["t"] if bars is not None and i is not None and 0 <= i < len(bars) else None)
    ta = t_a if t_a is not None else t(z.get("a"))
    tb = t_break if t_break is not None else t(z.get("break"))
    out: List[Dict] = []
    if z.get("bos_level") is not None:
        out.append(chk("Setup", "Break of structure", f"{'bull' if buy else 'bear'} BOS: close beyond {g(z['bos_level'])}",
                       "a BOS (not a CHoCH) at the leg's extreme — David's structure rule", True))
    else:
        out.append(chk("Setup", "Break of structure", f"{'bull' if buy else 'bear'} BOS", "a BOS at the leg's extreme",
                       True))
    fv = z.get("fvg")
    out.append(chk("Setup", "Gap A-B-C inside the BOS move",
                   f"FVG {g(fv['bottom'])} – {g(fv['top'])} ({fv['atr']} ATR)" if fv else "found (size not saved)",
                   "candle C's low above A's high (demand) / C's high below A's low (supply)", True))
    out.append(chk("Setup", "4th candle did not fill the gap", "unfilled", "the first gap the 4th candle leaves open = the zone",
                   True))
    out.append(chk("Setup", f"Zone = candle A ({z['side']})", f"{g(z['bottom'])} – {g(z['top'])}",
                   "one zone per BOS: candle A of that first gap", True))
    out.append(chk("Setup", "Zone still fresh", z.get("status") or "fresh",
                   "price has not come back to A since the BOS; no close through A; no CHoCH against it",
                   (z.get("status") or "fresh") == "fresh"))
    tg = (z.get("targets") or [])
    t1 = tg[S["TARGET"] - 1] if len(tg) >= S["TARGET"] else None
    out.append(chk("Entry", "Limit order at the zone", f"{'buy' if buy else 'sell'} limit {g(lv.get('price'))}",
                   f"{'A high + spread' if buy else 'A low'}: fills when price comes back", True))
    out.append(chk("Risk", "Stop beyond candle A", f"{g(lv.get('sl'))}",
                   f"A's {'low −' if buy else 'high + spread +'} {S.get('SL_BUFFER_POINTS', 0)} points (David 2026-11-09)", True))
    out.append(chk("Risk", f"Target T{S['TARGET']}", f"{g(lv.get('tp'))} · {lv.get('rr')} R" if lv.get("rr") is not None
                   else g(lv.get("tp")), "Fib 0.618 between the entry and the move's extreme", None))
    sp, risk = lv.get("spread"), (abs(lv["price"] - lv["sl"]) if lv.get("price") is not None and lv.get("sl") is not None else None)
    msr = max_spread_risk if max_spread_risk is not None else S["MAX_SPREAD_RISK"]
    if sp is not None and risk:
        out.append(chk("Risk", "Spread vs stop", f"{g(sp)} = {sp / risk:.0%} of {g(risk)}", f"≤ {msr:.0%}", sp <= msr * risk))
    else:
        out.append(chk("Risk", "Spread vs stop", "not recorded (order older than the checklist)", f"≤ {msr:.0%}", None))
    if gap is not None and risk:
        out.append(chk("Risk", "Broker stops level", f"stop {g(risk)} vs level {g(gap)}", "the stop outside it", risk > gap))
    marks: List[Dict] = []
    if ta is not None and z.get("top") is not None:
        marks.append({"type": "box", "label": f"{z['side']} zone · candle A", "t0": ta, "t1": None, "top": z["top"],
                      "bottom": z["bottom"], "color": ZONE_D if buy else ZONE_S})
    if fv and bars is not None and z.get("a") is not None:
        marks.append({"type": "box", "label": "FVG (A-B-C)", "t0": t(z["a"]), "t1": t(min(z["a"] + 3, len(bars) - 1)),
                      "top": fv["top"], "bottom": fv["bottom"], "color": "245,197,66"})
    if z.get("bos_level") is not None and bars is not None:
        marks.append({"type": "line", "label": "BOS level", "price": z["bos_level"], "t0": t(z.get("level_idx")), "t1": tb,
                      "color": "#4fc3f7", "dash": [4, 3]})
    if tb is not None:
        marks.append({"type": "vline", "label": "BOS", "t": tb, "color": "#4fc3f7"})
    for i, x in enumerate(tg):
        marks.append({"type": "line", "label": f"T{i + 1} (Fib {x['fib']}) when placed", "price": x["price"], "t0": tb, "t1": None,
                      "color": "#26c6da", "dash": [2, 4]})
    return {"checks": out, "marks": marks, "tf": "M15"}
