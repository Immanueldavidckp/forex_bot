"""
engine/research/profit/lab.py — the measurement bench for "which entry rule actually makes money".

Fixed 0.01 lot (David 2026-10-30: "no limit for trade and position ... lot take 0.01"), so profit is
measured in ACCOUNT DOLLARS per trade, not in R: with constant size, total profit = trades x mean $.

Costs are real: every entry crosses the spread recorded on that bar (buy at ask = bid + spread, sell at
bid), and the exit crosses it back. P&L = move_in_ticks x trade_tick_value x 0.01.

Exits follow the house rule from engine/backtest.py: when one bar holds both the stop and the target, the
STOP counts. Trades are capped to max_bars and closed at that bar's close, so nothing is held overnight
(no swap, which the history does not carry anyway).

Every rule is scored against the SAME-GEOMETRY random control, because that is the only honest question:
does the rule beat picking a bar at random with the identical stop, target and costs?
"""
from __future__ import annotations

import json
import math
import os
from typing import Dict, List, Tuple

import numpy as np

HIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "engine_data", "history")
HIST = os.path.normpath(HIST)


def load(sym: str, tf: str = "M15"):
    """bars -> dict of float arrays; spread is in PRICE units, vol may be absent."""
    with open(os.path.join(HIST, f"{sym}.json")) as f:
        d = json.load(f)
    b = d["bars"].get(tf)
    if not b:
        return None
    a = np.array([r[:6] for r in b], dtype=float)
    out = {"t": a[:, 0], "o": a[:, 1], "h": a[:, 2], "l": a[:, 3], "c": a[:, 4], "spread": a[:, 5],
           "info": d["info"], "market": d.get("market"), "sym": sym, "tf": tf}
    out["vol"] = np.array([r[6] if len(r) > 6 else 0.0 for r in b], dtype=float)
    return out


def atr(bars, period: int = 14) -> np.ndarray:
    h, l, c = bars["h"], bars["l"], bars["c"]
    pc = np.concatenate(([c[0]], c[:-1]))
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    out = np.full(len(tr), np.nan)
    if len(tr) > period:
        k = np.ones(period) / period
        sm = np.convolve(tr, k, mode="valid")
        out[period - 1:] = sm
    return out


def dollars_per_price(bars) -> float:
    """$ per 1.0 of price movement at 0.01 lot."""
    i = bars["info"]
    return (1.0 / i["trade_tick_size"]) * i["trade_tick_value"] * 0.01


def simulate(bars, idx: np.ndarray, side: np.ndarray, sl_atr: float, tp_atr: float,
             max_bars: int, atr_arr: np.ndarray) -> Dict:
    """idx: entry bar (fill at that bar's close). side: +1 buy, -1 sell.

    MT5 bars are BID prices. A buy enters at the ask (bid + spread) and leaves at the bid; a sell enters at
    the bid and leaves at the ask. Either way the round trip pays exactly ONE full spread, so barriers are
    measured in bid space off the bar close and one whole spread is charged as cost. Charging only half a
    spread (an earlier version of this file) invented an edge out of the rollover, when the bid is marked
    down several times its usual distance and then recovers.
    """
    h, l, c, sp = bars["h"], bars["l"], bars["c"], bars["spread"]
    n = len(c)
    keep = (idx >= 0) & (idx < n - max_bars - 1) & np.isfinite(atr_arr[np.clip(idx, 0, n - 1)])
    idx, side = idx[keep], side[keep]
    if len(idx) == 0:
        return {"n": 0}
    a = atr_arr[idx]
    ref = c[idx]                               # bid at the signal bar
    sl = ref - side * sl_atr * a
    tp = ref + side * tp_atr * a

    exit_px = np.full(len(idx), np.nan)
    done = np.zeros(len(idx), dtype=bool)
    for k in range(1, max_bars + 1):
        j = idx + k
        hh, ll = h[j], l[j]
        hit_sl = np.where(side > 0, ll <= sl, hh >= sl) & ~done
        hit_tp = np.where(side > 0, hh >= tp, ll <= tp) & ~done
        take_sl = hit_sl
        take_tp = hit_tp & ~hit_sl             # one bar holding both -> the stop counts
        exit_px[take_sl] = sl[take_sl]
        exit_px[take_tp] = tp[take_tp]
        done |= take_sl | take_tp
        if done.all():
            break
    rest = ~done
    if rest.any():
        exit_px[rest] = c[idx[rest] + max_bars]

    dpp = dollars_per_price(bars)
    gross = side * (exit_px - ref) * dpp
    cost = sp[idx] * dpp                       # one full spread per round trip
    pnl = gross - cost
    return {"n": int(len(pnl)), "pnl": pnl, "mean": float(pnl.mean()), "total": float(pnl.sum()),
            "win": float((pnl > 0).mean()),
            "se": float(pnl.std(ddof=1) / math.sqrt(len(pnl))) if len(pnl) > 1 else float("nan")}


def score(res: Dict) -> Dict:
    if not res.get("n"):
        return {"n": 0}
    t = res["mean"] / res["se"] if res["se"] and res["se"] > 0 else 0.0
    return {"n": res["n"], "mean": res["mean"], "total": res["total"], "win": res["win"],
            "se": res["se"], "t": t}


def control(bars, n_trades: int, sl_atr: float, tp_atr: float, max_bars: int,
            atr_arr: np.ndarray, seed: int = 0) -> Dict:
    """random entries, same geometry, both sides -- the only fair yardstick."""
    rng = np.random.default_rng(seed)
    n = len(bars["c"])
    idx = rng.integers(20, n - max_bars - 2, size=max(n_trades, 2000))
    side = rng.choice([-1, 1], size=len(idx))
    return score(simulate(bars, idx, side, sl_atr, tp_atr, max_bars, atr_arr))


def fmt(name: str, s: Dict) -> str:
    if not s.get("n"):
        return f"{name:<34} no trades"
    return (f"{name:<34} n={s['n']:>6}  mean=${s['mean']:+.4f}  t={s['t']:+5.2f}  "
            f"win={s['win']*100:4.1f}%  total=${s['total']:+9.2f}")
