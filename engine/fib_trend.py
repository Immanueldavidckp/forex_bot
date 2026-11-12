"""
engine/fib_trend.py — "FIB GO WITH TREND", the class rule (class video 5, ~/videos/trading/part 5.mp4; rules, quotes
and times: engine/research/fib_trend/class_video5/fib_trend_rules.md). The slide (video 47:00) and how he applies it:

    1. TREND NEED TO CHANGE       a CHoCH — "market structure shift" — of the swing structure as he draws it
                                  (swing_structure below: the last pivot high / low broken by a candle close)
    2. EMA SHOULD INTERCROSS      EMA 9 and EMA 21 on the close cross the new way at the trend change (1:01:14)
    3. 1 SWING NEED TO COMPLETE   "one swing means one break of structure: after the character changes, one BOS needs
                                  to complete" (49:31) — the 1st BOS after the CHoCH
    4. TAKE A TRADE IN NEXT SWING the leg after that BOS = the 2nd swing from the CHoCH. ONLY that one: "from the place
                                  where the CHoCH happens take the second swing"; a missed 2nd swing is not taken in
                                  the 3rd (1:13:16–1:13:40)
    5. EMA SHOULD NOT INTERCROSS  "after the character change it should not be inter-crossed" (1:15:13); "after the first
                                  intercross, till we take a trade, intercross should not happen" (52:17)
    6. IMPLEMENT FIB              "from the swing high to the CURRENT RUNNING low" (50:46): 1 = H, 0 = L; L is dragged
                                  down while the market still makes new lows (1:07:01). Sell: mirrored.
    7. 0.618 NEED TO TOUCH        a candle touches 0.618 from below, by body or wick (55:18, 56:03) — "the golden zone"
    8. TAKE A TRADE IN NEXT CANDLE ONCE IT CROSS 0.618 CANDLE
                                  mark the HIGH of that candle; the next candle going through it = the entry (a buy
                                  stop there; if the candle closed at its high, the next one opens there → enter at
                                  once). Next candle doesn't reach it → wait for the next candle that touches 0.618
                                  (56:15–58:29, 1:07:29–1:07:57)

    stop    "below 0.236, push it a little" (58:43–58:49, 1:09:30): 0.236 − SL_BUFFER_ATR × ATR
    target  1.618 (1:08:05). Risk-reward at least 1 : 1, else no entry (1:09:44–1:09:50)
    his trade (2 h gold, 28 Aug 2025): 0 = 3373.77, 1 = 3393.69, 0.618 = 3386.05, entry 3386.94, stop 3377.47
    (0.236 = 3378.40), target 3406.06, RR 2.03.
    markets  forex + gold, 1 h / 2 h / 4 h ("15 minutes and up"; higher is better); not crypto (1:13:44–1:13:52)

Everything is causal (candle by candle, closed candles only): the same code draws the /smc layer, runs the backtest
and decides the live order (engine/fib_book.py), so the chart shows what would have been traded.

    setups(bars, m=None) → one entry per traded swing (TRADE_SWINGS) of every trend (CHoCH → next CHoCH), oldest first
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .major_structure import atr14

EMA_FAST, EMA_SLOW = 9, 21
ENTRY_FIB, STOP_FIB, TARGET_FIB = 0.618, 0.236, 1.618
LEVELS = (0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.618)    # his template: 2.618 / 3.618 / 4.236 switched off (7:53)
SWING_N = 3                 # H is the swing's high once SWING_N candles after it made no new high ...
MIN_SWING_ATR = 1.0         # ... and price has come back from it by MIN_SWING_ATR × ATR(14): a pullback, not a wiggle
STRUCTURE_N = 4             # swing_structure pivots: 3 and 4 both give his 28 Aug 2025 trade to the cent (H, L, stop)
TRADE_SWINGS = (2,)         # the 2nd swing from the CHoCH only (1:13:16–1:13:40)
SL_BUFFER_ATR = 0.1         # "push it a little" below 0.236: his trade 0.93 under it on 2 h gold (ATR ~ 9)
MIN_RR = 1.0


def swing_structure(bars: List[Dict], n: int = 5) -> Dict:
    """the structure as the class draws it (video 5, 1:00:00–1:06:00 and 1:19:20–1:21:20): the last swing high / low
    (a pivot: n candles each side), broken by a candle BODY close beyond it (1:00:07). A break the trend's way = BOS,
    against it = CHoCH (the trend changes). Each level breaks once. → {"events": [{kind, side, level, level_idx, idx,
    origin {idx, price}}], "trend"} in major_structure's shape, so the rest of the code takes either."""
    N, ev, trend = len(bars), [], None
    sh = sl = None                                                  # (idx, price) of the live swing high / low
    for x in range(N):
        p = x - n                                                   # a pivot at p is known once x = p + n has closed
        if p >= n:
            if all(bars[p]["h"] > bars[q]["h"] for q in range(p - n, p)) and all(bars[p]["h"] >= bars[q]["h"] for q in range(p + 1, x + 1)):
                sh = (p, bars[p]["h"])
            if all(bars[p]["l"] < bars[q]["l"] for q in range(p - n, p)) and all(bars[p]["l"] <= bars[q]["l"] for q in range(p + 1, x + 1)):
                sl = (p, bars[p]["l"])
        c = bars[x]["c"]
        for side, lv in (("buy", sh), ("sell", sl)):
            if lv is None or not ((c > lv[1]) if side == "buy" else (c < lv[1])):
                continue
            rng = range(lv[0], x + 1)
            o = min(rng, key=lambda i: bars[i]["l"]) if side == "buy" else max(rng, key=lambda i: bars[i]["h"])
            ev.append({"kind": "BOS" if trend == side else "CHoCH", "side": side, "level": lv[1], "level_idx": lv[0],
                       "idx": x, "t": bars[x]["t"], "close": c,
                       "origin": {"idx": o, "price": bars[o]["l" if side == "buy" else "h"], "t": bars[o]["t"]}})
            trend = side
            if side == "buy":
                sh = None
            else:
                sl = None
    return {"events": ev, "trend": {"buy": "up", "sell": "down"}.get(trend)}


