"""
Offline tests of the V5 executor + monitor (book.py) on a fake MT5 — no terminal, no orders:

    cd ~/forex && python3 -m pytest -q engine/test_book.py
"""
from __future__ import annotations

import os
import tempfile

import pytest

from engine import book as B
from engine import config as C

MIN = 60_000


class FakeMT5:
    """Just enough of mt5_client for book.py: one symbol, positions / pending orders / SL changes / closes."""

    def __init__(self):
        self.pos, self.ords, self.calls, self.n = {}, {}, [], 100
        self.price = 100.0
        self.equity = 10_000.0

    def tick(self, s):
        return {"bid": self.price, "ask": self.price + 0.01, "time": 0}

    def order(self, s, side, vol, sl, tp, magic, comment, dev, check_only=False):
        self.n += 1
        self.pos[self.n] = {"ticket": self.n, "symbol": s, "type": 0 if side == "buy" else 1, "volume": vol, "price_open": self.price,
                            "price_current": self.price, "sl": sl, "tp": tp, "profit": 0.0, "comment": comment, "time_msc": self.n}
        self.calls.append(("order", side, vol, sl, tp))
        return {"ok": True, "order": self.n, "price": self.price}

    def pending(self, s, side, vol, price, sl, tp, magic, comment, check_only=False):
        self.n += 1
        self.ords[self.n] = {"ticket": self.n, "symbol": s, "volume_current": vol, "price_open": price, "sl": sl, "tp": tp, "comment": comment,
                             "side": side}
        self.calls.append(("pending", side, vol, price))
        return {"ok": True, "order": self.n, "order_type": f"{side} limit"}

    def fill_layer(self):
        tk, o = next(iter(self.ords.items()))
        del self.ords[tk]
        self.pos[tk] = {"ticket": tk, "symbol": o["symbol"], "type": 0 if o["side"] == "buy" else 1, "volume": o["volume_current"],
                        "price_open": o["price_open"], "price_current": o["price_open"], "sl": o["sl"], "tp": o["tp"], "profit": 0.0,
                        "comment": o["comment"], "time_msc": tk}

    def set_price(self, p):
        self.price = p
        for x in self.pos.values():
            x["price_current"] = p

    def call(self, reqs, timeout=60):
        return [{"result": {"equity": self.equity, "balance": self.equity, "demo": True, "algo_trading": True}},
                {"result": list(self.pos.values())}, {"result": list(self.ords.values())}]

    def sltp(self, t, sl=0, tp=0):
        self.pos[t]["sl"] = sl
        self.calls.append(("sltp", t, sl))
        return {"ok": True}

    def cancel(self, t):
        self.ords.pop(t, None)
        self.calls.append(("cancel", t))
        return {"ok": True}

    def close(self, t, comment="", deviation=20, check_only=False):
        self.pos.pop(t, None)
        self.calls.append(("close", t))
        return {"ok": True}

    def deals(self, position=None, days=3):
        return [{"entry": 0, "price": 100, "profit": 0}, {"entry": 1, "price": 99, "profit": -25.0, "commission": 0, "swap": 0, "reason": 4}]


class FakeFeed:
    def __init__(self):
        self.info = {"TEST": {"point": 0.01, "digits": 2, "trade_tick_value": 0.01, "trade_tick_size": 0.01, "trade_contract_size": 1,
                              "volume_step": 0.01, "volume_min": 0.01, "volume_max": 1000, "trade_stops_level": 10}}
        self.symbols, self.market, self.m5, self.m15 = ["TEST"], {"TEST": "crypto"}, [], []

    def completed(self, s, tf, at_ms=None):
        return {"M5": self.m5, "M15": self.m15}.get(tf, [])

    def get(self, s, tf):
        return self.completed(s, tf)


@pytest.fixture
def env(monkeypatch):
    d = tempfile.mkdtemp()
    for name in ("STATE_FILE", "JOURNAL_FILE", "OVERVIEW_FILE", "COMMANDS_FILE", "CONTROL_FILE"):
        monkeypatch.setattr(B, name, os.path.join(d, name.lower()), raising=False)
        monkeypatch.setattr(C, name, os.path.join(d, name.lower()), raising=False)
    monkeypatch.setitem(C.ENGINE, "lot_mode", "risk")
    fake = FakeMT5()
    monkeypatch.setattr(B, "mt5c", fake)
    feed = FakeFeed()
    bk = B.Book(feed)
    bk.read_broker()
    return bk, fake, feed


def sell_signal(bk, fake):
    """A sell at 100, SL 102 (zone top 101.80 + 20 points), TP 94 (3R), layer 40 % of the way to the SL."""
    rec = {"id": "TEST-S-1", "symbol": "TEST", "side": "sell", "invalidation": 101.80, "status": "waiting pullback", "tf": "M15"}
    plan = {"entry": 100.0, "stop": 102.0, "target": {"price": 94.0, "label": "3R", "rr": 3.0},
            "layer": {"price": 100.8, "level": "moderate", "depth": 0.4}, "strength": {"level": "moderate"}}
    bk.setups[rec["id"]] = rec
    bk.enter(rec, plan, bk.feed.info["TEST"])
    return rec


