"""
engine/filter_replay.py — the structure filter layer's test (David 2026-10-25): the last N days replayed twice
through the live engine code (Book.analyse → watch → signal, watch mode), once as the engine was (layer off) and
once with the layer on, for every symbol the engine trades. Prints how many setups the old logic took vs how many
pass every gate, and which gate rejected the rest.

    python3 -m engine.filter_replay [--days 7] [--symbols EURUSD,BITCOIN] [--jobs 12] [--cached | --offline]

Bars: fetched fresh from MT5 (enough for the engine's windows before the first day) into
engine_data/filters/replay_bars/, or with --offline the backtest history (engine_data/history). The clock steps
one M5 bar at a time; the next M5 bar plays the forming bar (the live engine re-reads it every minute), so a
pullback is caught within the bar it happens in. A pullback fills at the entry (sells at the bid, buys at the ask:
bid + that bar's spread). Only H4 (S&D H4 zones), M30 and M15 setups are worked out: H1 / M5 setups are chart-only
and never change a trade. Watch mode: no positions, so MAX_POSITIONS and "no re-entry after a loss" never act here.
→ engine_data/filters/replay-<date>.txt / .json
"""
from __future__ import annotations

import argparse
import bisect
import datetime as _dt
import json
import os
import re
import time
from collections import Counter, defaultdict
from multiprocessing import Pool
from typing import Dict, List

from . import book as B
from . import filters as FL
from .backtest import fixed_outcome, load
from .config import DATA_DIR, ENGINE, FILTERS
from .feed import TF_MIN
from .history import HIST_DIR, server_to_utc_ms

OUT_DIR = FILTERS["LOG_DIR"]
BARS_DIR = os.path.join(OUT_DIR, "replay_bars")
SIM_TFS = ["H4", "M30", "M15"]                 # the setup timeframes that can lead to a trade


def counts(days: int) -> Dict[str, int]:
    """Bars per timeframe: the engine's window + the replayed days + a margin."""
    return {tf: int(ENGINE["bars"][tf] + days * 1440 / TF_MIN[tf] + 60) for tf in ("H4", "H1", "M30", "M15", "M5")}


def fetch(days: int, symbols: List[str]) -> None:
    """Recent bars + symbol facts from MT5, in the backtest history format (epoch ms UTC, spread in price)."""
    from .feed import mt5c
    os.makedirs(BARS_DIR, exist_ok=True)
    n = counts(days)
    for k in range(0, len(symbols), 8):
        chunk = symbols[k:k + 8]
        reqs = []
        for s in chunk:
            reqs += [{"op": "info", "symbol": s}] + [{"op": "rates", "symbol": s, "tf": tf, "count": c} for tf, c in n.items()]
        res = mt5c.call(reqs, timeout=600)
        per = 1 + len(n)
        for j, s in enumerate(chunk):
            got = res[j * per:(j + 1) * per]
            if any("error" in r for r in got):
                print(f"{s}: {next(r['error'] for r in got if 'error' in r)}", flush=True)
                continue
            info = got[0]["result"]
            pt = float(info["point"])
            bars = {tf: [[server_to_utc_ms(x[0]), x[1], x[2], x[3], x[4], round(x[7] * pt, 10)] for x in r["result"]]
                    for tf, r in zip(n, got[1:])}
            with open(os.path.join(HIST_DIR, f"{s}.json")) as f:
                market = json.load(f)["market"]
            with open(os.path.join(BARS_DIR, f"{s}.json"), "w") as f:
                json.dump({"symbol": s, "market": market, "info": info, "fetched": int(time.time()), "bars": bars}, f, separators=(",", ":"))
        print(f"fetched {k + len(chunk)}/{len(symbols)}", flush=True)


