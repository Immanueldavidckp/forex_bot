"""
engine/fib_book.py — the class's Fib rules traded inside the V5 engine (config FIB, magic 5050800): the LIVE versions
of engine/fib_reject.py (limit 0.382 / stop under the swing low / 2R for Retracement, the taught entry with the same
stop and 2R for Go With Trend) with the reject checklist. `python3 -m engine.run fib on|off|status`; orders also need
engine trading ON, like S&D David's.

Each loop (run.py, after S&D David), per rule × timeframe (FIB["RULES"]) and symbol, once per closed candle:
  1. the closed candles (BARS of them the first time, then the last few, merged)
  2. fib_reject.setups() on them — the same code as the /smc layers and the backtest
  3. the order each live setup wants for the NEXT candle, unless the checklist rejects it (fib_reject.warnings with the
     live spread; the reason is kept in "why"):
        trend    status "buy stop" / "sell stop": a stop at the high / low of the candle that touched 0.618, stop under
                 the swing low, target 2R. Valid for ONE candle: the next close moves it to the new touch candle or
                 cancels it. Market already through it → a market order at once (the class: "place the buy entry
                 immediately").
        retrace  status "buy limit" / "sell limit": a limit at 0.382, stop under the swing low, target 2R; moved when the
                 swing high moves; cancelled at the next break (BOS / CHoCH) without a fill, or while the checklist
                 rejects it (placed again when it passes). Market already through the level → no order (no chase).
     chart levels are bid prices: a buy fills / a sell is stopped and closed at the ask = bid + spread.
  4. pending → open → closed followed from the broker (orders / positions / deals with this magic), booked
  5. engine_data/fib/state.json: every order and why a setup has none — the /smc page reads it (/api/fib)
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .book import _write, journal, log, money_per_move, stops_gap
from .config import FIB as S, load_control
from .feed import TF_MIN, mt5c, now_ms
from . import fib_reject as FR
from . import fib_trend as F

STATE_FILE = os.path.join(S["DIR"], "state.json")
SYNC_EVERY_MS = 30_000
os.makedirs(S["DIR"], exist_ok=True)


def enabled() -> bool:
    return bool(load_control().get("fib", S["ENABLED"]))


RULES = {r["id"]: r for r in S["RULES"]}          # id → {"rule": trend | retrace, "tf"}


def setups(rule: str, bars: List[Dict]) -> List[Dict]:
    return FR.setups(rule, bars)


def setup_id(rule: str, sym: str, tf: str, s: Dict, bars: List[Dict]) -> str:
    return f"{rule}-{sym}-{tf}-{bars[s['bos_idx']]['t']}"


def wants(rule: str, s: Dict) -> bool:
    """does this setup want an order now (on the last closed candle)?"""
    return s["status"] in (("buy stop", "sell stop") if rule == "trend" else ("buy limit", "sell limit"))


def levels(rule: str, s: Dict, tick: Dict, info: Dict) -> Dict:
    """a live setup + the tick → {"price", "sl", "tp", "market": bool} of its order, or {"why"}"""
    bid, ask = float(tick["bid"]), float(tick["ask"])
    sp = ask - bid
    dg = int(info.get("digits") or 5)
    gap = stops_gap(info)
    buy = s["side"] == "buy"
    want = s["mark"] if rule == "trend" else s["entry_level"]
    price, sl, tp = (want + sp, s["sl"], s["tp"]) if buy else (want, s["sl"] + sp, s["tp"] + sp)
    market = False
    if rule == "trend":                       # a stop order beyond the market; already through it → at once
        if (buy and price <= ask + gap) or (not buy and price >= bid - gap):
            price, market = (ask if buy else bid), True
    else:                                     # a limit behind the market; already through it → skip (no chase)
        if (buy and price >= ask - gap) or (not buy and price <= bid + gap):
            return {"why": f"price {bid:g} is already through 0.618 {want:g}"}
    risk = (price - sl) if buy else (sl - price)
    if risk <= max(gap, 0):
        return {"why": f"stop {risk:g} away: past the stop or inside the broker's stops level"}
    rr = ((tp - price) if buy else (price - tp)) / risk
    if rr < (F.MIN_RR if rule == "trend" else 0.8):
        return {"why": f"RR {rr:.2f} at {price:g} is too small"}
    return {"price": round(price, dg), "sl": round(sl, dg), "tp": round(tp, dg), "spread": sp, "rr": round(rr, 2),
            "market": market}


class FibBook:
    def __init__(self, feed, magic: int = S["MAGIC"]):
        self.feed, self.magic = feed, magic
        self.info: Dict[str, Dict] = {}
        self.bars: Dict[tuple, List[Dict]] = {}       # (symbol, tf) → closed bars
        self.setups: Dict[tuple, List[Dict]] = {}     # (rule id, symbol) → fib_reject setups
        self.ctx: Dict[tuple, Dict] = {}              # (symbol, tf) → fib_reject.context of its candles
        self.orders: Dict[str, Dict] = {}             # setup id → its order: pending → open → closed (or cancelled)
        self.why: Dict[str, str] = {}
        self.fetched: Dict[str, int] = {}             # tf → the bar slot fetched last
        self.synced_at = 0
        self.account: Dict = {}
        try:
            with open(STATE_FILE) as f:
                self.orders = json.load(f).get("orders", {})
        except Exception:
            pass

    def tfs(self) -> Dict[str, str]:
        return {rid: r["tf"] for rid, r in RULES.items()}

    def save(self, on: bool, trading: bool) -> None:
        cut = now_ms() - 30 * 86400_000
        self.orders = {k: v for k, v in self.orders.items() if v["state"] in ("pending", "open") or v.get("ended_ms", 0) > cut}
        done = [o for o in self.orders.values() if o["state"] == "closed"]
        _write(STATE_FILE, {"at": now_ms(), "on": on, "trading": trading, "magic": self.magic, "rules": {rid: {"tf": r["tf"]} for rid, r in RULES.items()},
                            "reject": {k: v["need"] for k, v in FR.REJECT.items()},
                            "symbols": list(self.info), "orders": self.orders, "why": self.why,
                            "totals": {"n": len(done), "won": sum(1 for o in done if (o.get("pnl_usd") or 0) > 0),
                                       "pnl_usd": round(sum(o.get("pnl_usd") or 0 for o in done), 2)}})

    def setup(self) -> None:
        res = mt5c.call([{"op": "info", "symbol": s} for s in S["SYMBOLS"]], timeout=180)
        for s, r in zip(S["SYMBOLS"], res):
            if "result" in r:
                self.info[s] = r["result"]
            else:
                log(f"fib: {s} not available: {r.get('error')}")

    def fetch(self, now: int) -> List[str]:
        """the timeframes with a newly closed bar (5 s after the boundary) → re-read for every symbol"""
        due = []
        for tf in sorted(set(self.tfs().values())):
            ms = TF_MIN[tf] * 60_000
            slot = now // ms
            if slot != self.fetched.get(tf) and now - slot * ms >= 5000:
                due.append(tf)
        if not due:
            return []
        syms = [s for s in S["SYMBOLS"] if s in self.info]
        wants_ = [(s, tf, S["BARS"] if len(self.bars.get((s, tf)) or []) < S["BARS"] // 2 else 12) for tf in due for s in syms]
        got = mt5c.bars_many(wants_, timeout=240, offset=self.feed.clock())
        for tf in due:
            ms = TF_MIN[tf] * 60_000
            for s in syms:
                new = [b for b in got.get((s, tf), []) if b["t"] + ms <= now]
                if not new:
                    continue
                old = [b for b in self.bars.get((s, tf), []) if b["t"] < new[0]["t"]]
                self.bars[(s, tf)] = (old + new)[-S["BARS"]:]
            self.fetched[tf] = now // ms
        return due

    def analyse(self, due: List[str]) -> None:
        for tf in due:
            for s in S["SYMBOLS"]:
                bars = self.bars.get((s, tf)) or []
                if len(bars) < 300:
                    continue
                try:
                    m = F.swing_structure(bars, F.STRUCTURE_N)
                    self.ctx[(s, tf)] = FR.context(bars)
                    for rid, r in RULES.items():
                        if r["tf"] == tf:
                            self.setups[(rid, s)] = FR.setups(r["rule"], bars, m)
                except Exception as e:
                    log(f"fib {tf} {s}: error {type(e).__name__}: {e}")

    def step(self, trading: bool, account: Optional[Dict] = None) -> None:
        now = now_ms()
        self.account = account or {}
        on = enabled()
        if len(self.info) < len(S["SYMBOLS"]) and now - getattr(self, "_setup_at", 0) > 600_000:
            self._setup_at = now
            self.setup()
        due = self.fetch(now)
        live = any(o["state"] in ("pending", "open") for o in self.orders.values())
        if live and (due or now - self.synced_at >= SYNC_EVERY_MS):
            self.sync(now)
        if due:
            self.analyse(due)
            self.plan(now, on, trading, due)
        elif live and not (on and trading) and any(o["state"] == "pending" for o in self.orders.values()):
            self.plan(now, on, trading, sorted(set(self.tfs().values())))
        self.save(on, trading)

    def plan(self, now: int, on: bool, trading: bool, due: List[str]) -> None:
        go = on and trading
        want: Dict[str, tuple] = {}
        for (rid, sym), ss in self.setups.items():
            rule, tf = RULES[rid]["rule"], RULES[rid]["tf"]
            bars = self.bars[(sym, tf)]
            for s in ss:
                if wants(rule, s):
                    want[setup_id(rule, sym, tf, s, bars)] = (rule, sym, tf, s)
        self.why = {k: v for k, v in self.why.items() if k in want}
        reqs, acts = [], []
        for zid, o in self.orders.items():                       # waiting orders whose rule re-read: still wanted?
            if o["state"] != "pending" or (go and o["tf"] not in due):
                continue
            if zid not in want or not go:
                reqs.append({"op": "cancel", "ticket": o["ticket"]})
                acts.append(("cancel", zid, "trading switched off" if not go else
                             "the next candle did not go through the mark" if o["rule"] == "trend" else
                             "the leg broke (BOS / CHoCH) without a pullback to the level"))
        if not go:
            for zid in want:
                if zid not in self.orders:
                    self.why[zid] = "Fib trading is off" if not on else "engine trading is off"
        elif self.margin_low():
            for zid in want:
                self.why[zid] = f"free margin under {S['MIN_FREE_MARGIN_PCT']} % of equity"
        elif want:
            syms = sorted({w[1] for w in want.values()})
            ticks = dict(zip(syms, mt5c.call([{"op": "tick", "symbol": s} for s in syms], timeout=60)))
            for zid, (rule, sym, tf, s) in want.items():
                t = (ticks.get(sym) or {}).get("result")
                o = self.orders.get(zid)
                if o and o["state"] == "cancelled":                 # taken off unfilled earlier (rejected / moved): may come back
                    o = None
                if not t or (o and o["state"] != "pending") or tf not in due:   # only the rules whose candle just closed
                    continue
                lv = levels(rule, s, t, self.info[sym])
                if "why" not in lv:                                 # the reject checklist, with the live spread
                    bars = self.bars[(sym, tf)]
                    ws = FR.warnings(rule, sym, s, bars, self.ctx[(sym, tf)], len(bars),
                                     s["mark"] if rule == "trend" else s["entry_level"], lv["spread"])
                    if len(ws) >= FR.REJECT[rule]["need"]:
                        lv = {"why": "rejected: " + "; ".join(ws)}
                    else:
                        lv["warnings"] = ws
                if "why" in lv:
                    self.why[zid] = lv["why"]
                    if o:                                           # its level moved somewhere it can't be: take it off
                        reqs.append({"op": "cancel", "ticket": o["ticket"]})
                        acts.append(("cancel", zid, lv["why"]))
                    continue
                self.why.pop(zid, None)
                if o is None:
                    c = f"FIB {'T' if rule == 'trend' else 'R'}{'B' if s['side'] == 'buy' else 'S'} {zid.split('-')[-1][-9:]}"
                    if lv["market"]:
                        reqs.append({"op": "order", "symbol": sym, "side": s["side"], "volume": self.lots(sym),
                                     "sl": lv["sl"], "tp": lv["tp"], "magic": self.magic, "comment": c, "deviation": 20})
                    else:
                        reqs.append({"op": "pending", "symbol": sym, "side": s["side"], "volume": self.lots(sym),
                                     "price": lv["price"], "sl": lv["sl"], "tp": lv["tp"], "magic": self.magic, "comment": c})
                    acts.append(("place", zid, (rule, sym, tf, s, lv)))
                elif not lv["market"] and any(abs(lv[k] - o[k]) > float(self.info[sym].get("point") or 0) / 2 for k in ("price", "sl", "tp")):
                    reqs.append({"op": "modify", "ticket": o["ticket"], "price": lv["price"], "sl": lv["sl"], "tp": lv["tp"]})
                    acts.append(("modify", zid, lv))
        if not reqs:
            return
        res = mt5c.call(reqs, timeout=120)
        for (what, zid, x), r in zip(acts, res):
            ok = "result" in r and r["result"].get("ok")
            err = r.get("error") or (f"{r['result'].get('retcode')} {r['result'].get('comment')}" if "result" in r else "")
            if what == "place":
                rule, sym, tf, s, lv = x
                if not ok:
                    self.why[zid] = f"order refused: {err}"
                    journal("fib_refused", id=zid, symbol=sym, why=err)
                    log(f"fib {rule} {sym}: order refused {err}")
                    continue
                res_ = r["result"]
                bars = self.bars[(sym, tf)]
                o = self.orders[zid] = {
                    "id": zid, "rule": rule, "symbol": sym, "tf": tf, "side": s["side"], "swing": s["swing"],
                    "ticket": res_.get("order"), "state": "open" if lv["market"] else "pending", "lots": self.lots(sym),
                    "price": res_.get("price") or lv["price"], "sl": lv["sl"], "tp": lv["tp"], "rr": lv["rr"],
                    "spread": lv["spread"], "warnings": lv.get("warnings", []), "t_bos": bars[s["bos_idx"]]["t"], "H": s["H"], "L": s["L"], "placed_ms": now,
                    "risk_usd": round(self.lots(sym) * abs(lv["price"] - lv["sl"]) * money_per_move(self.info[sym]), 2)}
                if lv["market"]:
                    o.update(entry=o["price"], opened_ms=now, position=res_.get("order"))
                journal("fib_order", **{k: o[k] for k in ("id", "rule", "symbol", "side", "ticket", "price", "sl", "tp", "rr")})
                log(f"fib {rule} {sym}: {'market' if lv['market'] else res_.get('order_type')} {o['lots']} @ {o['price']:g}, "
                    f"SL {o['sl']:g}, TP {o['tp']:g} ({o['rr']}R, risk ${o['risk_usd']})")
            elif what == "cancel":
                o = self.orders[zid]
                if ok:
                    o.update(state="cancelled", ended_ms=now, end=x)
                    journal("fib_cancel", id=zid, symbol=o["symbol"], why=x)
                    log(f"fib {o['rule']} {o['symbol']}: order {o['ticket']} cancelled ({x})")
                else:
                    o["error"] = f"cancel: {err}"
            elif what == "modify":
                o = self.orders[zid]
                if ok:
                    o.update(price=x["price"], sl=x["sl"], tp=x["tp"], rr=x["rr"])
                else:
                    o["error"] = f"modify: {err}"

    def lots(self, sym: str) -> float:
        info = self.info[sym]
        step = float(info.get("volume_step") or 0.01)
        return round(round(max(float(info["volume_min"]), 0.01) / step) * step, 8)

    def margin_low(self) -> bool:
        eq, free = self.account.get("equity"), self.account.get("margin_free")
        return bool(eq and free is not None and float(free) < float(eq) * S["MIN_FREE_MARGIN_PCT"] / 100)

    # ── following the orders at the broker (as sdd_book.py) ──
    def sync(self, now: int) -> None:
        self.synced_at = now
        res = mt5c.call([{"op": "orders", "magic": self.magic}, {"op": "positions", "magic": self.magic}], timeout=60)
        if any("result" not in r for r in res):
            return
        waiting = {o["ticket"] for o in res[0]["result"]}
        pos = {}
        for p in res[1]["result"]:
            pos[p["ticket"]] = p
            pos.setdefault(p.get("identifier"), p)
        for o in self.orders.values():
            if o["state"] == "pending":
                if o["ticket"] in waiting:
                    continue
                p = pos.get(o["ticket"])
                if p:
                    o.update(state="open", entry=p.get("price_open"), opened_ms=now, position=p["ticket"])
                    journal("fib_fill", id=o["id"], symbol=o["symbol"], side=o["side"], entry=o["entry"])
                    log(f"fib {o['rule']} {o['symbol']}: {o['side']} filled @ {o['entry']:g}")
                else:
                    self.book_exit(o, now)
            elif o["state"] == "open":
                p = pos.get(o.get("position", o["ticket"]))
                if p:
                    o.update(price_now=p.get("price_current"), pnl_now=p.get("profit"))
                    if p.get("sl"):
                        o["sl"] = p["sl"]
                else:
                    self.book_exit(o, now)

    def book_exit(self, o: Dict, now: int) -> None:
        ds = mt5c.deals(position=int(o.get("position") or o["ticket"]), days=30)
        ins = [x for x in ds if x.get("entry") == 0]
        outs = [x for x in ds if x.get("entry") == 1]
        if not ds:
            if o["state"] == "pending" and now - o.setdefault("gone_ms", now) > 60_000:
                o.update(state="cancelled", ended_ms=now, end="order gone at the broker (removed by hand?)")
                o.pop("gone_ms", None)
            return
        if not outs:
            if ins and o["state"] == "pending":
                o.update(state="open", entry=ins[0].get("price"), opened_ms=now)
            return
        pnl = round(sum(float(x.get(k) or 0) for x in ds for k in ("profit", "commission", "swap", "fee")), 2)
        reason = {4: "stop", 5: "target"}.get(outs[-1].get("reason"), "closed")
        o.update(state="closed", ended_ms=now, pnl_usd=pnl, end=reason, exit=outs[-1].get("price"),
                 entry=o.get("entry") or (ins[0].get("price") if ins else None))
        o.pop("gone_ms", None)
        journal("fib_exit", id=o["id"], symbol=o["symbol"], pnl_usd=pnl, reason=reason, exit=o["exit"])
        log(f"fib {o['rule']} {o['symbol']}: closed ({reason}) P&L ${pnl}")
