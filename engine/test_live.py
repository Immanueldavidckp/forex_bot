"""engine/test_live.py — the /smc page's live quotes (engine/live.py): who asked, one bridge call, the files (no MT5)."""
import json
import os
import time

from engine import learn, live


class FakeFeed:
    symbols = ["GOLD", "EURUSD"]

    def clock(self):
        return None


class FakeMT5:
    def __init__(self):
        self.reqs = []
        self.server_to_utc_ms = lambda t, off=None: t * 1000

    def call(self, reqs, timeout=0):
        self.reqs.append(reqs)
        out = []
        for q in reqs:
            if q["op"] == "tick":
                out.append({"result": {"bid": 4070.1, "ask": 4070.4, "time": 1_793_250_000}})
            else:
                out.append({"result": [[1_793_249_100, 4060.0, 4072.0, 4059.0, 4068.0, 900, 0, 30],
                                       [1_793_250_000, 4068.0, 4071.0, 4067.5, 4070.1, 120, 0, 30]][-q["count"]:]})
        return out


def _dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(live, "LIVE_DIR", str(tmp_path))
    monkeypatch.setattr(live, "WANT_DIR", str(tmp_path / "want"))
    monkeypatch.setattr(live, "HIST_DIR", str(tmp_path / "history"))
    monkeypatch.setattr(live, "TICKS", type("NoTicks", (), {"requests": lambda self, *a: []})())


def test_only_symbols_asked_for_lately_and_known_are_read(monkeypatch, tmp_path):
    _dirs(monkeypatch, tmp_path)
    for s in ("GOLD", "EURUSD", "NOTASYMBOL"):
        live.want(s)
    old = time.time() - live.WANT_S - 5
    os.utime(os.path.join(live.WANT_DIR, "EURUSD"), (old, old))      # nobody polled EURUSD for a minute
    assert live.wanted(set(FakeFeed.symbols)) == ["GOLD"]
    live.want("EURUSD")                                              # asked again → back in
    assert set(live.wanted(set(FakeFeed.symbols))) == {"GOLD", "EURUSD"}


def test_nobody_watching_means_no_bridge_call(monkeypatch, tmp_path):
    _dirs(monkeypatch, tmp_path)
    fake = FakeMT5()
    monkeypatch.setattr(live, "mt5c", fake)
    assert live.step(FakeFeed()) == [] and fake.reqs == []


def test_one_bridge_call_writes_tick_and_forming_bars(monkeypatch, tmp_path):
    _dirs(monkeypatch, tmp_path)
    fake = FakeMT5()
    monkeypatch.setattr(live, "mt5c", fake)
    live.want("GOLD")
    assert live.step(FakeFeed()) == ["GOLD"]
    assert len(fake.reqs) == 1 and [q["op"] for q in fake.reqs[0]] == ["tick"] + ["rates"] * 5
    assert {q["tf"]: q["count"] for q in fake.reqs[0][1:]} == live.ENGINE["bars"]     # deep enough to reach the saved history
    d = live.read("GOLD")
    assert d == json.load(open(tmp_path / "GOLD.json"))
    assert d["sym"] == "GOLD" and d["bid"] == 4070.1 and d["ask"] == 4070.4 and d["t_ms"] == 1_793_250_000_000
    assert set(d["bars"]) == {"H4", "H1", "M30", "M15", "M5"}
    assert d["bars"]["M15"] == [[1_793_249_100_000, 4060.0, 4072.0, 4059.0, 4068.0, 900],
                                [1_793_250_000_000, 4068.0, 4071.0, 4067.5, 4070.1, 120]]
    assert live.read("EURUSD") == {}


def test_a_symbol_outside_the_v5_feed_with_a_history_is_read(monkeypatch, tmp_path):
    """GOLD is no V5 symbol (no view file): its saved history makes it known, so /smc gets it live too."""
    _dirs(monkeypatch, tmp_path)
    fake = FakeMT5()
    monkeypatch.setattr(live, "mt5c", fake)
    feed = FakeFeed()
    feed.symbols = ["EURUSD"]
    live.want("GOLD")
    assert live.step(feed) == []
    os.makedirs(live.HIST_DIR)
    open(os.path.join(live.HIST_DIR, "GOLD.json"), "w").close()
    assert live.step(feed) == ["GOLD"]


def test_load_bars_merges_the_live_file_and_leaves_out_forming_bars(monkeypatch, tmp_path):
    """history + view + live file → closed bars only: a bar still forming when its file was written is not the bar."""
    H, V, L = (tmp_path / d for d in ("history", "view", "live"))
    for d in (H, V, L):
        d.mkdir()
    monkeypatch.setattr(learn, "HIST_DIR", str(H))
    monkeypatch.setattr(learn, "VIEW_DIR", str(V))
    monkeypatch.setattr(learn, "LIVE_DIR", str(L))
    B, t0 = 900_000, 1_793_000_000_000
    bar = lambda i, c: [t0 + i * B, c, c + 1, c - 1, c]
    # history fetched 5 min into bar 2: bars 0-1 closed, bar 2 a snapshot
    json.dump({"fetched": (t0 + 2 * B + 300_000) // 1000, "bars": {"M15": [bar(i, 10 + i) + [0.3, 100 + i] for i in range(3)]}},
              open(H / "GOLD.json", "w"))
    # the live file, written 1 min into bar 5: bars 2-4 closed (2 replaces the snapshot), bar 5 forming
    json.dump({"at": t0 + 5 * B + 60_000, "bars": {"M15": [bar(i, 20 + i) + [200 + i] for i in range(2, 6)]}}, open(L / "GOLD.json", "w"))
    rows = learn.load_bars("GOLD", "M15")
    assert [r[0] for r in rows] == [t0 + i * B for i in range(5)]
    assert rows[1][4] == 11 and rows[1][5] == 101                    # from the history, with its volume
    assert rows[2][4] == 22 and rows[2][5] == 202                    # the closed bar from the live file, not the snapshot
    assert rows[-1][4] == 24
