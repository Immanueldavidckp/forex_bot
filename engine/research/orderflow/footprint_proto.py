"""
footprint_proto.py — order-flow (footprint / cluster) chart prototype on FxPro MT5 ticks.  Research prototype,
pure Python + numpy, same conventions as engine/volume_profile.py (rows fixed in PRICE, floor(price / row)).

FxPro gives no traded volume and no aggressor side, so every tick is 1 unit of volume and the side is ESTIMATED
by `classify` (swappable).  Default (the aggressor agent's recommendation, 2026-10-29) = the tick rule on CHANGED
bid quotes only: bid up → 1 buy, bid down → 1 sell, binned at the NEW bid; unchanged-bid ticks are dropped (no
carry-forward).  `classify_tick_rule_bid_carry` is the MotiveWave / TradingView variant (unchanged → previous side).

    footprint(ticks, tf_ms, row, ...) -> {"row": row, "bars": [bar, ...], "cvd": [...], "stacked": [zone, ...]}

bar = {
  t            bar start, server-time epoch ms (floor(t / tf_ms) * tf_ms)
  o h l c      bid OHLC of the ticks in the bar
  rows         {price: (sell, buy)} — price = the row's lower edge (index * row), sell = bid-side (hit) volume,
               buy = ask-side (lifted) volume; only rows that traded
  volume       sum of all cells; delta = buy − sell; delta_pct = 100 * delta / volume
  max_delta /  the running (cumulative, tick by tick) delta's highest / lowest value inside the bar (Sierra "Max/Min
  min_delta    Delta"); it starts at 0, so max ≥ 0 ≥ min
  poc          the row with the most total volume (tie: nearest the bar's middle, then lower)
  vah val      value area (va_pct, default 70 %) grown from the POC: va_step = 2 → the CBOT two-row step used by
               engine/volume_profile.py; va_step = 1 → one row at a time (Sierra / most footprint platforms)
  imb_buy      rows where buy[P] ≥ ratio × sell[P − 1 row] (DIAGONAL: the ask at P against the bid one row lower)
  imb_sell     rows where sell[P] ≥ ratio × buy[P + 1 row]; both need the dominant cell ≥ min_vol; a zero on the
               weak side counts (ratio × 0 = 0) only when zero_rule = "count", never when "skip"
  stacked_buy / stacked_sell   [(low_price, high_price), ...] runs of ≥ stack consecutive imbalance rows
  unfinished_high / unfinished_low   True when BOTH cells at the bar's extreme row are > 0 (the auction did not
               finish: no 0 on the far side); a finished high has sell > 0, buy == 0 ... see report.md §2.4
}
cvd[i] = cumulative delta up to and including bar i; reset = "none" | "day" (FxPro server day) | "session"
zones  = the stacked zones carried forward: {"side", "lo", "hi", "t0", "t_end" | None, "status"}; a zone stays
         until a later bar CLOSES through it (buy zone: close < lo; sell zone: close > hi) — then it is "broken";
         a wick into it marks "touched".
"""
from __future__ import annotations

import gzip
import math
import time
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

SERVER_UTC_OFFSET_MS = 7_200_000        # FxPro server = EET (UTC+2 since 2026-10-25); the sample's times are server
DAY_MS = 86_400_000

# ------------------------------------------------------------------------------------------------ ticks --------

def load_ticks(path: str) -> Dict[str, np.ndarray]:
    """CSV(.gz) with time_msc_server, bid, ask, last, volume, volume_real, flags → arrays (one pass, numpy)."""
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt") as f:
        head = f.readline().strip().split(",")
        data = np.loadtxt(f, delimiter=",", dtype=np.float64)
    col = {k: i for i, k in enumerate(head)}
    return {
        "t": data[:, col["time_msc_server"]].astype(np.int64),
        "bid": data[:, col["bid"]],
        "ask": data[:, col["ask"]],
        "last": data[:, col["last"]],
        "flags": data[:, col["flags"]].astype(np.int64),
    }


