"""engine/test_pnl.py — the 24/7 profit report (David 2026-10-30: "check how much profit it can make")."""
from engine import pnl


def rows(nets, magic=5050505):
    return [{"t": 1_793_372_940_000 + i * 60_000, "magic": magic, "symbol": "EURUSD", "volume": 0.01,
             "net": n, "profit": n, "commission": 0.0, "swap": 0.0, "comment": ""} for i, n in enumerate(nets)]


def test_net_includes_commission_and_swap(monkeypatch):
    raw = [{"entry": 1, "time_msc": 1_793_372_950_000, "magic": 5050505, "symbol": "GOLD", "volume": 0.01,
            "profit": 1.0, "commission": -0.07, "swap": -0.58}]
    monkeypatch.setattr(pnl.mt5c, "deals", lambda days=7: raw)
    r = pnl.closed(7)
    assert len(r) == 1 and abs(r[0]["net"] - 0.35) < 1e-9     # the swap is not quietly dropped


def test_opening_deals_are_not_counted(monkeypatch):
    raw = [{"entry": 0, "time_msc": 1, "magic": 1, "profit": 99.0, "commission": 0, "swap": 0},
           {"entry": 1, "time_msc": 2, "magic": 1, "profit": 1.0, "commission": 0, "swap": 0}]
    monkeypatch.setattr(pnl.mt5c, "deals", lambda days=7: raw)
    assert [r["net"] for r in pnl.closed(7)] == [1.0]


def test_a_small_winning_run_is_not_called_profitable():
    """the whole point: a positive total whose interval spans zero is not an edge."""
    s = pnl.stats(rows([1.0, -0.9, 1.1, -1.0, 0.9, -0.8, 1.2, -1.1] * 10))
    assert s["total"] > 0 and s["lo"] < 0 < s["hi"]
    assert "indistinguishable from zero" in pnl.verdict(s)
    assert s["need_n"] and s["need_n"] > s["n"]


def test_a_real_loss_is_called_a_loss():
    s = pnl.stats(rows([-0.5] * 60))
    assert s["hi"] < 0 and "LOSING" in pnl.verdict(s)


def test_too_few_trades_says_so():
    assert "too few" in pnl.verdict(pnl.stats(rows([1.0, -1.0, 0.5])))


def test_no_trades_is_not_a_crash():
    assert pnl.stats([]) == {"n": 0} and pnl.verdict({"n": 0}) == "no closed trades yet"


def test_magics_are_kept_apart(monkeypatch):
    raw = []
    for m, net in ((5050505, -1.0), (5050600, 2.0), (24102099, 0.5)):
        raw.append({"entry": 1, "time_msc": 1_793_372_950_000, "magic": m, "symbol": "EURUSD",
                    "volume": 0.01, "profit": net, "commission": 0.0, "swap": 0.0})
    monkeypatch.setattr(pnl.mt5c, "deals", lambda days=7: raw)
    r = pnl.report(7)
    assert r["by_magic"][5050505]["name"] == "V5 engine"
    assert r["by_magic"][5050600]["total"] == 2.0
    assert r["all"]["n"] == 3


def test_the_run_marker_anchors_the_window():
    r0 = pnl.run_start()
    if r0:
        assert r0["profile"] == "profit" and r0["lot"] == 0.01 and r0["started_ms"] > 0
