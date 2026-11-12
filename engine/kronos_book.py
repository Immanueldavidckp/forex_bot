"""
engine/kronos_book.py — Kronos' trades inside the V5 engine (config KRONOS; David 2026-10-26).

The engine stays the only process that talks to MT5. Each loop (run.py, after V5's manage):
  1. once per closed M15 bar: CONTEXT + 1 bars of every Kronos symbol, with tick volume, in one bridge call
     → engine_data/kronos/feed/<SYMBOL>.json (closed bars only: [t_utc_ms, o, h, l, c, tick_volume, spread])
  2. kronos-signals (kronos/signals.py, GPU) forecasts each new bar → engine_data/kronos/signals.json
  3. a fresh forecast is decided once (decide()): trade or why not; trades go out at the minimum lot with
     their own magic, SL / TP on the order, and are closed after HOLD_BARS bars if neither was hit
  4. engine_data/kronos/view.json for the dashboard's /kronos page: the forecast fans, the decisions, the
     trades, and the live forecast record (each forecast scored once its HORIZON bars have closed)
  5. every loop, one bridge call: each symbol's forming bar + latest quote (the page's live candle and price) and
     Claude's own MT5 trades (magic CLAUDE_MAGIC, placed with the mt5 tools), shown with Claude's plan from
     claude_notes.json ({ticket: {"plan", "close_by_ms"}}) — never touched here
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import os
from typing import Dict, List, Optional

from .book import _write, journal, log, money_per_move, stops_gap
from .config import KRONOS as K, load_control
from .feed import TF_MIN, mt5c, now_ms

FEED_DIR = os.path.join(K["DIR"], "feed")
SIGNALS_FILE = os.path.join(K["DIR"], "signals.json")
STATE_FILE = os.path.join(K["DIR"], "state.json")
VIEW_FILE = os.path.join(K["DIR"], "view.json")
DECISIONS_FILE = os.path.join(K["DIR"], "decisions.jsonl")
REPORT_FILE = os.path.join(K["DIR"], "results", "report.txt")
CLAUDE_NOTES_FILE = os.path.join(K["DIR"], "claude_notes.json")
LIVE_EVERY_MS = 10_000                    # ≈ every engine loop (15 s)
BAR_MS = TF_MIN[K["TF"]] * 60_000
for _d in (K["DIR"], FEED_DIR):
    os.makedirs(_d, exist_ok=True)


def enabled() -> bool:
    return bool(load_control().get("kronos", K["ENABLED"]))


def atr(rows: List[list], n: int = K["ATR_PERIOD"]) -> float:
    """ATR(n) of feed rows [t, o, h, l, c, ...] (simple mean of the true ranges)."""
    tr = [max(r[2], p[4]) - min(r[3], p[4]) for p, r in zip(rows[-n - 1:-1], rows[-n:])]
    return sum(tr) / len(tr) if tr else 0.0


def friday_late(now: int) -> bool:
    d = _dt.datetime.fromtimestamp(now / 1000, _dt.timezone.utc)
    hh, mm = map(int, K["FRIDAY_LAST_ENTRY_UTC"].split(":"))
    return d.weekday() == 4 and (d.hour, d.minute) >= (hh, mm)


def lot_for(info: Dict) -> float:
    """The lot Kronos trades: the broker minimum (at least 0.01), on the volume step."""
    step = float(info.get("volume_step") or 0.01)
    return round(round(max(float(info.get("volume_min") or 0.01), 0.01) / step) * step, 8)


# David 2026-11-12 "kronos failing because of trend ... add the CHOCH and BOS": a Kronos trade must agree with the M15
# structure trend (the side of the last BOS / CHoCH of engine/major_structure.py, the structure S&D David uses), and a
# buy must also sit in the pullback, not at the leg's high. Replay of 3,723 recorded forecasts, 16 symbols, 17 days
# (engine/research/kronos_structure/backtest.py): Kronos alone −0.02 R a trade, with the trend +0.14 R, against −0.15 R;
# buys with the trend lose near the leg's high (−0.31 R) and break even in the pullback.
TREND_FILTER = K.get("TREND_FILTER", True)
BUY_PULLBACK_MAX = K.get("BUY_PULLBACK_MAX", 0.6)      # a buy only in the lower 60 % of the leg (protected low → leg high)


def structure(rows: List[list]) -> Optional[Dict]:
    """The M15 structure at the last closed bar of feed rows [t, o, h, l, c, ...]: {"side" buy / sell (the trend),
    "kind" BOS / CHoCH (the last event), "age" bars since it, "pos" where the close sits in the leg — 0 at the
    protected level, 1 at the leg's extreme}. None before the first break."""
    from .major_structure import major_structure
    bars = [{"t": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4]} for r in rows]
    ev = major_structure(bars)["events"]
    if not ev:
        return None
    e = ev[-1]
    prot, seg = e["origin"]["price"], bars[e["origin"]["idx"]:]
    ext = max(x["h"] for x in seg) if e["side"] == "buy" else min(x["l"] for x in seg)
    return {"side": e["side"], "kind": e["kind"], "age": len(bars) - 1 - e["idx"],
            "pos": (bars[-1]["c"] - prot) / (ext - prot) if ext != prot else 1.0}