# ------------------------------------------------------------------------------------------- classify ----------

def classify_tick_rule_bid(ticks: Dict[str, np.ndarray]) -> np.ndarray:
    """+1 buy / −1 sell / 0 dropped per tick: bid up = buy, bid down = sell, unchanged = 0 (not counted)."""
    bid = ticks["bid"]
    return np.sign(np.diff(bid, prepend=bid[0])).astype(np.int8)


def classify_tick_rule_bid_carry(ticks: Dict[str, np.ndarray]) -> np.ndarray:
    """+1 buy / −1 sell / 0 unknown per tick: bid up = buy, bid down = sell, unchanged = previous change's side."""
    bid = ticks["bid"]
    d = np.diff(bid, prepend=bid[0])
    s = np.sign(d).astype(np.int8)
    # forward-fill zeros with the last non-zero sign
    nz = s != 0
    idx = np.where(nz, np.arange(len(s)), 0)
    np.maximum.accumulate(idx, out=idx)
    filled = s[idx]
    filled[: int(np.argmax(nz))] = 0 if nz.any() else 0       # before the first change: unknown
    return filled


def classify_tick_rule_mid(ticks: Dict[str, np.ndarray]) -> np.ndarray:
    """Same rule on the mid price (bid + ask) / 2 — an alternative to swap in."""
    mid = (ticks["bid"] + ticks["ask"]) / 2
    return classify_tick_rule_bid_carry({"bid": mid})


# --------------------------------------------------------------------------------------------- rows ------------

def round_125(x: float) -> float:
    """The 1-2-5 step nearest (in log) to x (engine/volume_profile.row_size's rule)."""
    e = math.floor(math.log10(x))
    return min((k * 10 ** e for k in (1, 2, 5, 10)), key=lambda u: abs(math.log(u / x)))


def row_size(bars_hl: np.ndarray, point: float, target_rows: int = 12) -> float:
    """Row = median bar range / target_rows, rounded to a 1-2-5 multiple of the point, never below the point.
    bars_hl: array of (high − low) per bar of the timeframe (from the same ticks)."""
    rng = np.median(bars_hl[bars_hl > 0]) if (bars_hl > 0).any() else point
    raw = max(rng / target_rows, point)
    r = round_125(raw)
    return max(point, round(r / point) * point)


def row_size_price(price: float, tf: str) -> float:
    """engine/volume_profile.row_size's rule: ≈ 1 / 10,000 of the price, 1-2-5, ×2 on M30+."""
    return round_125(price * 1e-4) * (1 if tf in ("M5", "M15") else 2)


# ----------------------------------------------------------------------------------------- footprint -----------

def _value_area(prices: np.ndarray, tot: np.ndarray, poc_i: int, va_pct: float, step: int,
                stop: str = "reach") -> Tuple[float, float]:
    """Grow the value area from the POC, `step` rows at a time (1 = Sierra / ATAS / TradingView footprint,
    2 = CBOT / engine.volume_profile), taking the bigger side (tie: the upper side).
    stop = "reach": stop once the area holds ≥ va_pct of the volume (Sierra TPO, ATAS, CQG);
    stop = "never_exceed": stop BEFORE a step that would overshoot the target (TradingView Volume Profile help)."""
    n = len(tot)
    target = va_pct * tot.sum()
    top = bot = poc_i
    va = tot[poc_i]
    while va < target and (top < n - 1 or bot > 0):
        up = sum(tot[r] for r in range(top + 1, min(n, top + 1 + step)))
        dn = sum(tot[r] for r in range(max(0, bot - step), bot))
        if (up >= dn and top < n - 1) or bot == 0:
            add, k, side = up, min(step, n - 1 - top), "up"
        else:
            add, k, side = dn, min(step, bot), "dn"
        if stop == "never_exceed" and va + add > target + 1e-9:
            break
        va += add
        if side == "up":
            top += k
        else:
            bot -= k
    return float(prices[bot]), float(prices[top])


