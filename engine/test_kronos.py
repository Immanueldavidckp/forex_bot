"""
Offline tests of Kronos' trades (kronos_book.py) on a fake MT5 — no terminal, no GPU, no orders:

    cd ~/forex && python3 -m pytest -q engine/test_kronos.py
"""
from __future__ import annotations

import datetime as _dt
import json

import pytest

from engine import config as C
from engine import kronos_book as KB

BAR = KB.BAR_MS
T0 = int(_dt.datetime(2026, 10, 27, 10, 0, tzinfo=_dt.timezone.utc).timestamp() * 1000)   # a Tuesday
INFO = {"digits": 2, "point": 0.01, "volume_min": 0.01, "volume_step": 0.01, "volume_max": 100, "trade_stops_level": 10,
        "trade_tick_value": 0.01, "trade_tick_size": 0.01, "trade_contract_size": 1}


def rows(n=520, end=T0, price=4000.0, rng=4.0):
    """n closed M15 bars ending with the one that opened at `end` - BAR: each 4.0 high-low (ATR 4.0)."""
    return [[end - (n - i) * BAR, price, price + rng / 2, price - rng / 2, price, 100, 0.3] for i in range(n)]


def sig(p_up=0.9, last=4000.0, move=6.0, bar_t=T0 - BAR):
    med = [last + move * (k + 1) / 8 for k in range(8)]
    return {"bar_t": bar_t, "last": last, "p_up": p_up, "paths": 16, "median": med, "q10": [m - 5 for m in med],
            "q90": [m + 5 for m in med], "made_ms": T0 + 30_000, "secs": 20}


