"""
S&D David (the LIVE rule, engine/sd_david.py + engine/sdd_book.py) replayed on the Indian market, with a forex / gold
reference run through the SAME simulator (David 2026-11-12: "check the indian market does our S&D work").

Walk-forward, no look-ahead: after every closed bar k, sd_david.zones() runs on the bars that had closed by then (the
live window, the last 3000), exactly as the engine does each M15 bar. Then, as sdd_book.py trades it:
  every VALID zone that is live and still FRESH has one LIMIT order
      demand -> BUY at A's high,  stop A's low  - 10 points, target T1 (Fib 0.618, 1 = entry, 0 = recent high)
      supply -> SELL at A's low,  stop A's high + 10 points, target T1
  the target follows T1 while the order waits; the order is cancelled when the zone ends or stops being fresh
  skipped when the round-trip cost is over 25 % of the stop distance, or T1 is not beyond the entry
Fills on the next bars: a limit fills at the entry, or at the open when the bar gaps through it (better price); the
fill bar can stop the trade but not take profit; a bar that reaches both the stop and the target counts the stop;
a gap through the stop / target exits at the open. One trade per zone; trades on different zones may overlap.
Costs, round trip, as a share of price [ours]: NSE index futures 0.03 %, NSE stocks 0.06 % (STT + exchange + stamp +
GST + brokerage + a tick of slippage); forex / gold = the FxPro median spread from engine_data/symbol_cost.json.
R = (exit - entry, signed) minus the cost, divided by (|entry - stop| + cost).
India intraday (M15 / H1) is also run "EOD": a position still open at the day's last bar closes at its close
(intraday MIS square-off); waiting orders carry over, as the live book re-places them.

    python3 engine/research/sd_india/backtest.py      -> engine_data/india/results.json + a printed table
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from multiprocessing import Pool

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
from engine import learn, sd_david  # noqa: E402

DATA = os.path.join(ROOT, "engine_data", "india")
IST = timezone(timedelta(hours=5, minutes=30))
WINDOW, WARMUP = 3000, 200
SL_POINTS = 10
MAX_COST_RISK = 0.25
INDICES = {"NIFTY50", "BANKNIFTY", "FINNIFTY", "SENSEX"}
STOCKS = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN", "AXISBANK", "LT", "ITC", "BHARTIARTL"]
FX = {"GOLD": 0.01, "EURUSD": 0.00001, "GBPUSD": 0.00001, "USDJPY": 0.001}     # MT5 point
FX_BARS = 20000                                                                  # ~10 months of M15


def simulate(bars, point, cost_fn, eod=False):
    n = len(bars)
    pend, open_, done, seen = {}, [], [], set()
    day = [datetime.fromtimestamp(b["t"] / 1000, IST).date() for b in bars] if eod else None
    for k in range(WARMUP, n - 1):
        lo = max(0, k + 1 - WINDOW)
        win = bars[lo:k + 1]
        want = {}
        for z in sd_david.zones(win):
            if not z.get("valid") or not z.get("live") or z.get("status") != "fresh":
                continue
            key = win[z["break"]]["t"]
            if key in seen:
                continue
            tg = z.get("targets") or []
            if not tg:
                continue
            buy = z["dir"] == "buy"
            e, buf = z["proximal"], SL_POINTS * point
            sl = z["distal"] - buf if buy else z["distal"] + buf
            tp = tg[0]["price"]
            c = cost_fn(e)
            risk = abs(e - sl)
            if risk <= 0 or (buy and tp <= e) or (not buy and tp >= e) or c > MAX_COST_RISK * risk:
                continue
            want[key] = {"key": key, "buy": buy, "e": e, "sl": sl, "tp": tp, "cost": c, "t_break": key,
                         "rr": round(abs(tp - e) / (risk + c), 2)}
        pend = want                                          # live book: cancel what is no longer wanted, follow T1
        b = bars[k + 1]
        # open trades first (the fill bar of a new trade is handled below)
        still = []
        for tr in open_:
            x = exit_price(tr, b)
            if x is None and eod and day[k + 2 if k + 2 < n else k + 1] != day[k + 1]:
                x, why = b["c"], "eod"
            else:
                why = None
            if x is None:
                still.append(tr)
            else:
                done.append(close(tr, x, b, why or tr.pop("_why")))
        open_ = still
        for key, o in list(pend.items()):
            buy = o["buy"]
            if (buy and b["l"] <= o["e"]) or (not buy and b["h"] >= o["e"]):
                fill = min(b["o"], o["e"]) if buy else max(b["o"], o["e"])
                tr = dict(o, fill=fill, t_fill=b["t"])
                seen.add(key)
                pend.pop(key)
                if (buy and b["l"] <= o["sl"]) or (not buy and b["h"] >= o["sl"]):
                    done.append(close(tr, min(o["sl"], fill) if buy else max(o["sl"], fill), b, "stop"))
                elif eod and day[k + 2 if k + 2 < n else k + 1] != day[k + 1]:
                    done.append(close(tr, b["c"], b, "eod"))
                else:
                    open_.append(tr)
    for tr in open_:                                         # still open at the end: marked to the last close
        done.append(close(tr, bars[-1]["c"], bars[-1], "open"))
    return done


def exit_price(tr, b):
    buy = tr["buy"]
    if buy:
        if b["o"] <= tr["sl"]: tr["_why"] = "stop"; return b["o"]
        if b["o"] >= tr["tp"]: tr["_why"] = "target"; return b["o"]
        if b["l"] <= tr["sl"]: tr["_why"] = "stop"; return tr["sl"]
        if b["h"] >= tr["tp"]: tr["_why"] = "target"; return tr["tp"]
    else:
        if b["o"] >= tr["sl"]: tr["_why"] = "stop"; return b["o"]
        if b["o"] <= tr["tp"]: tr["_why"] = "target"; return b["o"]
        if b["h"] >= tr["sl"]: tr["_why"] = "stop"; return tr["sl"]
        if b["l"] <= tr["tp"]: tr["_why"] = "target"; return tr["tp"]
    return None


def close(tr, x, b, why):
    sgn = 1 if tr["buy"] else -1
    risk = abs(tr["fill"] - tr["sl"]) + tr["cost"]
    pnl = sgn * (x - tr["fill"]) - tr["cost"]
    raw = sgn * (x - tr["fill"])
    return {"t_break": tr["t_break"], "t_fill": tr["t_fill"], "t_exit": b["t"], "side": "buy" if tr["buy"] else "sell",
            "entry": tr["fill"], "sl": tr["sl"], "tp": tr["tp"], "exit": x, "why": why, "rr": tr["rr"],
            "R": round(pnl / risk, 4) if risk else 0.0, "R_nocost": round(raw / (risk - tr["cost"]), 4) if risk > tr["cost"] else 0.0}


def stats(tr, key="R"):
    if not tr:
        return {"n": 0}
    rs = [t[key] for t in tr]
    w = [r for r in rs if r > 0]
    l = [r for r in rs if r <= 0]
    eq = peak = dd = 0.0
    for r in sorted(tr, key=lambda t: t["t_exit"]):
        eq += r[key]; peak = max(peak, eq); dd = max(dd, peak - eq)
    return {"n": len(rs), "win": round(len(w) / len(rs) * 100, 1), "avgR": round(sum(rs) / len(rs), 3),
            "totR": round(sum(rs), 1), "pf": round(sum(w) / -sum(l), 2) if l and sum(l) < 0 else None,
            "maxdd": round(dd, 1), "avg_rr": round(sum(t["rr"] for t in tr) / len(tr), 2),
            "stops": sum(t["why"] == "stop" for t in tr), "targets": sum(t["why"] == "target" for t in tr)}


def load_india(name, tf):
    with open(os.path.join(DATA, f"{name}_{tf}.json")) as f:
        return learn.to_dicts(json.load(f)["bars"])


def job(args):
    group, name, tf = args
    if group == "fx":
        bars = learn.to_dicts(learn.load_bars(name, "M15", FX_BARS))
        with open(os.path.join(ROOT, "engine_data", "symbol_cost.json")) as f:
            sp = float(json.load(f)[name]["median_spread"])
        runs = {"hold": simulate(bars, FX[name], lambda p: sp)}
    else:
        bars = load_india(name, tf)
        c = 0.0003 if name in INDICES else 0.0006
        runs = {"hold": simulate(bars, 0.05, lambda p: c * p)}
        if tf in ("M15", "H1"):
            runs["eod"] = simulate(bars, 0.05, lambda p: c * p, eod=True)
    return {"group": group, "name": name, "tf": tf, "bars": len(bars), "from": bars[0]["t"], "to": bars[-1]["t"],
            "runs": runs}


def main():
    jobs = [("india", s, tf) for tf in ("M15", "H1", "D1") for s in sorted(INDICES) + STOCKS]
    jobs += [("fx", s, "M15") for s in FX]
    with Pool(min(16, len(jobs))) as p:
        res = p.map(job, jobs, chunksize=1)
    with open(os.path.join(DATA, "results.json"), "w") as f:
        json.dump(res, f)
    for r in res:
        for run, tr in r["runs"].items():
            s = stats(tr)
            print(f"{r['name']:<11}{r['tf']:<4}{run:<5}", json.dumps(s))


if __name__ == "__main__":
    main()