def _bar(t0: int, prices: np.ndarray, sell: np.ndarray, buy: np.ndarray, o: float, h: float, l: float, c: float,
         side_seq: np.ndarray, ratio: float, min_vol: float, zero_rule: str, stack: int, va_pct: float,
         va_step: int, va_stop: str = "reach", strict: bool = False) -> Dict:
    n = len(prices)
    tot = sell + buy
    volume = float(tot.sum())
    delta = float(buy.sum() - sell.sum())
    run = np.cumsum(side_seq)                       # running delta inside the bar
    max_d, min_d = float(max(0, run.max())), float(min(0, run.min()))
    mid = (n - 1) / 2
    poc_i = max(range(n), key=lambda r: (tot[r], -abs(r - mid), -r))
    val, vah = _value_area(prices, tot, poc_i, va_pct, va_step, va_stop)
    ge = (lambda a, b: a > b) if strict else (lambda a, b: a >= b)

    # diagonal imbalances: buy at r vs sell at r-1 ; sell at r vs buy at r+1  (rows are consecutive price steps)
    imb_buy = np.zeros(n, bool)
    imb_sell = np.zeros(n, bool)
    for r in range(n):
        if r > 0:
            opp = sell[r - 1]
            if buy[r] >= min_vol and buy[r] > 0 and (opp > 0 or zero_rule == "count") and ge(buy[r], ratio * opp):
                imb_buy[r] = True
        if r < n - 1:
            opp = buy[r + 1]
            if sell[r] >= min_vol and sell[r] > 0 and (opp > 0 or zero_rule == "count") and ge(sell[r], ratio * opp):
                imb_sell[r] = True

    def runs(mask: np.ndarray) -> List[Tuple[float, float]]:
        out, start = [], None
        for r in range(n + 1):
            on = r < n and mask[r]
            if on and start is None:
                start = r
            elif not on and start is not None:
                if r - start >= stack:
                    out.append((float(prices[start]), float(prices[r - 1])))
                start = None
        return out

    return {
        "t": int(t0), "o": o, "h": h, "l": l, "c": c,
        "rows": {float(p): (float(s), float(b)) for p, s, b in zip(prices, sell, buy)},
        "volume": volume, "delta": delta, "delta_pct": (100.0 * delta / volume) if volume else 0.0,
        "max_delta": max_d, "min_delta": min_d,
        "poc": float(prices[poc_i]), "vah": vah, "val": val,
        "imb_buy": [float(prices[r]) for r in range(n) if imb_buy[r]],
        "imb_sell": [float(prices[r]) for r in range(n) if imb_sell[r]],
        "stacked_buy": runs(imb_buy), "stacked_sell": runs(imb_sell),
        "unfinished_high": bool(sell[-1] > 0 and buy[-1] > 0),
        "unfinished_low": bool(sell[0] > 0 and buy[0] > 0),
    }


