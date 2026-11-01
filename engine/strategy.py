"""
engine/strategy.py — "MT5 EA — COMPLETE FINAL STRATEGY LOGIC V5" on bars. Pure functions: no MT5, no
state, no clock; every function returns what the dashboard draws, so the chart shows exactly what the
engine decided and why. Bars are completed bars only (feed.completed), oldest first.

  bias(bars, tf)              §2   HH+HL → buy, LH+LL → sell, otherwise no trade
  trade_bias(h4, h1)               David 2026-10-25: a trade needs the H4 and the H1 bias to agree
  structure(bars)                  BOS / CHoCH on any timeframe, by candle close (David 2026-10-24)
  bos_setups(bars, structure)      after each BOS, in the move that made it: supply / demand (§3-4) or,
                                   with none, the mitigation block (§6); its FVGs (the 2nd of several);
                                   the entry 10 % inside that FVG; invalidation = the setup's own zone
  sdh4_setups(h4 setup, m15, st)   S&D H4 (David 2026-10-25): price back at an H4 setup → an M15 BOS / CHoCH
                                   the same way from inside the H4 zone → that M15 move's own setup
  pullback(setup, bars)            the first bar that comes back to the entry
  final_target(...)           §18-19 the first untouched opposite structure level at ≥ 1:3, else no target
  pretrade(...)                    David's SL/TP fix: every check right before an order (one setup only)
  strength(m5, ...)           §13-14 weak / moderate / strong from body size, persistence and travel
  layer_price(...)            §12-13 one dynamic layer between the entry and the stop
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from . import tools
from .config import STRATEGY as S

def _body(b: Dict) -> float:
    return abs(b["c"] - b["o"])


def _up(b: Dict) -> bool:
    return b["c"] > b["o"]


def _down(b: Dict) -> bool:
    return b["c"] < b["o"]


def swings(bars: List[Dict], n: Optional[int] = None) -> List[Dict]:
    """Confirmed fractal swings (n bars each side, V5 Swing_Length = 2), labelled HH / LH / HL / LL."""
    n = n or int(S["swing_length"])
    return tools.label_swings(tools.swing_points(bars, n, n))


# ── §2 market bias (H1, and David 2026-10-25: H4 too) ───────────────────────

def bias(h1: List[Dict], tf: str = "H1") -> Dict:
    sw = swings(h1)
    highs, lows = [s for s in sw if s["kind"] == "high"], [s for s in sw if s["kind"] == "low"]
    out = {"bias": None, "swings": [{k: s[k] for k in ("t", "price", "kind", "label")} for s in sw[-10:]]}
    if len(highs) < 2 or len(lows) < 2:
        return {**out, "why": f"not enough {tf} swings yet"}
    h_prev, h_last, l_prev, l_last = highs[-2], highs[-1], lows[-2], lows[-1]
    close = h1[-1]["c"]
    if h_last["price"] > h_prev["price"] and l_last["price"] > l_prev["price"]:
        if close < l_last["price"]:
            return {**out, "why": f"HH+HL, but {tf} closed {close:g} below the last HL {l_last['price']:g}: structure broken"}
        return {**out, "bias": "buy", "why": f"HH {h_last['price']:g} > {h_prev['price']:g} and HL {l_last['price']:g} > {l_prev['price']:g}"}
    if h_last["price"] < h_prev["price"] and l_last["price"] < l_prev["price"]:
        if close > h_last["price"]:
            return {**out, "why": f"LH+LL, but {tf} closed {close:g} above the last LH {h_last['price']:g}: structure broken"}
        return {**out, "bias": "sell", "why": f"LH {h_last['price']:g} < {h_prev['price']:g} and LL {l_last['price']:g} < {l_prev['price']:g}"}
    hk = "HH" if h_last["price"] > h_prev["price"] else "LH"
    lk = "HL" if l_last["price"] > l_prev["price"] else "LL"
    return {**out, "why": f"unclear: {hk} with {lk}"}


def trade_bias(h4: List[Dict], h1: List[Dict]) -> Dict:
    """David 2026-10-25: the H4 and the H1 bias must agree (both HH+HL → buy, both LH+LL → sell), else no trade.
    → {bias, why, h4: bias(h4), h1: bias(h1), swings: the H1 swings}"""
    b4, b1 = bias(h4, "H4"), bias(h1, "H1")
    side = b1["bias"] if b1["bias"] and b1["bias"] == b4["bias"] else None
    word = lambda b: (b["bias"] or "none").upper()
    why = f"H4 and H1 {word(b1)}" if side else f"H4 {word(b4)} / H1 {word(b1)}: they must agree"
    return {"bias": side, "why": why, "h4": b4, "h1": b1, "swings": b1["swings"]}


def trend_label(bars: List[Dict]) -> Dict:
    """The same reading on any timeframe (H4 / M30 context on the charts)."""
    b = bias(bars)
    return {"trend": {"buy": "bullish", "sell": "bearish"}.get(b["bias"], "unclear"), "why": b.get("why"), "swings": b["swings"]}


# ── BOS on any timeframe (David 2026-10-24: "BOS is the key") ───────────────

def structure(bars: List[Dict], n: Optional[int] = None, window: Optional[int] = None) -> Dict:
    """Breaks by candle CLOSE (a wick through is not a break). Reworked 2026-10-26 from David's learning-chart
    labels (EURUSD M15 / GBPUSD H1 — the old swing-label kinds matched 10 of his 18 lines, this 15):
      with the trend      every broken swing is a BOS (an HL / LH broken while the bias already points that
                          way is the trend going on, not a change — David drew those as BOS)
      against the trend   only MAJOR structure turns it: the last major swing (major_swing_length bars each
                          side) formed before the current leg extreme. A close beyond it is the turn — BOS /
                          CHoCH by that major swing's own HH/LL vs LH/HL label, drawn at the major level.
                          A retrace poking through minor swings is NOT an event: those levels are just spent
                          (the old code flipped its bias there and pruned the real BOS levels, so David's
                          lines at 1.12684 / 1.15744 / 1.11882 had no engine event at all).
    Minor swings stay breakable until a close goes through them; when one close breaks several, the event is
    the most recent HH / LL among them (else the most recent). Each break carries the move that made it: from
    the lowest low (buy) / highest high (sell) since that swing → the break candle; minor swings of the other
    side older than that move's start are dropped (they belong to the old structure). Without a major swing
    yet (short series), an against-trend break falls back to the old rule: kind from the minor swing's label.
    window (backtest only): a swing more than `window` bars old stops being breakable, as when the live engine
    reads only its last ENGINE["bars"][tf] bars; None = the whole list (live).
    → {trend: up|down|None (last two swing highs and lows), events, swings, bos_level, choch_level}"""
    sw = swings(bars, n)
    nn = n or int(S["swing_length"])
    mj = swings(bars, max(int(S.get("major_swing_length", 4)), nn + 1)) if len(bars) > 2 * nn + 3 else []
    by_conf: Dict[int, List[Dict]] = {}
    for s in sw:
        by_conf.setdefault(s["confirmed"], []).append(s)
    mj_conf: Dict[int, List[Dict]] = {}
    for s in mj:
        mj_conf.setdefault(s["confirmed"], []).append(s)
    alive: Dict[str, List[Dict]] = {"high": [], "low": []}
    majors: Dict[str, List[Dict]] = {"high": [], "low": []}
    events: List[Dict] = []
    bias: Optional[str] = None
    ext: Optional[Dict] = None            # the current leg's extreme since the bias last turned
    for x, b in enumerate(bars):
        if window and x % 16 == 0:
            for k in alive:
                alive[k] = [s for s in alive[k] if s["idx"] >= x - window]
                majors[k] = [s for s in majors[k] if s["idx"] >= x - window]
        for kind, side in (("high", "buy"), ("low", "sell")):
            hit = [s for s in alive[kind] if (b["c"] > s["price"] if side == "buy" else b["c"] < s["price"])]
            ref = None
            if bias is not None and side != bias:
                refs = [m for m in majors[kind] if ext is None or m["idx"] <= ext["idx"]]
                ref = refs[-1] if refs else None
            if ref is not None:
                if not (b["c"] > ref["price"] if side == "buy" else b["c"] < ref["price"]):
                    if hit:               # a retrace through minor levels only: spent, no event, no turn
                        alive[kind] = [s for s in alive[kind] if all(s is not h for h in hit)]
                    continue
                lv = ref
            else:
                if not hit:
                    continue
                lv = max([s for s in hit if s.get("label") in ("HH", "LL")] or hit, key=lambda s: s["idx"])   # the HH / LL wins
            alive[kind] = [s for s in alive[kind] if all(s is not h for h in hit)]
            rng = range(min(lv["idx"], x), x + 1)
            o = min(rng, key=lambda i: bars[i]["l"]) if side == "buy" else max(rng, key=lambda i: bars[i]["h"])
            other = "low" if side == "buy" else "high"   # the other side's swings from before this move: old structure
            alive[other] = [s for s in alive[other] if s["idx"] >= o]
            events.append({"kind": "BOS" if side == bias or lv.get("label") in ("HH", "LL") else "CHoCH", "side": side,
                           "level": lv["price"], "level_t": lv["t"], "level_idx": lv["idx"], "level_label": lv.get("label"),
                           "t": b["t"], "idx": x, "close": b["c"],
                           "origin": {"price": bars[o]["l" if side == "buy" else "h"], "t": bars[o]["t"], "idx": o}})
            if bias != side or ext is None:
                bias = side
                e_rng = range(o, x + 1)
                ei = max(e_rng, key=lambda i: bars[i]["h"]) if side == "buy" else min(e_rng, key=lambda i: bars[i]["l"])
                ext = {"idx": ei, "price": bars[ei]["h" if side == "buy" else "l"]}
        if ext is not None:               # the leg extreme runs with the trend (checked next bar on)
            if bias == "buy" and b["h"] >= ext["price"]:
                ext = {"idx": x, "price": b["h"]}
            elif bias == "sell" and b["l"] <= ext["price"]:
                ext = {"idx": x, "price": b["l"]}
        for s in by_conf.get(x, []):              # a swing confirmed by this bar counts from the next bar on
            alive[s["kind"]].append(s)
        for s in mj_conf.get(x, []):
            majors[s["kind"]].append(s)
    hs, ls = [s for s in sw if s["kind"] == "high"][-2:], [s for s in sw if s["kind"] == "low"][-2:]
    trend = None
    if len(hs) == 2 and len(ls) == 2:
        up, dn = hs[1]["price"] > hs[0]["price"] and ls[1]["price"] > ls[0]["price"], hs[1]["price"] < hs[0]["price"] and ls[1]["price"] < ls[0]["price"]
        trend = "up" if up else "down" if dn else None
    last_alive = lambda k: alive[k][-1] if alive[k] and alive[k][-1] is (hs if k == "high" else ls)[-1] else None
    return {"trend": trend, "events": events, "swings": sw,
            "bos_level": last_alive("high") if trend == "up" else last_alive("low") if trend == "down" else None,
            "choch_level": last_alive("low") if trend == "up" else last_alive("high") if trend == "down" else None}


# ── after the BOS: supply / demand (or the mitigation block), FVG, entry ────

def mitigation_block(bars: List[Dict], a: int, b: int, side: str) -> Optional[Dict]:
    """§6: SELL RED RED GREEN RED RED (the GREEN), BUY GREEN GREEN RED GREEN GREEN (the RED), in bars a..b."""
    for i in range(max(a, 2), min(b, len(bars) - 3) + 1):
        w = bars[i - 2:i + 3]
        if side == "sell" and _down(w[0]) and _down(w[1]) and _up(w[2]) and _down(w[3]) and _down(w[4]) or \
           side == "buy" and _up(w[0]) and _up(w[1]) and _down(w[2]) and _up(w[3]) and _up(w[4]):
            return {"kind": "MB", "t": bars[i]["t"], "idx": i, "top": bars[i]["h"], "bottom": bars[i]["l"]}
    return None


def _zone(bars: List[Dict], o: int, x: int, side: str) -> Optional[Dict]:
    """§3-4 at the start of the BOS move: its first displacement candle (body ≥ 1.5 × the average of the 10
    before) and the final opposite candle before it (within zone_lookback_bars)."""
    k = int(S["body_average_bars"])
    opposite = _down if side == "buy" else _up
    for d in range(max(o, k), x + 1):
        if not (_up(bars[d]) if side == "buy" else _down(bars[d])):
            continue
        avg = sum(_body(b) for b in bars[d - k:d]) / k
        if avg <= 0 or _body(bars[d]) < float(S["displacement_mult"]) * avg:
            continue
        j = next((i for i in range(d - 1, max(d - 1 - int(S["zone_lookback_bars"]), -1), -1) if opposite(bars[i])), None)
        if j is None:
            continue
        z = bars[j]
        return {"kind": "demand" if side == "buy" else "supply", "top": z["h"], "bottom": z["l"], "t": z["t"], "idx": j,
                "displacement": {"t": bars[d]["t"], "idx": d, "x": round(_body(bars[d]) / avg, 2)}}
    return None


def _fvgs(bars: List[Dict], o: int, end: int, side: str) -> List[Dict]:
    """Every FVG of the move (middle candle after its origin, up to and including `end`), left to right."""
    out = []
    for c2 in range(o + 1, min(end, len(bars) - 2) + 1):
        a, c = bars[c2 - 1], bars[c2 + 1]
        if side == "buy" and c["l"] > a["h"]:
            out.append({"top": c["l"], "bottom": a["h"], "t": bars[c2]["t"], "idx": c2})
        elif side == "sell" and c["h"] < a["l"]:
            out.append({"top": a["l"], "bottom": c["h"], "t": bars[c2]["t"], "idx": c2})
    return out


def fvg_untaken(bars: List[Dict], rec: Dict, touching: bool = False) -> Optional[str]:
    """David 2026-10-25 (COSMOS M30: the FVG was traded straight back through): after the entry FVG completes,
    the next fvg_protect_candles candles must not trade back into it, and price must run ≥ fvg_min_runoff_atr ×
    ATR(14, own TF) beyond it before the first retrace — a pullback earlier than either is an invalid structure.
    touching = price is at the entry right now (the forming bar), judged as the retrace.
    Returns why the structure is invalid, or None while it holds."""
    f, side = rec.get("fvg"), rec["side"]
    if not f:
        return None
    c3 = f["idx"] + 1                                  # the candle that completed the gap
    into = (lambda b: b["l"] < f["top"]) if side == "buy" else (lambda b: b["h"] > f["bottom"])
    k = int(S["fvg_protect_candles"])
    after = bars[c3 + 1:]
    for j, b in enumerate(after[:k]):
        if into(b):
            return f"the FVG was traded back into {j + 1} candle(s) after forming (must stay clear for {k})"
    if touching and len(after) < k:
        return f"the pullback came {len(after) + 1} candle(s) after the FVG (must stay clear for {k})"
    first = next((c3 + 1 + j for j, b in enumerate(after) if into(b)), None)
    if first is None and not touching:
        return None                                    # no retrace yet: nothing to judge
    n = int(S["sl_atr_period"])
    a = tools.atr(bars[max(0, c3 - 4 * n): c3 + 1], n)
    if not a:
        return None
    end = first if first is not None else len(bars)
    run = (max(b["h"] for b in bars[c3:end]) - f["top"]) if side == "buy" else (f["bottom"] - min(b["l"] for b in bars[c3:end]))
    if run < float(S["fvg_min_runoff_atr"]) * a - 1e-12:
        return f"price came back into the FVG after running only {run:g} = {run / a:.2f} ATR (need {S['fvg_min_runoff_atr']:g})"
    return None


def setup_for(bars: List[Dict], st: Dict, e: Dict, tf: str, symbol: str = "") -> Dict:
    """The setup of one break e (an event of structure(bars)): in the move that made it (its origin → the break
    candle) the supply / demand zone, or when there is none the mitigation block; the FVGs inside that move
    (required; with two or more the 2nd, counted left to right); the entry fvg_entry_depth (10 %) inside that
    FVG from the side price comes back from. The move's end (first swing after the break) is kept for the chart."""
    n = len(bars)
    side, o, x = e["side"], e["origin"]["idx"], e["idx"]
    hk = "h" if side == "buy" else "l"
    peak = next((s for s in st["swings"] if s["kind"] == ("high" if side == "buy" else "low") and s["idx"] >= x), None)
    end = peak["idx"] if peak else (max if side == "buy" else min)(range(x, n), key=lambda i: bars[i][hk])
    zone = _zone(bars, o, x, side)
    mb = None if zone else mitigation_block(bars, o, x, side)
    fvgs = _fvgs(bars, o, x, side)          # inside the BOS move: its start → the BOS candle
    rec = {"id": f"{symbol}-{tf}-{'D' if side == 'buy' else 'S'}-{e['t'] // 1000}", "symbol": symbol, "tf": tf, "side": side,
           "bos": e, "leg": {"origin": e["origin"], "end_t": bars[end]["t"], "end_idx": end, "running": peak is None},
           "zone": zone, "mb": mb, "fvgs": fvgs}
    if not (zone or mb) or not fvgs:
        return {**rec, "complete": False,
                "missing": "no supply/demand or mitigation block" if not (zone or mb) else "no FVG in the BOS move"}
    poi = zone or mb
    pick = len(fvgs) if S["fvg_pick"] == "nearest" else min(len(fvgs), int(S["fvg_pick"]))
    f = fvgs[pick - 1]                  # "nearest" = the last one: the first FVG a retrace reaches, both sides
    depth = float(S["fvg_entry_depth"]) * (f["top"] - f["bottom"])
    formed = min(n - 1, max(x, f["idx"] + 1))
    return {**rec, "complete": True, "kind": poi["kind"], "poi": poi, "fvg": f, "fvg_pick": pick,
            # new rules §15: all this displacement's FVGs are one associated cluster, one setup area
            "cluster": {"top": max(g["top"] for g in fvgs), "bottom": min(g["bottom"] for g in fvgs), "n": len(fvgs)},
            "entry": f["top"] - depth if side == "buy" else f["bottom"] + depth,
            # David 2026-10-24 (SL/TP fix): only this setup's own supply high / demand low
            "invalidation": poi["bottom"] if side == "buy" else poi["top"],
            "formed_t": bars[formed]["t"], "formed_idx": formed}