def ema(vals: List[float], n: int) -> List[float]:
    """an EMA seeded with the first value, alpha 2 / (n + 1)"""
    a, out = 2 / (n + 1), []
    for v in vals:
        out.append(v if not out else out[-1] + a * (v - out[-1]))
    return out


def fib(one: float, zero: float, f: float) -> float:
    """the price of Fib level f with 1 = `one` and 0 = `zero` (TradingView's retracement tool drawn from 1 to 0)"""
    return zero + f * (one - zero)


def setups(bars: List[Dict], m: Optional[Dict] = None, n: int = STRUCTURE_N, *, swing_n: int = SWING_N,
           min_swing_atr: float = MIN_SWING_ATR, trade_swings=TRADE_SWINGS, ema_fast: int = EMA_FAST,
           ema_slow: int = EMA_SLOW, entry_fib: float = ENTRY_FIB, stop_fib: float = STOP_FIB,
           target_fib: float = TARGET_FIB, sl_buffer_atr: float = SL_BUFFER_ATR, min_rr: float = MIN_RR,
           entry_candle: str = "worst", target_r: Optional[float] = None) -> List[Dict]:
    """target_r: the target as a multiple of the risk from the entry (2.0 = 2R) instead of the Fib level target_fib"""
    N = len(bars)
    if N < ema_slow + 5:
        return []
    m = m or swing_structure(bars, n)
    P = dict(A=atr14(bars), swing_n=swing_n, min_swing_atr=min_swing_atr, trade_swings=tuple(trade_swings),
             entry_fib=entry_fib, stop_fib=stop_fib, target_fib=target_fib,
             sl_buffer_atr=sl_buffer_atr, min_rr=min_rr, entry_candle=entry_candle,
             target_r=target_r)
    closes = [b["c"] for b in bars]
    ef, es = ema(closes, ema_fast), ema(closes, ema_slow)
    ev = sorted(m["events"], key=lambda x: x["idx"])
    out: List[Dict] = []
    for e in ev:
        if e["kind"] != "CHoCH":
            continue
        end = next((x["idx"] for x in ev if x["kind"] == "CHoCH" and x["idx"] > e["idx"]), N)
        boss = [x for x in ev if x["kind"] == "BOS" and x["side"] == e["side"] and e["idx"] < x["idx"] < end]
        out += _trend(bars, ef, es, e, boss, end, P)
    return out