def footprint(ticks: Dict[str, np.ndarray], tf_ms: int, row: float, *, point: float = 0.01,
              classify: Callable[[Dict[str, np.ndarray]], np.ndarray] = classify_tick_rule_bid,
              ratio: float = 3.0, min_vol: float = 0.0, zero_rule: str = "skip", stack: int = 3,
              va_pct: float = 0.70, va_step: int = 1, va_stop: str = "reach", strict: bool = False,
              cvd_reset: str = "none", bin_price: str = "bid") -> Dict:
    t, bid = ticks["t"], ticks["bid"]
    side = classify(ticks)
    keep = side != 0
    t, bid, side = t[keep], bid[keep], side[keep]
    px = bid if bin_price == "bid" else (ticks["bid"][keep] + ticks["ask"][keep]) / 2
    # integer arithmetic: prices in points, rows = row_pts points → no floating-point edge cases
    row_pts = int(round(row / point))
    digits = max(0, -int(math.floor(math.log10(point) + 1e-9)))
    ridx = np.rint(px / point).astype(np.int64) // row_pts
    bar_t = (t // tf_ms) * tf_ms
    cuts = np.flatnonzero(np.diff(bar_t)) + 1
    starts = np.concatenate(([0], cuts))
    ends = np.concatenate((cuts, [len(t)]))

    bars: List[Dict] = []
    for a, b in zip(starts, ends):
        r = ridx[a:b]
        s = side[a:b]
        lo, hi = int(r.min()), int(r.max())
        n = hi - lo + 1
        buy = np.bincount(r[s > 0] - lo, minlength=n).astype(np.float64)
        sell = np.bincount(r[s < 0] - lo, minlength=n).astype(np.float64)
        prices = np.round(np.arange(lo, hi + 1) * row_pts * point, digits)
        pb = bid[a:b]
        bars.append(_bar(bar_t[a], prices, sell, buy, float(pb[0]), float(pb.max()), float(pb.min()),
                         float(pb[-1]), s, ratio, min_vol, zero_rule, stack, va_pct, va_step, va_stop, strict))

    # cumulative delta
    cvd: List[float] = []
    acc, last_key = 0.0, None
    for x in bars:
        if cvd_reset == "day":
            key = x["t"] // DAY_MS
        elif cvd_reset == "session":
            key = x["t"] // DAY_MS                                   # FxPro: one 24 h session a day (00:00 server)
        else:
            key = None
        if key != last_key:
            acc, last_key = 0.0, key
        acc += x["delta"]
        cvd.append(acc)

    # stacked-imbalance zones carried forward until a close through them
    zones: List[Dict] = []
    for i, x in enumerate(bars):
        for z in zones:
            if z["t_end"] is not None:
                continue
            if z["side"] == "buy":
                if x["c"] < z["lo"]:
                    z["t_end"], z["status"] = x["t"], "broken"
                elif x["l"] <= z["hi"] and z["t0"] != x["t"]:
                    z["status"] = "touched"; z["touches"] = z.get("touches", 0) + 1
            else:
                if x["c"] > z["hi"]:
                    z["t_end"], z["status"] = x["t"], "broken"
                elif x["h"] >= z["lo"] and z["t0"] != x["t"]:
                    z["status"] = "touched"; z["touches"] = z.get("touches", 0) + 1
        for lo, hi in x["stacked_buy"]:
            zones.append({"side": "buy", "lo": lo, "hi": hi + row, "t0": x["t"], "t_end": None, "status": "fresh"})
        for lo, hi in x["stacked_sell"]:
            zones.append({"side": "sell", "lo": lo, "hi": hi + row, "t0": x["t"], "t_end": None, "status": "fresh"})
    return {"row": row, "bars": bars, "cvd": cvd, "zones": zones}


# ----------------------------------------------------------------------------------------- rendering -----------

def text_footprint(bar: Dict, row: float, ratio: float = 3.0, width: int = 6) -> str:
    """One bar as text, top row first:  price | sell x buy  with POC '*', value area '|', imbalances '<' '>'."""
    ib, isl = set(bar["imb_buy"]), set(bar["imb_sell"])
    lines = [f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(bar['t'] / 1000))} server  O {bar['o']} H {bar['h']} "
             f"L {bar['l']} C {bar['c']}  vol {bar['volume']:.0f}  delta {bar['delta']:+.0f} "
             f"({bar['delta_pct']:+.0f} %)  max {bar['max_delta']:+.0f} min {bar['min_delta']:+.0f}  "
             f"POC {bar['poc']}  VA {bar['val']}–{bar['vah']}"
             f"{'  unfinished high' if bar['unfinished_high'] else ''}{'  unfinished low' if bar['unfinished_low'] else ''}"]
    for p in sorted(bar["rows"], reverse=True):
        s, b = bar["rows"][p]
        mark = "*" if p == bar["poc"] else ("|" if bar["val"] <= p <= bar["vah"] else " ")
        ls = "<" if p in isl else " "
        rb = ">" if p in ib else " "
        lines.append(f"  {p:>10.5g} {mark} {ls}{s:>{width}.0f} x {b:<{width}.0f}{rb}")
    if bar["stacked_buy"] or bar["stacked_sell"]:
        lines.append(f"  stacked buy {bar['stacked_buy']}  stacked sell {bar['stacked_sell']}")
    return "\n".join(lines)