def bos_setups(bars: List[Dict], st: Dict, tf: str, symbol: str = "", max_age: Optional[int] = None) -> List[Dict]:
    """David 2026-10-24: once a BOS happens, its setup (setup_for). CHoCH breaks are not traded on their own
    (only inside an H4 zone: sdh4_setups). max_age (backtest: the whole history) overrides setup_max_age_bars."""
    n = len(bars)
    age = int(S["setup_max_age_bars"]) if max_age is None else max_age
    return [setup_for(bars, st, e, tf, symbol) for e in st["events"] if e["kind"] == "BOS" and e["idx"] >= n - age]


def sdh4_setups(h4: Dict, bars: List[Dict], st: Dict, tf: str, symbol: str = "") -> Tuple[List[Dict], Optional[int]]:
    """S&D H4 (David 2026-10-25): price came back to an H4 setup's entry (its FVG, above its demand / below its
    supply) at h4["touch_t"]. From then on, every BOS or CHoCH of this timeframe (M15) the same way whose move
    started inside the H4 area (between the H4 entry and the H4 invalidation) gets its own setup, as a BOS setup
    gets one (setup_for: M15 zone or MB + FVG → entry 10 % inside). The H4 area is broken by the first close of
    this timeframe beyond the H4 invalidation; no setup after it.
    → (the setups, complete or not, each with parent = the H4 setup's id; the break time or None)"""
    side, buy = h4["side"], h4["side"] == "buy"
    lo, hi = sorted((h4["entry"], h4["invalidation"]))
    inv = h4["invalidation"]
    broken = next((b["t"] for b in bars if b["t"] >= h4["touch_t"] and (b["c"] < inv if buy else b["c"] > inv)), None)
    out = []
    for e in st["events"]:
        if e["side"] != side or e["t"] < h4["touch_t"] or broken is not None and e["t"] >= broken:
            continue
        if not lo <= e["origin"]["price"] <= hi:
            continue
        rec = setup_for(bars, st, e, tf, symbol)
        rec.update(id=f"{symbol}-H4{tf}-{'D' if buy else 'S'}-{e['t'] // 1000}", entry_type="S&D H4", parent=h4["id"])
        out.append(rec)
    return out, broken