def test_normal_and_layer_sizes(env):
    bk, fake, _ = env
    sell_signal(bk, fake)
    order, pend = fake.calls[0], fake.calls[1]
    assert order[:2] == ("order", "sell") and order[2] == 125.0           # 2.5 % of 10,000 = $250 / $2 per unit
    assert pend[:2] == ("pending", "sell") and pend[3] == 100.8 and pend[2] == 125.0   # 1.5 % = $150 / $1.2 per unit
    t = bk.trades["TEST-S-1"]
    assert t["mode"] == "A" and t["layer"]["state"] == "pending" and t["rr"] == 3.0


def test_layer_fill_tp1_and_trail(env):
    bk, fake, feed = env
    sell_signal(bk, fake)
    fake.fill_layer()
    bk.read_broker(); bk.manage()
    t = bk.trades["TEST-S-1"]
    assert t["mode"] == "B" and t["tp1"] == pytest.approx(97.0)              # centre of 100 → 94
    fake.set_price(96.9)                                                     # Target 1 reached
    bk.read_broker(); bk.manage()
    sls = [c for c in fake.calls if c[0] == "sltp"]
    assert len(sls) == 2 and all(c[2] == pytest.approx(99.8) for c in sls)   # both SLs past the first entry (−0.1R)
    assert t["tp1_hit"]
    # a new confirmed M5 swing high below the stop → trail down to it + 20 points
    t0 = t["opened_ms"]
    feed.m5 = [{"t": t0 + i * 5 * MIN, "o": p, "h": p + .1, "l": p - .1, "c": p} for i, p in
               enumerate([99.0, 98.5, 98.0, 98.6, 98.2, 97.6, 97.2, 96.9])]
    bk.read_broker(); bk.manage()
    assert t["stop"] == pytest.approx(98.9)                                   # swing high 98.7 + 0.2
    fake.set_price(97.5)                                                     # bounce: the stop never goes back up
    bk.read_broker(); bk.manage()
    assert t["stop"] == pytest.approx(98.9)


def test_mode_a_break_even_near_target(env):
    bk, fake, feed = env
    sell_signal(bk, fake)
    t = bk.trades["TEST-S-1"]
    fake.set_price(97.0)                                                     # 50 % of the way: keep the original SL
    bk.read_broker(); bk.manage()
    assert t["stop"] == 102.0
    fake.set_price(95.0)                                                     # 83 % of the way, still going: keep
    bk.read_broker(); bk.manage()
    assert t["stop"] == 102.0 and not t["be_done"]
    fake.set_price(95.8)                                                     # turned back up ≥ 10 % of the way → break-even
    bk.read_broker(); bk.manage()
    assert t["be_done"] and t["stop"] == pytest.approx(100.0)


def test_normal_stopped_cancels_layer(env):
    bk, fake, _ = env
    sell_signal(bk, fake)
    t = bk.trades["TEST-S-1"]
    fake.pos.pop(t["normal"]["ticket"])                                      # broker stopped the normal out
    bk.read_broker(); bk.manage()
    assert ("cancel", t["layer"]["order"]) in fake.calls and t["layer"]["state"] == "cancelled"
    bk.read_broker(); bk.manage()
    assert t["closed"] and t["pnl_usd"] == -25.0


def test_slots_count_pending_layers(env):
    bk, fake, _ = env
    sell_signal(bk, fake)
    assert bk.running() == 1 and bk.pending_layers() == 1 and bk.free_slots() == 18


def test_dashboard_commands(env):
    bk, fake, _ = env
    sell_signal(bk, fake)
    t = bk.trades["TEST-S-1"]
    bk.command({"action": "cancel_setup", "id": "TEST-S-1"})
    assert ("cancel", t["layer"]["order"]) in fake.calls
    bk.read_broker()
    bk.command({"action": "close_setup", "id": "TEST-S-1"})
    assert ("close", t["normal"]["ticket"]) in fake.calls


def _bos_setup(bk, feed, fake):
    from engine import strategy as V
    from engine.test_strategy import UP, bars
    b = bars(UP)
    rec = {**[x for x in V.bos_setups(b, V.structure(b), "M15", "TEST") if x["complete"]][0], "status": "waiting pullback", "touch_t": b[-1]["t"]}
    feed.m15 = feed.m5 = b
    fake.price = 10.68                                                       # buy at the ask 10.69, stop 9.7 − 20 points = 9.5
    bk.setups[rec["id"]] = rec
    return rec, b


