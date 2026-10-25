"""
engine/book.py — picker, executor and monitor for the V5 strategy, and the files the dashboard reads.

  Picker    on every new M5 bar, for every symbol and every setup timeframe: the H4 + H1 bias (they must
            agree, David 2026-10-25), the BOS / CHoCH structure, and after every BOS its supply / demand (or
            mitigation block) + FVG setup (both sides, so the chart shows why; only the bias side trades).
            Three entries: S&D M15 and S&D M30 (a setup of that timeframe) and S&D H4 (price back at an H4
            setup → an M15 BOS / CHoCH from inside the H4 zone → that M15 move's own setup). Price coming back to the entry (10 % inside
            the chosen FVG) of a live, bias-aligned setup on a trade timeframe is a signal; a pullback the
            engine did not see live is "missed", never traded late; a newer BOS the same way supersedes it.
  Executor  signal → NORMAL entry at the market (2.5 % of equity, SL = this setup's zone + buffer, TP = the
            first untouched opposite structure ≥ 1:3) and ONE dynamic LAYER as a pending limit order (1.5 %),
            same SL and TP. David's SL/TP fix (2026-10-24): right before the order every level is checked to
            belong to this one setup; a stop over 3 × the M15 ATR, no structure target at ≥ 1:3, or either
            on the wrong side → no trade (nothing is moved to pass). Never more than max_running_trades positions + pending layers. Watch mode (trading
            off, the default) records the signal and sends nothing.
  Monitor   every loop: layer fill → Mode B; Mode A keeps the original SL until the price got very close to
            the final target and turns (→ break-even); Mode B moves both SLs past the first entry at
            Target 1 and then trails M5 swings; from 3R the stop locks (n − 2)R at nR and trails M5 swings;
            a stop only ever moves toward profit. A closed normal cancels its pending layer; a close beyond
            the zone on the setup's timeframe cancels an unfilled layer. Exits are booked from the broker's deals.
  Commands  from the dashboard (commands.jsonl): trading on/off, cancel a setup, close a setup or a ticket.
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import os
import time
from typing import Dict, List, Optional

from . import filters as FL
from . import strategy as V
from .config import (COMMANDS_FILE, ENGINE, JOURNAL_FILE, OVERVIEW_FILE, STATE_FILE, STRATEGY as S, VIEW_DIR,
                     load_control, save_control)
from .feed import TF_MIN, Feed, mt5c, now_ms

ACTIVE = ("waiting pullback",)
ZONE = "zone reached"                          # an H4 setup price came back to: S&D H4 watches M15 inside it


def log(msg: str) -> None:
    print(f"[v5 {_dt.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _write(path: str, obj) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, separators=(",", ":"), default=str)
    os.replace(tmp, path)


IST = _dt.timezone(_dt.timedelta(hours=5, minutes=30), "IST")    # David 2026-10-24: times he reads are Indian time


def hm(ms: int) -> str:
    return _dt.datetime.fromtimestamp(ms / 1000, IST).strftime("%a %H:%M IST")


def journal(event: str, **kw) -> None:
    rec = {"at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "event": event, **kw}
    with open(JOURNAL_FILE, "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def money_per_move(info: Dict) -> float:
    tv, ts = float(info.get("trade_tick_value") or 0), float(info.get("trade_tick_size") or 0)
    return tv / ts if tv > 0 and ts > 0 else float(info.get("trade_contract_size") or 1.0)


def floor_step(x: float, step: float) -> float:
    return round(math.floor(x / step + 1e-9) * step, 8)


def stops_gap(info: Dict) -> float:
    """The broker's minimum distance from the market for a stop, a target or a pending order (+ margin)."""
    return float(info.get("trade_stops_level") or 0) * float(info["point"]) * float(ENGINE["stops_level_margin"])