def entry_bos(m5: List[Dict], side: str, after_t: int) -> Optional[Dict]:
    """New rules §18 (David 2026-10-25): after the retrace into the zone + FVG area the entry needs its own
    proof — an M5 candle CLOSING beyond the latest valid confirmed M5 swing in the trade direction (a close
    break of structure(), BOS or CHoCH). Returns the first such break after after_t, or None yet."""
    return next((e for e in structure(m5)["events"] if e["side"] == side and e["t"] > after_t), None)


def pullback(st: Dict, seq: List[Dict]) -> Optional[int]:
    """The first bar of seq (bars after the setup formed) whose low (buy) / high (sell) reaches the entry."""
    e = st["entry"]
    return next((i for i, b in enumerate(seq) if (b["l"] <= e if st["side"] == "buy" else b["h"] >= e)), None)


# ── §17-19 stop and target ──────────────────────────────────────────────────

def stop_price(st: Dict, point: float) -> float:
    buf = float(S["sl_buffer_points"]) * point
    return st["invalidation"] + buf if st["side"] == "sell" else st["invalidation"] - buf


def opposite_levels(side: str, *series: List[Dict]) -> List[Tuple[float, str]]:
    """Structure in the trade's way: swing lows (sell) / highs (buy) of the given timeframes that price has
    not traded through since they formed (David 2026-10-24: never old structure that is already taken)."""
    kind = "low" if side == "sell" else "high"
    out = []
    for name, bars in series:
        for s in swings(bars):
            if s["kind"] != kind:
                continue
            later = bars[s["idx"] + 1:]
            if any(b["l"] < s["price"] if kind == "low" else b["h"] > s["price"] for b in later):
                continue
            out.append((s["price"], f"{name} swing {s.get('label') or kind}"))
    return out


