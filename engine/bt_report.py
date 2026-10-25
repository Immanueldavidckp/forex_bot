"""
engine/bt_report.py — what the backtest says (python3 -m engine.backtest report): the engine as it trades now,
whether each live filter earns its keep, where the targets should be, which chart features separate the
setups that work from the worthless ones, and filter rules "trained" on the older 60 % of the history and
judged only on the newer 40 % (a rule that only works on the months it was found on is not kept).

Outcome = R of the fixed stop / target trade (structure target; 3R what-if for setups the engine refuses for
having none). → engine_data/backtest/report.txt + report.json
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple

from .backtest import OUT_DIR, SETUPS_FILE

NUM = ["disp_x", "zone_atr", "fvg_n", "fvg_atr", "move_atr", "break_atr", "bos_streak", "choch_against", "bos_against",
       "sl_atr", "sl_pct", "spread_frac", "atr_pct", "rr", "range_pos", "entry_zone_r", "age_bars", "wait_m5",
       "strength_score", "hour"]
CAT = ["tf", "side", "market", "kind", "tgt_tf", "h4", "tf_trend", "strength", "leg_running", "dow"]
TRAIN_FRAC = 0.6
MIN_N = 40


def ts(ms: int) -> str:
    return _dt.datetime.fromtimestamp(ms / 1000, _dt.timezone.utc).strftime("%Y-%m-%d")


def val(r: Dict, k: str):
    return r[k] if k in ("tf", "side", "market", "symbol") else r["feats"].get(k)


def R(r: Dict) -> Optional[float]:
    return (r.get("fixed") or {}).get("r")


def stats(rs: List[Dict], f: Callable = R) -> Dict:
    xs = [f(r) for r in rs if f(r) is not None]
    if not xs:
        return {"n": 0}
    eq = dd = peak = 0.0
    for x in xs:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return {"n": len(xs), "win": round(sum(1 for x in xs if x > 0) / len(xs), 3), "avg": round(sum(xs) / len(xs), 3),
            "sum": round(sum(xs), 1), "dd": round(dd, 1)}


def fmt(s: Dict) -> str:
    if not s.get("n"):
        return "n=0"
    return f"n={s['n']:5d} win {s['win']:5.1%} avg {s['avg']:+.2f}R sum {s['sum']:+7.1f}R maxDD {s['dd']:5.1f}R"


def quantiles(xs: List[float], qs: List[float]) -> List[float]:
    xs = sorted(xs)
    return sorted({xs[min(len(xs) - 1, int(q * len(xs)))] for q in qs}) if xs else []


def conditions(train: List[Dict]) -> List[Tuple[str, Callable]]:
    out = []
    for k in NUM:
        xs = [val(r, k) for r in train if val(r, k) is not None]
        for q in quantiles(xs, [i / 10 for i in range(1, 10)]):
            out.append((f"{k} <= {q:g}", lambda r, k=k, q=q: val(r, k) is not None and val(r, k) <= q))
            out.append((f"{k} >= {q:g}", lambda r, k=k, q=q: val(r, k) is not None and val(r, k) >= q))
    for k in CAT:
        for v in sorted({str(val(r, k)) for r in train}):
            out.append((f"{k} == {v}", lambda r, k=k, v=v: str(val(r, k)) == v))
            out.append((f"{k} != {v}", lambda r, k=k, v=v: str(val(r, k)) != v))
    return out


def train_rules(train: List[Dict], test: List[Dict], depth: int = 3) -> Tuple[List[Dict], List[Dict]]:
    """Greedy: each step adds the condition that lifts the train average R most while keeping ≥ max(MIN_N, 20 %)
    of the train setups; every step is also scored on the test setups it never saw."""
    conds = conditions(train)
    singles = []
    base = stats(train)["avg"]
    for name, c in conds:
        a, b = [r for r in train if c(r)], [r for r in test if c(r)]
        sa = stats(a)
        if sa.get("n", 0) >= max(MIN_N, 0.2 * len(train)):
            singles.append({"rule": name, "train": sa, "test": stats(b), "lift": round(sa["avg"] - base, 3)})
    singles.sort(key=lambda x: -x["lift"])
    path, chosen, cur_tr, cur_te = [], [], train, test
    for _ in range(depth):
        best = None
        for name, c in conds:
            if name in chosen:
                continue
            a = [r for r in cur_tr if c(r)]
            sa = stats(a)
            if sa.get("n", 0) < max(MIN_N, 0.2 * len(train)):
                continue
            if best is None or sa["avg"] > best[1]["avg"]:
                best = (name, sa, c)
        if best is None or best[1]["avg"] <= stats(cur_tr)["avg"] + 0.02:
            break
        name, sa, c = best
        chosen.append(name)
        cur_tr, cur_te = [r for r in cur_tr if c(r)], [r for r in cur_te if c(r)]
        path.append({"rules": list(chosen), "train": sa, "test": stats(cur_te)})
    return singles, path


def buckets(train: List[Dict], test: List[Dict], k: str, cat: bool) -> List[Dict]:
    rows = []
    if cat:
        for v in sorted({str(val(r, k)) for r in train + test}):
            a, b = [r for r in train if str(val(r, k)) == v], [r for r in test if str(val(r, k)) == v]
            rows.append({"bucket": v, "train": stats(a), "test": stats(b)})
        return rows
    xs = [val(r, k) for r in train if val(r, k) is not None]
    edges = quantiles(xs, [0.2, 0.4, 0.6, 0.8])
    lo = None
    for hi in edges + [None]:
        def inb(r, lo=lo, hi=hi):
            x = val(r, k)
            return x is not None and (lo is None or x > lo) and (hi is None or x <= hi)
        a, b = [r for r in train if inb(r)], [r for r in test if inb(r)]
        rows.append({"bucket": f"{'' if lo is None else f'>{lo:g} '}{'' if hi is None else f'<={hi:g}'}".strip() or "all",
                     "train": stats(a), "test": stats(b)})
        lo = hi
    return rows


def targets(rs: List[Dict]) -> List[Dict]:
    """Fixed R targets read off the excursion before the stop: P(reached X R) × X − P(not) × 1."""
    xs = [r["fixed"] for r in rs if r.get("fixed") and r["fixed"]["exit"] != "open"]
    out = []
    for X in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8):
        hit = sum(1 for f in xs if f["mfe_r"] >= X)
        out.append({"target_r": X, "n": len(xs), "hit": round(hit / len(xs), 3) if xs else None,
                    "avg": round((hit * X - (len(xs) - hit)) / len(xs), 3) if xs else None})
    return out


def main(run: str = "") -> int:
    src = SETUPS_FILE.replace(".jsonl", f"_{run}.jsonl") if run else SETUPS_FILE
    rs = [json.loads(line) for line in open(src)]
    ok = [r for r in rs if R(r) is not None]
    traded = sorted([r for r in ok if r["traded"] and r["live_tf"]], key=lambda r: r["touch_t"])
    aligned = sorted([r for r in ok if r["aligned"]], key=lambda r: r["touch_t"])
    cut = traded[int(TRAIN_FRAC * len(traded))]["touch_t"] if traded else 0
    tr_tr, tr_te = [r for r in traded if r["touch_t"] < cut], [r for r in traded if r["touch_t"] >= cut]
    lines: List[str] = []
    rep: Dict = {"generated": ts(int(_dt.datetime.now().timestamp() * 1000)), "cut": ts(cut),
                 "from": ts(min(r["touch_t"] for r in rs)), "to": ts(max(r["touch_t"] for r in rs))}
    P = lines.append
    P(f"V5 backtest — {len(rs)} touched setups {rep['from']} → {rep['to']}; train before {rep['cut']}, test after")
    P("")
    P("1. THE ENGINE AS IT TRADES NOW (M15 + M30, every live check passed), fixed stop / structure target")
    rep["engine"] = {}
    for name, sub in [("all", traded), ("train", tr_tr), ("test", tr_te)] + \
            [(f"{tf}", [r for r in traded if r["tf"] == tf]) for tf in ("M15", "M30")] + \
            [(m, [r for r in traded if r["market"] == m]) for m in ("crypto", "forex")] + \
            [(s, [r for r in traded if r["side"] == s]) for s in ("buy", "sell")]:
        rep["engine"][name] = {"fixed": stats(sub), "managed": stats(sub, lambda r: (r.get("managed") or {}).get("r"))}
        P(f"   {name:7s} fixed   {fmt(rep['engine'][name]['fixed'])}")
        P(f"   {'':7s} managed {fmt(rep['engine'][name]['managed'])}   (live Mode A/B + layer, in normal-R)")
    P("")
    h1 = [r for r in ok if r["traded"] and r["tf"] == "H1"]
    if h1:
        P(f"   H1 (chart only today) would be: {fmt(stats(h1))}")
        rep["engine"]["H1 what-if"] = {"fixed": stats(h1)}
        P("")
    P("2. THE LIVE FILTERS — how the setups each one refuses would have done (3R what-if when no target)")
    rep["filters"] = {}
    groups = defaultdict(list)
    for r in ok:
        if not r["live_tf"]:
            continue
        w = r["why"] or "TRADED"
        key = ("TRADED" if w == "TRADED" else "against the H1 bias" if "against the H1" in w else "no structure target" if "no structure" in w
               else "SL > 3× ATR" if "ATR" in w else "broker stops level" if "broker" in w else "spread" if "spread" in w else w[:40])
        groups[key].append(r)
    for k, sub in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        rep["filters"][k] = stats(sub)
        P(f"   {k:22s} {fmt(stats(sub))}")
    P("")
    P("3. TARGETS — fixed R targets for the traded setups, from how far price went before the stop")
    rep["targets"] = targets(traded)
    for t in rep["targets"]:
        P(f"   {t['target_r']:>4}R target: reached {t['hit']:.1%} → avg {t['avg']:+.2f}R")
    P("")
    P("4. PER SYMBOL (traded, fixed R) — train | test")
    rep["symbols"] = {}
    for s in sorted({r["symbol"] for r in traded}):
        a, b = [r for r in tr_tr if r["symbol"] == s], [r for r in tr_te if r["symbol"] == s]
        rep["symbols"][s] = {"train": stats(a), "test": stats(b)}
    for s, v in sorted(rep["symbols"].items(), key=lambda kv: -(kv[1]["train"].get("sum", 0) + kv[1]["test"].get("sum", 0))):
        P(f"   {s:12s} {fmt(v['train'])} | {fmt(v['test'])}")
    P("")
    P("5. CHART FEATURES (traded setups) — buckets from the train part, train | test")
    rep["features"] = {}
    for k in CAT + NUM:
        rows = buckets(tr_tr, tr_te, k, k in CAT)
        rep["features"][k] = rows
        P(f"   {k}")
        for row in rows:
            P(f"      {row['bucket']:18s} {fmt(row['train'])} | {fmt(row['test'])}")
    P("")
    P("6. TRAINED FILTERS (found on train, judged on test)")
    singles, path = train_rules(tr_tr, tr_te)
    rep["rules_single"], rep["rules_path"] = singles[:25], path
    P(f"   baseline        train {fmt(stats(tr_tr))} | test {fmt(stats(tr_te))}")
    P("   best single conditions:")
    for x in singles[:25]:
        P(f"      {x['rule']:28s} train {fmt(x['train'])} | test {fmt(x['test'])}")
    P("   greedy combination:")
    for x in path:
        P(f"      {' AND '.join(x['rules'])}")
        P(f"         train {fmt(x['train'])} | test {fmt(x['test'])}")
    P("")
    P("7. THE SAME TRAINING ON EVERY BIAS-ALIGNED SETUP (also the ones the live checks refuse)")
    cut2 = aligned[int(TRAIN_FRAC * len(aligned))]["touch_t"] if aligned else 0
    al_tr, al_te = [r for r in aligned if r["touch_t"] < cut2 and r["live_tf"]], [r for r in aligned if r["touch_t"] >= cut2 and r["live_tf"]]
    s2, p2 = train_rules(al_tr, al_te)
    rep["aligned_rules_single"], rep["aligned_rules_path"] = s2[:25], p2
    P(f"   baseline        train {fmt(stats(al_tr))} | test {fmt(stats(al_te))}")
    for x in s2[:15]:
        P(f"      {x['rule']:28s} train {fmt(x['train'])} | test {fmt(x['test'])}")
    for x in p2:
        P(f"      {' AND '.join(x['rules'])}")
        P(f"         train {fmt(x['train'])} | test {fmt(x['test'])}")
    name = f"report{'_' + run if run else ''}"
    with open(os.path.join(OUT_DIR, f"{name}.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(OUT_DIR, f"{name}.json"), "w") as f:
        json.dump(rep, f, indent=1)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