# ── the live Book on a clock that steps through the history ──
class SimFeed:
    def __init__(self, d: Dict):
        self.symbols, self.market, self.info = [d["symbol"]], {d["symbol"]: d["market"]}, {d["symbol"]: d["info"]}
        self.ser = {tf: d["bars"][tf] for tf in d["bars"]}
        self.T = {tf: [b["t"] for b in v] for tf, v in self.ser.items()}
        self.now = 0

    def _done(self, tf: str) -> int:
        return bisect.bisect_right(self.T[tf], self.now - TF_MIN[tf] * 60_000)

    def completed(self, sym, tf, at_ms=None):
        i = self._done(tf)
        return self.ser[tf][max(0, i - ENGINE["bars"][tf] + 1):i]

    def get(self, sym, tf):
        i = self._done(tf)
        nxt = self.ser[tf][i:i + 1]
        return self.completed(sym, tf) + (nxt if nxt and nxt[0]["t"] <= self.now else [])


class SimMT5:
    def __init__(self):
        self.book = None

    def tick(self, sym):
        """The price at the pullback: the entry, or the bar's open when it opened beyond it."""
        bk = self.book
        rec = bk.sim_rec
        m5 = bk.feed.get(sym, "M5")
        hit = next((b for b in reversed(m5) if b["t"] == rec["touch_t"]), m5[-1])
        e = rec["entry"]
        bid = max(e, hit["o"]) if rec["side"] == "sell" else min(e, hit["o"])
        return {"bid": bid, "ask": bid + hit["sp"], "time": 0}


class SimBook(B.Book):
    def _load(self):
        self.sim_rec = None

    def view(self, sym, b, rows, structs):
        return {"setups": [], "focus": None}

    def signal(self, rec, trading, h1, bars, m5):
        self.sim_rec = rec
        return super().signal(rec, trading, h1, bars, m5)


def run_pass(d: Dict, start: int, end: int, on: bool) -> Dict:
    FL.FORCE = on
    recs: List[Dict] = []
    jr: List[Dict] = []
    FL.SINK = recs.append
    feed = SimFeed(d)
    B.now_ms = lambda: feed.now
    B.journal = lambda event, **kw: jr.append({"event": event, **kw})
    sim = SimMT5()
    B.mt5c = sim
    bk = SimBook(feed)
    sim.book = bk
    bk.account = {"equity": 10_000.0}
    sym = d["symbol"]
    m5 = feed.ser["M5"]
    for b in m5[bisect.bisect_left(feed.T["M5"], start):]:
        if b["t"] >= end:
            break
        feed.now = b["t"] + 300_000            # this M5 bar has just closed; the next one is forming
        try:
            bk.analyse(sym, trading=False)
        except Exception as e:                  # one bad step must not end the replay
            jr.append({"event": "error", "t": feed.now, "error": f"{type(e).__name__}: {e}"})
    attempts = [{"id": r["id"], "tf": r["tf"], "entry_type": r.get("entry_type"), "status": r["status"], "why": r.get("why"),
                 "gate": r.get("gate"), "touch_t": r.get("touch_t"), "side": r["side"], "plan": r.get("plan")}
                for r in bk.setups.values() if r["status"] in ("signal", "refused", "against bias") and r.get("touch_t", 0) >= start
                and r["tf"] != ENGINE["sdh4"]["zone_tf"]]
    for a in attempts:                          # outcome of the trades taken: stop / target only, on M5
        if a["status"] == "signal":
            p = a["plan"]
            j = bisect.bisect_left(feed.T["M5"], a["touch_t"])
            a["outcome"] = fixed_outcome(a["side"], p["entry"], p["stop"], p["target"]["price"], m5, j)
        a.pop("plan", None)
    return {"attempts": attempts, "records": recs, "errors": [x for x in jr if x["event"] == "error"][:5]}


def _job(arg):
    path, days, end_cap = arg
    B.log = lambda *a, **k: None
    B._write = lambda *a, **k: None             # never the live dashboard's view files
    ENGINE["setup_tfs"] = SIM_TFS
    d = load(path)
    sym = d["symbol"]
    end = min(d["bars"]["M5"][-1]["t"] + 300_000, end_cap)
    start = end - days * 86_400_000
    try:
        off = run_pass(d, start, end, False)
        on = run_pass(d, start, end, True)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"symbol": sym, "error": f"{type(e).__name__}: {e}"}
    return {"symbol": sym, "market": d["market"], "start": start, "end": end, "off": off, "on": on}


