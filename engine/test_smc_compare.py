"""engine/test_smc_compare.py — the /smc page's two indicators against what MT5 itself drew on our bars, and the
page data (no MT5, no files outside engine/testdata)."""
import collections
import csv
import gzip
import json
import os

import numpy as np

from engine import learn, smc_compare
from engine.third_party import luxalgo_smc, smc_zones_ref

DATA = os.path.join(os.path.dirname(__file__), "testdata")


def _rows(name):
    with gzip.open(os.path.join(DATA, name), "rt", newline="") as f:
        return [r for r in csv.reader(f) if r]


def test_luxalgo_port_draws_what_the_mt5_indicator_drew():
    """EURUSD M15, 3,028 bars, dumped from the MT5 port (itself identical to TradingView): every structure line,
    order block, live FVG, swing point and EQH / EQL the same, and the same premium / discount zones."""
    rows = _rows("luxalgo_mt5_EURUSD_M15.csv.gz")
    bars = [r for r in rows if r[0] == "bar"]
    t = [int(r[1]) for r in bars]
    o, h, l, c = ([float(r[k]) for r in bars] for k in (3, 4, 5, 6))
    d = luxalgo_smc.smc(t, o, h, l, c)
    R = lambda x: round(x, 5)
    side = {"089981": "bull", "F23645": "bear"}
    last = t[-1]
    mt5_lines = {(int(r[3]), int(r[5]), R(float(r[4])), side[r[7]], "internal" if r[8] == "1" else "swing")
                 for r in rows if r[0] == "line" and r[4] == r[6] and r[7] in side and r[8] in ("0", "1")
                 and int(r[5]) <= last}                      # (the strong / weak high-low lines reach past the last bar)
    assert mt5_lines == {(b["t_from"], b["t"], R(b["level"]), b["side"], b["scope"]) for b in d["breaks"]}
    box = {"33B22833": ("swing", "bear"), "331848CC": ("swing", "bull"), "33F77C80": ("internal", "bear"), "333179F5": ("internal", "bull")}
    mt5_obs = {(int(r[3]), R(max(float(r[4]), float(r[6]))), R(min(float(r[4]), float(r[6]))), *box[r[7]])
               for r in rows if r[0] == "box" and r[7] in box}
    assert mt5_obs == {(ob["t0"], R(ob["top"]), R(ob["bottom"]), ob["scope"], ob["side"])
                       for ob in d["obs"] if ob["t_end"] is None and ob["shown"]}
    halves = collections.defaultdict(list)                  # LuxAlgo draws an FVG as two half boxes
    for r in rows:
        if r[0] == "box" and r[7] in ("4DFF0008", "4D00FF68"):
            halves[(int(r[3]), r[7])] += [float(r[4]), float(r[6])]
    assert {(k[0], R(min(v)), R(max(v)), "bear" if k[1] == "4DFF0008" else "bull") for k, v in halves.items()} \
        == {(f["t0"], R(f["lo"]), R(f["hi"]), f["side"]) for f in d["fvgs"] if f["t_end"] is None}
    labels = lambda texts: collections.Counter(r[5] for r in rows if r[0] == "label" and r[5] in texts)
    assert labels(("HH", "HL", "LH", "LL")) == collections.Counter(s["text"] for s in d["swings"])
    assert labels(("EQH", "EQL")) == collections.Counter(e["text"] for e in d["equal"])
    pd = {r[7]: (R(min(float(r[4]), float(r[6]))), R(max(float(r[4]), float(r[6]))))
          for r in rows if r[0] == "box" and r[7] in ("33F23645", "33878B94", "33089981")}
    z = d["zones"]
    assert pd == {"33F23645": tuple(map(R, z["premium"])), "33878B94": tuple(map(R, sorted(z["equilibrium"]))),
                  "33089981": tuple(map(R, z["discount"]))}


def test_smc_zones_reference_reproduces_the_mt5_buffers():
    """GOLD M15, 3,024 bars of the MT5 indicator's 16 buffers. That run got swing 14 / ATR 1 / OB touch (MT5 counts
    `input group` lines as parameters, so the passed list shifted), which the reference reproduces too."""
    rows = list(csv.DictReader(gzip.open(os.path.join(DATA, "smczones_mt5_GOLD_M15.csv.gz"), "rt", newline="")))
    a = {k: np.array([float(r[k]) for r in rows]) for k in ("open", "high", "low", "close")}
    t = np.array([int(r["time"]) for r in rows])
    out, _, breaks, _ = smc_zones_ref.smc_zones(t, a["open"], a["high"], a["low"], a["close"], swing=14, atr=1, ob_mit=0)
    cols = {"ob_bull_top": "ob_bull_top", "ob_bull_bot": "ob_bull_bot", "ob_bear_top": "ob_bear_top", "ob_bear_bot": "ob_bear_bot",
            "fvg_bull_top": "fvg_bull_top", "fvg_bull_bot": "fvg_bull_bot", "fvg_bear_top": "fvg_bear_top",
            "fvg_bear_bot": "fvg_bear_bot", "struct": "structure", "level": "broken_level", "sweep_bull": "sweep_low",
            "sweep_bear": "sweep_high"}
    for ref, col in cols.items():
        mt5 = np.array([float(r[col]) if r[col] else np.nan for r in rows])
        same = (np.isnan(mt5) & np.isnan(out[ref])) | np.isclose(mt5, out[ref], rtol=0, atol=1e-9)
        assert same.all(), (col, np.where(~same)[0][:5])
    assert len(breaks) == sum(1 for r in rows if r["structure"])


