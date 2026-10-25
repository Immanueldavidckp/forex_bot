"""
engine/filters.py — the structure-quality filter layer (David 2026-10-25): eight hard gates checked right before
any order, on top of the V5 checks, because the engine marked too many BOS / FVG setups in ranging markets.
Pure functions on bars, like strategy.py. Book calls them only while enabled(): Book.plan takes the Gate 6 stop
and target from plan_levels(), Book.signal runs evaluate() and refuses at the first gate that fails.

  G1 swing     the swing the break closed through is significant: SWING_LEFT / SWING_RIGHT fractal whose leg from
               the previous significant swing is ≥ 1 ATR (significant_swings); a smaller pivot is not structure
  G2 break     body close beyond it; the breaking move (1-3 candles) ranges ≥ 1.5 ATR and leaves an FVG ≥ 0.3 ATR;
               the entry FVG untraded until the entry attempt. A break that fails is "drift", not BOS
  G3 regime    the setup timeframe's last significant high and low agree with the side (HH + HL / LH + LL); the
               last 4 significant swings inside a band < 3 ATR = RANGE. RANGE or no trend → no trade
  G4 bias      H4 and H1 bias = the break's side, M30 not against the H4 bias; a counter-bias break is a CHoCH
               candidate: logged, never traded
  G5 location  the impulse starts in the discount (buy) / premium (sell) half of the current H4 leg, from a zone
               price has not been back in; the nearest opposing structure ≥ 3 × the stop distance away
  G6 stop / RR S&D H4 on M15: SL beyond the M15 swing that started the break + spread + 0.25 × ATR(M15) (never the
               H4 stop); stop distance ≥ stops level, ≥ 3 × spread, ≤ 3 × ATR(M15); TP = the nearest opposing
               structure, RR ≥ 3 after the SL is final, never stretched; SL / TP on the tick size, right order
  G7 expiry    price back in the FVG within 12 M15 candles of the setup forming; no CHoCH against it before the
               fill; one trade per H4 zone; no new trade on a zone that already lost
  G8 market    ATR(M15) ≥ its 30th percentile of 200 bars; spread ≤ 1.5 × the 20-bar average; inside the symbol's
               sessions (forex: London + New York; crypto: 24/7)

Every decision is one record: a boolean per gate, the values, the first gate that rejected it →
engine_data/filters/candidates-YYYY-MM-DD.jsonl (IST date). Thresholds: config.FILTERS.
"""
from __future__ import annotations

import bisect
import datetime as _dt
import json
import math
import os
from typing import Callable, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from . import strategy as V
from . import tools
from .config import ENGINE, FILTERS as F, STRUCTURE_FILTERS_ENABLED, load_control

GATES = {"G1": "swing", "G2": "break", "G3": "regime", "G4": "bias", "G5": "location", "G6": "stop/RR",
         "G7": "expiry/zone", "G8": "market"}
IST = _dt.timezone(_dt.timedelta(hours=5, minutes=30), "IST")
FORCE: Optional[bool] = None                    # tests / the replay: on or off regardless of config and control.json
SINK: Optional[Callable[[Dict], None]] = None   # tests / the replay collect the records here instead of the file


def enabled() -> bool:
    if FORCE is not None:
        return FORCE
    c = load_control().get("structure_filters")
    return STRUCTURE_FILTERS_ENABLED if c is None else bool(c)


def is_sdh4(rec: Dict) -> bool:
    """An S&D H4 entry on M15: a break inside an H4 zone (its own S&D H4 setup or an M15 setup marked with the zone)."""
    return bool(rec.get("parent")) and rec.get("tf") == ENGINE["sdh4"]["confirm_tf"]


# ── helpers ─────────────────────────────────────────────────────────────────

def atrs(bars: List[Dict]) -> List[Optional[float]]:
    """ATR(ATR_PERIOD) per bar, from the bars up to it (None while warming up)."""
    return tools.atr_series(bars, int(F["ATR_PERIOD"]))


def at(bars: List[Dict], t: int) -> Optional[int]:
    """Index of the bar starting at t."""
    i = bisect.bisect_left([b["t"] for b in bars], t)
    return i if i < len(bars) and bars[i]["t"] == t else None


