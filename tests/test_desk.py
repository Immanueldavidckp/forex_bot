#!/usr/bin/env python3
"""Offline tests for the forex desk: pair maths, hours, indicators, guard, paper fills, stops, OpenClaw ticket.

  python3 -m unittest discover -s tests -v
"""
import os, sys, tempfile, unittest
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.update(LIVE="0", SPREAD_PIPS="", RISK_PER_TRADE_PCT="1.0", MAX_LEVERAGE="10", MAX_NOTIONAL_USD="1000",
                  DAILY_LOSS_LIMIT_PCT="3", MIN_CONFIDENCE="0.6", MIN_REWARD_RISK="1.5", EVENT_BLACKOUT_HOURS="2")

import claude_trading_desk as ctd  # noqa: E402
import llm_paper_trader as lpt  # noqa: E402
import place_order as po  # noqa: E402

NY = lpt.NY
ROLES = ("research", "news", "strategy", "code", "risk", "boss")


def market(**kw):
    m = {"symbol": "EUR/USD", "price": 1.08500, "atr14": 0.00150, "pip_size": 0.0001, "rollover_window": False,
         "hours_to_weekly_close": 40, "ema20": 1.0845, "ema50": 1.0830, "rsi14": 58, "low_24": 1.0820,
         "high_24": 1.0880}
    m.update(kw)
    return m


def reports(action="buy", stop=1.08300, target=1.08850, size=0.5, **over):
    r = {"research": {"trend": "up", "strength": 0.7, "support": 1.082, "resistance": 1.088, "summary": "up"},
         "news": {"sentiment": 0.2, "risk_event_next_24h": False, "next_event_hours": None, "summary": "quiet"},
         "strategy": {"action": action, "size_pct": size, "stop": stop, "target": target, "confidence": 0.7},
         "code": {"valid": True, "reward_risk": 1.75, "stop_atr": 1.33, "issues": []},
         "risk": {"verdict": "approve", "size_pct": size, "reasons": []},
         "boss": {"action": action, "size_pct": size, "stop": stop, "target": target, "confidence": 0.7,
                  "summary": "trend long"}}
    for role, fields in over.items():
        r[role] = {**r[role], **fields}
    return r