def decide(sig: Dict, rows: List[list], info: Dict, market: str, now: int, tick: Optional[Dict] = None) -> Dict:
    """One forecast → {"side": "buy" | "sell" | None, "why", and for a trade "entry", "sl", "tp", "atr"}.
    Without a tick the levels are estimated from the last close ± half the bar's spread (the pre-check)."""
    p_up, last = float(sig["p_up"]), float(sig["last"])
    agree = max(p_up, 1 - p_up)
    move = float(sig["median"][-1]) - last
    out: Dict = {"side": None, "p_up": p_up, "move": move}
    if agree < K["P_MIN"]:
        return {**out, "why": f"{agree:.0%} of the paths agree on a side (need {K['P_MIN']:.0%})"}
    side = "buy" if p_up >= K["P_MIN"] else "sell"
    if (move > 0) != (side == "buy"):
        return {**out, "why": f"the median path ends against the {side} side"}
    st = structure(rows) if TREND_FILTER else None
    if TREND_FILTER:
        if not st:
            return {**out, "why": "no M15 trend yet (no BOS / CHoCH in the bars)"}
        if st["side"] != side:
            return {**out, "why": f"M15 trend is {'up' if st['side'] == 'buy' else 'down'} (last {st['kind']} "
                                  f"{st['age']} bars ago): a Kronos {side} is against it"}
        if side == "buy" and st["pos"] > BUY_PULLBACK_MAX:
            return {**out, "why": f"buy at {st['pos']:.0%} of the up leg: only in the pullback (≤ {BUY_PULLBACK_MAX:.0%})"}
    spread = float(tick["ask"]) - float(tick["bid"]) if tick else float(rows[-1][6] or 0)
    if abs(move) < K["MIN_MOVE_SPREAD_X"] * spread:
        return {**out, "why": f"median move {abs(move):g} is under {K['MIN_MOVE_SPREAD_X']:g} × the spread {spread:g}"}
    if market != "crypto" and friday_late(now):
        return {**out, "why": f"Friday after {K['FRIDAY_LAST_ENTRY_UTC']} UTC: the hold would cross the weekly close"}
    a = atr(rows)
    if a <= 0:
        return {**out, "why": "no ATR (too few bars)"}
    sg = 1 if side == "buy" else -1
    entry = float(tick["ask"] if side == "buy" else tick["bid"]) if tick else last + sg * spread / 2
    gap = stops_gap(info)
    sl_d = max(K["SL_ATR"] * a, gap)
    tp_d = max(K["TP_ATR"] * a, gap)
    capped = False
    if K.get("MAX_RISK_USD"):                       # David 2026-11-09: stop never risks more than $2 at the lot traded
        mpm = money_per_move(info) * lot_for(info)
        cap_d = K["MAX_RISK_USD"] / mpm if mpm > 0 else sl_d
        if cap_d < sl_d:
            if cap_d < gap:
                return {**out, "why": f"a ${K['MAX_RISK_USD']:g} stop ({cap_d:g}) is inside the broker's stops level {gap:g}"}
            sl_d, capped = cap_d, True
    if spread > K["MAX_SPREAD_SL"] * sl_d:
        return {**out, "why": f"spread {spread:g} is over {K['MAX_SPREAD_SL']:.0%} of the stop {sl_d:g}"}
    dg = int(info.get("digits") or 5)
    # David 2026-11-11: the last gate before the order — the stop risks at most MAX_RISK_USD and the target is at
    # least MIN_RR × the stop (more is fine, less never). Checked on the prices as they will be sent (rounded).
    rr_min = K.get("MIN_RR") or 0
    tp_d = max(tp_d, rr_min * sl_d)
    pt = 10 ** -dg
    sl_d, tp_d = max(math.floor(sl_d / pt + 1e-9), 1) * pt, math.ceil(tp_d / pt - 1e-9) * pt   # stop in, target out
    risk_usd = sl_d * money_per_move(info) * lot_for(info)
    if K.get("MAX_RISK_USD") and risk_usd > K["MAX_RISK_USD"] + 1e-9:
        return {**out, "why": f"the stop would risk ${risk_usd:.2f} (max ${K['MAX_RISK_USD']:g})"}
    if tp_d < rr_min * sl_d - 1e-12:
        return {**out, "why": f"target {tp_d:g} is under {rr_min:g} × the stop {sl_d:g}"}
    from .trade_checks import chk, g
    checks = [
        chk("Setup", "Kronos paths agreeing", f"{agree:.0%} of {sig.get('paths', K['PATHS'])} paths {'up' if side == 'buy' else 'down'} (P up {p_up:.0%})",
            f"≥ {K['P_MIN']:.0%} on one side", True),
        chk("Setup", "Median path ends on that side", f"{move:+.6g} in {K['HORIZON']} bars", "up for a buy, down for a sell", True),
        *([chk("Setup", "M15 trend (last BOS / CHoCH)", f"{'up' if st['side'] == 'buy' else 'down'}: {st['kind']} {st['age']} bars ago",
               "the same side as Kronos", True),
           chk("Setup", "Place in the leg", f"{st['pos']:.0%} from the protected level to the leg's extreme",
               f"a buy: ≤ {BUY_PULLBACK_MAX:.0%} (in the pullback); a sell: anywhere", True)] if st else []),
        chk("Setup", "Median move vs spread", f"{g(abs(move))} = {abs(move) / spread:.1f} × spread {g(spread)}" if spread else f"{g(abs(move))}, spread 0",
            f"≥ {K['MIN_MOVE_SPREAD_X']:g} × the spread", True),
        chk("Guard", "Friday late (forex / gold)", "crypto: trades all week" if market == "crypto" else "not Friday late",
            f"no entry after Friday {K['FRIDAY_LAST_ENTRY_UTC']} UTC", True),
        chk("Risk", "Stop", (f"{g(sl_d)} = ${K['MAX_RISK_USD']:g} cap (1 ATR = {g(K['SL_ATR'] * a)})" if capped else
                             f"{K['SL_ATR']:g} ATR(M15) = {g(sl_d)}" + (" (stops level)" if sl_d == gap else "")),
            f"{K['SL_ATR']:g} ATR, at most ${K.get('MAX_RISK_USD') or 0:g} at {lot_for(info):g} lot, outside the stops level {g(gap)}", True),
        chk("Risk", "Target", f"{g(tp_d)} ({tp_d / sl_d:.2f} R; {K['TP_ATR']:g} ATR = {g(K['TP_ATR'] * a)})",
            f"{K['TP_ATR']:g} ATR, never under {rr_min:g} × the stop", True),
        chk("Risk", "Money at the stop", f"${risk_usd:.2f} at {lot_for(info):g} lot", f"≤ ${K.get('MAX_RISK_USD') or 0:g}", True),
        chk("Risk", "Spread vs stop", f"{g(spread)} = {spread / sl_d:.0%} of the stop", f"≤ {K['MAX_SPREAD_SL']:.0%}", True),
    ]
    return {**out, "side": side, "entry": round(entry, dg), "sl": round(entry - sg * sl_d, dg), "tp": round(entry + sg * tp_d, dg),
            "atr": a, "checks": checks, "why": f"{agree:.0%} of {sig.get('paths', K['PATHS'])} paths {'up' if side == 'buy' else 'down'}, "
                             f"median {move:+g} in {K['HORIZON']} bars"}