def bar_spread(b: Dict, point: float) -> float:
    """A bar's spread in price: the replay's "sp" (price) or the live feed's "spread" (points)."""
    if b.get("sp") is not None:
        return float(b["sp"])
    return float(b.get("spread") or 0) * point


def round_tick(x: float, tick: float, up: bool) -> float:
    """x on the symbol's tick grid, rounded up or down (a stop away from the entry, a target toward it)."""
    if not tick:
        return x
    k = math.ceil(x / tick - 1e-9) if up else math.floor(x / tick + 1e-9)
    return round(k * tick, len(f"{tick:.10f}".rstrip("0").split(".")[1]))


def significant_swings(bars: List[Dict], a: Optional[List[Optional[float]]] = None) -> List[Dict]:
    """Gate 1: SWING_LEFT / SWING_RIGHT fractals, kept only when the leg from the last significant swing of the other
    kind is ≥ SWING_MIN_LEG_ATR × the ATR at the swing. A fractal beyond the last significant swing of its own kind
    (no significant swing between) replaces it: the structure extended; one short of it is ignored, so a structure
    point ends only with a significant swing, never with a wick. Each gets leg, leg_atr and label HH / LH / HL / LL."""
    a = a if a is not None else atrs(bars)
    out: List[Dict] = []
    for s in tools.swing_points(bars, int(F["SWING_LEFT"]), int(F["SWING_RIGHT"])):
        s = dict(s)
        if not out:
            out.append(s)
            continue
        last = out[-1]
        if s["kind"] == last["kind"]:
            if (s["price"] > last["price"]) if s["kind"] == "high" else (s["price"] < last["price"]):
                out[-1] = s
            continue
        atr = a[s["idx"]] if s["idx"] < len(a) else None
        if atr and abs(s["price"] - last["price"]) >= float(F["SWING_MIN_LEG_ATR"]) * atr:
            out.append(s)
    prev: Dict[str, Optional[Dict]] = {"high": None, "low": None}
    for i, s in enumerate(out):
        atr = a[s["idx"]] if s["idx"] < len(a) else None
        s["leg"] = abs(s["price"] - out[i - 1]["price"]) if i else None
        s["leg_atr"] = round(s["leg"] / atr, 2) if s["leg"] is not None and atr else None
        p = prev[s["kind"]]
        s["label"] = (("H" if s["kind"] == "high" else "L") if p is None else
                      ("HH" if s["price"] > p["price"] else "LH") if s["kind"] == "high" else ("HL" if s["price"] > p["price"] else "LL"))
        prev[s["kind"]] = s
    return out


def opposing_levels(side: str, entry: float, series: List[Tuple[str, List[Dict]]]) -> List[Tuple[float, str]]:
    """Structure in the trade's way: significant swing lows (sell) / highs (buy) beyond the entry that price has not
    traded through since they formed, on each named timeframe."""
    kind = "low" if side == "sell" else "high"
    out = []
    for name, bars in series:
        for s in significant_swings(bars):
            if s["kind"] != kind or (s["price"] >= entry if side == "sell" else s["price"] <= entry):
                continue
            if any(b["l"] < s["price"] if kind == "low" else b["h"] > s["price"] for b in bars[s["idx"] + 1:]):
                continue
            out.append((s["price"], f"{name} {s['label']}"))
    return out


# ── Gate 6: the stop and the target (Book.plan uses these while the layer is on) ──