class FakeMT5:
    Mt5Error = RuntimeError

    def __init__(self):
        self.pos, self.calls, self.n = {}, [], 500
        self.stale, self.rates = 0, 0                 # stale: how many rates replies still serve 5-bar-old history
        self.deal_log = {}
        self.server_to_utc_ms = lambda t, off=None: t * 1000

    def call(self, reqs, timeout=0):
        out = []
        for q in reqs:
            if q["op"] == "info":
                out.append({"result": INFO})
            elif q["op"] == "positions":
                out.append({"result": self.positions(q.get("magic"))})
            elif q["op"] == "tick":
                out.append({"result": {"bid": 4000.0, "ask": 4000.3, "time": (T0 + 300_000) // 1000}})
            elif q["op"] == "rates" and q["count"] == 1:                # the live read: the forming bar
                out.append({"result": [[(T0 + BAR) // 1000, 4000.0, 4003.0, 3998.0, 4000.0, 50, 0, 30]]})
            elif q["op"] == "rates":
                self.rates += 1
                end = T0 + BAR - (5 * BAR if self.stale else 0)
                self.stale = max(0, self.stale - 1)
                out.append({"result": [[r[0] // 1000, r[1], r[2], r[3], r[4], r[5], 0, 30] for r in rows(q["count"], end=end)]})
        return out

    def tick(self, s):
        return {"bid": 4000.0, "ask": 4000.3}

    def order(self, sym, side, q, sl, tp, magic, comment, dev):
        self.calls.append(("order", sym, side, q, sl, tp, magic, comment))
        self.n += 1
        self.pos[self.n] = {"ticket": self.n, "symbol": sym, "price_open": 4000.3 if side == "buy" else 4000.0, "price_current": 4001.0,
                            "profit": 0.7, "time_msc": self.n, "magic": magic}
        return {"ok": True, "order": self.n}

    def positions(self, magic=None, symbol=None):
        return [p for p in self.pos.values() if magic is None or p["magic"] == magic]

    def close(self, ticket, comment="", **kw):
        self.calls.append(("close", ticket, comment))
        self.pos.pop(ticket, None)
        self.deal_log[ticket] = [{"entry": 0, "profit": 0}, {"entry": 1, "reason": 3, "price": 4003.0, "profit": 2.7, "commission": -0.1}]
        return {"ok": True}

    def deals(self, position=None, days=3):
        return self.deal_log.get(position, [])


class FakeFeed:
    market = {"BITCOIN": "crypto", "EURUSD": "forex"}

    def clock(self):
        return None


@pytest.fixture
def kb(tmp_path, monkeypatch):
    fake = FakeMT5()
    monkeypatch.setattr(KB, "mt5c", fake)
    for name in ("FEED_DIR", "SIGNALS_FILE", "STATE_FILE", "VIEW_FILE", "DECISIONS_FILE", "REPORT_FILE", "CLAUDE_NOTES_FILE"):
        p = tmp_path / name.lower()
        if name == "FEED_DIR":
            p.mkdir()
        monkeypatch.setattr(KB, name, str(p))
    monkeypatch.setattr(KB, "journal", lambda *a, **k: None)
    monkeypatch.setattr(KB, "log", lambda *a, **k: None)
    monkeypatch.setattr(KB, "enabled", lambda: True)
    monkeypatch.setitem(KB.K, "SYMBOLS", ["GOLD"])
    clock = {"now": T0 + 60_000}
    monkeypatch.setattr(KB, "now_ms", lambda: clock["now"])
    b = KB.KronosBook(FakeFeed())
    b.fake, b.clock = fake, clock
    return b


def write_sig(kb, s):
    with open(KB.SIGNALS_FILE, "w") as f:
        json.dump({"GOLD": s}, f)


# ── decide() ──

def test_decide_buy_levels():
    d = KB.decide(sig(0.9), rows(), INFO, "metal", T0)
    assert d["side"] == "buy"
    assert d["sl"] == pytest.approx(d["entry"] - 1.0 * 4.0)          # SL 1 × ATR
    assert d["tp"] == pytest.approx(d["entry"] + 2.0 * 4.0)          # TP 2 × ATR, not the median move (6.0)


def test_decide_tp_twice_the_stop_and_sell():
    d = KB.decide(sig(0.1, move=-1.0), rows(), INFO, "metal", T0)
    assert d["side"] == "sell" and d["tp"] == pytest.approx(d["entry"] - 8.0) and d["sl"] == pytest.approx(d["entry"] + 4.0)


def test_decide_needs_agreement_and_room():
    assert KB.decide(sig(0.6), rows(), INFO, "metal", T0)["side"] is None
    assert "spread" in KB.decide(sig(0.9, move=0.5), rows(), INFO, "metal", T0)["why"]     # 0.5 < 2 × 0.3 spread


def test_decide_friday_late_only_off_crypto():
    fri = int(_dt.datetime(2026, 10, 30, 20, 0, tzinfo=_dt.timezone.utc).timestamp() * 1000)
    assert KB.decide(sig(0.9), rows(), INFO, "forex", fri)["side"] is None
    assert KB.decide(sig(0.9), rows(), INFO, "crypto", fri)["side"] == "buy"


def test_decide_stop_widened_to_stops_level():
    wide = {**INFO, "trade_stops_level": 1000}                      # 10.0 × 1.1 margin = 11.0 > 1 × ATR
    d = KB.decide(sig(0.9), rows(), wide, "metal", T0, {"bid": 4000.0, "ask": 4000.3})
    assert d["entry"] - d["sl"] == pytest.approx(11.0)


# ── the book on a fake MT5 ──

def test_entry_time_exit_and_booking(kb):
    write_sig(kb, sig(0.9))
    kb.step(trading=True)
    assert open(KB.FEED_DIR + "/GOLD.json").read()                   # the bars for the forecaster
    orders = [c for c in kb.fake.calls if c[0] == "order"]
    assert len(orders) == 1 and orders[0][2] == "buy" and orders[0][6] == C.KRONOS["MAGIC"] and orders[0][3] == 0.01
    t = next(iter(kb.trades.values()))
    assert t["close_by_ms"] == t["opened_ms"] + 8 * BAR
    kb.step(trading=True)                                            # same forecast: decided once
    assert len([c for c in kb.fake.calls if c[0] == "order"]) == 1
    kb.clock["now"] = t["close_by_ms"] + 1000
    kb.step(trading=True)                                            # 8 bars up → closed at market
    assert ("close", t["ticket"], "KRN time exit") in kb.fake.calls
    kb.step(trading=True)                                            # gone → booked from the deals
    assert t["closed"] and t["pnl_usd"] == 2.6 and t["reason"] == "time"
    view = json.load(open(KB.VIEW_FILE))
    assert view["totals"] == {"n": 1, "won": 1, "pnl_usd": 2.6} and view["open"] == []


def test_no_order_when_trading_off(kb):
    write_sig(kb, sig(0.9))
    kb.step(trading=False)
    assert not [c for c in kb.fake.calls if c[0] == "order"]
    assert kb.decisions["GOLD"]["side"] == "buy" and "trading is off" in kb.decisions["GOLD"]["action"]


def test_stale_forecast_not_traded(kb):
    write_sig(kb, sig(0.9))
    kb.clock["now"] = T0 + 11 * 60_000                               # 11 min after the bar closed
    kb.step(trading=True)
    assert not [c for c in kb.fake.calls if c[0] == "order"] and "too late" in kb.decisions["GOLD"]["action"]


def test_live_record_scores_after_horizon(kb):
    kb.rows["GOLD"] = rows(end=T0)
    kb.pending = [{"symbol": "GOLD", "bar_t": T0 - 9 * BAR, "last": 3990.0, "end": 3995.0, "p_up": 0.8}]
    kb.resolve()                                                     # the bar 8 later closed at 4000 > 3990: a hit
    assert kb.record["GOLD"] == {"n": 1, "hit": 1, "n_conf": 1, "hit_conf": 1} and kb.pending == []


def test_dashboard_close_command(monkeypatch):
    from engine import book as B
    fake = FakeMT5()
    fake.order("GOLD", "buy", 0.01, 3990, 4010, C.KRONOS["MAGIC"], "KRN", 30)
    monkeypatch.setattr(B, "mt5c", fake)
    monkeypatch.setattr(B, "journal", lambda *a, **k: None)
    bk = B.Book.__new__(B.Book)
    bk.positions = []
    bk.command({"action": "kronos_close", "ticket": 501})
    assert ("close", 501, "KRN closed (dashboard)") in fake.calls


def test_stale_bars_are_asked_again(kb):
    kb.fake.stale = 1                                                # the terminal first serves old history
    kb.step(trading=False)
    assert kb.rows["GOLD"][-1][0] == T0 - 5 * BAR
    kb.clock["now"] += 16_000
    kb.step(trading=False)                                           # asked again 15 s later: now the fresh bar
    assert kb.rows["GOLD"][-1][0] == T0 - BAR and kb.fake.rates == 2
    kb.clock["now"] += 16_000
    kb.step(trading=False)                                           # fresh: no more asks until the next bar
    assert kb.fake.rates == 2


def test_no_limit_stacks_trades_on_one_symbol(kb):
    write_sig(kb, sig(0.9))
    kb.step(trading=True)
    kb.clock["now"] = T0 + BAR + 60_000                              # the next bar's forecast, the first trade still open
    write_sig(kb, sig(0.85, bar_t=T0))
    kb.step(trading=True)
    orders = [c for c in kb.fake.calls if c[0] == "order"]
    assert len(orders) == 2 and len({t["ticket"] for t in kb.trades.values()}) == 2


def test_limits_apply_when_set(kb, monkeypatch):
    monkeypatch.setitem(KB.K, "MAX_PER_SYMBOL", 1)
    write_sig(kb, sig(0.9))
    kb.step(trading=True)
    kb.clock["now"] = T0 + BAR + 60_000
    write_sig(kb, sig(0.85, bar_t=T0))
    kb.step(trading=True)
    assert len([c for c in kb.fake.calls if c[0] == "order"]) == 1 and "already open here" in kb.decisions["GOLD"]["action"]


def test_free_margin_guard(kb):
    write_sig(kb, sig(0.9))
    kb.step(trading=True, account={"equity": 1000.0, "margin_free": 200.0})
    assert not [c for c in kb.fake.calls if c[0] == "order"] and "free margin" in kb.decisions["GOLD"]["action"]


def test_claude_trades_shown_never_touched_and_booked(kb):
    """Claude's own MT5 trade (magic CLAUDE_MAGIC): on the page with its plan, never closed by the engine, booked once gone."""
    cm = C.KRONOS["CLAUDE_MAGIC"]
    kb.fake.pos[900] = {"ticket": 900, "symbol": "EURCAD", "type": 1, "volume": 0.01, "price_open": 1.56448, "sl": 1.5656,
                        "tp": 1.5628, "price_current": 1.5644, "profit": 0.05, "time": T0 // 1000, "magic": cm}
    with open(KB.CLAUDE_NOTES_FILE, "w") as f:
        json.dump({"900": {"plan": "trend down + Kronos 75 % down", "close_by_ms": T0 + 8 * BAR}}, f)
    kb.step(trading=True)
    c = json.load(open(KB.VIEW_FILE))["claude"]
    assert c["magic"] == cm and len(c["open"]) == 1 and c["closed"] == []
    t = c["open"][0]
    assert (t["side"], t["entry"], t["sl"], t["tp"], t["opened_ms"]) == ("sell", 1.56448, 1.5656, 1.5628, T0)
    assert t["plan"] == "trend down + Kronos 75 % down" and t["close_by_ms"] == T0 + 8 * BAR
    kb.clock["now"] += 20 * BAR                                      # long past any Kronos hold: still not the engine's to close
    kb.step(trading=True)
    assert not [c for c in kb.fake.calls if c[0] in ("close", "order")] and kb.trades == {}
    kb.fake.pos.pop(900)                                             # the broker's TP took it
    kb.fake.deal_log[900] = [{"entry": 0, "profit": 0}, {"entry": 1, "reason": 5, "price": 1.5628, "profit": 1.18, "commission": 0}]
    kb.clock["now"] += 31_000
    kb.step(trading=True)
    c = json.load(open(KB.VIEW_FILE))["claude"]
    assert c["open"] == [] and c["closed"][0]["reason"] == "target" and c["totals"] == {"n": 1, "won": 1, "pnl_usd": 1.18}


def test_live_quote_and_forming_bar_in_the_view(kb):
    kb.step(trading=False)
    g = json.load(open(KB.VIEW_FILE))["symbols"][0]
    assert g["live"] == {"bid": 4000.0, "ask": 4000.3, "t_ms": T0 + 300_000, "bar": [(T0 + BAR) // 1000, 4000.0, 4003.0, 3998.0, 4000.0]}
    assert g["bars"][-1][0] == T0 // 1000 - BAR // 1000                   # closed bars stay closed-only
