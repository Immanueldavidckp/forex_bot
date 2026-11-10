"""
engine/sdd_book.py — DAVID's supply / demand traded inside the V5 engine (config SDD; David 2026-11-05).

The engine stays the only process that talks to MT5. Each loop (run.py, after V5 and Kronos):
  1. once per closed M15 bar: the bars of every SDD symbol (the first time BARS of them, then the last few, merged)
  2. sd_david.zones() on the closed bars (the same rule and window as the /smc chart's "S&D David" layer)
  3. every valid zone that is live and still FRESH (price has not come back to it) gets one LIMIT order:
        demand (bull BOS) → BUY LIMIT at A's high + the spread (fills when the bid touches A's high),
                            stop A's low, target T1
        supply (bear BOS) → SELL LIMIT at A's low, stop A's high + the spread, target T1 + the spread
     its target follows T1 while the order waits (the recent high / low still grows); it is cancelled when the zone
     ends (a close through candle A, or a CHoCH against it) or was touched without a fill
  4. pending → open → closed is followed from the broker (orders / positions / deals with this magic) and booked
  5. engine_data/sdd/state.json: every zone's order and why a zone has none — the /smc page's right-hand list reads it
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .book import _write, journal, log, money_per_move, stops_gap
from .config import SDD as S, load_control
from .feed import TF_MIN, mt5c, now_ms
from .major_structure import major_structure
from . import sd_david

STATE_FILE = os.path.join(S["DIR"], "state.json")
BAR_MS = TF_MIN[S["TF"]] * 60_000
SYNC_EVERY_MS = 30_000
STRUCTURE_N = 5                           # = smc_compare.STRUCTURE_N
os.makedirs(S["DIR"], exist_ok=True)


def enabled() -> bool:
    return bool(load_control().get("sdd", S["ENABLED"]))


def zone_id(sym: str, z: Dict, bars: List[Dict]) -> str:
    return f"{sym}-{bars[z['break']]['t']}"


def levels(z: Dict, tick: Dict, info: Dict, target: int = S["TARGET"], max_spread_risk: float = S["MAX_SPREAD_RISK"]) -> Dict:
    """One fresh zone + the live tick → {"price", "sl", "tp"} of its limit order, or {"why"} when it can't be placed.
    Chart levels are bid prices: a buy fills / a sell is stopped and closed at the ask = bid + spread."""
    bid, ask = float(tick["bid"]), float(tick["ask"])
    sp = ask - bid
    dg = int(info.get("digits") or 5)
    gap = stops_gap(info)
    tg = (z.get("targets") or [])[target - 1:target]
    if not tg:
        return {"why": "no target"}
    t1 = float(tg[0]["price"])
    buf = S["SL_BUFFER_POINTS"] * float(info.get("point") or 0)
    if z["dir"] == "buy":
        price, sl, tp = z["proximal"] + sp, z["distal"] - buf, t1
        if price >= ask - gap:
            return {"why": f"price {bid:g} is already at / below the entry {z['proximal']:g}"}
        if tp <= price:
            return {"why": f"T1 {tp:g} is not above the entry"}
    else:
        price, sl, tp = z["proximal"], z["distal"] + sp + buf, t1 + sp
        if price <= bid + gap:
            return {"why": f"price {bid:g} is already at / above the entry {z['proximal']:g}"}
        if tp >= price:
            return {"why": f"T1 {t1:g} is not below the entry"}
    risk = abs(price - sl)
    if risk <= max(gap, 0) or risk == 0:
        return {"why": f"stop {risk:g} away is inside the broker's stops level"}
    if sp > max_spread_risk * risk:
        return {"why": f"spread {sp:g} is over {max_spread_risk:.0%} of the stop distance {risk:g}"}
    return {"price": round(price, dg), "sl": round(sl, dg), "tp": round(tp, dg), "spread": sp,
            "rr": round(abs(tp - price) / risk, 2)}


class SddBook:
    def __init__(self, feed, magic: int = S["MAGIC"]):
        self.feed, self.magic = feed, magic
        self.info: Dict[str, Dict] = {}
        self.bars: Dict[str, List[Dict]] = {}
        self.zones: Dict[str, List[Dict]] = {}       # symbol → sd_david zones of its closed bars
        self.orders: Dict[str, Dict] = {}            # zone id → its order: pending → open → closed (or cancelled)
        self.why: Dict[str, str] = {}                # zone id → why it has no order
        self.fetched_slot = 0
        self.synced_at = 0
        self.account: Dict = {}
        self._load()

    # ── persistence ──
    def _load(self) -> None:
        try:
            with open(STATE_FILE) as f:
                st = json.load(f)
        except Exception:
            return
        self.orders = st.get("orders", {})

    def save(self, on: bool, trading: bool) -> None:
        cut = now_ms() - 30 * 86400_000
        self.orders = {k: v for k, v in self.orders.items() if v["state"] in ("pending", "open") or v.get("ended_ms", 0) > cut}
        done = [o for o in self.orders.values() if o["state"] == "closed"]
        _write(STATE_FILE, {"at": now_ms(), "on": on, "trading": trading, "magic": self.magic, "tf": S["TF"],
                            "target": f"T{S['TARGET']}", "symbols": list(self.info), "orders": self.orders, "why": self.why,
                            "totals": {"n": len(done), "won": sum(1 for o in done if (o.get("pnl_usd") or 0) > 0),
                                       "pnl_usd": round(sum(o.get("pnl_usd") or 0 for o in done), 2)}})

    # ── MT5 reads ──
    def symbols(self) -> List[str]:
        if S["SYMBOLS"] != "all":
            return list(S["SYMBOLS"])
        return list(dict.fromkeys(list(S.get("SYMBOLS_EXTRA") or []) + list(self.feed.symbols)))

    def setup(self) -> None:
        syms = self.symbols()
        res = mt5c.call([{"op": "info", "symbol": s} for s in syms], timeout=180)
        for s, r in zip(syms, res):
            if "result" in r:
                self.info[s] = r["result"]
            else:
                log(f"sdd: {s} not available: {r.get('error')}")

    def fetch(self, now: int) -> bool:
        """Once per closed bar (5 s after the boundary). → True when new bars came in."""
        slot = now // BAR_MS
        if slot == self.fetched_slot or now - slot * BAR_MS < 5000:
            return False
        syms = [s for s in self.symbols() if s in self.info]
        wants = [(s, S["TF"], S["BARS"] if len(self.bars.get(s) or []) < S["BARS"] // 2 else 12) for s in syms]
        got = mt5c.bars_many(wants, timeout=240, offset=self.feed.clock())
        for s in syms:
            new = [b for b in got.get((s, S["TF"]), []) if b["t"] + BAR_MS <= now]       # closed bars only
            if not new:
                continue
            old = [b for b in self.bars.get(s, []) if b["t"] < new[0]["t"]]
            self.bars[s] = (old + new)[-S["BARS"]:]
        self.fetched_slot = slot
        return True

    def analyse(self) -> None:
        for s, bars in self.bars.items():
            if len(bars) < 200:
                continue
            try:
                self.zones[s] = sd_david.zones(bars, major_structure(bars, STRUCTURE_N), STRUCTURE_N)
            except Exception as e:
                log(f"sdd {s}: zones error {type(e).__name__}: {e}")

    # ── the loop step ──
    def step(self, trading: bool, account: Optional[Dict] = None) -> None:
        now = now_ms()
        self.account = account or {}
        on = enabled()
        if not self.info or len(self.info) < len(self.symbols()) and now - getattr(self, "_setup_at", 0) > 600_000:
            self._setup_at = now
            self.setup()
        new = self.fetch(now)
        live = any(o["state"] in ("pending", "open") for o in self.orders.values())
        if live and (new or now - self.synced_at >= SYNC_EVERY_MS):
            self.sync(now)
        if new:
            self.analyse()
            self.plan(now, on, trading)
        elif live and not (on and trading) and any(o["state"] == "pending" for o in self.orders.values()):
            self.plan(now, on, trading)                # switched off: take the waiting orders back off now
        self.save(on, trading)

    def plan(self, now: int, on: bool, trading: bool) -> None:
        """Every fresh zone → a limit order; every pending order whose zone is over (or that is off) → cancelled;
        a waiting order's target follows T1. All in one bridge call."""
        go = on and trading
        reqs: List[Dict] = []
        acts: List[tuple] = []
        want: Dict[str, Dict] = {}                     # zone id → (sym, zone) of the fresh zones
        for s, zs in self.zones.items():
            bars = self.bars[s]
            for z in zs:
                if z["valid"] and z["live"] and z["status"] == "fresh":
                    want[zone_id(s, z, bars)] = (s, z)
        self.why = {k: v for k, v in self.why.items() if k in want}
        for zid, o in self.orders.items():             # waiting orders: still wanted?
            if o["state"] != "pending" or (go and o["symbol"] not in self.zones):   # no bars for it this time: leave it
                continue
            if zid not in want or not go:
                why = "trading switched off" if not go else self._end_why(o)
                reqs.append({"op": "cancel", "ticket": o["ticket"]})
                acts.append(("cancel", zid, why))
        new_zones = [(zid, sz) for zid, sz in want.items() if zid not in self.orders]
        if not go:
            for zid, _ in new_zones:
                self.why[zid] = "S&D David trading is off" if not on else "engine trading is off"
        elif self.margin_low():
            for zid, _ in new_zones:
                self.why[zid] = f"free margin under {S['MIN_FREE_MARGIN_PCT']} % of equity"
        else:
            syms = sorted({s for _, (s, _) in new_zones} | {self.orders[z]["symbol"] for z in want if z in self.orders
                                                              and self.orders[z]["state"] == "pending"})
            ticks = dict(zip(syms, mt5c.call([{"op": "tick", "symbol": s} for s in syms], timeout=60))) if syms else {}
            for zid, (s, z) in want.items():
                t = (ticks.get(s) or {}).get("result")
                if not t:
                    continue
                lv = levels(z, t, self.info[s])
                o = self.orders.get(zid)
                if o is None:
                    if "why" in lv:
                        self.why[zid] = lv["why"]
                        continue
                    self.why.pop(zid, None)
                    reqs.append({"op": "pending", "symbol": s, "side": z["dir"], "volume": self.lots(s), "price": lv["price"],
                                 "sl": lv["sl"], "tp": lv["tp"], "magic": self.magic,
                                 "comment": f"SDD {'D' if z['dir'] == 'buy' else 'S'} {zid.split('-')[-1][-9:]}"})
                    acts.append(("place", zid, (s, z, lv)))
                elif o["state"] == "pending" and "tp" in lv:
                    # the stop the rule wants now (SL_BUFFER_POINTS beyond A; a sell keeps the spread it was placed with,
                    # so a moving spread doesn't move the stop every loop)
                    info = self.info[s]
                    buf = S["SL_BUFFER_POINTS"] * float(info.get("point") or 0)
                    want_sl = round(z["distal"] - buf if z["dir"] == "buy" else z["distal"] + float(o.get("spread") or 0) + buf,
                                    int(info.get("digits") or 5))
                    sl_move = abs(want_sl - o["sl"]) > float(info.get("point") or 0) / 2
                    if sl_move or abs(lv["tp"] - o["tp"]) > 1e-9:
                        reqs.append({"op": "modify", "ticket": o["ticket"], "tp": lv["tp"], "sl": want_sl if sl_move else o["sl"]})
                        acts.append(("tp", zid, (lv["tp"], want_sl if sl_move else None)))
        if not reqs:
            return
        res = mt5c.call(reqs, timeout=120)
        for (what, zid, x), r in zip(acts, res):
            ok = "result" in r and r["result"].get("ok")
            err = r.get("error") or (f"{r['result'].get('retcode')} {r['result'].get('comment')}" if "result" in r else "")
            if what == "place":
                s, z, lv = x
                if not ok:
                    self.why[zid] = f"order refused: {err}"
                    journal("sdd_refused", id=zid, symbol=s, why=err)
                    log(f"sdd {s}: order refused {err}")
                    continue
                o = self.orders[zid] = {
                    "id": zid, "symbol": s, "side": z["dir"], "zone": z["side"], "ticket": r["result"].get("order"),
                    "state": "pending", "lots": self.lots(s), "price": lv["price"], "sl": lv["sl"], "tp": lv["tp"], "rr": lv["rr"],
                    "spread": lv["spread"], "t_break": self.bars[s][z["break"]]["t"], "t_a": self.bars[s][z["a"]]["t"],
                    "zone_top": z["top"], "zone_bottom": z["bottom"], "placed_ms": now,
                    "risk_usd": round(self.lots(s) * abs(lv["price"] - lv["sl"]) * money_per_move(self.info[s]), 2)}
                try:                                   # the checklist the dashboard shows for this trade (trade_checks.py)
                    from .trade_checks import chk, sdd_checks
                    w = sdd_checks(z, self.bars[s], lv, gap=stops_gap(self.info[s]))
                    o["checks"] = w["checks"] + [
                        chk("Guard", "Free margin", "enough", f"≥ {S['MIN_FREE_MARGIN_PCT']} % of equity", True),
                        chk("Guard", "S&D David + engine trading", "both ON", "", True),
                        chk("Guard", "Order kept until", "filled, or the zone ends (close through A / CHoCH against) or is touched unfilled",
                            "then cancelled", None)]
                    o["marks"] = w["marks"]
                except Exception as e:
                    log(f"sdd {s}: checklist failed {type(e).__name__}: {e}")
                journal("sdd_order", **{k: o[k] for k in ("id", "symbol", "side", "ticket", "price", "sl", "tp", "rr")})
                log(f"sdd {s}: {r['result'].get('order_type')} {o['lots']} @ {o['price']:g}, SL {o['sl']:g}, TP {o['tp']:g} "
                    f"({o['rr']}R, risk ${o['risk_usd']})")
            elif what == "cancel":
                o = self.orders[zid]
                if ok:
                    o.update(state="cancelled", ended_ms=now, end=x)
                    journal("sdd_cancel", id=zid, symbol=o["symbol"], why=x)
                    log(f"sdd {o['symbol']}: order {o['ticket']} cancelled ({x})")
                else:
                    o["error"] = f"cancel: {err}"          # filled meanwhile? the next sync finds out
            elif what == "tp":
                o = self.orders[zid]
                if ok:
                    o["tp"] = x[0]
                    if x[1] is not None:
                        old = o["sl"]
                        o["sl"] = x[1]
                        o["risk_usd"] = round(o["lots"] * abs(o["price"] - x[1]) * money_per_move(self.info[o["symbol"]]), 2)
                        o["rr"] = round(abs(o["tp"] - o["price"]) / abs(o["price"] - x[1]), 2) if o["price"] != x[1] else o.get("rr")
                        journal("sdd_sl_move", id=zid, symbol=o["symbol"], old=old, sl=x[1], why="SL_BUFFER_POINTS")
                        log(f"sdd {o['symbol']}: stop {old:g} → {x[1]:g} ({S['SL_BUFFER_POINTS']} points beyond the zone)")
                else:
                    o["error"] = f"target / stop move: {err}"

    def _end_why(self, o: Dict) -> str:
        z = next((z for z in self.zones.get(o["symbol"], []) if z["valid"] and self.bars[o["symbol"]][z["break"]]["t"] == o["t_break"]), None)
        if z is None:
            return "zone gone from the chart"
        if z["status"] == "broken":
            return "zone broken (a close through candle A)"
        if z["superseded_idx"] is not None:
            return "CHoCH against the zone"
        if z["status"] == "tested":
            return "price touched the zone without filling the order"
        return "zone over"

    def lots(self, sym: str) -> float:
        info = self.info[sym]
        step = float(info.get("volume_step") or 0.01)
        return round(round(max(float(info["volume_min"]), 0.01) / step) * step, 8)

    def margin_low(self) -> bool:
        eq, free = self.account.get("equity"), self.account.get("margin_free")
        return bool(eq and free is not None and float(free) < float(eq) * S["MIN_FREE_MARGIN_PCT"] / 100)

    # ── following the orders at the broker ──
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
                    journal("sdd_fill", id=o["id"], symbol=o["symbol"], side=o["side"], entry=o["entry"])
                    log(f"sdd {o['symbol']}: {o['side']} filled @ {o['entry']:g}")
                else:
                    self.book_exit(o, now)              # filled and closed between two looks, or removed by hand
            elif o["state"] == "open":
                p = pos.get(o.get("position", o["ticket"]))
                if p:
                    o.update(price_now=p.get("price_current"), pnl_now=p.get("profit"))
                    if p.get("sl"):                 # a stop moved at the broker by hand shows on /smc and the trade window
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
                log(f"sdd {o['symbol']}: order {o['ticket']} gone at the broker")
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
        journal("sdd_exit", id=o["id"], symbol=o["symbol"], pnl_usd=pnl, reason=reason, exit=o["exit"])
        log(f"sdd {o['symbol']}: closed ({reason}) P&L ${pnl}")