def _bars(n=400, seed=7):
    rng = np.random.default_rng(seed)
    t0, p, out = 1_793_000_000_000, 4000.0, []
    for i in range(n):
        o = p
        c = o + rng.normal(0, 3) + 2.5 * np.sin(i / 25)
        out.append([t0 + i * 900_000, o, max(o, c) + abs(rng.normal(0, 1.5)), min(o, c) - abs(rng.normal(0, 1.5)), c])
        p = c
    return out


def test_page_has_every_layer_and_is_json(monkeypatch):
    rows = _bars()
    monkeypatch.setattr(learn, "load_bars", lambda sym, tf, n=3000: rows)
    monkeypatch.setattr(smc_compare, "_CACHE", {})
    d = smc_compare.page("GOLD", "M15")
    json.dumps(d)
    assert d["bars"] == rows and {"zones", "lux", "v5", "levels", "summary", "ta", "sd"} <= set(d)
    assert set(d["ta"]) == {"levels", "candles", "candle_info", "trend", "patterns", "ind", "profile", "wyckoff", "elliott"}
    assert len(d["ta"]["ind"]["rsi"]) == len(rows) and d["ta"]["ind"]["vwap"] is None     # these bars carry no volume
    s = d["summary"]
    assert s["price"] == rows[-1][4] and s["t_last"] == rows[-1][0]
    assert d["zones"]["breaks"] and d["lux"]["breaks"]
    for b in d["zones"]["breaks"] + d["lux"]["breaks"]:
        assert b["kind"] in ("BOS", "CHoCH") and b["side"] in ("bull", "bear") and b["t_from"] <= b["t"]
    for z in s["zones"]["live"] + s["lux"]["live"]:
        assert z["bottom"] <= z["top"] and z["t_end"] is None
    for e in s["v5"]["breaks"]:
        assert e["side"] in ("bull", "bear")


def test_supply_demand_on_the_page_is_only_the_valid_zones(monkeypatch):
    """/smc carries supply_demand.page: every drawn zone passed David's gate (a major BOS / CHoCH out of the box),
    the summary lists the nearest live origin boxes per side, and the filtered counts explain the rest."""
    rows = _bars()
    monkeypatch.setattr(learn, "load_bars", lambda sym, tf, n=3000: rows)
    monkeypatch.setattr(smc_compare, "_CACHE", {})
    d = smc_compare.page("GOLD", "M15")
    S, times = d["sd"], {r[0] for r in rows}
    assert S["valid"] == len(S["zones"]) < S["candidates"] and sum(S["filtered"].values()) == S["candidates"] - S["valid"]
    for z in S["zones"]:
        assert z["side"] in ("supply", "demand") and z["event"] in ("BOS", "CHoCH")
        assert z["bottom"] <= z["entry"] <= z["top"] and z["t0"] in times and z["t0"] <= z["t_out"] <= z["t_break"]
        assert z["status"] in ("fresh", "tested", "spent", "broken", "flipped", "dead")
        assert z["live"] == (z["status"] in ("fresh", "tested") and z["t_superseded"] is None)
        assert 0 <= z["score"] <= 10 and sum(z["parts"].values()) == z["score"]
    sd = d["summary"]["sd"]
    assert sd["n_live"] == sum(1 for z in S["zones"] if z["live"]) and len(sd["live"]) <= 2 * smc_compare.SD_SHOW
    assert sd["n_origin"] == sum(1 for z in S["zones"] if z["live"] and z["role"].startswith("origin")) <= sd["n_live"]
    assert all(z["live"] and z["role"].startswith("origin") for z in sd["live"])


def test_too_few_bars_is_a_message_not_a_crash(monkeypatch):
    monkeypatch.setattr(learn, "load_bars", lambda sym, tf, n=3000: _bars(30))
    monkeypatch.setattr(smc_compare, "_CACHE", {})
    assert "error" in smc_compare.page("NEWCOIN", "H4")


def test_previous_day_is_the_previous_server_day():
    # FxPro server day = Asia/Nicosia (UTC+2 now): 2026-10-27 22:00 UTC is already the 28th there
    day27 = [[1_793_052_000_000 + i * 3_600_000, 1, 10 + i, 1 - i, 1] for i in range(22)]   # 27th 00:00 server …
    day28 = [[day27[-1][0] + 3 * 3_600_000, 1, 99, -99, 1]]                                  # … 28th 00:00 server
    lv = smc_compare.prev_day(day27 + day28)
    assert lv["day"] == "2026-10-27" and lv["PDH"] == 31 and lv["PDL"] == -20


def test_page_is_computed_once_per_chart_per_30_s(monkeypatch):
    calls = []
    monkeypatch.setattr(learn, "load_bars", lambda sym, tf, n=3000: calls.append(1) or _bars())
    monkeypatch.setattr(smc_compare, "_CACHE", {})
    a = smc_compare.page("GOLD", "M15")
    assert smc_compare.page("GOLD", "M15") is a and len(calls) == 1
    smc_compare.page("GOLD", "H1")
    assert len(calls) == 2