def kronos_marks(sig: Dict, entry: float) -> List[Dict]:
    """The forecast the trade was taken on: the median path + the 10–90 % band, drawn from the entry bar's close."""
    t0 = sig["bar_t"] + BAR_MS
    med = list(sig.get("median") or [])
    ts = [t0 + i * BAR_MS for i in range(len(med) + 1)]
    m = {"type": "path", "label": f"Kronos median, {sig.get('paths', K['PATHS'])} paths (10–90 % band)", "t": ts,
         "p": [sig.get("last", entry)] + med, "color": "#b388ff"}
    if sig.get("q10") and sig.get("q90"):
        m["band"] = [[sig.get("last", entry)] + list(sig["q10"]), [sig.get("last", entry)] + list(sig["q90"])]
    return [m]


class KronosBook:
    def __init__(self, feed, magic: int = K["MAGIC"]):
        self.feed, self.magic = feed, magic
        self.info: Dict[str, Dict] = {}
        self.rows: Dict[str, List[list]] = {}
        self.trades: Dict[str, Dict] = {}         # id "<SYMBOL>-<bar_t>" → the trade
        self.done: Dict[str, int] = {}            # symbol → bar_t of the last forecast decided
        self.decisions: Dict[str, Dict] = {}      # symbol → the last decision (for the page)
        self.pending: List[Dict] = []             # forecasts waiting for their HORIZON bars (live record)
        self.record: Dict[str, Dict] = {}         # symbol → {"n", "hit", "n_conf", "hit_conf"}
        self.positions: List[Dict] = []
        self.pos_ok = False
        self.fetched_slot = 0
        self.retry_at = 0
        self.account: Dict = {}
        self.claude: Dict[str, Dict] = {}         # ticket → Claude's own trade (magic CLAUDE_MAGIC), for the page only
        self.live: Dict[str, Dict] = {}           # symbol → {"bid", "ask", "t_ms", "bar": forming [t_s, o, h, l, c]}
        self.live_at = 0
        self.live_err = ""
        self._load()

    # ── persistence ──
    def _load(self) -> None:
        try:
            with open(STATE_FILE) as f:
                st = json.load(f)
        except Exception:
            return
        self.trades, self.done = st.get("trades", {}), st.get("done", {})
        self.decisions, self.pending, self.record = st.get("decisions", {}), st.get("pending", []), st.get("record", {})
        self.claude = st.get("claude", {})

    def save(self) -> None:
        cut = now_ms() - 14 * 86400_000           # closed trades stay on the page for 14 days
        self.trades = {k: v for k, v in self.trades.items() if not v.get("closed") or v.get("closed_ms", 0) > cut}
        self.claude = {k: v for k, v in self.claude.items() if not v.get("closed") or v.get("closed_ms", 0) > cut}
        _write(STATE_FILE, {"trades": self.trades, "done": self.done, "decisions": self.decisions,
                            "pending": self.pending[-500:], "record": self.record, "claude": self.claude})

    def market(self, sym: str) -> str:
        return self.feed.market.get(sym) or ("metal" if sym in ("GOLD", "SILVER") else "forex")

    # ── MT5 reads (all through the engine's bridge) ──
    def setup(self) -> None:
        res = mt5c.call([{"op": "info", "symbol": s} for s in K["SYMBOLS"]], timeout=120)
        for s, r in zip(K["SYMBOLS"], res):
            if "result" in r:
                self.info[s] = r["result"]
            else:
                log(f"kronos: {s} not available: {r.get('error')}")

    def fetch_bars(self, now: int) -> None:
        """Once per closed bar (3 s after the boundary): the newest CONTEXT closed bars of every symbol. A symbol whose
        newest bar is not the one that just closed is asked again every 15 s for 2 min: a terminal that has just
        (re)selected a symbol serves its old history first (GOLD after the MT5 restart, 2026-10-26: 70 min stale)."""
        slot = now // BAR_MS
        if now - slot * BAR_MS < 3000:
            return
        if slot == self.fetched_slot:
            want = (slot - 1) * BAR_MS
            if now - slot * BAR_MS > 120_000 or now - self.retry_at < 15_000:
                return
            syms = [s for s in K["SYMBOLS"] if s in self.info and (self.rows.get(s) or [[0]])[-1][0] < want]
            if not syms:
                return
            self.retry_at = now
        else:
            syms = [s for s in K["SYMBOLS"] if s in self.info]
        res = mt5c.call([{"op": "rates", "symbol": s, "tf": K["TF"], "count": K["CONTEXT"] + 1} for s in syms], timeout=120)
        off = self.feed.clock()
        for s, r in zip(syms, res):
            if "result" not in r:
                continue
            pt = float(self.info[s]["point"])
            rows = [[mt5c.server_to_utc_ms(x[0], off), x[1], x[2], x[3], x[4], x[5], round((x[7] if len(x) > 7 else 0) * pt, 10)]
                    for x in r["result"]]
            rows = [x for x in rows if x[0] + BAR_MS <= now][-K["CONTEXT"]:]
            self.rows[s] = rows
            _write(os.path.join(FEED_DIR, f"{s}.json"), {"symbol": s, "tf": K["TF"], "written": now, "bars": rows})
        self.fetched_slot = slot
        self.resolve()

    def read_positions(self) -> None:
        self.pos_ok = False
        self.positions = mt5c.positions(magic=self.magic)
        self.pos_ok = True

    # ── the loop step ──
    def step(self, trading: bool, account: Optional[Dict] = None) -> None:
        now = now_ms()
        self.account = account or {}
        if not self.info:
            self.setup()
        self.fetch_bars(now)
        on = enabled()
        if any(not t.get("closed") for t in self.trades.values()):
            self.read_positions()
            self.manage(now)
        try:                                      # a failed live read must not stop Kronos' own trades
            self.read_live(now)
            self.live_err = ""
        except Exception as e:
            if str(e) != self.live_err:
                log(f"kronos: live quotes / Claude's trades: {type(e).__name__}: {e}")
            self.live_err = str(e)
        try:
            with open(SIGNALS_FILE) as f:
                sigs = json.load(f)
        except (FileNotFoundError, ValueError):
            sigs = {}
        for sym, sig in sigs.items():
            if sym not in self.info or sig.get("bar_t") == self.done.get(sym) or not self.rows.get(sym):
                continue
            self.done[sym] = sig["bar_t"]
            self.pending.append({"symbol": sym, "bar_t": sig["bar_t"], "last": sig["last"], "end": sig["median"][-1], "p_up": sig["p_up"]})
            self.consider(sym, sig, now, on, trading)
        self.write_view(now, on, trading, sigs)
        self.save()

    def consider(self, sym: str, sig: Dict, now: int, on: bool, trading: bool) -> None:
        info, rows = self.info[sym], self.rows[sym]
        d = decide(sig, rows, info, self.market(sym), now)
        age = now - (sig["bar_t"] + BAR_MS)
        open_here = [t for t in self.trades.values() if t["symbol"] == sym and not t.get("closed")]
        n_open = sum(1 for t in self.trades.values() if not t.get("closed"))
        act = ""
        if d["side"]:
            if age > K["SIGNAL_MAX_AGE_SEC"] * 1000:
                act = f"forecast came {age // 60000} min after the bar closed: too late"
            elif K["MAX_PER_SYMBOL"] and len(open_here) >= K["MAX_PER_SYMBOL"]:
                act = f"{len(open_here)} Kronos trade(s) already open here (max {K['MAX_PER_SYMBOL']})"
            elif K["MAX_POSITIONS"] and n_open >= K["MAX_POSITIONS"]:
                act = f"{n_open} Kronos positions open (max {K['MAX_POSITIONS']})"
            elif self.margin_low():
                act = f"free margin under {K['MIN_FREE_MARGIN_PCT']} % of equity"
            elif not on:
                act = "Kronos trading is off"
            elif not trading:
                act = "engine trading is off (or the account is not ready)"
            else:
                tick = mt5c.tick(sym)
                d = decide(sig, rows, info, self.market(sym), now, tick)
                if d["side"]:
                    from .trade_checks import chk
                    d["checks"] = d.get("checks", []) + [
                        chk("Guard", "Forecast age", f"{age // 1000} s after the bar closed", f"≤ {K['SIGNAL_MAX_AGE_SEC'] // 60} min", True),
                        chk("Guard", "Free margin", "enough", f"≥ {K['MIN_FREE_MARGIN_PCT']} % of equity", True),
                        chk("Guard", "Kronos + engine trading", "both ON", "switches on /kronos and the home page", True),
                        chk("Guard", "Exit plan", f"TP / SL at the broker · {K['HOLD_BARS']} bars (2 h) time exit", "", None)]
                act = self.enter(sym, sig, d, info) if d["side"] else ""
        rec = {"bar_t": sig["bar_t"], "at": now, "p_up": sig["p_up"], "side": d["side"], "why": d["why"],
               "action": act or ("no trade" if not d["side"] else "")}
        self.decisions[sym] = rec
        with open(DECISIONS_FILE, "a") as f:
            f.write(json.dumps({"symbol": sym, **rec}) + "\n")

    def recheck(self, sym: str, d: Dict, info: Dict, fill: float, ticket) -> Dict:
        """David 2026-11-11, after the trade is confirmed: measured from the real fill, the stop must risk at most
        MAX_RISK_USD and the target must be at least MIN_RR × the stop. A fill that slipped breaks one of them → the
        stop is pulled in (never pushed out) and / or the target pushed out on the ticket. → d with the levels in force."""
        sg = 1 if d["side"] == "buy" else -1
        dg = int(info.get("digits") or 5)
        pt, mpm = 10 ** -dg, money_per_move(info) * lot_for(info)
        sl_d, tp_d = sg * (fill - d["sl"]), sg * (d["tp"] - fill)
        new_sl, new_tp = sl_d, tp_d
        if K.get("MAX_RISK_USD") and mpm > 0 and sl_d * mpm > K["MAX_RISK_USD"] + 1e-9:
            new_sl = math.floor(K["MAX_RISK_USD"] / mpm / pt + 1e-9) * pt
        if new_sl <= 0:
            return d
        if K.get("MIN_RR") and tp_d < K["MIN_RR"] * new_sl - 1e-12:
            new_tp = math.ceil(K["MIN_RR"] * new_sl / pt - 1e-9) * pt
        if new_sl == sl_d and new_tp == tp_d:
            return d
        sl, tp = round(fill - sg * new_sl, dg), round(fill + sg * new_tp, dg)
        res = mt5c.sltp(ticket, sl, tp) if ticket else {"ok": False, "comment": "no ticket"}
        if not res.get("ok"):
            log(f"kronos {sym}: fill {fill:g} left risk ${sl_d * mpm:.2f} / {tp_d / sl_d:.2f} R and the fix was refused "
                f"({res.get('retcode')} {res.get('comment')}) — levels unchanged")
            journal("kronos_recheck_failed", symbol=sym, ticket=ticket, why=f"{res.get('retcode')} {res.get('comment')}")
            return d
        log(f"kronos {sym}: after the fill {fill:g} → SL {sl:g} (${new_sl * mpm:.2f}), TP {tp:g} ({new_tp / new_sl:.2f} R)")
        journal("kronos_recheck", symbol=sym, ticket=ticket, fill=fill, sl=sl, tp=tp)
        return {**d, "sl": sl, "tp": tp}

    def enter(self, sym: str, sig: Dict, d: Dict, info: Dict) -> str:
        q = lot_for(info)
        tag = _dt.datetime.fromtimestamp(sig["bar_t"] / 1000, _dt.timezone.utc).strftime("%d%H%M")
        res = mt5c.order(sym, d["side"], q, d["sl"], d["tp"], self.magic, f"KRN {tag}", 30)
        if not res.get("ok"):
            journal("kronos_refused", symbol=sym, side=d["side"], why=f"{res.get('retcode')} {res.get('comment')}")
            log(f"kronos {sym} {d['side']}: order refused {res.get('retcode')} {res.get('comment')}")
            return f"order refused: {res.get('retcode')} {res.get('comment')}"
        self.read_positions()
        mine = {t.get("ticket") for t in self.trades.values()}
        pos = next((p for p in self.positions if p["ticket"] == res.get("order")), None) or \
            max((p for p in self.positions if p["symbol"] == sym and p["ticket"] not in mine), key=lambda p: p.get("time_msc", 0), default=None)
        fill = float(pos["price_open"]) if pos else float(res.get("price") or d["entry"])
        d = self.recheck(sym, d, info, fill, pos["ticket"] if pos else res.get("order"))
        tid = f"{sym}-{sig['bar_t']}"
        opened = now_ms()
        self.trades[tid] = {"id": tid, "symbol": sym, "side": d["side"], "lots": q, "entry": fill, "sl": d["sl"], "tp": d["tp"],
                            "ticket": pos["ticket"] if pos else res.get("order"), "opened_ms": opened,
                            "close_by_ms": opened + K["HOLD_BARS"] * BAR_MS, "bar_t": sig["bar_t"], "p_up": sig["p_up"],
                            "median_end": sig["median"][-1], "risk_usd": round(q * abs(fill - d["sl"]) * money_per_move(info), 2),
                            "checks": d.get("checks"), "marks": kronos_marks(sig, fill)}
        journal("kronos_entry", id=tid, symbol=sym, side=d["side"], lots=q, entry=fill, sl=d["sl"], tp=d["tp"], p_up=sig["p_up"])
        log(f"kronos {sym} {d['side']}: {q} @ {fill:g}, SL {d['sl']:g}, TP {d['tp']:g} ({d['why']})")
        return f"{d['side']} {q} @ {fill:g}"

    def margin_low(self) -> bool:
        eq, free = self.account.get("equity"), self.account.get("margin_free")
        return bool(eq and free is not None and float(free) < float(eq) * K["MIN_FREE_MARGIN_PCT"] / 100)

    def manage(self, now: int) -> None:
        if not self.pos_ok:
            return
        pos_by = {p["ticket"]: p for p in self.positions}
        for t in self.trades.values():
            if t.get("closed"):
                continue
            p = pos_by.get(t["ticket"])
            if p:
                t["price_now"], t["pnl_now"] = p.get("price_current"), p.get("profit")
                if p.get("sl"):                     # a stop moved at the broker (e.g. pulled in to $2) shows on /kronos
                    t["sl"] = p["sl"]
                if p.get("tp"):
                    t["tp"] = p["tp"]
                if now >= t["close_by_ms"] and not t.get("closing"):
                    r = mt5c.close(int(t["ticket"]), "KRN time exit")
                    if r.get("ok"):
                        t["closing"] = "time"
                        log(f"kronos {t['symbol']}: {K['HOLD_BARS']} bars up, closed")
                    else:
                        t["close_error"] = f"{r.get('retcode')} {r.get('comment')}"
                continue
            self.book_exit(t, now)

    def book_exit(self, t: Dict, now: int, who: str = "kronos") -> None:
        ds = mt5c.deals(position=int(t["ticket"]))
        outs = [x for x in ds if x.get("entry") == 1]
        if not outs and now - t.setdefault("gone_ms", now) < 60_000:
            return                                  # the closing deal is not in the history yet: next loop
        t.pop("gone_ms", None)
        pnl = round(sum(float(x.get(k) or 0) for x in ds for k in ("profit", "commission", "swap", "fee")), 2)
        reason = {4: "stop", 5: "target"}.get(outs[-1].get("reason"), t.get("closing") or "closed") if outs else (t.get("closing") or "closed")
        t.update(closed=True, closed_ms=now, pnl_usd=pnl, reason=reason, exit=outs[-1].get("price") if outs else None)
        journal(f"{who}_exit", id=t["id"], symbol=t["symbol"], pnl_usd=pnl, reason=reason, exit=t["exit"])
        log(f"{who} {t['symbol']}: closed ({reason}) P&L ${pnl}")

    # ── live quotes + Claude's own trades: read only ──
    def read_live(self, now: int) -> None:
        """Every LIVE_EVERY_MS, one bridge call: Claude's positions, then a tick and the forming bar of every symbol."""
        if now - self.live_at < LIVE_EVERY_MS:
            return
        self.live_at = now
        syms = [s for s in K["SYMBOLS"] if s in self.info]
        res = mt5c.call([{"op": "positions", "magic": K["CLAUDE_MAGIC"]}] + [{"op": "tick", "symbol": s} for s in syms]
                        + [{"op": "rates", "symbol": s, "tf": K["TF"], "count": 1} for s in syms], timeout=60)
        off = self.feed.clock()
        for s, tk, rt in zip(syms, res[1:1 + len(syms)], res[1 + len(syms):]):
            if "result" not in tk or not rt.get("result"):
                continue
            q, x = tk["result"], rt["result"][-1]
            self.live[s] = {"bid": q.get("bid"), "ask": q.get("ask"),
                            "t_ms": mt5c.server_to_utc_ms(int(q["time"]), off) if q.get("time") else None,
                            "bar": [mt5c.server_to_utc_ms(x[0], off) // 1000, x[1], x[2], x[3], x[4]]}
        if "result" not in res[0]:
            raise RuntimeError(f"Claude's positions: {res[0].get('error')}")
        self.track_claude(res[0]["result"], now, off)

    def track_claude(self, pos: List[Dict], now: int, off) -> None:
        """Claude's open positions (magic CLAUDE_MAGIC) → self.claude; one that is gone is booked from its deals like
        a Kronos trade. Nothing here sends an order, modifies or closes."""
        for p in pos:
            tid = str(p["ticket"])
            t = self.claude.get(tid)
            if t is None:
                t = self.claude[tid] = {"id": tid, "ticket": p["ticket"], "symbol": p["symbol"], "side": "sell" if p.get("type") == 1 else "buy",
                                        "lots": p.get("volume"), "entry": p.get("price_open"), "comment": p.get("comment", ""),
                                        "opened_ms": mt5c.server_to_utc_ms(int(p.get("time") or 0), off) if p.get("time") else now}
            t.update(sl=p.get("sl") or None, tp=p.get("tp") or None, price_now=p.get("price_current"), pnl_now=p.get("profit"))
        live = {str(p["ticket"]) for p in pos}
        for tid, t in self.claude.items():
            if not t.get("closed") and tid not in live:
                self.book_exit(t, now, "claude")

    def claude_view(self) -> Dict:
        try:
            with open(CLAUDE_NOTES_FILE) as f:
                notes = json.load(f)
        except (FileNotFoundError, ValueError):
            notes = {}
        both = [{**t, **(notes.get(t["id"]) or {})} for t in self.claude.values()]
        closed = sorted((t for t in both if t.get("closed")), key=lambda t: -t["closed_ms"])
        return {"magic": K["CLAUDE_MAGIC"], "open": [t for t in both if not t.get("closed")], "closed": closed[:50],
                "totals": {"n": len(closed), "won": sum(1 for t in closed if (t.get("pnl_usd") or 0) > 0),
                           "pnl_usd": round(sum(t.get("pnl_usd") or 0 for t in closed), 2)}}

    # ── the live forecast record ──
    def resolve(self) -> None:
        """A forecast made at bar_t is scored on the close of the bar HORIZON bars later (its last forecast bar)."""
        keep = []
        for f in self.pending:
            rows = self.rows.get(f["symbol"]) or []
            want = f["bar_t"] + K["HORIZON"] * BAR_MS
            if not rows or rows[-1][0] < want:
                keep.append(f)
                continue
            real = next((r[4] for r in rows if r[0] == want), None)
            if real is None or real == f["last"]:
                continue                            # a gap inside the horizon (closed market) or no move: not scored
            hit = (f["end"] > f["last"]) == (real > f["last"])
            rec = self.record.setdefault(f["symbol"], {"n": 0, "hit": 0, "n_conf": 0, "hit_conf": 0})
            rec["n"] += 1
            rec["hit"] += int(hit)
            if max(f["p_up"], 1 - f["p_up"]) >= K["P_MIN"]:
                rec["n_conf"] += 1
                rec["hit_conf"] += int(hit)
        self.pending = keep

    # ── the dashboard ──
    def write_view(self, now: int, on: bool, trading: bool, sigs: Dict) -> None:
        try:
            with open(REPORT_FILE) as f:
                report = f.read()
        except FileNotFoundError:
            report = ""
        closed = sorted((t for t in self.trades.values() if t.get("closed")), key=lambda t: -t["closed_ms"])
        made = max((s.get("made_ms", 0) for s in sigs.values()), default=0)
        _write(VIEW_FILE, {
            "at": now, "kronos_on": on, "trading": trading, "service_ms": made,
            "config": {k: K[k] for k in ("SYMBOLS", "MAGIC", "TF", "CONTEXT", "HORIZON", "PATHS", "P_MIN", "MIN_MOVE_SPREAD_X",
                                         "SL_ATR", "TP_ATR", "MAX_RISK_USD", "HOLD_BARS", "MAX_POSITIONS", "MAX_PER_SYMBOL")},
            "symbols": [{"symbol": s, "market": self.market(s), "digits": (self.info.get(s) or {}).get("digits"),
                         "bars": [[r[0] // 1000, r[1], r[2], r[3], r[4]] for r in (self.rows.get(s) or [])[-96:]],
                         "live": self.live.get(s),
                         "signal": {k: v for k, v in sigs[s].items() if k != "each"} if s in sigs else None,
                         "decision": self.decisions.get(s), "record": self.record.get(s)}
                        for s in K["SYMBOLS"]],
            "open": [t for t in self.trades.values() if not t.get("closed")],
            "closed": closed[:50],
            "totals": {"n": len(closed), "won": sum(1 for t in closed if (t.get("pnl_usd") or 0) > 0),
                       "pnl_usd": round(sum(t.get("pnl_usd") or 0 for t in closed), 2)},
            "claude": self.claude_view(),
            "test_report": report})