# ── report ──
def report(res: List[Dict], days: int) -> str:
    ist = lambda ms: _dt.datetime.fromtimestamp(ms / 1000, B.IST).strftime("%Y-%m-%d %H:%M")
    ok = [r for r in res if "error" not in r]
    off = [a for r in ok for a in r["off"]["attempts"]]
    recs = [x for r in ok for x in r["on"]["records"]]
    on = [a for r in ok for a in r["on"]["attempts"]]
    took_old = [a for a in off if a["status"] == "signal"]
    took_new = [a for a in on if a["status"] == "signal"]
    L = []
    L.append(f"Structure filter replay: the last {days} days, {ist(min(r['start'] for r in ok))} → {ist(max(r['end'] for r in ok))} IST, "
             f"{len(ok)} symbols ({sum(r['market'] == 'crypto' for r in ok)} crypto, {sum(r['market'] == 'forex' for r in ok)} forex)")
    L.append("entries: S&D M15, S&D M30, S&D H4 (M15 inside a reached H4 zone); watch mode, the live engine code\n")
    L.append(f"{'':36s}{'old logic':>12s}{'filters on':>12s}")
    L.append(f"{'live pullbacks to a setup (attempts)':36s}{len(off):12d}{len(on):12d}")
    L.append(f"{'  against the H4/H1 bias':36s}{sum(a['status'] == 'against bias' for a in off):12d}{sum(a['status'] == 'against bias' for a in on):12d}")
    L.append(f"{'  refused':36s}{sum(a['status'] == 'refused' for a in off):12d}{sum(a['status'] == 'refused' for a in on):12d}")
    L.append(f"{'  TAKEN (signal = an order if trading)':36s}{len(took_old):12d}{len(took_new):12d}")
    for et in ("S&D M15", "S&D M30", "S&D H4"):
        L.append(f"{'    ' + et:36s}{sum(a['entry_type'] == et for a in took_old):12d}{sum(a['entry_type'] == et for a in took_new):12d}")
    L.append(f"\nfilters on: {len(recs)} decision records (every live attempt, counter-bias ones included)")
    L.append("rejected by the FIRST failing gate:")
    first = Counter(x["first_fail"] for x in recs)
    for g, name in FL.GATES.items():
        L.append(f"  {g} {name:12s}{first.get(g, 0):6d}  {100 * first.get(g, 0) / max(1, len(recs)):5.1f} %")
    passed_gates = first.get(None, 0)
    L.append(f"  all 8 gates passed {passed_gates:6d}  (of those {sum(1 for x in recs if not x['first_fail'] and x.get('checks'))} then refused by the V5 checks)")
    L.append("every gate's fails (one record can fail several):")
    L.append("  " + "  ".join(f"{g} {sum(1 for x in recs if g in x['fails'])}" for g in FL.GATES))
    old_take = [x for x in recs if x.get("old_logic") == "take"]
    L.append(f"\nof the {len(old_take)} attempts the old logic would take (same moment, filters on), first failing gate:")
    c2 = Counter(x["first_fail"] for x in old_take)
    L.append("  " + "  ".join(f"{g} {c2.get(g, 0)}" for g in FL.GATES) + f"  passed {c2.get(None, 0)}")
    L.append("would pass if only this one gate were dropped:  " + "  ".join(
        f"{g} {sum(1 for x in recs if set(x['fails']) <= {g})}" for g in FL.GATES))
    L.append("\nwhat each gate catches (every fail, numbers left out):")
    for g in FL.GATES:
        det = Counter()
        for x in recs:
            for part in (x["why"].get(g) or "").replace("drift: ", "").split("; "):
                if part:
                    det[re.sub(r"\d[\d.e+-]*", "#", part.split(" (")[0])[:78]] += 1
        for w, n in det.most_common(4):
            L.append(f"  {g} {n:5d}  {w}")
    L.append("\nthe old logic's trades, and the filters' verdict at the same moment:")
    by_id = {x["id"]: x for x in recs}
    for a in sorted(took_old, key=lambda a: a["touch_t"]):
        o, x = a.get("outcome") or {}, by_id.get(a["id"]) or {}
        g = x.get("first_fail")
        L.append(f"  {ist(a['touch_t'])}  {a['id']:28s} {a['side']:4s} {o.get('exit') or '?':4s} {o.get('r') if o.get('r') is not None else '':>6}R  "
                 f"→ {g or 'pass'} {(x.get('why') or {}).get(g, '')[:90]}")
    for name, took in (("old logic", took_old), ("filters on", took_new)):
        done = [a["outcome"] for a in took if a.get("outcome") and a["outcome"]["r"] is not None]
        L.append(f"\n{name}: {len(took)} taken, {len(done)} reached the stop or the target in the window: "
                 f"{sum(1 for o in done if o['r'] > 0)} won, {sum(1 for o in done if o['r'] < 0)} lost, {sum(o['r'] for o in done):+.1f} R "
                 f"(stop / target only, M5; {len(took) - len(done)} still open)")
    L.append("\ntaken with the filters on:")
    for a in sorted(took_new, key=lambda a: a["touch_t"]):
        o = a.get("outcome") or {}
        L.append(f"  {ist(a['touch_t'])}  {a['id']:28s} {a['entry_type'] or '':8s} {a['side']:4s}  outcome {o.get('exit')} {o.get('r')}")
    errs = [(r["symbol"], e) for r in ok for p in ("off", "on") for e in r[p]["errors"]]
    if errs:
        L.append(f"\nreplay errors: {errs[:5]}")
    bad = [r for r in res if "error" in r]
    if bad:
        L.append(f"symbols that failed: {[(r['symbol'], r['error']) for r in bad]}")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="the structure filter layer vs the old logic on the last days")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--symbols", default="")
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--offline", action="store_true", help="use engine_data/history instead of fetching from MT5")
    ap.add_argument("--cached", action="store_true", help="the bars the last run fetched (engine_data/filters/replay_bars)")
    a = ap.parse_args()
    syms = sorted(x[:-5] for x in os.listdir(HIST_DIR) if x.endswith(".json"))
    if a.symbols:
        syms = [s for s in syms if s in a.symbols.split(",")]
    src = HIST_DIR if a.offline else BARS_DIR
    if not a.offline and not a.cached:
        t0 = time.time()
        fetch(a.days, syms)
        print(f"bars fetched in {time.time() - t0:.0f} s", flush=True)
    paths = [os.path.join(src, f"{s}.json") for s in syms if os.path.exists(os.path.join(src, f"{s}.json"))]
    end_cap = int(time.time() * 1000) if not a.cached else 10 ** 14
    t0 = time.time()
    res = []
    with Pool(min(a.jobs, len(paths))) as pool:
        for r in pool.imap_unordered(_job, [(p, a.days, end_cap) for p in paths]):
            res.append(r)
            if "error" in r:
                print(f"{r['symbol']}: ERROR {r['error']}", flush=True)
            else:
                print(f"{r['symbol']:12s} old took {sum(x['status'] == 'signal' for x in r['off']['attempts']):3d}, "
                      f"filters took {sum(x['status'] == 'signal' for x in r['on']['attempts']):3d} "
                      f"({len(r['on']['records'])} records) {time.time() - t0:.0f} s", flush=True)
    txt = report(res, a.days)
    print("\n" + txt)
    os.makedirs(OUT_DIR, exist_ok=True)
    day = _dt.datetime.now(B.IST).strftime("%Y-%m-%d")
    with open(os.path.join(OUT_DIR, f"replay-{day}.txt"), "w") as f:
        f.write(txt + "\n")
    with open(os.path.join(OUT_DIR, f"replay-{day}.json"), "w") as f:
        json.dump(res, f, default=str)
    print(f"\n→ {os.path.join(OUT_DIR, f'replay-{day}.txt')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