class Book:
    def __init__(self, feed: Feed, magic: int = ENGINE["magic"]):
        self.feed, self.magic = feed, magic
        self.setups: Dict[str, Dict] = {}
        self.trades: Dict[str, Dict] = {}
        self.views: Dict[str, Dict] = {}
        self.cmd_pos = 0
        self.mt5_ops: List[str] = []              # dashboard → the run loop's Terminal: start / stop / restart / login
        self.last_m5: Dict[str, int] = {}
        self.account: Dict = {}
        self.positions: List[Dict] = []
        self.orders: List[Dict] = []
        self._load()

    # ── persistence ──
    def _load(self) -> None:
        try:
            with open(STATE_FILE) as f:
                st = json.load(f)
            self.setups, self.trades, self.cmd_pos = st.get("setups", {}), st.get("trades", {}), int(st.get("cmd_pos", 0))
        except Exception:
            pass
        for r in self.setups.values():            # H4 entries reached before S&D H4 (2026-10-25) were "touched" etc.: now H4 zones
            if r.get("tf") == ENGINE["sdh4"]["zone_tf"] and r.get("touch_t") and r["status"] in ("touched", "missed", "against bias"):
                r.update(status=ZONE, why="price came back to the H4 entry (before S&D H4 existed): S&D H4 watches M15 inside it")
        if not os.path.exists(COMMANDS_FILE):
            self.cmd_pos = 0

    def save(self) -> None:
        cut = now_ms() - 3 * 86400_000            # keep finished setups for 3 days
        self.setups = {k: v for k, v in self.setups.items()
                       if v["status"] in ACTIVE or v["status"] == ZONE or v.get("trade_id") in self.trades or v.get("seen_ms", 0) > cut}
        _write(STATE_FILE, {"setups": self.setups, "trades": self.trades, "cmd_pos": self.cmd_pos})

    # ── broker reads ──
    def read_broker(self) -> None:
        res = mt5c.call([{"op": "account"}, {"op": "positions", "magic": self.magic}, {"op": "orders", "magic": self.magic}], timeout=60)
        if any("error" in r for r in res):
            raise RuntimeError("; ".join(r["error"] for r in res if "error" in r))
        self.account, self.positions, self.orders = res[0]["result"], res[1]["result"], res[2]["result"]

    def running(self) -> int:
        return len(self.positions)

    def pending_layers(self) -> int:
        return len(self.orders)

    def max_slots(self) -> int:
        """§35-37 max_running_trades; the structure filter layer caps it at FILTERS["MAX_POSITIONS"] (David 2026-10-25)."""
        m = int(S["max_running_trades"])
        return min(m, int(FL.F["MAX_POSITIONS"])) if FL.enabled() else m

    def free_slots(self) -> int:
        """§35-37: open positions + pending layers (a pending layer would become a position) < max."""
        return self.max_slots() - self.running() - self.pending_layers()

    # ── picker ──
    def analyse(self, sym: str, trading: bool) -> Optional[Dict]:
        f = self.feed
        h1, m5 = f.completed(sym, "H1"), f.completed(sym, "M5")
        if len(h1) < 30 or len(m5) < 40:
            return None
        b = V.trade_bias(f.completed(sym, "H4"), h1)
        raw = f.get(sym, "M5")
        forming = raw[-1] if raw and raw[-1]["t"] > m5[-1]["t"] else None
        structs: Dict[str, Dict] = {}
        rows, live_ids, bos_tf = [], set(), {}
        for tf in ENGINE["setup_tfs"]:
            bars = f.completed(sym, tf)
            if len(bars) < 30:
                continue
            st = structs[tf] = V.structure(bars)
            cands = V.bos_setups(bars, st, tf, sym)
            # David 2026-10-24: a BOS without its own supply/demand (or MB) + FVG is not used, so it can't supersede
            bos_t = bos_tf[tf] = {side: [c["bos"]["t"] for c in cands if c["complete"] and c["side"] == side] for side in ("buy", "sell")}
            for c in cands:
                if not c["complete"]:
                    continue
                live_ids.add(c["id"])
                rec = self.setups.get(c["id"])
                if rec is None:
                    rec = self.setups[c["id"]] = {**c, "status": "waiting pullback", "seen_ms": now_ms()}
                elif rec["status"] not in ACTIVE:
                    rows.append(rec)                  # finished: keep showing it, never re-trade it
                    continue
                # the move can still be running: its FVG list (and so the 2nd FVG) may grow until it ends
                rec.update({k: c[k] for k in ("leg", "zone", "mb", "fvgs", "kind", "poi", "fvg", "fvg_pick", "entry", "invalidation", "formed_t")})
                rec.setdefault("entry_type", f"S&D {tf}" if tf in ENGINE["trade_tfs"] else None)   # the H4 setups are S&D H4 zones, not entries
                rec["aligned"] = b["bias"] == c["side"]
                self.watch(rec, b, bars, m5, forming, bos_t[c["side"]], trading, h1)
                rows.append(rec)
        rows += [r for r in self.sdh4(sym, b, structs, bos_tf, live_ids, m5, forming, trading, h1) if all(r is not x for x in rows)]
        for sid, rec in self.setups.items():      # setups that scrolled out of their timeframe's window
            if rec.get("symbol") == sym and rec["status"] in ACTIVE and sid not in live_ids:
                rec.update(status="stale", why="older than the chart window")
        view = self.view(sym, b, rows, structs)
        self.views[sym] = view
        _write(os.path.join(VIEW_DIR, f"{sym}.json"), view)
        return view

    def watch(self, rec: Dict, b: Dict, bars: List[Dict], m5: List[Dict], forming: Optional[Dict], bos_times: List[int],
              trading: bool, h1: List[Dict]) -> None:
        """Has price come back to the entry since the setup formed? History on the setup's own timeframe,
        the last ~33 h on M5 plus the forming M5 bar, so a pullback is seen within a minute."""
        tf = rec["tf"]
        tf_ms = TF_MIN[tf] * 60_000
        t0 = rec["formed_t"] + tf_ms
        bad = V.fvg_untaken(bars, rec)             # David 2026-10-25: FVG traded into early / no run before the retrace
        if bad:
            rec.update(status="invalid", why=bad, ended_t=now_ms())
            return
        seq = [x for x in bars if x["t"] >= t0 and x["t"] + tf_ms <= m5[0]["t"]] + [x for x in m5 if x["t"] >= t0]
        if forming and forming["t"] >= t0:
            seq.append(forming)
        i = V.pullback(rec, seq)
        newer = [t for t in bos_times if t > rec["bos"]["t"]]
        if newer and (i is None or seq[i]["t"] >= newer[0]):
            rec.update(status="superseded", why=f"a newer {tf} BOS setup ({hm(newer[0])}) came before the pullback", ended_t=newer[0])
            return
        if i is None:
            if sum(1 for x in bars if x["t"] >= t0) > int(S["setup_max_age_bars"]):
                rec.update(status="stale", why="older than the setup age limit")
            elif FL.enabled() and tf != ENGINE["sdh4"]["zone_tf"] and not rec.get("expired") \
                    and now_ms() - t0 > int(FL.F["SETUP_EXPIRY_M15_BARS"]) * 900_000:
                # Gate 7: past its expiry; kept watching only so a late pullback is logged (and refused) as a candidate
                rec.update(expired=True, why=f"G7: no pullback into the FVG within {FL.F['SETUP_EXPIRY_M15_BARS']} M15 candles")
            return
        hit = seq[i]
        rec["touch_t"] = hit["t"]
        bad = V.fvg_untaken([x for x in bars if x["t"] + tf_ms <= hit["t"]], rec, touching=True)
        if bad:
            rec.update(status="invalid", why=bad, ended_t=hit["t"])
            return
        if tf == ENGINE["sdh4"]["zone_tf"]:       # S&D H4: the H4 setup only marks the zone; the entry comes from M15
            ctf = ENGINE["sdh4"]["confirm_tf"]
            rec.update(status=ZONE, why=f"price came back to the H4 entry at {hm(hit['t'])}: S&D H4 waits for an {ctf} "
                       f"BOS / CHoCH {'up' if rec['side'] == 'buy' else 'down'} from inside the H4 zone")
            journal("zone_reached", id=rec["id"], entry=rec["entry"])
            return
        live = hit is forming or hit is m5[-1] and now_ms() - hit["t"] <= 3 * 300_000   # a closed market is never live
        if not rec["aligned"]:
            rec.update(status="against bias", why=f"price came back to the entry, but {b.get('why')}", ended_t=hit["t"])
            if live and tf in ENGINE["trade_tfs"] and FL.enabled():
                self.counter_bias(rec, bars, h1)          # Gate 4: a CHoCH candidate, logged, never traded
        elif not live:
            rec.update(status="missed", why=f"price came back to the entry at {hm(hit['t'])}, before the engine saw it live", ended_t=hit["t"])
        elif tf not in ENGINE["trade_tfs"]:
            rec.update(status="touched", why=f"chart only: {tf} is not a trade timeframe ({', '.join(ENGINE['trade_tfs'])})", ended_t=hit["t"])
            journal("touched", id=rec["id"], entry=rec["entry"])
        else:
            self.signal(rec, trading, h1, bars, m5)

    def sdh4(self, sym: str, b: Dict, structs: Dict[str, Dict], bos_tf: Dict[str, Dict], live_ids: set, m5: List[Dict],
             forming: Optional[Dict], trading: bool, h1: List[Dict]) -> List[Dict]:
        """S&D H4 (David 2026-10-25): every H4 setup price came back to ("zone reached") watches M15 for a BOS or
        CHoCH the same way from inside the H4 zone; that break's own M15 setup (zone or MB + FVG) is the entry,
        watched like any M15 setup. A break that is a BOS with its own S&D M15 setup is that same setup (one
        trade): it is only marked with the H4 parent. The H4 zone ends at an M15 close beyond its invalidation,
        a newer H4 BOS setup the same way, setup_max_age_bars M15 bars, or once one of its entries is taken."""
        ztf, ctf = ENGINE["sdh4"]["zone_tf"], ENGINE["sdh4"]["confirm_tf"]
        st, bars = structs.get(ctf), self.feed.completed(sym, ctf)
        if not st:
            return []
        mine = [r for r in self.setups.values() if r.get("symbol") == sym]
        kids_of = {}
        for r in mine:
            if r["tf"] == ctf and r.get("entry_type") == "S&D H4":
                kids_of.setdefault(r["parent"], []).append(r)
        normal = {(r["side"], r["bos"]["t"]): r for r in mine if r["tf"] == ctf and r.get("entry_type") != "S&D H4"}
        rows = []
        for p in [r for r in mine if r["tf"] == ztf and r.get("touch_t")]:
            live = p["status"] == ZONE
            if not live and not any(k["status"] in ACTIVE for k in kids_of.get(p["id"], [])):
                continue
            cands, broken = V.sdh4_setups(p, bars, st, ctf, sym)
            cands = [c for c in cands if c["complete"]]
            for c in cands:
                twin = normal.get((c["side"], c["bos"]["t"]))
                if twin:                              # the same break already has its S&D M15 setup: one trade, two names
                    twin.setdefault("parent", p["id"])
                    continue
                rec = self.setups.get(c["id"])
                if rec is None:
                    if not live:
                        continue                      # an ended H4 zone makes no new entries
                    rec = self.setups[c["id"]] = {**c, "status": "waiting pullback", "seen_ms": now_ms()}
                    kids_of.setdefault(p["id"], []).append(rec)
                    log(f"{sym} S&D H4 {c['side']}: {ctf} {c['bos']['kind']} {hm(c['bos']['t'])} inside the H4 zone → setup, entry {c['entry']:g}")
                elif rec["status"] in ACTIVE:
                    rec.update({k: c[k] for k in ("leg", "zone", "mb", "fvgs", "kind", "poi", "fvg", "fvg_pick", "entry", "invalidation", "formed_t")})
            newer_kids = [c["bos"]["t"] for c in cands if not normal.get((c["side"], c["bos"]["t"]))]
            for rec in kids_of.get(p["id"], []):
                if rec["status"] in ACTIVE:
                    live_ids.add(rec["id"])
                    rec["aligned"] = b["bias"] == rec["side"]
                    self.watch(rec, b, bars, m5, forming, bos_tf.get(ctf, {}).get(rec["side"], []) + newer_kids, trading, h1)
                rows.append(rec)
            rows.append(p)
            if not live:
                continue
            took = next((k for k in kids_of.get(p["id"], []) + [r for r in normal.values() if r.get("parent") == p["id"]]
                         if k["status"] in ("signal", "entered")), None)
            newer = [r["bos"]["t"] for r in mine if r["tf"] == ztf and r["side"] == p["side"] and r.get("complete")
                     and r["bos"]["t"] > p["bos"]["t"] and r["bos"]["t"] >= p["touch_t"]]
            if took:
                p.update(status="used", why=f"S&D H4 entry taken: {took['id']}", ended_t=took.get("touch_t"))
            elif broken is not None:
                p.update(status="zone broken", why=f"an {ctf} candle closed beyond the H4 invalidation {p['invalidation']:g} at {hm(broken)}", ended_t=broken)
            elif newer:
                p.update(status="superseded", why=f"a newer {ztf} BOS setup ({hm(min(newer))})", ended_t=min(newer))
            elif sum(1 for x in bars if x["t"] >= p["touch_t"]) > int(S["setup_max_age_bars"]):
                p.update(status="stale", why=f"no {ctf} entry within {S['setup_max_age_bars']} {ctf} bars of reaching the H4 zone")
        return rows

    # ── executor ──
    def plan(self, rec: Dict, entry: float, bars: List[Dict], h1: List[Dict], spread: Optional[float] = None,
             filtered: Optional[bool] = None) -> Dict:
        """Stop, target and the pre-trade checks from this one setup only, worked out fresh every time
        (David's SL/TP fix: never a level of an older setup, a stale zone or a previous target). With the structure
        filter layer on (filtered None = FL.enabled()): Gate 6's stop (S&D H4 on M15: beyond the M15 swing that started
        the break + spread + 0.25 ATR) and target (the nearest opposing structure, RR checked, never stretched)."""
        sym, side = rec["symbol"], rec["side"]
        extra = {}
        if FL.enabled() if filtered is None else filtered:
            info = self.feed.info[sym]
            sp = spread if spread is not None else float(info.get("spread") or 0) * float(info["point"])
            lv = FL.plan_levels(rec, entry, sp, info, [(rec["tf"], bars)] + [(tf, self.feed.completed(sym, tf)) for tf in FL.F["TARGET_TFS"]],
                                self.feed.completed(sym, "M15"))
            stop, tgt = lv["stop"], lv["target"]
            extra = {"stop_rule": lv["stop_rule"], "filters": True}
            limits = {"min_rr": FL.F["MIN_RR"], "sl_max": FL.F["SL_MAX_ATR"]}      # the profile rules, not STRATEGY's
        else:
            stop = V.stop_price(rec, float(self.feed.info[sym]["point"]))
            levels = V.opposite_levels(side, (rec["tf"], bars), ("H1", h1), ("H4", self.feed.completed(sym, "H4")))
            tgt = V.final_target(side, entry, stop, levels)
            limits = {}
        atr = V.sl_atr(self.feed.completed(sym, S["sl_atr_tf"]))
        return {"setup": rec["id"], "entry": entry, "stop": stop, "target": tgt, "atr": atr,
                "sl_atr_x": round(abs(entry - stop) / atr, 2) if atr else None,
                "why": V.pretrade(rec, entry, stop, tgt, atr, **limits), **extra}

    def signal(self, rec: Dict, trading: bool, h1: List[Dict], bars: List[Dict], m5: List[Dict]) -> None:
        sym, side, tf = rec["symbol"], rec["side"], rec["tf"]
        tick = mt5c.tick(sym)
        bid, ask = float(tick["bid"]), float(tick["ask"])
        entry = bid if side == "sell" else ask         # the price the normal entry executes at
        plan = self.plan(rec, entry, bars, h1, spread=ask - bid)
        stop, tgt = plan["stop"], plan["target"]
        x = len(m5) - 1                            # the pullback into the FVG, measured on M5 for the layer depth
        r = next((k for k, bb in enumerate(m5) if bb["t"] > rec["leg"]["end_t"]), max(0, x - 6))
        st = V.strength(m5, min(r, x), x, side)
        lay = V.layer_price(side, entry, stop, st["level"])
        plan.update(layer=lay, strength=st, bid=bid, ask=ask)
        rec["plan"] = plan
        at = rec.get("touch_t")
        why = plan["why"] or self.refuse(sym, side, entry, stop, tgt["price"], bid, ask)
        if FL.enabled():                           # the structure filter layer: every gate, refused at the first that fails
            cand = self.gates(rec, plan, entry, bid, ask, bars, h1, why, trading)
            g = cand["first_fail"]
            if g:
                why = f"{g} {FL.GATES[g]}: {cand['why'][g]}"
                rec["gate"] = g
        if why:
            rec.update(status="refused", why=why, ended_t=at)
            journal("refused", id=rec["id"], why=why, plan=plan)
            log(f"{sym} {tf} {side}: pullback to the entry, refused: {why}")
            return
        if not trading:
            rec.update(status="signal", why="watch mode: trading is off", ended_t=at)
            journal("signal", id=rec["id"], plan=plan)
            log(f"{sym} {tf} {side}: SIGNAL (watch mode) entry {entry:g} SL {stop:g} TP {tgt['price']:g} ({tgt['rr']}R), layer {lay['price']:g} {st['level']}")
            return
        self.enter(rec, plan, self.feed.info[sym])

    def refuse(self, sym, side, entry, stop, tp, bid, ask) -> Optional[str]:
        lvl = stops_gap(self.feed.info[sym])
        close_px = ask if side == "sell" else bid               # a sell closes at the ask, a buy at the bid
        dist = abs(entry - stop)
        if side == "sell" and not (stop - close_px >= lvl and close_px - tp >= lvl) or \
           side == "buy" and not (close_px - stop >= lvl and tp - close_px >= lvl):
            return f"SL {stop:g} / TP {tp:g} inside the broker's {lvl:g} from the {'ask' if side == 'sell' else 'bid'} {close_px:g}"
        if (ask - bid) > float(ENGINE["max_spread_frac"]) * dist:
            return f"spread {ask - bid:g} is over {ENGINE['max_spread_frac']:g} of the stop distance {dist:g}"
        if self.free_slots() < 1:
            return f"all {self.max_slots()} position slots are in use"
        return None

    # ── the structure filter layer (engine/filters.py, David 2026-10-25) ──
    def gates(self, rec: Dict, plan: Dict, entry: float, bid: float, ask: float, bars: List[Dict], h1: List[Dict],
              checks: Optional[str], trading: bool) -> Dict:
        """Every gate for this entry attempt → the decision record (also written to the day's candidates file), with
        the V5 checks on the filtered plan (checks) and what the engine without the layer would have done (old_logic)."""
        f, sym = self.feed, rec["symbol"]
        info = f.info[sym]
        ctx = {"now": now_ms(), "entry": entry, "bid": bid, "ask": ask, "info": info, "market": f.market.get(sym),
               "bars": {**{tf: f.completed(sym, tf) for tf in ("M15", "M30", "H1", "H4")}, rec["tf"]: bars},
               "bias": V.trade_bias(f.completed(sym, "H4"), h1), "plan": plan, "zones": self.taken_zones(sym),
               "lots": self.lots(sym, entry, plan["stop"], S["normal_risk_pct"]), "money_per_move": money_per_move(info),
               "equity": float(self.account.get("equity") or 0)}
        cand = FL.evaluate(rec, ctx)
        old = self.plan(rec, entry, bars, h1, filtered=False)
        old_why = "against the H4 / H1 bias" if rec.get("aligned") is False else \
            old["why"] or self.refuse(sym, rec["side"], entry, old["stop"], old["target"]["price"], bid, ask)
        cand.update(checks=checks, old_logic=old_why or "take", old_plan={k: old[k] for k in ("stop", "sl_atr_x")} | {"tp": old["target"]["price"], "rr": old["target"]["rr"]},
                    passed=not cand["first_fail"] and not checks, trading=trading)
        FL.write(cand)
        return cand

    def counter_bias(self, rec: Dict, bars: List[Dict], h1: List[Dict]) -> None:
        """Gate 4: a live pullback to a setup against the H4 / H1 bias is a CHoCH candidate: its record is logged
        (at the setup's entry, the last M15 bar's spread), it is never traded."""
        sym = rec["symbol"]
        info = self.feed.info[sym]
        m15 = self.feed.completed(sym, "M15")
        sp = FL.bar_spread(m15[-1], float(info["point"])) if m15 else 0.0
        entry = rec["entry"]
        bid, ask = (entry, entry + sp) if rec["side"] == "sell" else (entry - sp, entry)
        plan = self.plan(rec, entry, bars, h1, spread=sp, filtered=True)
        self.gates(rec, plan, entry, bid, ask, bars, h1, f"against the bias: {rec.get('why')}", False)

    def taken_zones(self, sym: str) -> List[Dict]:
        """The zones this symbol already traded (or signalled in watch mode) for Gate 7: H4 parent, side, zone, lost."""
        out = []
        for sid, r in self.setups.items():
            poi = r.get("poi") or {}
            if r.get("symbol") != sym or poi.get("top") is None or not (r.get("trade_id") or r["status"] in ("signal", "entered", "closed")):
                continue
            t = self.trades.get(r.get("trade_id") or sid) or {}
            out.append({"id": sid, "parent": r.get("parent"), "side": r["side"], "top": poi["top"], "bottom": poi["bottom"],
                        "lost": bool(t.get("closed")) and float(t.get("pnl_usd") or 0) < 0})
        return out

    def lots(self, sym: str, price: float, stop: float, risk_pct: float) -> float:
        info = self.feed.info[sym]
        if ENGINE.get("lot_mode") == "min":           # with the filter layer: 0.01, or volume_min when that is larger
            return max(float(info["volume_min"]), float(FL.F["TEST_LOT"])) if FL.enabled() else float(info["volume_min"])
        per_lot = abs(price - stop) * money_per_move(info)
        q = floor_step(float(self.account["equity"]) * risk_pct / 100.0 / per_lot, float(info["volume_step"])) if per_lot else 0.0
        return min(q, float(info["volume_max"])) if q >= float(info["volume_min"]) else 0.0

    def enter(self, rec: Dict, plan: Dict, info: Dict) -> None:
        sym, side, sid = rec["symbol"], rec["side"], rec["id"]
        stop, tp = plan["stop"], plan["target"]["price"]
        q = self.lots(sym, plan["entry"], stop, S["normal_risk_pct"])
        if not q:
            rec.update(status="refused", why="normal size below the broker's minimum lot")
            journal("refused", id=sid, why=rec["why"])
            return
        tag = sid.split("-", 1)[-1][-26:]           # "M15-D-1792778400": the symbol is on the position already
        res = mt5c.order(sym, side, q, stop, tp, self.magic, f"V5N {tag}", 30)
        if not res.get("ok"):
            rec.update(status="refused", why=f"order refused: {res.get('retcode')} {res.get('comment')}")
            journal("refused", id=sid, why=rec["why"], plan=plan)
            log(f"{sym} {side}: normal order refused {res.get('retcode')} {res.get('comment')}")
            return
        self.read_broker()
        pos = max((p for p in self.positions if p["symbol"] == sym and p["comment"].startswith("V5N")), key=lambda p: p["time_msc"], default=None)
        fill = float(pos["price_open"]) if pos else float(res.get("price") or plan["entry"])
        risk_usd = round(q * abs(fill - stop) * money_per_move(info), 2)
        t = {"id": sid, "symbol": sym, "tf": rec.get("tf", "M15"), "entry_type": rec.get("entry_type"), "side": side, "entry": fill, "stop0": stop, "stop": stop, "tp": tp,
             "tp_label": plan["target"]["label"], "rr": round(abs(tp - fill) / abs(fill - stop), 2), "opened_ms": now_ms(),
             "normal": {"ticket": pos["ticket"] if pos else res.get("order"), "lots": q, "risk_usd": risk_usd, "open": True},
             "layer": None, "mode": "A", "best": fill, "tp1": None, "tp1_hit": False, "be_done": False, "locked_r": 0.0}
        self.trades[sid] = t
        rec.update(status="entered", trade_id=sid, why=f"normal {q} @ {fill:g}")
        journal("entry", id=sid, symbol=sym, entry_type=rec.get("entry_type"), side=side, lots=q, entry=fill, stop=stop, tp=tp, rr=t["rr"], risk_usd=risk_usd,
                strength=plan["strength"], target=plan["target"]["label"])
        log(f"{sym} {side}: NORMAL {q} @ {fill:g}, SL {stop:g}, TP {tp:g} ({t['rr']}R, {plan['target']['label']}), risk ${risk_usd}")
        if S["layer_entry"] and self.free_slots() >= 1:
            lp = plan["layer"]["price"]
            lq = self.lots(sym, lp, stop, S["layer_risk_pct"])
            # a limit order inside the broker's stops level is refused (10015 Invalid price: UNISWAP, CHAINLINK
            # 2026-10-24); the layer stays at its V5 depth, it is not moved deeper to pass
            mkt = plan.get("bid") if side == "sell" else plan.get("ask")
            gap = stops_gap(info)
            if lq and mkt is not None and abs(lp - float(mkt)) < gap:
                why = f"layer {lp:g} is {abs(lp - float(mkt)):g} from the {'bid' if side == 'sell' else 'ask'} {float(mkt):g}, inside the broker's {gap:g}"
                journal("layer_refused", id=sid, why=why)
                log(f"{sym} {side}: no layer: {why}")
                lq = 0.0
            if lq:
                r2 = mt5c.pending(sym, side, lq, lp, stop, tp, self.magic, f"V5L {tag}")
                if r2.get("ok"):
                    t["layer"] = {"order": r2.get("order"), "price": lp, "lots": lq, "state": "pending", "level": plan["layer"]["level"],
                                  "risk_usd": round(lq * abs(lp - stop) * money_per_move(info), 2)}
                    # count it now: a second signal in the same pass must see this slot as taken (§35 never 21)
                    self.orders.append({"ticket": r2.get("order"), "symbol": sym, "volume_current": lq, "price_open": lp,
                                        "sl": stop, "tp": tp, "comment": f"V5L {tag}"})
                    journal("layer_placed", id=sid, price=lp, lots=lq, level=plan["layer"]["level"], order=r2.get("order"))
                    log(f"{sym} {side}: LAYER {r2.get('order_type')} {lq} @ {lp:g} ({plan['layer']['level']})")
                else:
                    journal("layer_refused", id=sid, why=f"{r2.get('retcode')} {r2.get('comment')}")

    # ── monitor ──
    def manage(self) -> None:
        pos_by = {p["ticket"]: p for p in self.positions}
        ord_by = {o["ticket"]: o for o in self.orders}
        for sid, t in list(self.trades.items()):
            if t.get("closed"):
                continue
            sym, side, info = t["symbol"], t["side"], self.feed.info.get(t["symbol"], {})
            lay = t.get("layer")
            # layer filled? (the position opened by a pending order carries the order's ticket)
            if lay and lay["state"] == "pending" and lay["order"] not in ord_by:
                p = pos_by.get(lay["order"]) or next((x for x in self.positions if x["symbol"] == sym and x["comment"].startswith("V5L")), None)
                if p:
                    lay.update(state="filled", ticket=p["ticket"], fill=float(p["price_open"]))
                    t["mode"], t["tp1"] = "B", t["entry"] + float(S["tp1_fraction"]) * (t["tp"] - t["entry"])
                    journal("layer_filled", id=sid, fill=lay["fill"], tp1=t["tp1"])
                    log(f"{sym}: layer filled @ {lay['fill']:g} → Mode B, Target 1 {t['tp1']:g}")
                else:
                    lay["state"] = "gone"
            normal_open = t["normal"]["ticket"] in pos_by
            if t["normal"]["open"] and not normal_open:
                t["normal"]["open"] = False
                self.book_exit(t, t["normal"]["ticket"], "normal")
                if lay and lay["state"] == "pending":
                    self.cancel_layer(t, "the normal entry closed")
            if lay and lay["state"] == "filled" and lay.get("ticket") not in pos_by and not lay.get("closed"):
                lay["closed"] = True
                self.book_exit(t, lay["ticket"], "layer")
            mine = [pos_by[x] for x in (t["normal"]["ticket"], (lay or {}).get("ticket")) if x in pos_by]
            if not mine and not (lay and lay["state"] == "pending"):
                t["closed"] = True
                self.setups.get(sid, {}).update(status="closed")
                journal("trade_closed", id=sid)
                continue
            if not mine:
                continue
            # an unfilled layer dies with its setup (§33): a close beyond the zone on the setup's timeframe
            if lay and lay["state"] == "pending":
                tfb = self.feed.completed(sym, t.get("tf", "M15"))
                inv = t["stop0"] - float(S["sl_buffer_points"]) * float(info.get("point") or 0) * (1 if side == "sell" else -1)
                if any((side == "sell" and b["c"] > inv) or (side == "buy" and b["c"] < inv) for b in tfb if b["t"] > t["opened_ms"] - 900_000):
                    self.cancel_layer(t, "setup invalidated")
            self.trail(t, mine)

    def trail(self, t: Dict, mine: List[Dict]) -> None:
        sym, side = t["symbol"], t["side"]
        sg = -1 if side == "sell" else 1
        entry, risk = t["entry"], abs(t["entry"] - t["stop0"])
        if not risk:
            return
        m5 = [b for b in self.feed.completed(sym, "M5") if b["t"] >= t["opened_ms"] - 300_000]
        px = float(mine[0]["price_current"])
        seen = [px, float(t.get("best") or entry)] + [b["h"] if sg == 1 else b["l"] for b in m5]
        best = max(seen) if sg == 1 else min(seen)          # the best price since entry, kept across loops
        t["best"] = best
        r_best = sg * (best - entry) / risk
        span = abs(t["tp"] - entry)
        prog_best, prog_now = sg * (best - entry) / span, sg * (px - entry) / span
        cur = float(t["stop"])
        want, why = cur, ""

        def better(x):          # toward profit = up for a buy, down for a sell
            return sg * (x - want) > 0

        buf = float(S["sl_buffer_points"]) * float(self.feed.info[sym]["point"])
        swings = [s for s in V.swings(m5) if s["kind"] == ("low" if sg == 1 else "high")]
        if t["mode"] == "A" and S["normal_target_near_protection"] and not t["be_done"] and prog_best >= S["near_target_progress"]:
            turned = prog_now <= prog_best - S["reversal_giveback"] or (m5 and ((m5[-1]["c"] < m5[-1]["o"]) if sg == 1 else (m5[-1]["c"] > m5[-1]["o"])))
            if turned and better(entry):
                want, why = entry, f"Mode A: {prog_best:.0%} of the way to the target, then turned → break-even"
                t["be_done"] = True
        if t["mode"] == "B" and S["layer_profit_protection"]:
            if not t["tp1_hit"] and sg * (best - t["tp1"]) >= 0:
                t["tp1_hit"] = True
                lock = entry + sg * max(float(S["tp1_lock_r"]) * risk, buf)
                if better(lock):
                    want, why = lock, f"Mode B: Target 1 {t['tp1']:g} hit → SL past the first entry"
                journal("tp1_hit", id=t["id"], tp1=t["tp1"])
            if t["tp1_hit"] and S["structure_trailing"]:
                after = [s for s in swings if s["t"] >= t["opened_ms"]]
                if after:
                    lvl = after[-1]["price"] - sg * buf
                    if better(lvl):
                        want, why = lvl, f"Mode B: trail to the M5 swing {after[-1]['price']:g}"
        if r_best >= S["lock_start_r"]:
            n = math.floor(r_best)
            lock = entry + sg * (n - S["lock_gap_r"]) * risk
            if better(lock):
                want, why = lock, f"{r_best:.1f}R reached → lock {n - S['lock_gap_r']:g}R"
            if S["structure_trailing"] and swings:
                lvl = swings[-1]["price"] - sg * buf
                if better(lvl) and sg * (lvl - entry) > 0:
                    want, why = lvl, f"{r_best:.1f}R: trail to the M5 swing {swings[-1]['price']:g}"
        if want == cur:
            return
        lvl_min = stops_gap(self.feed.info[sym])
        close_px = float(mine[0]["price_current"])
        if sg == 1 and want > close_px - lvl_min or sg == -1 and want < close_px + lvl_min:
            want = close_px - sg * lvl_min                 # as close as the broker allows
        if sg * (want - cur) <= 0:
            return                                         # §32 one-way: never back toward more risk
        ok = True
        for p in mine:
            r = mt5c.sltp(p["ticket"], sl=want, tp=float(p["tp"] or t["tp"]))
            ok = ok and bool(r.get("ok"))
        if ok:
            journal("sl_moved", id=t["id"], frm=cur, to=want, why=why)
            log(f"{sym}: SL {cur:g} → {want:g} ({why})")
            t["stop"] = want

    def cancel_layer(self, t: Dict, why: str) -> None:
        lay = t["layer"]
        r = mt5c.cancel(lay["order"])
        lay["state"] = "cancelled" if r.get("ok") else lay["state"]
        journal("layer_cancelled", id=t["id"], why=why, ok=r.get("ok"))
        log(f"{t['symbol']}: layer cancelled ({why}) ok={r.get('ok')}")

    def book_exit(self, t: Dict, ticket: int, leg: str) -> None:
        ds = []
        for _ in range(4):
            ds = mt5c.deals(position=ticket)
            if any(d["entry"] == 1 for d in ds):
                break
            time.sleep(1)
        outs = [d for d in ds if d["entry"] == 1]
        pnl = round(sum(float(d.get(k) or 0) for d in ds for k in ("profit", "commission", "swap", "fee")), 2)
        reason = {4: "stop", 5: "target"}.get(outs[-1]["reason"], "closed") if outs else "closed"
        journal("exit", id=t["id"], symbol=t["symbol"], leg=leg, ticket=ticket, price=outs[-1]["price"] if outs else None,
                pnl_usd=pnl, reason=reason)
        log(f"{t['symbol']}: {leg} closed ({reason}) P&L ${pnl}")
        t.setdefault("pnl_usd", 0.0)
        t["pnl_usd"] = round(t["pnl_usd"] + pnl, 2)

    # ── commands from the dashboard ──
    def commands(self) -> None:
        try:
            with open(COMMANDS_FILE) as f:
                lines = f.readlines()
        except FileNotFoundError:
            return
        for line in lines[self.cmd_pos:]:
            try:
                c = json.loads(line)
            except ValueError:
                continue
            self.command(c)
        self.cmd_pos = len(lines)

    def command(self, c: Dict) -> None:
        a = c.get("action")
        if a == "trading":
            save_control(trading=bool(c.get("on")))
            journal("trading", on=bool(c.get("on")))
            log(f"dashboard: trading {'ON' if c.get('on') else 'OFF'}")
        elif a == "mt5":
            self.mt5_ops.append(str(c.get("op")))
            journal("mt5_command", op=c.get("op"), by="dashboard")
        elif a == "cancel_setup":
            rec = self.setups.get(c.get("id"))
            if rec and rec["status"] in ACTIVE + ("signal",):
                rec.update(status="cancelled", why="cancelled from the dashboard")
            t = self.trades.get(c.get("id"))
            if t and t.get("layer") and t["layer"]["state"] == "pending":
                self.cancel_layer(t, "cancelled from the dashboard")
            journal("cancel_setup", id=c.get("id"))
            log(f"dashboard: cancel setup {c.get('id')}")
        elif a in ("close_setup", "close_ticket"):
            t = self.trades.get(c.get("id")) if a == "close_setup" else None
            tickets = [c.get("ticket")] if a == "close_ticket" else \
                [x for x in ((t or {}).get("normal", {}).get("ticket"), ((t or {}).get("layer") or {}).get("ticket")) if x]
            if t and t.get("layer") and t["layer"]["state"] == "pending":
                self.cancel_layer(t, "closed from the dashboard")
            for tk in tickets:
                if any(p["ticket"] == tk for p in self.positions):
                    r = mt5c.close(int(tk), "V5 closed (dashboard)")
                    journal("close", ticket=tk, ok=r.get("ok"), by="dashboard")
                    log(f"dashboard: close #{tk} ok={r.get('ok')} {r.get('comment')}")

    # ── what the dashboard reads ──
    def view(self, sym: str, b: Dict, rows: List[Dict], structs: Dict[str, Dict]) -> Dict:
        f = self.feed
        bars, marks, struct = {}, {}, {}
        lvl = lambda L: {k: L[k] for k in ("price", "t", "label") if k in L} if L else None
        used = {(r["tf"], r["side"], r["bos"]["t"]) for r in rows}      # BOS that made a setup (zone or MB + FVG)
        for tf in ENGINE["chart_tfs"]:
            bs = f.get(sym, tf)                    # every bar the engine has: the big chart scrolls back through them
            bars[tf] = [[x["t"] // 1000, x["o"], x["h"], x["l"], x["c"]] for x in bs]
            st = structs.get(tf) or V.structure(f.completed(sym, tf))
            t_from = bs[0]["t"] if bs else 0
            marks[tf] = [{k: s[k] for k in ("t", "price", "kind", "label")} for s in st["swings"] if s["t"] >= t_from]
            struct[tf] = {"trend": st["trend"], "bos_level": lvl(st["bos_level"]), "choch_level": lvl(st["choch_level"]),
                          "events": [{**{k: e[k] for k in ("kind", "side", "level", "level_t", "level_label", "t", "close")},
                                      "origin": e["origin"], "setup": (tf, e["side"], e["t"]) in used}
                                     for e in st["events"] if e["t"] >= t_from]}
        price = bars["M5"][-1][4] if bars.get("M5") else None
        live = [r for r in rows if r["status"] in ACTIVE and r.get("aligned") and not r.get("expired")]

        def away(r):                               # price's distance from the entry, in entry → invalidation units
            return abs((price if price is not None else r["entry"]) - r["entry"]) / (abs(r["entry"] - r["invalidation"]) or 1e-12)
        focus = min(live, key=lambda r: (r["tf"] not in ENGINE["trade_tfs"], away(r)), default=None)
        # what the trade would be if price came back now: the same stop / target / checks the order would get
        preview = self.plan(focus, focus["entry"], f.completed(sym, focus["tf"]), f.completed(sym, "H1")) if focus else {}
        checks = {"bias": b["bias"], "bias_why": b.get("why"), "bos": focus["tf"] if focus else None,
                  "poi": focus["kind"] if focus else None, "fvg": f"{focus['fvg_pick']} of {len(focus['fvgs'])}" if focus else None,
                  "entry": focus["entry"] if focus else None, "rr": (preview.get("target") or {}).get("rr"),
                  "sl_atr": preview.get("sl_atr_x"), "tp": (preview.get("target") or {}).get("price"),
                  "tp_label": (preview.get("target") or {}).get("label"), "why": preview.get("why")}
        per_tf: Dict[str, List[Dict]] = {}         # every setup on the chart (the small charts draw the first 6 per timeframe)
        for r in sorted(rows, key=lambda r: (r["status"] not in ACTIVE, -r["bos"]["t"])):
            if bars.get(r["tf"]) and r["poi"]["t"] // 1000 >= bars[r["tf"]][0][0] or r is focus:
                per_tf.setdefault(r["tf"], []).append(r)
        keep = ("id", "tf", "side", "kind", "bos", "leg", "poi", "zone", "mb", "fvgs", "fvg", "fvg_pick", "entry", "invalidation",
                "status", "why", "aligned", "touch_t", "plan", "trade_id", "formed_t", "ended_t", "entry_type", "parent")
        open_t = [x for x in self.trades.values() if x["symbol"] == sym and not x.get("closed")]
        return {"symbol": sym, "market": f.market.get(sym), "updated": now_ms(), "digits": f.info[sym].get("digits"),
                "bias": b, "structure": struct, "trend": {tf: struct[tf]["trend"] for tf in struct}, "checks": checks,
                "focus": focus["id"] if focus else None, "trade_tfs": ENGINE["trade_tfs"], "view_bars": ENGINE["view_bars"],
                "bars": bars, "swings": marks,
                "setups": [{**{k: r.get(k) for k in keep}, "preview": preview if r is focus else None} for v in per_tf.values() for r in v],
                "trades": open_t}

    def overview(self, trading: bool, mt5: Optional[Dict] = None) -> None:
        syms = []
        for s in self.feed.symbols:
            v = self.views.get(s)
            if not v:
                continue
            st = next((x for x in v["setups"] if x["id"] == v["focus"]), None)
            syms.append({"symbol": s, "market": v["market"], "bias": v["bias"]["bias"], "bias_why": v["bias"].get("why"),
                         "trend": v["trend"], "checks": v["checks"], "stage": st["status"] if st else None,
                         "price": v["bars"]["M5"][-1][4] if v["bars"].get("M5") else None,
                         "open": len(v["trades"]), "updated": v["updated"]})
        _write(OVERVIEW_FILE, {
            "at": now_ms(), "trading": trading, "account": self.account, "mt5": mt5,
            "slots": {"running": self.running(), "pending_layers": self.pending_layers(), "max": self.max_slots()},
            "filters": FL.enabled(), "filter_profile": FL.profile(),
            "symbols": syms,
            "positions": [{k: p.get(k) for k in ("ticket", "symbol", "type", "volume", "price_open", "price_current", "sl", "tp", "profit", "comment")}
                          for p in self.positions],
            "orders": [{k: o.get(k) for k in ("ticket", "symbol", "type", "volume_current", "price_open", "sl", "tp", "comment")} for o in self.orders],
            "trades": [x for x in self.trades.values() if not x.get("closed")],
            "signals": sorted([r for r in self.setups.values() if r["status"] in ("signal", "entered", "refused")],
                              key=lambda r: -r.get("seen_ms", 0))[:40],
            "strategy": S, "engine": {k: ENGINE[k] for k in ("magic", "markets", "chart_tfs", "setup_tfs", "trade_tfs", "max_spread_frac")}})