class TempState(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = po.STATE_FILE, po.LIVE, ctd.TICKETS
        po.STATE_FILE, po.LIVE, ctd.TICKETS = os.path.join(self.tmp.name, "state.json"), False, self.tmp.name

    def tearDown(self):
        po.STATE_FILE, po.LIVE, ctd.TICKETS = self.old
        self.tmp.cleanup()


class PairMaths(unittest.TestCase):
    def test_norm_and_pips(self):
        self.assertEqual(lpt.norm("eurusd"), "EUR/USD")
        self.assertEqual(lpt.norm("USD_JPY"), "USD/JPY")
        self.assertRaises(ValueError, lpt.norm, "EUR/GBP")
        self.assertEqual(lpt.pip_size("USD/JPY"), 0.01)
        self.assertEqual(lpt.pip_size("GBP/USD"), 0.0001)
        self.assertEqual(lpt.decimals("USD/JPY"), 3)

    def test_pnl_in_usd(self):
        self.assertAlmostEqual(lpt.pnl_usd("EUR/USD", "long", 1000, 1.0850, 1.0870), 2.00)
        self.assertAlmostEqual(lpt.pnl_usd("EUR/USD", "short", 1000, 1.0850, 1.0870), -2.00)
        self.assertAlmostEqual(lpt.pnl_usd("USD/JPY", "short", 1000, 150.00, 149.50), 500 / 149.5)
        self.assertEqual(lpt.notional_usd("USD/JPY", 300, 150.0), 300)


class Hours(unittest.TestCase):
    def test_week(self):
        self.assertTrue(lpt.market_open(datetime(2026, 10, 21, 12, tzinfo=NY)))     # Wednesday
        self.assertTrue(lpt.market_open(datetime(2026, 10, 23, 16, 59, tzinfo=NY)))  # Friday before close
        self.assertFalse(lpt.market_open(datetime(2026, 10, 23, 17, 1, tzinfo=NY)))
        self.assertFalse(lpt.market_open(datetime(2026, 10, 24, 12, tzinfo=NY)))     # Saturday
        self.assertFalse(lpt.market_open(datetime(2026, 10, 25, 16, tzinfo=NY)))     # Sunday before open
        self.assertTrue(lpt.market_open(datetime(2026, 10, 25, 17, 30, tzinfo=NY)))

    def test_close_and_rollover(self):
        self.assertAlmostEqual(lpt.hours_to_close(datetime(2026, 10, 23, 15, tzinfo=NY)), 2.0)
        self.assertTrue(lpt.in_rollover(datetime(2026, 10, 21, 16, 50, tzinfo=NY)))
        self.assertFalse(lpt.in_rollover(datetime(2026, 10, 21, 12, tzinfo=NY)))
        self.assertEqual(lpt.trading_day(datetime(2026, 10, 21, 17, 30, tzinfo=NY)), "2026-10-22")


class Indicators(unittest.TestCase):
    def test_values(self):
        up = [{"t": i, "o": 1 + i / 1000, "h": 1 + i / 1000 + 0.0005, "l": 1 + i / 1000 - 0.0005, "c": 1 + i / 1000}
              for i in range(100)]
        ind = lpt.indicators(up)
        self.assertGreater(ind["ema20"], ind["ema50"])
        self.assertEqual(ind["rsi14"], 100.0)
        self.assertAlmostEqual(ind["atr14"], 0.0015, places=6)   # true range reaches back to the prior close

    def test_mock_feed_moves(self):
        feed = lpt.MockFeed(7, start=1.085)
        a, b = feed.get(), feed.get()
        self.assertEqual(len(a), 150)
        self.assertGreater(b[-1]["t"], a[-1]["t"])

    def test_yahoo_tick_folded_into_its_candle(self):
        cs = [{"t": 0, "o": 1, "h": 2, "l": 0.5, "c": 1.5}, {"t": 3600, "o": 1.5, "h": 1.6, "l": 1.4, "c": 1.5},
              {"t": 3600 + 1380, "o": 1.7, "h": 1.7, "l": 1.7, "c": 1.7}]
        out = lpt._merge(cs, 3600)
        self.assertEqual(len(out), 2)
        self.assertEqual((out[-1]["h"], out[-1]["c"]), (1.7, 1.7))


class ParseJson(unittest.TestCase):
    def test_replies(self):
        self.assertEqual(ctd.parse_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(ctd.parse_json('Sure. {"a": {"b": [1, 2]}} done'), {"a": {"b": [1, 2]}})
        self.assertIn("error", ctd.parse_json("no json here"))
        self.assertIn("error", ctd.parse_json(None))


class Guard(unittest.TestCase):
    def test_valid_long_is_sized_from_risk(self):
        f = ctd.guard(reports(), market(), None, 50)
        self.assertEqual((f["action"], f["side"]), ("buy", "long"))
        self.assertEqual(f["units"], 125)                 # $50 x 1% x 0.5 = $0.25 over a 20-pip stop
        self.assertAlmostEqual(f["risk_usd"], 0.25)

    def test_valid_short(self):
        f = ctd.guard(reports("sell", stop=1.08700, target=1.08150), market(), None, 50)
        self.assertEqual((f["action"], f["side"]), ("sell", "short"))

    def test_usd_jpy_sizing(self):
        m = market(symbol="USD/JPY", price=150.00, atr14=0.25, pip_size=0.01)
        f = ctd.guard(reports(stop=149.70, target=150.50, size=1.0), m, None, 100)
        self.assertEqual(f["units"], 500)                 # $1 risk / (0.30 JPY / 150) per unit

    def test_leverage_and_notional_caps(self):
        f = ctd.guard(reports(size=1.0), market(), None, 10_000)
        self.assertEqual(f["units"], int(1000 / 1.085))   # MAX_NOTIONAL_USD wins over the risk-based size

    def test_risk_reduce_caps_size(self):
        f = ctd.guard(reports(size=0.8, risk={"verdict": "reduce", "size_pct": 0.2}), market(), None, 50)
        self.assertEqual(f["size_pct"], 0.2)

    def test_blocks(self):
        cases = {
            "wrong side": reports(stop=1.08600),
            "reward:risk": reports(target=1.08700),
            "risk reject": reports(risk={"verdict": "reject"}),
            "quant": reports(code={"valid": False, "issues": ["bad stop"]}),
            "mismatch": reports(strategy={"action": "hold"}),
            "low confidence": reports(boss={"confidence": 0.4}),
            "event": reports(news={"next_event_hours": 1}),
            "event, time unknown": reports(news={"risk_event_next_24h": True, "next_event_hours": None}),
            "agent error": reports(research={"error": "timeout"}),
            "stop too tight": reports(stop=1.08450, target=1.08600),
            "stop too wide": reports(stop=1.07900, target=1.09500),
        }
        for name, r in cases.items():
            with self.subTest(name):
                self.assertEqual(ctd.guard(r, market(), None, 50)["action"], "hold")
        self.assertEqual(ctd.guard(reports(), market(), None, 50, day_pnl=-1.6)["action"], "hold")
        later = reports(news={"risk_event_next_24h": True, "next_event_hours": 9})
        self.assertEqual(ctd.guard(later, market(), None, 50)["action"], "buy")      # known and far enough away
        self.assertEqual(ctd.guard(reports(), market(rollover_window=True), None, 50)["action"], "hold")
        self.assertEqual(ctd.guard(reports(), market(hours_to_weekly_close=1), None, 50)["action"], "hold")
        self.assertEqual(ctd.guard({"boss": {"error": "x"}}, market(), None, 50)["action"], "hold")

    def test_with_open_position(self):
        held = {"symbol": "EUR/USD", "side": "long", "units": 100, "stop": 1.083, "target": 1.0885}
        self.assertEqual(ctd.guard(reports("close"), market(), held, 50)["action"], "close")
        self.assertEqual(ctd.guard(reports("sell"), market(), held, 50)["action"], "close")   # exit, never flip
        self.assertEqual(ctd.guard(reports("buy"), market(), held, 50)["action"], "hold")     # never add


class PaperAccount(TempState):
    def test_long_stopped_out_at_bid(self):
        r = po.open_position("EUR/USD", "long", 125, 1.08300, 1.08850, 1.08500)
        self.assertEqual(r["fill"], 1.08505)              # ask = mid + half a 1-pip spread
        self.assertIsNone(po.check_price(1.08310))        # bid 1.08305, still above the stop
        t = po.check_price(1.08300)                       # bid 1.08295: crossed between checks, filled there
        self.assertEqual((t["reason"], t["exit"]), ("stop", 1.08295))
        self.assertAlmostEqual(po.load()["day_pnl"], 125 * (1.08295 - 1.08505), places=6)

    def test_short_target_and_ticket_runs_once(self):
        a = po.open_position("EUR/USD", "short", 100, 1.08700, 1.08150, 1.08500, ticket="T1")
        b = po.open_position("EUR/USD", "short", 100, 1.08700, 1.08150, 1.08500, ticket="T1")
        self.assertEqual(a, b)
        self.assertEqual(po.check_price(1.08140)["reason"], "target")
        self.assertGreater(po.load()["total_pnl"], 0)

    def test_candles_before_open_only_count_their_close(self):
        po.open_position("EUR/USD", "long", 100, 1.08300, 1.08850, 1.08500)
        opened = po.load()["position"]["opened_t"]
        old_bar = {"t": opened - 7800, "o": 1.0810, "h": 1.0815, "l": 1.0790, "c": 1.0795}     # ended before
        early = {"t": opened - 600, "o": 1.0850, "h": 1.0851, "l": 1.0820, "c": 1.0849}       # opened in this one
        self.assertIsNone(po.check_exits([old_bar, early]))
        gap = {"t": opened + 60, "o": 1.0825, "h": 1.0830, "l": 1.0820, "c": 1.0828}
        t = po.check_exits([gap])
        self.assertEqual(t["reason"], "stop")
        self.assertAlmostEqual(t["exit"], 1.08245)         # gapped through the stop: filled at the open's bid

    def test_order_checks(self):
        self.assertIn("stop < price", po.check_order("EUR/USD", "long", 100, 1.086, 1.090, 1.085))
        self.assertIn("MAX_NOTIONAL", po.check_order("EUR/USD", "long", 5000, 1.083, 1.090, 1.085))
        self.assertFalse(po.open_position("EUR/USD", "long", 0, 1.083, 1.090, 1.085)["ok"])
        po.open_position("EUR/USD", "long", 100, 1.083, 1.090, 1.085)
        self.assertFalse(po.open_position("EUR/USD", "long", 100, 1.083, 1.090, 1.085)["ok"])   # one at a time
        self.assertFalse(po.close_position("USD/JPY", 150.0)["ok"])
        self.assertTrue(po.close_position("EUR/USD", 1.0860)["ok"])


class Handoff(TempState):
    def test_paper(self):
        final = ctd.guard(reports(), market(), None, 50)
        order, res = ctd.handoff(final, "EUR/USD", "paper", 1.085)
        self.assertTrue(res["ok"], res)
        self.assertEqual(po.load()["position"]["units"], order["units"])

    def test_openclaw_ticket_is_verified_in_state(self):
        old = ctd.CFG["OPENCLAW_CMD"]
        try:
            ctd.CFG["OPENCLAW_CMD"] = f"{sys.executable} {os.path.join(ROOT, 'tests', 'fake_openclaw.py')}"
            final = ctd.guard(reports(), market(), None, 50)
            order, res = ctd.handoff(final, "EUR/USD", "openclaw", 1.085)
            self.assertTrue(res["ok"], res)
            self.assertEqual(res["via"], "openclaw")
            self.assertIn("--simulate", ctd.place_order_cmd(order))
            self.assertEqual(po.load()["position"]["side"], "long")
            ctd.CFG["OPENCLAW_CMD"] = "true"                 # "succeeds" but never runs the ticket
            _, res = ctd.handoff({"action": "close"}, "EUR/USD", "openclaw", 1.086)
            self.assertFalse(res["ok"])
            self.assertIsNotNone(po.load()["position"])
        finally:
            ctd.CFG["OPENCLAW_CMD"] = old


class MockDesk(unittest.TestCase):
    def test_mock_roles_chain_into_guard(self):
        candles = lpt.MockFeed(3).get()
        ind = lpt.indicators(candles)
        m = market(price=candles[-1]["c"], **{k: v for k, v in ind.items()},
                   low_24=min(c["l"] for c in candles[-24:]), high_24=max(c["h"] for c in candles[-24:]))
        data = {"market": m, "account": {"holding": None}}
        for role in ROLES:
            data[role] = ctd.mock_agent(role, data)
            self.assertNotIn("error", data[role])
        final = ctd.guard({r: data[r] for r in ROLES}, m, None, 50)
        self.assertIn(final["action"], ("buy", "sell", "hold"))
        if final["action"] != "hold":
            self.assertGreaterEqual(final["units"], 1)


if __name__ == "__main__":
    unittest.main()
