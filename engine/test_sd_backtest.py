"""offline tests of engine/sd_backtest.manage: spread-aware stops / targets, TP1 → break-even, the fill candle"""
import unittest

from .sd_backtest import manage


class FakeChart:
    def __init__(self, hl):
        self.Hl = [h for h, _ in hl]
        self.Ll = [lo for _, lo in hl]
        self.C5 = [(h + lo) / 2 for h, lo in hl]


class ManageTest(unittest.TestCase):
    def test_sell_stop_is_an_ask_order(self):
        # sell 100 (bid), SL 110 (ask), spread 2: the bid only has to reach 108
        c = FakeChart([(101, 99), (108, 100)])
        r = manage(c, "sell", 100.0, 110.0, None, 80.0, 2.0, 0, False)
        self.assertEqual((r["reason"], r["exit_j"], round(r["R"], 6)), ("SL", 1, -1.0))

    def test_sell_target_needs_the_bid_spread_lower(self):
        # TP 80 (ask) fills when the bid reaches 78: a low of 79 is not enough
        c = FakeChart([(101, 79), (101, 78)])
        r = manage(c, "sell", 100.0, 110.0, None, 80.0, 2.0, 0, False)
        self.assertEqual((r["reason"], r["exit_j"], round(r["R"], 6)), ("TP2", 1, 2.0))

    def test_buy_entry_pays_the_spread_exits_on_the_bid(self):
        # buy 100 (ask), SL 95 (bid), TP 110 (bid)
        c = FakeChart([(105, 96), (110, 101)])
        r = manage(c, "buy", 100.0, 95.0, None, 110.0, 2.0, 0, False)
        self.assertEqual((r["reason"], round(r["R"], 6)), ("TP2", 2.0))

    def test_tp1_then_break_even(self):
        # sell 100 / SL 110 / TP1 90 / TP2 70, spread 0: half at 90 (+0.5R), the rest stopped at the entry
        c = FakeChart([(101, 89), (100, 95)])
        r = manage(c, "sell", 100.0, 110.0, 90.0, 70.0, 0.0, 0, False)
        self.assertEqual((r["reason"], r["tp1_j"], round(r["R"], 6)), ("BE", 0, 0.5))

    def test_stop_wins_a_candle_that_reaches_both(self):
        c = FakeChart([(111, 69)])
        r = manage(c, "sell", 100.0, 110.0, None, 70.0, 0.0, 0, False)
        self.assertEqual(r["reason"], "SL")

    def test_fill_candle_cannot_take_profit(self):
        c = FakeChart([(100, 60), (101, 99)])
        r = manage(c, "sell", 100.0, 110.0, None, 70.0, 0.0, 0, True)
        self.assertEqual(r["reason"], "open")


if __name__ == "__main__":
    unittest.main()