def _trend(bars, ef, es, e, boss, end, P) -> List[Dict]:
    buy = e["side"] == "buy"
    sg = 1 if buy else -1
    ok = lambda i: (ef[i] - es[i]) * sg > 0                         # EMA 9 on the trend's side of EMA 21
    x = e["idx"]
    # rule 2: the cross at the trend change — the last one up to the CHoCH candle if the EMAs are already the new way
    # there, else the first one after it
    if ok(x):
        cross = next((i for i in range(x, 0, -1) if ok(i) and not ok(i - 1)), 0)
    else:
        cross = next((i for i in range(x + 1, end) if ok(i) and not ok(i - 1)), None)
    # rule 5: after the CHoCH (and the cross) no cross back
    back = None if cross is None else next((i for i in range(max(cross, x), end) if not ok(i)), None)
    out = []
    for k, b in enumerate(boss):
        swing = k + 2
        if swing not in P["trade_swings"]:
            continue
        w_end = boss[k + 1]["idx"] if k + 1 < len(boss) else end
        s = {"side": e["side"], "swing": swing, "choch_idx": x, "choch_level": e["level"], "cross_idx": cross,
             "cross_back_idx": back, "bos_idx": b["idx"], "bos_level": b["level"], "w_end": w_end,
             "trend_end": end if end < len(bars) else None}
        # the entry may fill IN the candle that makes the next BOS (a stop order inside it: his 28 Aug trade); rule 5 ends
        # the swing's chance at the cross back
        stop = min(w_end + 1, len(bars)) if back is None else min(w_end + 1, back, len(bars))
        _swing(bars, s, b["idx"], stop, buy, P)
        _judge(bars, s, buy, P, stop)
        out.append(s)
    return out


def _swing(bars, s, start, stop, buy, P) -> None:
    """the leg after the BOS: its high H and the pullback's low L (both running), the Fib armed once H is a swing
    (SWING_N candles + MIN_SWING_ATR); then the first candle that touches 0.618 → its high is the entry, hit by the next
    candle or replaced by the next 0.618 touch"""
    sg = 1 if buy else -1
    hi = (lambda b: b["h"]) if buy else (lambda b: b["l"])
    lo = (lambda b: b["l"]) if buy else (lambda b: b["h"])
    past = lambda a, b: (a - b) * sg > 0                           # a is further the trend's way than b
    A = P["A"]
    h, l, armed, armed_at, mark, ent = start, None, False, None, None, None
    first = None                                                   # the swing's FIRST 0.618 touch: (candle, h, l) then
    for j in range(start + 1, stop):
        b = bars[j]
        if mark is not None and not past(mark[1], hi(b)):          # this candle went through the touch candle's high
            px = b["o"] if past(b["o"], mark[1]) else mark[1]      # opened beyond it (a gap): filled at the open
            ent = (mark[0], j, px)
            break
        mark = None
        if past(hi(b), hi(bars[h])):                               # a new high: the swing goes on, the Fib is redrawn
            h, l, armed = j, None, False
            continue
        if l is None or past(lo(bars[l]), lo(b)):                  # a new low: the Fib's 0 is dragged with it
            l = j
        if not armed and j - h >= P["swing_n"] and abs(hi(bars[h]) - lo(bars[l])) >= P["min_swing_atr"] * A[h]:
            armed, armed_at = True, j
        if armed and l < j and not past(fib(hi(bars[h]), lo(bars[l]), P["entry_fib"]), hi(b)):
            mark = (j, hi(b))                                      # touched 0.618 (body or wick): mark its high
            if first is None:
                first = (j, h, l)
    s["first_touch"] = first
    s.update(h_idx=h, l_idx=l, armed=armed, armed_idx=armed_at if armed else None,
             touch_idx=ent[0] if ent else (mark[0] if mark else None), entry_idx=ent[1] if ent else None,
             entry=ent[2] if ent else None, mark=ent[2] if ent else (mark[1] if mark else None))
    H, L = hi(bars[h]), (lo(bars[l]) if l is not None else None)
    s.update(H=H, L=L, levels=None if L is None else {str(f): fib(H, L, f) for f in LEVELS})
    if L is not None:
        buf = P["sl_buffer_atr"] * A[h]
        s.update(entry_level=fib(H, L, P["entry_fib"]), sl=fib(H, L, P["stop_fib"]) - sg * buf, tp=fib(H, L, P["target_fib"]))
    else:
        s.update(entry_level=None, sl=None, tp=None)


