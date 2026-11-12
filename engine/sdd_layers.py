"""
engine/sdd_layers.py — S&D David traded with LAYER entries (class video 6 [28:01–31:52]; David 2026-11-12: "implement
this into the live and we have to track this vs now normal tp how this differ").

The same zones as engine/sdd_book.py (its bars and zones are shared — one bar fetch for both), a second way to trade
them, on its own magic, so every zone has a normal result and a layered result to compare (dashboard /api/sdd/compare):

  entries   three limit orders per FRESH zone, minimum lot each
              L1  the FVG's near edge — the first thing price touches coming back (demand: candle C's low, supply: C's high)
              L2  candle A's wick = the normal S&D David entry (demand: A's high, supply: A's low)
              L3  candle A's 50 % line
            a layer price has already passed when the zone is first seen is skipped (it would fill at once)
  stop      one for all three, the S&D David stop: beyond candle A by SL_BUFFER_POINTS (a sell adds the spread)
  targets   measured from L1 to the leg's extreme (sd_david's fib_ext = the class's "overall target"):
              L1 → TP_FRACS[0] (50 %), L2 → 75 %, L3 → 100 %. While nothing has filled they follow the extreme.
  managing  a layer takes its target → the zone's waiting layers are cancelled, its open layers go to break-even
            (their own entry); a second target → the last layer's stop goes to the first target
  cancel    waiting layers go when the zone ends (close through A / CHoCH against it), when a layer of the zone took
            its target, or when trading is switched off — the same life as the normal S&D David order

engine_data/sdd_layers/state.json: every layer (pending → open → closed / cancelled / skipped) with its zone id
(= the S&D David order id of that zone), read by the dashboard's trade lists, the S&D layers room and the comparison.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .book import _write, journal, log, money_per_move, stops_gap
from .config import SDD as SD, SDD_LAYERS as S, load_control
from .feed import mt5c, now_ms
from .sdd_book import zone_id

STATE_FILE = os.path.join(S["DIR"], "state.json")
SYNC_EVERY_MS = 30_000
os.makedirs(S["DIR"], exist_ok=True)
NAMES = {1: "FVG edge", 2: "candle A's wick", 3: "A's 50 % line"}


def enabled() -> bool:
    return bool(load_control().get("sdd_layers", S["ENABLED"]))


def layer_plan(z: Dict, tick: Dict, info: Dict, fracs: List[float] = None) -> Dict:
    """One fresh zone + the live tick → {"layers": [{"k", "price", "sl", "tp", "rr"} or {"k", "why"}], "ext", "spread"}
    (bid-level chart prices; a buy fills at the ask, a sell is stopped / closed at the ask), or {"why"}."""
    fracs = fracs or S["TP_FRACS"]
    bid, ask = float(tick["bid"]), float(tick["ask"])
    sp = ask - bid
    dg = int(info.get("digits") or 5)
    pt = float(info.get("point") or 0)
    gap = stops_gap(info)
    buy = z["dir"] == "buy"
    fv, ext = z.get("fvg") or {}, z.get("fib_ext")
    if ext is None or not fv:
        return {"why": "zone has no FVG / no leg extreme"}
    buf = SD["SL_BUFFER_POINTS"] * pt
    l1 = float(fv["top"] if buy else fv["bottom"])               # the FVG's near edge
    lv = [l1, float(z["proximal"]), float(z.get("mid") if z.get("mid") is not None else (z["top"] + z["bottom"]) / 2)]
    if (buy and not lv[0] >= lv[1] >= lv[2]) or (not buy and not lv[0] <= lv[1] <= lv[2]):
        return {"why": f"layers out of order {lv}"}
    if (buy and ext <= l1) or (not buy and ext >= l1):
        return {"why": f"the leg's extreme {ext:g} is not beyond the first layer {l1:g}"}
    sl = z["distal"] - buf if buy else z["distal"] + sp + buf
    out = []
    for k, (e, f) in enumerate(zip(lv, fracs), 1):
        price = e + sp if buy else e                             # a buy limit fills when the ASK reaches e + spread
        tp = l1 + f * (ext - l1) + (0 if buy else sp)            # a sell closes at the ask
        risk = abs(price - sl)
        if buy and price >= ask - gap or not buy and price <= bid + gap:
            out.append({"k": k, "why": f"price {bid:g} is already past this layer ({e:g})"})
        elif risk <= max(gap, 0) or risk == 0:
            out.append({"k": k, "why": f"stop {risk:g} away is inside the broker's stops level"})
        elif sp > SD["MAX_SPREAD_RISK"] * risk:
            out.append({"k": k, "why": f"spread {sp:g} is over {SD['MAX_SPREAD_RISK']:.0%} of the stop distance {risk:g}"})
        elif (buy and tp <= price) or (not buy and tp >= price):
            out.append({"k": k, "why": f"target {tp:g} is not beyond the entry {price:g}"})
        else:
            out.append({"k": k, "price": round(price, dg), "sl": round(sl, dg), "tp": round(tp, dg),
                        "rr": round(abs(tp - price) / risk, 2)})
    return {"layers": out, "ext": ext, "spread": sp}


def marks(z: Dict, t_a: int, plan: Dict, side: str) -> List[Dict]:
    """What the layered trade looks at, for the trade chart: candle A, the FVG, the three entries, targets and the stop."""
    col = "76,175,80" if side == "buy" else "239,83,80"
    m = [{"type": "box", "t0": t_a, "top": z["top"], "bottom": z["bottom"], "label": f"{z['side']} · candle A", "color": col},
         {"type": "box", "t0": t_a, "top": z["fvg"]["top"], "bottom": z["fvg"]["bottom"], "label": "FVG (A-B-C)", "color": "245,197,66"}]
    for L in plan["layers"]:
        if "price" in L:
            m.append({"type": "line", "t0": t_a, "price": L["price"], "label": f"L{L['k']} entry", "color": "#e6e9ef", "dash": [2, 3]})
            m.append({"type": "line", "t0": t_a, "price": L["tp"], "label": f"TP{L['k']}", "color": "102,187,106", "dash": [6, 4]})
    return m


class SddLayerBook:
    def __init__(self, main, magic: int = S["MAGIC"]):
        self.main, self.magic = main, magic             # main = the SddBook: its info, bars and zones are used here
        self.orders: Dict[str, Dict] = {}               # "<zone id>#L<k>" → one layer
        self.why: Dict[str, str] = {}                   # zone id → why the zone has no layers
        self.seen_slot = 0
        self.synced_at = 0
        self._load()

    def _load(self) -> None:
        try:
            with open(STATE_FILE) as f:
                self.orders = json.load(f).get("orders", {})
        except Exception:
            pass

    def save(self, on: bool, trading: bool) -> None:
        cut = now_ms() - 30 * 86400_000
        self.orders = {k: v for k, v in self.orders.items()
                       if v["state"] in ("pending", "open") or v.get("ended_ms", v.get("placed_ms", 0)) > cut}
        done = [o for o in self.orders.values() if o["state"] == "closed"]
        _write(STATE_FILE, {"at": now_ms(), "on": on, "trading": trading, "magic": self.magic, "tp_fracs": S["TP_FRACS"],
                            "orders": self.orders, "why": self.why,
                            "totals": {"n": len(done), "won": sum(1 for o in done if (o.get("pnl_usd") or 0) > 0),
                                       "pnl_usd": round(sum(o.get("pnl_usd") or 0 for o in done), 2)}})

    def zone_layers(self, zid: str) -> List[Dict]:
        return [o for o in self.orders.values() if o["zone_id"] == zid]

    # ── the loop step (after SddBook.step: its bars / zones are fresh) ──
    def step(self, trading: bool, account: Optional[Dict] = None) -> None:
        now = now_ms()
        on = enabled()
        live = any(o["state"] in ("pending", "open") for o in self.orders.values())
        new = self.main.fetched_slot != self.seen_slot
        if live and (new or now - self.synced_at >= SYNC_EVERY_MS):
            self.sync(now)
        if new:
            self.seen_slot = self.main.fetched_slot
            self.plan(now, on, trading, account or {})
        elif live and not (on and trading) and any(o["state"] == "pending" for o in self.orders.values()):
            self.plan(now, on, trading, account or {})
        self.save(on, trading)

    def plan(self, now: int, on: bool, trading: bool, account: Dict) -> None:
        go = on and trading
        zones: Dict[str, tuple] = {}                     # every valid zone the main book sees: zone id → (symbol, zone)
        for s, zs in self.main.zones.items():
            for z in zs:
                if z["valid"]:
                    zones[zone_id(s, z, self.main.bars[s])] = (s, z)
        reqs, acts = [], []
        for key, o in self.orders.items():               # waiting layers: still wanted?
            if o["state"] != "pending" or (go and o["symbol"] not in self.main.zones):
                continue
            sz = zones.get(o["zone_id"])
            why = None
            if not go:
                why = "trading switched off"
            elif sz is None:
                why = "zone gone from the chart"
            elif not sz[1]["live"]:
                why = "zone broken (a close through candle A)" if sz[1]["status"] == "broken" else "CHoCH against the zone"
            elif any(x["state"] == "closed" and x.get("end") == "target" for x in self.zone_layers(o["zone_id"])):
                why = "another layer of this zone took its target"
            if why:
                reqs.append({"op": "cancel", "ticket": o["ticket"]})
                acts.append(("cancel", key, why))
        fresh = {zid: sz for zid, sz in zones.items() if sz[1]["live"] and sz[1]["status"] == "fresh"}
        self.why = {k: v for k, v in self.why.items() if k in fresh}
        new_zones = [(zid, sz) for zid, sz in fresh.items() if not self.zone_layers(zid)]
        idle = [zid for zid, _ in fresh.items() if self.zone_layers(zid)
                and not any(o["state"] in ("open", "closed") for o in self.zone_layers(zid))]
        if not go:
            for zid, _ in new_zones:
                self.why[zid] = "S&D layers trading is off" if not on else "engine trading is off"
        elif self._margin_low(account):
            for zid, _ in new_zones:
                self.why[zid] = f"free margin under {SD['MIN_FREE_MARGIN_PCT']} % of equity"
        else:
            syms = sorted({fresh[z][0] for z, _ in new_zones} | {fresh[z][0] for z in idle})
            ticks = dict(zip(syms, mt5c.call([{"op": "tick", "symbol": s} for s in syms], timeout=60))) if syms else {}
            for zid, (s, z) in new_zones:
                t = (ticks.get(s) or {}).get("result")
                if not t:
                    continue
                pl = layer_plan(z, t, self.main.info[s])
                if "why" in pl:
                    self.why[zid] = pl["why"]
                    continue
                for L in pl["layers"]:
                    if "why" in L:
                        self.orders[f"{zid}#L{L['k']}"] = self._record(zid, s, z, L, pl, now, state="skipped", end=L["why"])
                        continue
                    reqs.append({"op": "pending", "symbol": s, "side": z["dir"], "volume": self.main.lots(s), "price": L["price"],
                                 "sl": L["sl"], "tp": L["tp"], "magic": self.magic,
                                 "comment": f"SDL{L['k']} {'D' if z['dir'] == 'buy' else 'S'} {zid.split('-')[-1][-8:]}"})
                    acts.append(("place", f"{zid}#L{L['k']}", (zid, s, z, L, pl)))
            for zid in idle:                             # nothing filled yet: the targets follow the leg's extreme
                s, z = fresh[zid]
                t = (ticks.get(s) or {}).get("result")
                if not t:
                    continue
                pl = layer_plan(z, t, self.main.info[s])
                for L in pl.get("layers", []):
                    o = self.orders.get(f"{zid}#L{L['k']}")
                    if o and o["state"] == "pending" and "tp" in L and abs(L["tp"] - o["tp"]) > 1e-9:
                        reqs.append({"op": "modify", "ticket": o["ticket"], "tp": L["tp"], "sl": o["sl"]})
                        acts.append(("tp", o["key"], L["tp"]))
        if not reqs:
            return
        res = mt5c.call(reqs, timeout=120)
        for (what, key, x), r in zip(acts, res):
            ok = "result" in r and r["result"].get("ok")
            err = r.get("error") or (f"{r['result'].get('retcode')} {r['result'].get('comment')}" if "result" in r else "")
            if what == "place":
                zid, s, z, L, pl = x
                if not ok:
                    self.orders[key] = self._record(zid, s, z, L, pl, now, state="skipped", end=f"order refused: {err}")
                    journal("sdl_refused", id=key, symbol=s, why=err)
                    log(f"sdd layers {s} L{L['k']}: order refused {err}")
                    continue
                o = self.orders[key] = self._record(zid, s, z, L, pl, now, state="pending", ticket=r["result"].get("order"))
                journal("sdl_order", **{k: o[k] for k in ("id", "symbol", "side", "layer", "ticket", "price", "sl", "tp", "rr")})
                log(f"sdd layers {s} L{L['k']} ({NAMES[L['k']]}): {o['lots']} @ {o['price']:g}, SL {o['sl']:g}, TP {o['tp']:g} "
                    f"({o['rr']}R, risk ${o['risk_usd']})")
            elif what == "cancel":
                o = self.orders[key]
                if ok:
                    o.update(state="cancelled", ended_ms=now, end=x)
                    journal("sdl_cancel", id=key, symbol=o["symbol"], why=x)
                    log(f"sdd layers {o['symbol']} L{o['layer']}: cancelled ({x})")
                else:
                    o["error"] = f"cancel: {err}"
            elif what == "tp":
                o = self.orders[key]
                if ok:
                    o["tp"] = x
                    o["rr"] = round(abs(x - o["price"]) / abs(o["price"] - o["sl"]), 2) if o["price"] != o["sl"] else o.get("rr")
                else:
                    o["error"] = f"target move: {err}"

    def _record(self, zid, s, z, L, pl, now, **kw) -> Dict:
        bars, info = self.main.bars[s], self.main.info[s]
        t_a = bars[z["a"]]["t"]
        o = {"id": f"{zid}#L{L['k']}", "key": f"{zid}#L{L['k']}", "zone_id": zid, "layer": L["k"], "where": NAMES[L["k"]],
             "symbol": s, "side": z["dir"], "zone": z["side"], "lots": self.main.lots(s),
             "price": L.get("price"), "sl": L.get("sl"), "tp": L.get("tp"), "rr": L.get("rr"), "spread": pl["spread"],
             "ext": pl["ext"], "t_break": bars[z["break"]]["t"], "t_a": t_a, "zone_top": z["top"], "zone_bottom": z["bottom"],
             "zone_mid": z.get("mid"), "fvg_top": z["fvg"]["top"], "fvg_bottom": z["fvg"]["bottom"], "placed_ms": now,
             "tp1": next((x["tp"] for x in pl["layers"] if x["k"] == 1 and "tp" in x), None)}
        if L.get("price") is not None:
            o["risk_usd"] = round(o["lots"] * abs(L["price"] - L["sl"]) * money_per_move(info), 2)
        try:
            from .trade_checks import chk, sdd_checks
            w = sdd_checks(z, bars, {"price": L.get("price"), "sl": L.get("sl"), "tp": L.get("tp"), "rr": L.get("rr")},
                           gap=stops_gap(info))
            o["checks"] = [c for c in w["checks"] if c.get("group") == "Setup"] + [
                chk("Layer", f"L{L['k']}: {NAMES[L['k']]}", f"limit {L.get('price')}",
                    "L1 the FVG's near edge · L2 candle A's wick · L3 A's 50 % line (class video 6, 28:01)", "price" in L),
                chk("Layer", "Stop", f"{L.get('sl')}", "one stop for all layers: beyond candle A (as S&D David)", "price" in L),
                chk("Layer", f"Target TP{L['k']}", f"{L.get('tp')} ({L.get('rr')} R)",
                    f"{S['TP_FRACS'][L['k'] - 1]:.0%} of the way from L1 to the leg's extreme {pl['ext']:g}", "price" in L),
                chk("Layer", "After a target", "waiting layers cancelled · open ones to break-even · after 2 targets the last to TP1",
                    "class video 6, 30:19–30:44", None)]
            o["marks"] = marks(z, t_a, pl, z["dir"])
        except Exception as e:
            log(f"sdd layers {s}: checklist failed {type(e).__name__}: {e}")
        o.update(kw)
        if kw.get("state") == "skipped":
            o["ended_ms"] = now
        return o

    @staticmethod
    def _margin_low(account: Dict) -> bool:
        eq, free = account.get("equity"), account.get("margin_free")
        return bool(eq and free is not None and float(free) < float(eq) * SD["MIN_FREE_MARGIN_PCT"] / 100)

    # ── following the layers at the broker ──
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
        touched = set()
        for o in self.orders.values():
            if o["state"] == "pending":
                if o["ticket"] in waiting:
                    continue
                p = pos.get(o["ticket"])
                if p:
                    o.update(state="open", entry=p.get("price_open"), opened_ms=now, position=p["ticket"])
                    journal("sdl_fill", id=o["id"], symbol=o["symbol"], side=o["side"], entry=o["entry"])
                    log(f"sdd layers {o['symbol']} L{o['layer']}: filled @ {o['entry']:g}")
                elif self.book_exit(o, now):
                    touched.add(o["zone_id"])
            elif o["state"] == "open":
                p = pos.get(o.get("position", o["ticket"]))
                if p:
                    o.update(price_now=p.get("price_current"), pnl_now=p.get("profit"))
                    if p.get("sl"):
                        o["sl"] = p["sl"]
                elif self.book_exit(o, now):
                    touched.add(o["zone_id"])
        for zid in touched:
            self.after_target(zid, now)

    def book_exit(self, o: Dict, now: int) -> bool:
        """→ True when the layer closed at its target."""
        ds = mt5c.deals(position=int(o.get("position") or o["ticket"]), days=30)
        ins = [x for x in ds if x.get("entry") == 0]
        outs = [x for x in ds if x.get("entry") == 1]
        if not ds:
            if o["state"] == "pending" and now - o.setdefault("gone_ms", now) > 60_000:
                o.update(state="cancelled", ended_ms=now, end="order gone at the broker (removed by hand?)")
                o.pop("gone_ms", None)
            return False
        if not outs:
            if ins and o["state"] == "pending":
                o.update(state="open", entry=ins[0].get("price"), opened_ms=now)
            return False
        pnl = round(sum(float(x.get(k) or 0) for x in ds for k in ("profit", "commission", "swap", "fee")), 2)
        reason = {4: "stop", 5: "target"}.get(outs[-1].get("reason"), "closed")
        if reason == "stop" and o.get("be"):
            reason = "break-even" if abs(pnl) < max(0.05, 0.1 * (o.get("risk_usd") or 0)) else "trailed stop"
        o.update(state="closed", ended_ms=now, pnl_usd=pnl, end=reason, exit=outs[-1].get("price"),
                 entry=o.get("entry") or (ins[0].get("price") if ins else None), opened_ms=o.get("opened_ms") or now)
        o.pop("gone_ms", None)
        journal("sdl_exit", id=o["id"], symbol=o["symbol"], layer=o["layer"], pnl_usd=pnl, reason=reason, exit=o["exit"])
        log(f"sdd layers {o['symbol']} L{o['layer']}: closed ({reason}) P&L ${pnl}")
        return reason == "target"

    def after_target(self, zid: str, now: int) -> None:
        """A layer of this zone took its target: cancel the waiting ones; open ones to break-even, after two targets the
        last one's stop to TP1 (class video 6, 30:19–30:44)."""
        Ls = self.zone_layers(zid)
        hits = sorted((x for x in Ls if x["state"] == "closed" and x.get("end") == "target"), key=lambda x: x["layer"])
        reqs, acts = [], []
        for o in Ls:
            if o["state"] == "pending":
                reqs.append({"op": "cancel", "ticket": o["ticket"]})
                acts.append(("cancel", o))
            elif o["state"] == "open" and o.get("entry") is not None:
                buy = o["side"] == "buy"
                want = o["entry"] if len(hits) < 2 else (hits[0].get("tp") or o["entry"])
                better = want > (o["sl"] or -1e18) if buy else want < (o["sl"] or 1e18)
                if better:
                    reqs.append({"op": "sltp", "ticket": o.get("position", o["ticket"]), "sl": want, "tp": o["tp"]})
                    acts.append(("sl", o, want))
        if not reqs:
            return
        for a, r in zip(acts, mt5c.call(reqs, timeout=60)):
            ok = "result" in r and r["result"].get("ok")
            o = a[1]
            if a[0] == "cancel" and ok:
                o.update(state="cancelled", ended_ms=now, end="another layer of this zone took its target")
                journal("sdl_cancel", id=o["id"], symbol=o["symbol"], why=o["end"])
            elif a[0] == "sl" and ok:
                old, o["sl"], o["be"] = o["sl"], a[2], True
                journal("sdl_sl_move", id=o["id"], symbol=o["symbol"], old=old, sl=a[2], why="a layer took its target")
                log(f"sdd layers {o['symbol']} L{o['layer']}: stop {old:g} → {a[2]:g} (a layer took its target)")
            elif not ok:
                o["error"] = f"{a[0]}: {r.get('error') or r.get('result')}"
