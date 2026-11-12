"""engine/sdd_layers.py: three layer entries per S&D David zone (class video 6), their targets, and what happens after a
target (waiting layers cancelled, open ones to break-even, after two targets the last one's stop to TP1)."""
import pytest

from engine import sdd_layers as SL

INFO = {"digits": 2, "point": 0.01, "trade_stops_level": 0, "volume_min": 0.01, "volume_step": 0.01,
        "trade_tick_value": 0.01, "trade_tick_size": 0.01, "trade_contract_size": 1}


def demand():
    # candle A 100.00 – 102.00 (mid 101), FVG 102.00 – 103.00 above it, the leg went up to 111.00
    return {"dir": "buy", "side": "demand", "top": 102.0, "bottom": 100.0, "mid": 101.0, "proximal": 102.0, "distal": 100.0,
            "fvg": {"bottom": 102.0, "top": 103.0, "atr": 0.5}, "fib_ext": 111.0, "valid": True, "live": True,
            "status": "fresh", "a": 0, "break": 3, "targets": [{"fib": 0.618, "price": 105.4, "rr": 1.7}]}


def supply():
    return {"dir": "sell", "side": "supply", "top": 202.0, "bottom": 200.0, "mid": 201.0, "proximal": 200.0, "distal": 202.0,
            "fvg": {"bottom": 199.0, "top": 200.0, "atr": 0.5}, "fib_ext": 191.0, "valid": True, "live": True,
            "status": "fresh", "a": 0, "break": 3, "targets": [{"fib": 0.618, "price": 196.6, "rr": 1.7}]}


def test_demand_three_layers_one_stop_targets_from_L1():
    p = SL.layer_plan(demand(), {"bid": 108.0, "ask": 108.1}, INFO)
    L = {x["k"]: x for x in p["layers"]}
    assert [L[k]["price"] for k in (1, 2, 3)] == [103.1, 102.1, 101.1]          # FVG edge / A's high / A's 50 %, + spread
    assert {L[k]["sl"] for k in L} == {99.9}                                      # one stop: 10 points under A's low
    assert [L[k]["tp"] for k in (1, 2, 3)] == [107.0, 109.0, 111.0]              # 50 / 75 / 100 % from L1 (103) to 111


def test_supply_layers_carry_the_spread_on_the_stop_and_targets():
    p = SL.layer_plan(supply(), {"bid": 195.0, "ask": 195.1}, INFO)
    L = {x["k"]: x for x in p["layers"]}
    assert [L[k]["price"] for k in (1, 2, 3)] == [199.0, 200.0, 201.0]
    assert {L[k]["sl"] for k in L} == {202.2}                                     # A's high + spread + 10 points
    assert [L[k]["tp"] for k in (1, 2, 3)] == [195.1, 193.1, 191.1]              # 50 / 75 / 100 % from 199 to 191, + spread
    wide = SL.layer_plan(supply(), {"bid": 195.0, "ask": 195.5}, INFO)          # spread 0.5 > 25 % of L3's 1.6 stop
    assert "spread" in {x["k"]: x for x in wide["layers"]}[3]["why"]


def test_a_layer_price_already_passed_is_skipped():
    p = SL.layer_plan(demand(), {"bid": 102.5, "ask": 102.6}, INFO)              # already inside the FVG
    L = {x["k"]: x for x in p["layers"]}
    assert "why" in L[1] and "price" in L[2] and "price" in L[3]


def test_no_fvg_or_extreme_places_nothing():
    z = demand()
    z["fib_ext"] = 102.5                                                          # the leg's extreme under L1
    assert "why" in SL.layer_plan(z, {"bid": 108.0, "ask": 108.1}, INFO)


# ── the book on a fake MT5 ──

class FakeMT5:
    def __init__(self):
        self.n, self.orders, self.pos, self.deal_log, self.calls, self.others = 1000, {}, {}, {}, [], 0

    def call(self, reqs, timeout=0):
        out = []
        for q in reqs:
            self.calls.append(q)
            op = q["op"]
            if op == "tick":
                out.append({"result": {"bid": 108.0, "ask": 108.1}})
            elif op == "pending":
                self.n += 1
                self.orders[self.n] = q
                out.append({"result": {"ok": True, "order": self.n}})
            elif op == "cancel":
                self.orders.pop(q["ticket"], None)
                out.append({"result": {"ok": True}})
            elif op in ("modify", "sltp"):
                out.append({"result": {"ok": True}})
            elif op == "orders":
                mine = [{"ticket": t, "magic": q.get("magic", SL.S["MAGIC"])} for t in self.orders]
                out.append({"result": mine + [{"ticket": -i, "magic": 5050700} for i in range(1, self.others + 1)]})
            elif op == "positions":
                out.append({"result": list(self.pos.values())})
        return out

    def deals(self, position=None, days=3):
        return self.deal_log.get(position, [])

    def fill(self, ticket, price):
        self.orders.pop(ticket)
        self.pos[ticket] = {"ticket": ticket, "identifier": ticket, "price_open": price, "price_current": price, "profit": 0, "sl": 0}

    def close(self, ticket, price, profit, reason):
        self.pos.pop(ticket)
        self.deal_log[ticket] = [{"entry": 0, "price": 0, "profit": 0}, {"entry": 1, "price": price, "profit": profit, "reason": reason}]