def _judge(bars, s, buy, P, stop) -> None:
    """why there is no trade, or the trade and how it ended (stop / target; both in one candle = the stop)"""
    N = len(bars)
    s.update(status=None, why=None, rr=None, exit_idx=None, exit=None, result=None)
    if s["cross_idx"] is None:
        s["status"], s["why"] = "no trade", "EMA 9 never crossed EMA 21 the new way (rule 2)"
        return
    rr = lambda px: abs(s["tp"] - px) / abs(px - s["sl"]) if s["sl"] is not None and px != s["sl"] else 0
    ref = s["entry"] if s["entry_idx"] is not None else s["mark"]
    if P.get("target_r") and ref is not None and s["sl"] is not None:   # the target = target_r × the risk from the entry
        s["tp"] = ref + P["target_r"] * (ref - s["sl"])
    if s["entry_idx"] is None:
        if stop >= N:                                               # the swing is still going on
            s["status"] = ("buy stop" if buy else "sell stop") if s["mark"] is not None else \
                          "waiting for 0.618" if s["armed"] else "swing forming"
            if s["mark"] is not None:
                s["rr"] = round(rr(s["mark"]), 2)
                if s["rr"] < P["min_rr"]:
                    s["status"], s["why"] = "waiting for 0.618", f"RR {s['rr']} under {P['min_rr']} at the mark"
            return
        nxt = "the EMA cross back (rule 5)" if s["cross_back_idx"] is not None and stop == s["cross_back_idx"] else \
              "the CHoCH" if s["trend_end"] is not None and stop >= s["trend_end"] else "the next BOS"
        s["status"], s["why"] = "no trade", (f"no entry (0.618 touch + next candle through its high) before {nxt}"
                                             if s["armed"] else f"no pullback big enough for a Fib before {nxt}")
        return
    px = s["entry"]
    s["rr"] = round(rr(px), 2)
    if (px - s["sl"]) * (1 if buy else -1) <= 0 or s["rr"] < P["min_rr"]:
        s.update(status="no trade", why=f"RR {s['rr']} under {P['min_rr']} at the entry {px:g}", entry_idx=None)
        return
    s["status"] = "open"
    for q in range(s["entry_idx"], N):
        b = bars[q]
        hit_sl = b["l"] <= s["sl"] if buy else b["h"] >= s["sl"]
        if q == s["entry_idx"] and hit_sl and P.get("entry_candle") == "best":   # research only: the low came BEFORE
            hit_sl = b["c"] <= s["sl"] if buy else b["c"] >= s["sl"]              # the fill unless it closed there
        hit_tp = (b["h"] >= s["tp"] if buy else b["l"] <= s["tp"]) and not (q == s["entry_idx"] and hit_sl)
        if hit_sl or hit_tp:
            win = hit_tp and not hit_sl
            s.update(status="won" if win else "lost", exit_idx=q, exit=s["tp"] if win else s["sl"],
                     result=s["rr"] if win else -1.0)
            return


# ── FIB RETRACEMENT: the class's second rule ("the easy one, regular entries", video 1:32:05–2:02:46) ──
#   in a trend, at every BOS: Fib from the swing high (1 = the high of the leg that broke structure; "modify the high,
#   the low stays the same" while price makes new highs without an entry, 1:43:05–1:43:37) to the PREVIOUS swing low
#   (0 = the low that leg started from, "the low in the break-off structure", 1:41:35–1:42:49). Sell: mirrored.
#   entry   a LIMIT at 0.618 ("if 0.618 touches, entry", 1:37:55)
#   stop    exactly 0.236; target 1 = the swing high: 1 : 1 ("set your stop loss in exactly 0.236", 1:37:14–1:37:34)
#   which swings  "safety side" (1:58:24–2:02:24): after a CHoCH, swing 1 = confirmation (no trade), swings 2 and 3
#                 trade, 4 no ("a chance of a character change"), 5 = confirmation, 6 trade. Experienced: every BOS.
#   timeframe 5 min – 4 h, best 15 / 30 min (1:38:05)
RETRACE_SWINGS = {"safety": (2, 3, 6), "every": None}
RETRACE_ENTRY, RETRACE_STOP, RETRACE_TARGET = 0.618, 0.236, 1.0