def final_target(side: str, entry: float, stop: float, levels: List[Tuple[float, str]]) -> Dict:
    """§18-19: the first structure level in the way at ≥ min_rr. David 2026-10-24 (SL/TP fix): none in
    reach → no target (price None) and no trade; the target is never stretched to 1:3."""
    risk = abs(entry - stop)
    need = entry - S["min_rr"] * risk if side == "sell" else entry + S["min_rr"] * risk
    beyond = [(p, l) for p, l in levels if (side == "sell" and p <= need) or (side == "buy" and p >= need)]
    if not beyond:
        return {"price": None, "label": f"no structure target at ≥ 1:{S['min_rr']:g}", "rr": None, "min_rr_price": need}
    p, label = min(beyond, key=lambda v: abs(v[0] - entry))
    return {"price": p, "label": label, "rr": round(abs(p - entry) / risk, 2) if risk else None, "min_rr_price": need}


def sl_atr(bars: List[Dict]) -> Optional[float]:
    """The ATR the stop distance is judged by (sl_atr_tf bars, period sl_atr_period)."""
    n = int(S["sl_atr_period"])
    return tools.atr(bars[-(4 * n + 1):], n)


def pretrade(st: Dict, entry: float, stop: float, tgt: Dict, atr: Optional[float],
             min_rr: Optional[float] = None, sl_max: Optional[float] = None) -> Optional[str]:
    """David's SL/TP bug fix (2026-10-24), checked right before an order. Everything comes from this one
    setup: its BOS, its zone, its FVG inside the BOS move, the stop from its own zone + buffer on the right
    side and not abnormally far (≤ sl_max_atr_mult × ATR; never moved closer to pass), a real structure
    target on the right side at ≥ min_rr. The structure filter layer passes its profile's min_rr / sl_max
    (2026-10-25: Book.plan with the layer on), so one threshold rules both; None = STRATEGY's own.
    Returns why not, or None when the order may go."""
    min_rr = float(S["min_rr"]) if min_rr is None else float(min_rr)
    sl_max = float(S["sl_max_atr_mult"]) if sl_max is None else float(sl_max)
    side = st["side"]
    sell = side == "sell"
    bos, poi, f = st.get("bos") or {}, st.get("poi") or {}, st.get("fvg") or {}
    # S&D H4 (David 2026-10-25): inside an H4 zone the M15 break may be a CHoCH as well
    if bos.get("kind") not in (("BOS", "CHoCH") if st.get("parent") else ("BOS",)) or bos.get("side") != side:
        return "not this setup's BOS"
    if poi.get("kind") not in (("supply", "MB") if sell else ("demand", "MB")):
        return f"no {'supply' if sell else 'demand'} zone (or mitigation block) in this setup"
    if not f or f not in (st.get("fvgs") or []) or not bos["origin"]["t"] < f["t"] <= bos["t"] \
            or not f["bottom"] <= st["entry"] <= f["top"]:
        return "the FVG is not this setup's (inside its BOS move, holding the entry)"
    if st.get("invalidation") != (poi["top"] if sell else poi["bottom"]):
        return "the stop is not from this setup's own zone"
    if not entry or entry <= 0:
        return "no valid entry price"
    if sell and stop <= entry or not sell and stop >= entry:
        return f"SL {stop:g} is not {'above' if sell else 'below'} the entry {entry:g}: price is already beyond the zone"
    risk = abs(entry - stop)
    if not atr:
        return "no ATR to judge the stop distance"
    if risk > sl_max * atr:
        return f"SL distance {risk:g} is {risk / atr:.1f}× the {S['sl_atr_tf']} ATR {atr:g} (max {sl_max:g}×): abnormal stop"
    tp = (tgt or {}).get("price")
    if tp is None:
        return (tgt or {}).get("label") or "no target"
    if sell and tp >= entry or not sell and tp <= entry:
        return f"TP {tp:g} is on the wrong side of the entry {entry:g}"
    rr = abs(tp - entry) / risk
    if rr < min_rr - 1e-9:
        return f"RR {rr:.2f} is under {min_rr:g}"
    return None


