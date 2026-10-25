"""
Offline tests of the MT5 supervisor (engine/terminal.py) — no terminal is started or stopped:

    cd ~/forex && python3 -m pytest -q engine/test_terminal.py
"""
from __future__ import annotations

import os
import tempfile

import pytest

from engine import terminal as TM


class Calls(list):
    def rec(self, name):
        return lambda *a, **k: self.append((name, a, k)) or True


@pytest.fixture
def term(monkeypatch):
    ctl = {}
    monkeypatch.setattr(TM, "load_control", lambda: dict(ctl))
    monkeypatch.setattr(TM, "save_control", lambda **kw: ctl.update(kw) or dict(ctl))
    monkeypatch.setattr(TM.mt5c, "terminal_running", lambda: True)
    monkeypatch.setitem(TM.ENGINE, "mt5_login", 592224888)
    t = TM.Terminal(lambda m: None, lambda *a, **k: None)
    calls = Calls()
    monkeypatch.setattr(t, "start", calls.rec("start"))
    monkeypatch.setattr(t, "stop", calls.rec("stop"))
    monkeypatch.setattr(t, "login", calls.rec("login"))
    return t, calls, ctl


def good(**kw):
    return {"login": 592224888, "server": "FxPro-MT5 Demo", "connected": True, "algo_trading": True, **kw}


def test_broken_wine_restarts_at_once(term):
    t, calls, _ = term
    t.on_error(RuntimeError("bridge wrote nothing (exit 1): Your wineserver binary was not upgraded correctly"))
    assert [c[0] for c in calls] == ["stop", "start"]


def test_one_failed_call_waits_two_restart(term):
    t, calls, _ = term
    t.on_error(RuntimeError("bridge timed out after 60 s"))
    assert calls == []
    t.on_error(RuntimeError("bridge timed out after 60 s"))
    assert [c[0] for c in calls] == ["stop", "start"]


def test_restarts_back_off(term):
    t, calls, _ = term
    now = 1_000_000.0
    t.restarts = [now - 60]
    assert "next after 180" in t.may_restart(now)
    t.restarts = [now - 3000, now - 2500, now - 2000, now - 1500, now - 400]
    assert "restarts this hour" in t.may_restart(now)              # 5 in the hour → 15 min apart
    assert t.may_restart(now + 600) is None


def test_disconnected_gets_two_minutes(term, monkeypatch):
    t, calls, _ = term
    clock = [1_000_000.0]
    monkeypatch.setattr(TM.time, "time", lambda: clock[0])
    t.check_account(good(connected=False))
    clock[0] += 60
    t.check_account(good(connected=False))
    assert calls == []
    clock[0] += 90
    t.check_account(good(connected=False))
    assert [c[0] for c in calls] == ["stop", "start"]


def test_other_account_logs_back_in(term):
    t, calls, _ = term
    t.check_account(good(login=114458583, server="MetaQuotes-Demo"))
    assert [c[0] for c in calls] == ["login"]


def test_algo_trading_off_restarts_with_the_fix_once_an_hour(term, monkeypatch):
    t, calls, _ = term
    fixed = []
    monkeypatch.setattr(TM, "set_algo_enabled", lambda: fixed.append(1) or True)
    t.check_account(good(algo_trading=False))
    t.check_account(good(algo_trading=False))
    assert [c[0] for c in calls] == ["stop", "start"] and fixed == [1]


def test_stopped_by_hand_stays_off(term, monkeypatch):
    t, calls, ctl = term
    monkeypatch.setattr(TM.mt5c, "terminal_running", lambda: False)
    t.command("stop")
    assert ctl["mt5"] == "off" and not t.ensure_running() and [c[0] for c in calls] == ["stop"]
    t.command("start")
    assert ctl["mt5"] == "auto" and calls[-1][0] == "start"


def test_terminal_down_is_started(term, monkeypatch):
    t, calls, _ = term
    monkeypatch.setattr(TM.mt5c, "terminal_running", lambda: False)
    assert t.ensure_running() and [c[0] for c in calls] == ["start"]


def test_common_ini_algo_switch():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "common.ini")
    with open(p, "wb") as f:
        f.write("[Common]\r\nEnabled=0\r\n[Experts]\r\nAllowDllImport=0\r\nEnabled=0\r\nAccount=1\r\n".encode("utf-16"))
    assert TM.set_algo_enabled(p)
    text = open(p, "rb").read().decode("utf-16")
    assert "[Common]\r\nEnabled=0" in text and "[Experts]\r\nAllowDllImport=0\r\nEnabled=1\r\n" in text   # only the Experts one
    assert not TM.set_algo_enabled(p)