def test_signal_without_a_structure_target_is_not_traded(env):
    bk, fake, feed = env
    rec, b = _bos_setup(bk, feed, fake)
    bk.signal(rec, True, [], b, b)                                           # only the 11.7 high above: 3R needs 14.26
    assert rec["status"] == "refused" and "no structure target" in rec["why"]
    assert not [c for c in fake.calls if c[0] == "order"]


def test_signal_trades_to_the_structure_target(env):
    bk, fake, feed = env
    rec, b = _bos_setup(bk, feed, fake)
    h1 = [{"t": i * 3_600_000, "o": 12, "h": h, "l": 11, "c": 12} for i, h in enumerate((12, 13, 15, 13, 12))]   # an untouched H1 high at 15
    bk.signal(rec, True, h1, b, b)
    order = next(c for c in fake.calls if c[0] == "order")
    assert rec["status"] == "entered" and order[3] == pytest.approx(9.5) and order[4] == 15
    assert rec["plan"]["setup"] == rec["id"] and rec["plan"]["why"] is None


def test_layer_inside_the_stops_level_is_not_sent(env):
    bk, fake, _ = env
    rec = {"id": "TEST-S-2", "symbol": "TEST", "side": "sell", "invalidation": 101.80, "status": "waiting pullback", "tf": "M15"}
    plan = {"entry": 100.0, "stop": 102.0, "target": {"price": 94.0, "label": "3R", "rr": 3.0}, "bid": 100.0, "ask": 100.01,
            "layer": {"price": 100.05, "level": "weak", "depth": 0.025}, "strength": {"level": "weak"}}
    bk.setups[rec["id"]] = rec
    bk.enter(rec, plan, bk.feed.info["TEST"])                                # stops level 10 points × 1.1 = 0.11 > 0.05
    assert [c[0] for c in fake.calls] == ["order"] and bk.trades["TEST-S-2"]["layer"] is None


def test_clock_is_measured_again_when_bars_look_an_hour_old(monkeypatch):
    import datetime as dt
    from engine.feed import Feed
    f = Feed()
    f.symbols, f.market, f.offset = ["BITCOIN"], {"BITCOIN": "crypto"}, dt.timedelta(hours=3)
    f.bars[("BITCOIN", "M5")] = [{"t": B.now_ms() - 62 * MIN}]                # stamped with summer time after the switch
    monkeypatch.setattr(f, "detect_clock", lambda: setattr(f, "offset", dt.timedelta(hours=2)))
    assert f.check_clock() and f.offset == dt.timedelta(hours=2)
    f.bars[("BITCOIN", "M5")] = [{"t": B.now_ms() - 2 * MIN}]
    f.clock_at = 0
    assert not f.check_clock()                                               # a fresh bar: nothing to do


def test_minimum_lot_mode(env, monkeypatch):
    bk, fake, _ = env
    monkeypatch.setitem(C.ENGINE, "lot_mode", "min")
    sell_signal(bk, fake)
    assert fake.calls[0][2] == 0.01 and fake.calls[1][2] == 0.01                # normal and layer at volume_min


def test_sdh4_setups_inside_a_reached_h4_zone(env):
    """David 2026-10-25: an H4 zone price came back to → its M15 CHoCH gets its own S&D H4 setup; the M15 BOS that
    already has its S&D M15 setup is that same setup (one trade), only marked with the H4 parent."""
    from engine import strategy as V
    from engine.test_strategy import UP, bars
    bk, fake, feed = env
    m15 = feed.m15 = bars(UP)
    st = V.structure(m15)
    normal = [c for c in V.bos_setups(m15, st, "M15", "TEST") if c["complete"]][0]
    bk.setups[normal["id"]] = {**normal, "status": "waiting pullback", "entry_type": "S&D M15"}
    bk.setups["TEST-H4-D-1"] = {"id": "TEST-H4-D-1", "symbol": "TEST", "tf": "H4", "side": "buy", "entry": 9.8, "invalidation": 9.0,
                                "touch_t": m15[8]["t"], "status": B.ZONE, "bos": {"t": 0}, "complete": True}
    m5 = [{**m15[-1], "t": m15[-1]["t"] + 900_000}]
    live = set()
    rows = bk.sdh4("TEST", {"bias": "buy", "why": "test"}, {"M15": st}, {"M15": {"buy": [normal["bos"]["t"]], "sell": []}}, live, m5, None, False, [])
    kids = [r for r in bk.setups.values() if r.get("entry_type") == "S&D H4"]
    assert bk.setups[normal["id"]]["parent"] == "TEST-H4-D-1"
    assert [k["bos"]["kind"] for k in kids] == ["CHoCH"] and kids[0]["parent"] == "TEST-H4-D-1" and kids[0]["id"] in live
    assert kids[0]["status"] != "waiting pullback" or kids[0]["aligned"]     # watched like any M15 setup (here: superseded by the BOS)
    assert any(r["id"] == "TEST-H4-D-1" for r in rows) and bk.setups["TEST-H4-D-1"]["status"] == B.ZONE