def analyze_table(table: Dict[float, Tuple[float, float]], row: float, point: Optional[float] = None, **kw) -> Dict:
    """A footprint bar from a {price: (sell/bid, buy/ask)} table (documentation examples / unit tests).
    Missing prices inside the range are empty rows (0 x 0).  Keyword arguments as footprint()'s."""
    ratio, min_vol = kw.get("ratio", 3.0), kw.get("min_vol", 0.0)
    zero_rule, stack = kw.get("zero_rule", "skip"), kw.get("stack", 3)
    va_pct, va_step = kw.get("va_pct", 0.70), kw.get("va_step", 1)
    va_stop, strict = kw.get("va_stop", "reach"), kw.get("strict", False)
    point = point or row
    digits = max(0, -int(math.floor(math.log10(point) + 1e-9)))
    lo, hi = min(table), max(table)
    n = int(round((hi - lo) / row)) + 1
    prices = np.round(lo + np.arange(n) * row, digits)
    sell = np.zeros(n); buy = np.zeros(n)
    for p, (s_, b_) in table.items():
        i = int(round((p - lo) / row)); sell[i] += s_; buy[i] += b_
    seq = np.concatenate((np.ones(int(buy.sum())), -np.ones(int(sell.sum())))) if (buy.sum() + sell.sum()) else np.zeros(1)
    return _bar(0, prices, sell, buy, float(lo), float(hi), float(lo), float(hi), seq, ratio, min_vol, zero_rule,
                stack, va_pct, va_step, va_stop, strict)


# ------------------------------------------------------------------------------------------ checks -------------

def check(fp: Dict, cvd_reset: str = "none") -> Dict[str, bool]:
    """Internal consistency: rows sum to volume, delta = buy − sell, OHLC vs the row range, CVD = Σ delta."""
    ok = {"rows_sum": True, "delta": True, "ohlc_rows": True, "cvd": True, "va_contains_poc": True, "maxmin": True}
    row = fp["row"]
    acc, last_key = 0.0, None
    for x, c in zip(fp["bars"], fp["cvd"]):
        key = x["t"] // DAY_MS if cvd_reset in ("day", "session") else None
        if key != last_key:
            acc, last_key = 0.0, key
        s = sum(v[0] for v in x["rows"].values())
        b = sum(v[1] for v in x["rows"].values())
        ok["rows_sum"] &= (s + b == x["volume"])
        ok["delta"] &= (b - s == x["delta"])
        lo, hi = min(x["rows"]), max(x["rows"])
        eps = row * 1e-6
        ok["ohlc_rows"] &= (lo - eps <= x["l"] < lo + row - eps) and (hi - eps <= x["h"] < hi + row - eps)
        ok["va_contains_poc"] &= x["val"] <= x["poc"] <= x["vah"]
        ok["maxmin"] &= x["min_delta"] <= min(0, x["delta"]) and x["max_delta"] >= max(0, x["delta"])
        acc += x["delta"]
        ok["cvd"] &= abs(acc - c) < 1e-6
    return ok


# ------------------------------------------------------------------------------------------- main --------------