def retrace_setups(bars: List[Dict], m: Optional[Dict] = None, n: int = STRUCTURE_N, *, mode: str = "safety",
                   entry_fib: float = RETRACE_ENTRY, stop_fib: float = RETRACE_STOP,
                   target_fib: float = RETRACE_TARGET, stop_buffer_atr: float = 0.0,
                   target_r: Optional[float] = None) -> List[Dict]:
    """one entry per BOS leg (swing 2, 3, … from the CHoCH), the swings the mode trades, oldest first"""
    N = len(bars)
    if N < 30:
        return []
    m = m or swing_structure(bars, n)
    A = atr14(bars)
    ev = sorted(m["events"], key=lambda x: x["idx"])
    allowed = RETRACE_SWINGS[mode]
    out: List[Dict] = []
    swing = None
    for k, e in enumerate(ev):
        if e["kind"] == "CHoCH":
            swing = 1
            continue
        if swing is None:                                           # before the first CHoCH: no count yet
            continue
        swing += 1
        if allowed is not None and swing not in allowed:
            continue
        w_end = next((x["idx"] for x in ev[k + 1:]), N)             # the next BOS / CHoCH ends this leg's setup
        out.append(_retrace(bars, e, swing, w_end, entry_fib, stop_fib, target_fib, stop_buffer_atr, target_r, A))
    return out


def _retrace(bars, e, swing, w_end, entry_fib, stop_fib, target_fib, stop_buffer_atr=0.0, target_r=None, A=None) -> Dict:
    """stop_buffer_atr: the stop that many ATR beyond the stop_fib level; target_r: the target as a multiple of the risk
    (2.0 = 2R) instead of the Fib level target_fib"""
    buy = e["side"] == "buy"
    sg = 1 if buy else -1
    hi = (lambda b: b["h"]) if buy else (lambda b: b["l"])
    lo = (lambda b: b["l"]) if buy else (lambda b: b["h"])
    N, x, o = len(bars), e["idx"], e["origin"]["idx"]
    h = max(range(o, x + 1), key=lambda i: hi(bars[i]) * sg)
    L = lo(bars[o])
    s = {"side": e["side"], "kind": "retrace", "swing": swing, "bos_idx": x, "bos_level": e["level"], "l_idx": o, "L": L,
         "w_end": w_end, "entry_idx": None, "entry": None, "status": None, "why": None, "exit_idx": None, "exit": None,
         "result": None, "rr": 1.0}
    def lvl():
        en = fib(hi(bars[h]), L, entry_fib)
        sl = fib(hi(bars[h]), L, stop_fib) - sg * (stop_buffer_atr * A[h] if stop_buffer_atr else 0.0)
        return en, sl, (en + target_r * (en - sl) if target_r else fib(hi(bars[h]), L, target_fib))
    for j in range(x + 1, w_end):
        b = bars[j]
        en, sl, tp = lvl()
        # the pullback touched the level: the limit fills. A candle that OPENS already through it has no order working
        # (the live book never chases: fib_book.levels) — it waits for the next close on the right side of the level
        if j > h and (lo(b) - en) * sg <= 0 and (b["o"] - en) * sg >= 0:
            s.update(entry_idx=j, entry=en)
            break
        if (hi(b) - hi(bars[h])) * sg > 0:                          # a new high before the entry: modify the high
            h = j
    en, sl, tp = lvl()
    H = hi(bars[h])
    s.update(h_idx=h, H=H, entry_level=en, sl=sl, tp=tp, levels={str(f): fib(H, L, f) for f in LEVELS})
    if s["entry_idx"] is None:
        s["status"] = ("buy limit" if buy else "sell limit") if w_end >= N else "no trade"
        if w_end < N:
            s["why"] = "no pullback to the entry level before the next break"
        return s
    px = s["entry"]
    if target_r:                                                    # a gap fill: 2R from the real entry
        tp = px + target_r * (px - sl)
        s["tp"] = tp
    s["rr"] = round(abs(tp - px) / abs(px - sl), 2) if px != sl else None
    if (px - sl) * sg <= 0:
        s.update(status="no trade", why="opened beyond the stop", entry_idx=None)
        return s
    s["status"] = "open"
    for q in range(s["entry_idx"], N):
        b = bars[q]
        hit_sl = b["l"] <= sl if buy else b["h"] >= sl
        hit_tp = q > s["entry_idx"] and (b["h"] >= tp if buy else b["l"] <= tp)   # the fill candle: only the stop
        if hit_sl or hit_tp:
            win = hit_tp and not hit_sl
            s.update(status="won" if win else "lost", exit_idx=q, exit=tp if win else sl, result=s["rr"] if win else -1.0)
            break
    return s