def plan_levels(rec: Dict, entry: float, spread: float, info: Dict, series: List[Tuple[str, List[Dict]]],
                m15: List[Dict]) -> Dict:
    """S&D H4 on M15: SL beyond the M15 swing that started the break (the move's origin) + spread + SL_ATR_BUFFER ×
    ATR(14, M15). Every other entry keeps its V5 stop (its own zone + sl_buffer_points). TP = the nearest opposing
    structure (not the first one at ≥ 3R: a nearer one is in the way). SL rounded away from the entry, TP toward it.
    → {stop, target {price, label, rr, min_rr_price}, stop_rule}"""
    side, sell = rec["side"], rec["side"] == "sell"
    point = float(info["point"])
    tick = float(info.get("trade_tick_size") or point)
    if is_sdh4(rec):
        a15 = V.sl_atr(m15) or 0.0
        o = rec["bos"]["origin"]["price"]
        buf = spread + float(F["SL_ATR_BUFFER"]) * a15
        stop = o + buf if sell else o - buf
        rule = f"M15 swing {o:g} that started the break + spread {spread:g} + {F['SL_ATR_BUFFER']:g} × ATR {a15:g}"
    else:
        stop = V.stop_price(rec, point)
        rule = f"this setup's zone {rec['invalidation']:g} + {V.S['sl_buffer_points']} points (V5)"
    stop = round_tick(stop, tick, up=sell)
    risk = abs(entry - stop)
    lv = opposing_levels(side, entry, series)
    need = entry - float(F["MIN_RR"]) * risk if sell else entry + float(F["MIN_RR"]) * risk
    if not lv:
        return {"stop": stop, "stop_rule": rule,
                "target": {"price": None, "label": "no opposing structure to aim at", "rr": None, "min_rr_price": need}}
    p, label = min(lv, key=lambda v: abs(v[0] - entry))
    tp = round_tick(p, tick, up=sell)
    return {"stop": stop, "stop_rule": rule,
            "target": {"price": tp, "label": f"nearest: {label}", "rr": round(abs(tp - entry) / risk, 2) if risk else None,
                       "min_rr_price": need}}


def stop_checks(side: str, entry: float, stop: float, tgt: Dict, spread: float, stops_level: float,
                atr15: Optional[float]) -> Tuple[bool, Optional[str], Optional[float]]:
    """Gate 6 on a final SL and target: SL > entry > TP (sell) / SL < entry < TP (buy); stop distance ≥ the broker's
    stops level, ≥ SL_MIN_SPREAD_X × spread, ≤ SL_MAX_ATR × ATR(14, M15); a target; RR ≥ MIN_RR.
    → (ok, the first reason it fails, RR)"""
    sell = side == "sell"
    tp = (tgt or {}).get("price")
    dist = abs(entry - stop)
    rr = abs(tp - entry) / dist if tp is not None and dist else None
    checks = [
        (sell and stop > entry and (tp is None or tp < entry) or not sell and stop < entry and (tp is None or tp > entry),
         f"levels out of order: {'SL > entry > TP' if sell else 'SL < entry < TP'} needed (SL {stop:g}, entry {entry:g}, TP {tp})"),
        (dist >= stops_level, f"stop distance {dist:g} < the broker's stops level {stops_level:g}"),
        (dist >= float(F["SL_MIN_SPREAD_X"]) * spread, f"stop distance {dist:g} < {F['SL_MIN_SPREAD_X']:g} × spread {spread:g}"),
        (bool(atr15) and dist <= float(F["SL_MAX_ATR"]) * atr15,
         f"stop distance {dist:g} = {dist / atr15 if atr15 else 0:.1f} ATR(M15) {atr15} (max {F['SL_MAX_ATR']:g})"),
        (tp is not None, (tgt or {}).get("label") or "no target"),
        (rr is not None and rr >= float(F["MIN_RR"]) - 1e-9, f"RR {rr or 0:.2f} to the nearest structure {tp} (need {F['MIN_RR']:g})"),
    ]
    return all(ok for ok, _ in checks), next((m for ok, m in checks if not ok), None), rr


# ── the gates ───────────────────────────────────────────────────────────────

def _pctl(vals: List[float], p: float) -> Optional[float]:
    v = sorted(vals)
    return v[int(round(p / 100 * (len(v) - 1)))] if v else None


def market_regime(sig: List[Dict], atr: Optional[float]) -> Tuple[str, Optional[float]]:
    """Gate 3 from the significant swings: RANGE when the last RANGE_SWINGS of them sit inside a band narrower than
    RANGE_BAND_ATR × ATR; else UP (last two highs and lows: HH + HL), DOWN (LH + LL) or NO TREND. → (regime, band in ATR)"""
    hs = [s for s in sig if s["kind"] == "high"][-2:]
    ls = [s for s in sig if s["kind"] == "low"][-2:]
    last = sig[-int(F["RANGE_SWINGS"]):]
    band = max(s["price"] for s in last) - min(s["price"] for s in last) if len(last) == int(F["RANGE_SWINGS"]) else None
    up = len(hs) == 2 and len(ls) == 2 and hs[1]["price"] > hs[0]["price"] and ls[1]["price"] > ls[0]["price"]
    dn = len(hs) == 2 and len(ls) == 2 and hs[1]["price"] < hs[0]["price"] and ls[1]["price"] < ls[0]["price"]
    band_atr = round(band / atr, 2) if band is not None and atr else None
    if band_atr is not None and band_atr < float(F["RANGE_BAND_ATR"]):
        return "RANGE", band_atr
    return ("UP" if up else "DOWN" if dn else "NO TREND"), band_atr