if __name__ == "__main__":
    import sys
    base = "/tmp/claude-1000/-home-david-forex/6f79950b-2f79-4743-8184-d36a070b7e52/scratchpad/orderflow_data/"
    sym = sys.argv[1] if len(sys.argv) > 1 else "GOLD"
    point = {"GOLD": 0.01, "EURUSD": 0.00001}[sym]
    t0 = time.perf_counter()
    ticks = load_ticks(base + f"{sym}_ticks.csv.gz")
    print(f"{sym}: {len(ticks['t']):,} ticks loaded in {time.perf_counter() - t0:.1f} s")
    side = classify_tick_rule_bid(ticks)
    print(f"  tick rule (changed bid only): buy {int((side > 0).sum()):,}  sell {int((side < 0).sum()):,}  "
          f"dropped (unchanged bid) {int((side == 0).sum()):,}")
    for tf, tf_ms in (("M5", 300_000), ("M15", 900_000)):
        # row size from the bars' ranges
        bt = (ticks["t"] // tf_ms) * tf_ms
        cuts = np.flatnonzero(np.diff(bt)) + 1
        hl = np.array([ticks["bid"][a:b].max() - ticks["bid"][a:b].min()
                       for a, b in zip(np.r_[0, cuts], np.r_[cuts, len(bt)])])
        r_atr = row_size(hl, point, 12)
        r_px = row_size_price(float(np.median(ticks["bid"])), tf)
        print(f"\n== {tf}: median bar range {np.median(hl):.5g}, row (range/12, 1-2-5) = {r_atr}, "
              f"row (price/10k rule) = {r_px}")
        t1 = time.perf_counter()
        fp = footprint(ticks, tf_ms, r_atr, point=point, ratio=3.0, min_vol=0, stack=3, va_step=1, cvd_reset="day")
        dt = time.perf_counter() - t1
        nb = len(fp["bars"])
        nrows = sum(len(x["rows"]) for x in fp["bars"])
        print(f"   {nb} bars, {nrows} cells ({nrows / nb:.1f} rows/bar), footprint() {dt:.2f} s, "
              f"checks {check(fp, "day")}")
        ni = sum(len(x["imb_buy"]) + len(x["imb_sell"]) for x in fp["bars"])
        ns = sum(len(x["stacked_buy"]) + len(x["stacked_sell"]) for x in fp["bars"])
        nu = sum(x["unfinished_high"] + x["unfinished_low"] for x in fp["bars"])
        print(f"   imbalances {ni} ({ni / nrows * 100:.1f} % of cells), stacked zones {ns}, "
              f"unfinished extremes {nu} of {2 * nb}, zones broken "
              f"{sum(z['status'] == 'broken' for z in fp['zones'])} / touched "
              f"{sum(z['status'] == 'touched' for z in fp['zones'])} / fresh {sum(z['status'] == 'fresh' for z in fp['zones'])}")
        for mv in (0, 3, 5, 10):
            fpm = footprint(ticks, tf_ms, r_atr, point=point, ratio=3.0, min_vol=mv, stack=3, va_step=1)
            cells = sum(len(x["rows"]) for x in fpm["bars"])
            ni = sum(len(x["imb_buy"]) + len(x["imb_sell"]) for x in fpm["bars"])
            ns = sum(len(x["stacked_buy"]) + len(x["stacked_sell"]) for x in fpm["bars"])
            print(f"   min_vol {mv:>2}: imbalances {ni:>5} ({ni / cells * 100:4.1f} % of cells), stacked zones {ns}")
        # example bars: a median-size bar and the bar with the most stacked imbalances (min_vol 5)
        fp5 = footprint(ticks, tf_ms, r_atr, point=point, ratio=3.0, min_vol=5, stack=3, va_step=1)
        bars_sorted = sorted(fp5["bars"], key=lambda x: len(x["rows"]))
        med = bars_sorted[len(bars_sorted) // 2]
        stk = max(fp5["bars"], key=lambda x: len(x["stacked_buy"]) + len(x["stacked_sell"]))
        for x in (med, stk):
            print(text_footprint(x, r_atr))
            print()
        zs = fp5["zones"]
        print(f"   zones (min_vol 5): {len(zs)}; broken {sum(z['status'] == 'broken' for z in zs)}, "
              f"touched before break {sum(z.get('touches', 0) > 0 for z in zs)}, open {sum(z['t_end'] is None for z in zs)}")
