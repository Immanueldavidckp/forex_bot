"""engine/test_ticks.py — the tick store for the order-flow chart (engine/ticks.py): today's ticks appended without
gaps or doubles, past days fetched whole, server clock → UTC (no MT5: a fake bridge writes the .npy replies)."""
import datetime as dt

import numpy as np
import pytest

from engine import ticks

OFF = dt.timedelta(hours=2)                       # the server clock is UTC+2 (FxPro in winter)
DAY = ticks.DAY_MS
TODAY = 1_793_232_000_000                         # 2026-10-29 00:00 UTC
STEP = 400                                        # a tick every 400 ms, two ticks on every 10th millisecond stamp


class FakeBridge:
    def __init__(self, now_ms):
        self.now_ms, self.calls, self.late = now_ms, [], 0     # late: ms before now that MT5 has not filled in yet

    def ticks_between(self, from_s, to_s):
        t0 = (from_s * 1000 - 7_200_000) // STEP * STEP          # back to UTC, on the tick grid
        t1 = min(to_s * 1000 - 7_200_000, self.now_ms)
        t = np.arange(max(t0, TODAY - 9 * DAY), t1, STEP, dtype=np.int64)
        t = np.sort(np.concatenate([t, t[(t // STEP) % 10 == 0]]))  # same-millisecond pairs
        if self.late:                                            # the newest tick is there, some just before it not yet
            t = np.concatenate([t[t < t1 - self.late], t[-1:]]) if len(t) else t
        bid = 4000 + (t // STEP % 50) * 0.01
        return t + 7_200_000, bid

    def call(self, reqs, timeout=0):
        out = []
        for q in reqs:
            self.calls.append(q)
            if q["op"] == "info":
                out.append({"result": {"point": 0.01, "digits": 2}})
            elif q["op"] == "ticks":
                ts, bid = self.ticks_between(q["from_s"], q.get("to_s") or (self.now_ms + 7_200_000) // 1000 + 1)
                a = np.empty(len(ts), dtype=[("time_msc", "<i8"), ("bid", "<f8"), ("ask", "<f8"), ("flags", "<u4")])
                a["time_msc"], a["bid"], a["ask"], a["flags"] = ts, bid, bid + 0.15, 6
                np.save(q["path"][2:].replace("\\", "/"), a)
                out.append({"result": {"n": len(a)}})
        return out


@pytest.fixture
def store(monkeypatch, tmp_path):
    monkeypatch.setattr(ticks, "TICK_DIR", str(tmp_path))
    return ticks.Store()


def run(store, bridge):
    reqs = store.requests("GOLD", bridge.now_ms, OFF)
    for q, r in zip(reqs, bridge.call(reqs)):
        store.take("GOLD", q, r, OFF)
    return reqs


def expected(t0, t1):
    t = np.arange(t0, t1, STEP, dtype=np.int64)
    return np.sort(np.concatenate([t, t[(t // STEP) % 10 == 0]]))


def test_first_run_today_from_midnight_and_yesterday_whole(store):
    b = FakeBridge(TODAY + 3_600_000)                             # 01:00 UTC
    reqs = run(store, b)
    assert [q.get("kind") for q in reqs] == ["info", "new", "day"]
    a, point = ticks.load("GOLD", TODAY - DAY, TODAY + DAY)
    assert point == 0.01
    assert np.array_equal(a["t"], expected(TODAY - DAY, TODAY + 3_600_000))   # nothing doubled, nothing missing
    assert a["bid"][0] == 400000 and np.all(a["ask"] - a["bid"] == 15)       # prices in points
    assert ticks.meta("GOLD")["complete"] == ["2026-10-28"]


def test_next_loops_append_only_the_new_ticks(store):
    b = FakeBridge(TODAY + 3_600_000)
    run(store, b)
    for k in range(3):                                            # three more loops, 15 s apart
        b.now_ms += 15_000
        run(store, b)
    a, _ = ticks.load("GOLD", TODAY, TODAY + DAY)
    assert np.array_equal(a["t"], expected(TODAY, TODAY + 3_600_000 + 45_000))
    fresh = ticks.Store()                                         # an engine restart finds where it stopped
    b.now_ms += 15_000
    reqs = fresh.requests("GOLD", b.now_ms, OFF)
    for q, r in zip(reqs, b.call(reqs)):
        fresh.take("GOLD", q, r, OFF)
    a, _ = ticks.load("GOLD", TODAY, TODAY + DAY)
    assert np.array_equal(a["t"], expected(TODAY, TODAY + 3_600_000 + 60_000))


def test_backfill_goes_one_day_back_per_loop_then_stops(store):
    b = FakeBridge(TODAY + 3_600_000)
    days = []
    for _ in range(ticks.BACKFILL_DAYS + 2):
        days += [q["day"] for q in run(store, b) if q.get("kind") == "day"]
    assert days == [(dt.datetime(2026, 10, 29) - dt.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, ticks.BACKFILL_DAYS + 1)]
    a, _ = ticks.load("GOLD", TODAY - ticks.BACKFILL_DAYS * DAY, TODAY + DAY)
    assert np.array_equal(a["t"], expected(TODAY - ticks.BACKFILL_DAYS * DAY, b.now_ms))


def test_after_midnight_yesterday_is_fetched_again_whole(store):
    b = FakeBridge(TODAY + DAY - 60_000)                          # 23:59 UTC: today's file is appended live
    run(store, b)
    b.now_ms = TODAY + DAY + 120_000                              # 00:02 next day
    run(store, b)
    a, _ = ticks.load("GOLD", TODAY - DAY, TODAY + 2 * DAY)
    assert np.array_equal(a["t"], expected(TODAY - DAY, TODAY + DAY + 120_000))
    assert "2026-10-29" in ticks.meta("GOLD")["complete"]


def test_server_clock_to_utc_follows_summer_time():
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("Asia/Nicosia")                                 # EEST (UTC+3) until 2026-10-25 01:00 UTC
    utc = np.array([TODAY - 4 * DAY + 3_600_000 * (1 + h) for h in (-2, -1, 1, 2)], dtype=np.int64)   # around 10-25 01:00 UTC
    server = np.array([u + (3 if u < 1_792_890_000_000 else 2) * 3_600_000 for u in utc], dtype=np.int64)
    assert np.array_equal(ticks._to_utc(server, tz), utc)


def test_ticks_mt5_adds_late_to_a_second_are_not_lost(store):
    """MT5 can hand out a second's newest tick before all of that second's ticks are in (seen on FxPro 2026-10-29):
    the next loop writes the last REWRITE_MS again from MT5's newer copy."""
    b = FakeBridge(TODAY + 3_600_000)
    run(store, b)
    b.now_ms += 15_000
    b.late = 2_000                                                # this reply misses the 2 s before its last tick
    run(store, b)
    b.late = 0
    b.now_ms += 15_000
    run(store, b)
    a, _ = ticks.load("GOLD", TODAY, TODAY + DAY)
    assert np.array_equal(a["t"], expected(TODAY, TODAY + 3_600_000 + 30_000))


def test_old_days_are_deleted_for_every_symbol_and_replies_are_not_kept(store, tmp_path):
    import os
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=ticks.KEEP_DAYS + 2)).strftime("%Y-%m-%d")
    os.makedirs(tmp_path / "EURUSD")
    open(tmp_path / "EURUSD" / f"{old}.bin", "wb").close()        # a symbol nobody watches any more
    b = FakeBridge(TODAY + 3_600_000)
    run(store, b)                                                 # GOLD's first loop fetches a past day → prune
    assert not (tmp_path / "EURUSD" / f"{old}.bin").exists()
    assert os.listdir(tmp_path / "tmp") == []