def session_open(symbol: str, market: str, now: int) -> Tuple[bool, str]:
    allowed = F["SYMBOL_SESSIONS"].get(symbol) or F["SYMBOL_SESSIONS"].get(market) or "24/7"
    if allowed == "24/7":
        return True, "24/7"
    open_ = []
    for name in allowed:
        tz, a, b = F["SESSIONS"][name]
        loc = _dt.datetime.fromtimestamp(now / 1000, ZoneInfo(tz))
        if loc.weekday() < 5 and a <= loc.strftime("%H:%M") < b:
            open_.append(name)
    return bool(open_), "+".join(open_) or f"closed (trades {'+'.join(allowed)})"


def evaluate(rec: Dict, ctx: Dict) -> Dict:
    """Every gate for one setup at its entry attempt, none skipped (so the log shows which gates do the work).
    ctx: now (ms), entry, bid, ask, info, market, bars {setup tf, "M15", "M30", "H1", "H4": completed bars},
    bias (strategy.trade_bias), plan (Book.plan with the Gate 6 stop / target), zones (the trades taken before:
    [{id, parent, side, top, bottom, lost}]), lots, money_per_move, equity.
    → {gates {G1..G8: bool}, why {gate: reason}, first_fail, break, values, ...} (the record, minus Book's fields)"""
    side, sell, tf = rec["side"], rec["side"] == "sell", rec["tf"]
    bars = ctx["bars"][tf]
    info, now = ctx["info"], ctx["now"]
    point = float(info["point"])
    entry, bid, ask = ctx["entry"], ctx["bid"], ctx["ask"]
    spread = max(0.0, ask - bid)
    a = atrs(bars)
    bos = rec["bos"]
    beyond = (lambda p, lvl: p > lvl) if not sell else (lambda p, lvl: p < lvl)
    g: Dict[str, bool] = {}
    why: Dict[str, str] = {}
    val: Dict = {"atr": a[-1] if a else None}

    # G1 swing significance: the last significant swing before the break bar is the one closed through
    x = at(bars, bos["t"])
    ref = None
    if x is None or x < 20:
        g["G1"], why["G1"] = False, f"the {tf} break bar is outside the {len(bars)} bars read"
    else:
        sig = significant_swings(bars[:x], a[:x])
        ref = next((s for s in reversed(sig) if s["kind"] == ("low" if sell else "high")), None)
        if ref is None:
            g["G1"], why["G1"] = False, "no significant swing to break"
        else:
            val.update(swing_level=ref["price"], swing_label=ref["label"], swing_leg=ref["leg"], swing_leg_atr=ref["leg_atr"],
                       engine_level=bos["level"])
            early = next((b for b in bars[ref["idx"] + 1:x] if beyond(b["c"], ref["price"])), None)
            if ref["leg"] is None:
                g["G1"], why["G1"] = False, "the last significant swing has no earlier swing to measure its leg"
            elif early is not None:
                g["G1"], why["G1"] = False, f"the significant {ref['kind']} {ref['price']:g} was closed through before this break: it broke a minor pivot"
            elif not beyond(bars[x]["c"], ref["price"]):
                g["G1"], why["G1"] = False, (f"the break closed {bars[x]['c']:g} through a minor pivot {bos['level']:g}, not the significant "
                                             f"{ref['kind']} {ref['price']:g} (leg {ref['leg_atr']} ATR)")
            else:
                g["G1"] = True

    # G2 break quality: body close beyond, displacement ≥ 1.5 ATR in 1-3 candles leaving an FVG ≥ 0.3 ATR, entry FVG fresh
    if x is None or x < 20:
        g["G2"], why["G2"] = False, "no break bar"
    else:
        a0 = a[x - 1] or a[x]
        lvl = ref["price"] if ref else bos["level"]
        close_ok = beyond(bars[x]["c"], lvl)
        k_ok, best = None, 0.0
        for k in range(1, int(F["DISPLACEMENT_MAX_CANDLES"]) + 1):
            seg = bars[x - k + 1:x + 1]
            rng = max(b["h"] for b in seg) - min(b["l"] for b in seg)
            net = (seg[-1]["c"] - seg[0]["o"]) * (-1 if sell else 1)
            best = max(best, rng / a0 if a0 else 0.0)
            if net > 0 and a0 and rng >= float(F["DISPLACEMENT_MIN_ATR"]) * a0:
                k_ok = k                                  # the longest 1-3 candle window that is a displacement
        span = k_ok or int(F["DISPLACEMENT_MAX_CANDLES"])
        gap = 0.0
        for c2 in range(max(1, x - span + 1), min(x, len(bars) - 2) + 1):
            g_ = (bars[c2 - 1]["l"] - bars[c2 + 1]["h"]) if sell else (bars[c2 + 1]["l"] - bars[c2 - 1]["h"])
            gap = max(gap, g_)
        fvg_ok = bool(a0) and gap >= float(F["FVG_MIN_ATR"]) * a0
        f = rec.get("fvg") or {}
        c2 = at(bars, f["t"]) if f else None
        fresh = c2 is not None and not any((b["h"] > f["top"]) if sell else (b["l"] < f["bottom"]) for b in bars[c2 + 2:])
        val.update(disp_atr=round(best, 2), disp_candles=k_ok, disp_fvg_atr=round(gap / a0, 2) if a0 else None, fvg_fresh=fresh)
        g["G2"] = close_ok and bool(k_ok) and fvg_ok and fresh
        if not g["G2"]:
            why["G2"] = "drift: " + "; ".join(m for ok, m in (
                (close_ok, f"no body close beyond {lvl:g}"),
                (bool(k_ok), f"the break moved {best:.2f} ATR in 1-{F['DISPLACEMENT_MAX_CANDLES']} candles (need {F['DISPLACEMENT_MIN_ATR']:g})"),
                (fvg_ok, f"its FVG is {gap / a0 if a0 else 0:.2f} ATR (need {F['FVG_MIN_ATR']:g})"),
                (fresh, "the entry FVG was traded through before the entry")) if not ok)
    val["break"] = (bos.get("kind") or "BOS") if g.get("G1") and g.get("G2") else "drift"

    # G3 regime on the setup's timeframe
    sig_now = significant_swings(bars, a)
    regime, band_atr = market_regime(sig_now, a[-1] if a else None)
    val.update(regime=regime, band_atr=band_atr, structure=" ".join(s["label"] for s in sig_now[-4:]))
    g["G3"] = regime == ("DOWN" if sell else "UP")
    if not g["G3"]:
        why["G3"] = (f"{tf} RANGE: last {F['RANGE_SWINGS']} significant swings inside {val['band_atr']} ATR (< {F['RANGE_BAND_ATR']:g})"
                     if regime == "RANGE" else f"{tf} {regime} ({val['structure']}), the trade is a {side}")

    # G4 bias: H4 and H1 with the side, M30 not against H4
    b = ctx["bias"]
    b4, b1 = (b.get("h4") or {}).get("bias"), (b.get("h1") or {}).get("bias")
    m30 = V.bias(ctx["bars"][F["NOT_AGAINST_TF"]], F["NOT_AGAINST_TF"])["bias"] if ctx["bars"].get(F["NOT_AGAINST_TF"]) else None
    val.update(bias_h4=b4, bias_h1=b1, trend_m30=m30)
    with_bias = b4 == side and b1 == side
    g["G4"] = with_bias and not (m30 and m30 != b4)
    if not with_bias:
        why["G4"] = f"counter-bias (H4 {b4 or 'none'}, H1 {b1 or 'none'}): a CHoCH candidate, logged, never traded"
    elif not g["G4"]:
        why["G4"] = f"M30 is {m30}, against the H4 {b4}"

    # G6 first (G5 needs its stop distance): the plan's stop and nearest target
    p = ctx["plan"]
    stop, tgt = p["stop"], p.get("target") or {}
    tp = tgt.get("price")
    dist = abs(entry - stop)
    a15 = V.sl_atr(ctx["bars"]["M15"])
    lvl_min = float(info.get("trade_stops_level") or 0) * point
    ok6, why6, rr = stop_checks(side, entry, stop, tgt, spread, lvl_min, a15)
    val.update(stop=stop, stop_rule=p.get("stop_rule"), stop_dist=dist, stop_atr15=round(dist / a15, 2) if a15 else None,
               atr15=a15, spread=spread, stops_level=lvl_min, tp=tp, tp_label=tgt.get("label"), rr=round(rr, 2) if rr else None)
    g["G6"] = ok6
    if not ok6:
        why["G6"] = why6

    # G5 location: discount / premium of the current H4 leg, fresh zone, room to the nearest structure
    h4 = ctx["bars"][F["LOCATION_TF"]]
    s4 = significant_swings(h4)
    H = next((s for s in reversed(s4) if s["kind"] == "high"), None)
    L = next((s for s in reversed(s4) if s["kind"] == "low"), None)
    pos = None
    if H and L:
        after = h4[max(H["idx"], L["idx"]) + 1:]
        hi = max([H["price"]] + [x_["h"] for x_ in after])
        lo = min([L["price"]] + [x_["l"] for x_ in after])
        pos = (bos["origin"]["price"] - lo) / (hi - lo) if hi > lo else None
        val.update(h4_leg=[lo, hi])
    pd_ok = pos is not None and (pos >= float(F["PD_SPLIT"]) if sell else pos <= float(F["PD_SPLIT"]))
    poi = rec.get("poi") or {}
    z = rec.get("zone") or {}
    z0 = at(bars, (z.get("displacement") or {}).get("t") or 0) if z else None
    if z0 is None and poi.get("t"):
        z0 = (at(bars, poi["t"]) or 0) + 2                     # mitigation block: the pattern ends 2 bars after it
    zone_fresh = z0 is not None and not any((b_["h"] >= poi["bottom"]) if sell else (b_["l"] <= poi["top"]) for b_ in bars[z0 + 1:])
    room = abs(tp - entry) / dist if tp is not None and dist else None
    room_ok = tp is None or (room is not None and room >= float(F["MIN_ROOM_R"]) - 1e-9)
    val.update(pd_pos=round(pos, 3) if pos is not None else None, zone_fresh=zone_fresh, room_r=round(room, 2) if room else None)
    g["G5"] = pd_ok and zone_fresh and room_ok
    if not g["G5"]:
        why["G5"] = "; ".join(m for ok, m in (
            (pd_ok, f"the impulse starts at {pos:.0%} of the H4 leg (needs the {'premium' if sell else 'discount'} half)" if pos is not None
             else "no H4 leg to measure premium / discount"),
            (zone_fresh, "price was back in the zone before the entry"),
            (room_ok, f"only {room or 0:.2f} × the stop to the nearest structure: the move is mostly done")) if not ok)

    # G7 expiry, CHoCH against before the fill, one trade per H4 zone, no re-entry after a loss
    tf_ms = int(bars[1]["t"] - bars[0]["t"]) if len(bars) > 1 else 900_000
    touch = rec.get("touch_t") or now
    waited = (touch - (rec["formed_t"] + tf_ms)) / 900_000
    expired = waited > int(F["SETUP_EXPIRY_M15_BARS"])
    against = None
    if x is not None:
        for s in sig_now:
            if s["idx"] <= x or s["kind"] != ("high" if sell else "low"):
                continue
            hit = next((b_ for b_ in bars[s["idx"] + int(F["SWING_RIGHT"]) + 1:] if (b_["c"] > s["price"] if sell else b_["c"] < s["price"])), None)
            if hit:
                against = {"level": s["price"], "t": hit["t"]}
                break
    zones = ctx.get("zones") or []
    par = rec.get("parent")
    same_zone = next((z_ for z_ in zones if par and z_.get("parent") == par and z_["id"] != rec["id"]), None) \
        if F["ONE_TRADE_PER_H4_ZONE"] else None
    lost = next((z_ for z_ in zones if z_.get("lost") and z_["side"] == side and z_["id"] != rec["id"] and poi
                 and z_["bottom"] <= poi["top"] and poi["bottom"] <= z_["top"]), None) if F["NO_REENTRY_AFTER_LOSS"] else None
    val.update(waited_m15=round(waited, 1), choch_against=against)
    g["G7"] = not expired and against is None and same_zone is None and lost is None
    if not g["G7"]:
        why["G7"] = "; ".join(m for bad, m in (
            (expired, f"expired: price came back {waited:.0f} M15 candles after the setup formed (max {F['SETUP_EXPIRY_M15_BARS']})"),
            (against is not None, f"cancelled: a CHoCH against it closed through {(against or {}).get('level')} before the fill"),
            (same_zone is not None, f"one trade per H4 zone: {(same_zone or {}).get('id')} already traded it"),
            (lost is not None, f"no re-entry: {(lost or {}).get('id')} lost on this zone")) if bad)

    # G8 volatility, spread, session
    m15 = ctx["bars"]["M15"]
    a15s = [v for v in atrs(m15)[-int(F["ATR_PCTL_BARS"]):] if v]
    p30 = _pctl(a15s, float(F["ATR_MIN_PCTL"]))
    vol_ok = bool(a15s) and a15s[-1] >= p30
    sps = [bar_spread(b_, point) for b_ in m15[-int(F["SPREAD_AVG_BARS"]):]]
    avg_sp = sum(sps) / len(sps) if sps else 0.0
    sp_ok = avg_sp <= 0 or spread <= float(F["SPREAD_MAX_X_AVG"]) * avg_sp     # BITCOIN / ETHEREUM quote no spread
    sess_ok, sess = session_open(rec.get("symbol", ""), ctx.get("market") or "", now)
    val.update(atr15_pctl_value=p30, atr15_now=a15s[-1] if a15s else None, spread_avg=avg_sp,
               spread_x_avg=round(spread / avg_sp, 2) if avg_sp > 0 else None, session=sess)
    g["G8"] = vol_ok and sp_ok and sess_ok
    if not g["G8"]:
        why["G8"] = "; ".join(m for ok, m in (
            (vol_ok, f"ATR(M15) {a15s[-1] if a15s else 0:g} below its {F['ATR_MIN_PCTL']}th percentile {p30} of {len(a15s)} bars"),
            (sp_ok, f"spread {spread:g} > {F['SPREAD_MAX_X_AVG']:g} × the {F['SPREAD_AVG_BARS']}-bar average {avg_sp:g}"),
            (sess_ok, f"session {sess}")) if not ok)

    order = ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"]
    first = next((k for k in order if not g[k]), None)
    lots, mpm, eq = ctx.get("lots") or 0.0, ctx.get("money_per_move") or 0.0, ctx.get("equity") or 0.0
    risk_usd = dist * mpm * lots
    return {"at": _dt.datetime.fromtimestamp(now / 1000, _dt.timezone.utc).isoformat(timespec="seconds"), "t": now,
            "id": rec["id"], "symbol": rec.get("symbol"), "market": ctx.get("market"), "tf": tf, "entry_type": rec.get("entry_type"),
            "parent": rec.get("parent"), "side": side, "bos_kind": bos.get("kind"), "break": val["break"],
            "gates": {k: g[k] for k in order}, "first_fail": first, "fails": [k for k in order if not g[k]],
            "why": {k: why[k] for k in order if k in why}, "values": val,
            "entry": entry, "stop": stop, "tp": tp, "rr": val["rr"], "lots": lots, "risk_usd": round(risk_usd, 2),
            "risk_pct": round(100 * risk_usd / eq, 6) if eq else None}


def write(rec: Dict) -> None:
    """Append a decision record to the day's file (IST date of the decision)."""
    if SINK is not None:
        SINK(rec)
        return
    os.makedirs(F["LOG_DIR"], exist_ok=True)
    day = _dt.datetime.fromtimestamp(rec["t"] / 1000, IST).strftime("%Y-%m-%d")
    with open(os.path.join(F["LOG_DIR"], f"candidates-{day}.jsonl"), "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")