class Main:
    def __init__(self):
        self.info = {"GOLD": INFO}
        self.bars = {"GOLD": [{"t": i * 900_000, "o": 1, "h": 1, "l": 1, "c": 1} for i in range(10)]}
        self.zones = {"GOLD": [demand()]}
        self.fetched_slot = 0

    def lots(self, s):
        return 0.01


@pytest.fixture
def book(tmp_path, monkeypatch):
    fake = FakeMT5()
    monkeypatch.setattr(SL, "mt5c", fake)
    monkeypatch.setattr(SL, "STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setattr(SL, "journal", lambda *a, **k: None)
    monkeypatch.setattr(SL, "log", lambda *a, **k: None)
    monkeypatch.setattr(SL, "enabled", lambda: True)
    b = SL.SddLayerBook(Main())
    b.fake = fake
    return b


def new_bar(b):
    b.main.fetched_slot += 1
    b.step(trading=True, account={"equity": 1000, "margin_free": 900})


def test_places_three_layers_once_per_zone(book):
    new_bar(book)
    placed = [q for q in book.fake.calls if q["op"] == "pending"]
    assert [q["price"] for q in placed] == [103.1, 102.1, 101.1] and {q["sl"] for q in placed} == {99.9}
    assert {q["magic"] for q in placed} == {SL.S["MAGIC"]}
    new_bar(book)                                                                 # same zone: no second set
    assert len([q for q in book.fake.calls if q["op"] == "pending"]) == 3


def test_a_target_cancels_the_waiting_layers_and_moves_the_open_to_break_even(book):
    new_bar(book)
    t1, t2, t3 = sorted(book.fake.orders)
    book.fake.fill(t1, 103.1)
    book.fake.fill(t2, 102.1)
    new_bar(book)                                                                 # both fills seen
    book.fake.close(t1, 107.0, 3.9, 5)                                            # L1 takes TP1
    new_bar(book)
    o = {x["layer"]: x for x in book.orders.values()}
    assert o[1]["state"] == "closed" and o[1]["end"] == "target"
    assert o[3]["state"] == "cancelled"                                           # L3 was still waiting
    assert o[2]["sl"] == 102.1 and o[2]["be"]                                     # L2 to its entry
    assert {"op": "sltp", "ticket": t2, "sl": 102.1, "tp": o[2]["tp"]} in book.fake.calls


def test_after_two_targets_the_last_layer_stop_goes_to_tp1(book):
    new_bar(book)
    t1, t2, t3 = sorted(book.fake.orders)
    for t, p in ((t1, 103.1), (t2, 102.1), (t3, 101.1)):
        book.fake.fill(t, p)
    new_bar(book)
    book.fake.close(t1, 107.0, 3.9, 5)
    new_bar(book)
    book.fake.close(t2, 109.0, 6.9, 5)
    new_bar(book)
    o = {x["layer"]: x for x in book.orders.values()}
    assert o[3]["sl"] == 107.0                                                    # TP1's price
    book.fake.close(t3, 107.0, 5.9, 4)
    new_bar(book)
    assert o[3]["state"] == "closed" and o[3]["end"] == "trailed stop"


def test_zone_broken_cancels_its_waiting_layers(book):
    new_bar(book)
    z = book.main.zones["GOLD"][0]
    z.update(live=False, status="broken")
    new_bar(book)
    assert all(o["state"] == "cancelled" and "broken" in o["end"] for o in book.orders.values())


def test_switched_off_takes_the_waiting_layers_back(book, monkeypatch):
    new_bar(book)
    monkeypatch.setattr(SL, "enabled", lambda: False)
    book.step(trading=True, account={})
    assert all(o["state"] == "cancelled" for o in book.orders.values())


def test_layers_leave_order_slots_for_the_others(book):
    book.fake.others = SL.S["ORDER_LIMIT"] - SL.S["RESERVE"] - 2         # room for 2 layers only: a 3-layer set waits
    new_bar(book)
    assert not [q for q in book.fake.calls if q["op"] == "pending"]
    assert "no free order slot" in book.why[next(iter(book.why))]


def test_over_budget_gives_back_the_unfilled_set(book):
    new_bar(book)
    assert len(book.fake.orders) == 3
    book.fake.others = SL.S["ORDER_LIMIT"] - SL.S["RESERVE"] - 1         # the others grew: our 3 no longer fit
    new_bar(book)
    assert not book.fake.orders and not book.orders                        # cancelled and forgotten (may come back)