# ── §12-15 dynamic layer ────────────────────────────────────────────────────

def strength(m5: List[Dict], r: int, x: int, side: str) -> Dict:
    """How strongly price pulled back into the setup (bars r-6 .. the pullback's extreme at the entry):
    big bodies vs the 20 before, a run of candles in the retracement direction, distance in M5 ATRs.
    0-1 of 3 → weak, 2 → moderate, 3 → strong."""
    a = max(0, r - 6)
    seg = m5[a:x + 1]
    if not seg:
        return {"level": "weak", "score": 0}
    sell = side == "sell"                        # the retracement runs against the trade: up into supply, down into demand
    peak = (max if sell else min)(range(len(seg)), key=lambda i: seg[i]["h"] if sell else seg[i]["l"])
    leg = seg[:peak + 1]
    before = m5[max(0, a - 20):a] or leg
    ratio = (sum(_body(b) for b in leg[-5:]) / max(1, len(leg[-5:]))) / max(1e-12, sum(_body(b) for b in before) / len(before))
    run = best = 0
    for b in leg:
        run = run + 1 if (_up(b) if sell else _down(b)) else 0
        best = max(best, run)
    atr = tools.atr(m5[max(0, x - 40):x + 1], 14) or 0.0
    travel = ((leg[-1]["h"] - min(b["l"] for b in leg)) if sell else (max(b["h"] for b in leg) - leg[-1]["l"])) / atr if atr else 0.0
    score = int(ratio >= S["strength_body_ratio"]) + int(best >= S["strength_consecutive"]) + int(travel >= S["strength_travel_atr"])
    level = "strong" if score == 3 else "moderate" if score == 2 else "weak"
    return {"level": level, "score": score, "body_ratio": round(ratio, 2), "run": best, "travel_atr": round(travel, 2)}


def layer_price(side: str, entry: float, stop: float, level: str) -> Dict:
    depth = float(S["layer_depth"][level])
    px = entry + depth * (stop - entry)          # toward the stop on either side
    return {"price": px, "depth": depth, "level": level}
