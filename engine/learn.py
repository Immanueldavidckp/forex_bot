"""
engine/learn.py — David's learning chart (2026-10-25: "the engine is not finding the correct structure, so I
will draw the lines — CHoCH, FVG, BOS, supply/demand — and you train the engine from that").

The /learn page (dashboard.py) lets David draw labels on real bars; they land here as one JSON line each in
engine_data/learn/labels.jsonl (append-only: adds, deletes and note edits are separate lines, so nothing he
drew is ever lost). This module turns them into training:

  labels(sym, tf)       the labels as they stand now
  detect(sym, tf)       what the ENGINE sees on the same bars (strategy.structure + setup_for: swings,
                        BOS / CHoCH events, supply / demand / MB zones, FVGs)
  compare(sym, tf)      every label matched against the engine: ok (same thing, same place), mixed (the
                        engine calls it something else), missed (the engine has nothing there). Inside a
                        "region" label (the span David marked completely) engine events WITHOUT a matching
                        label are counted as extras — that is the engine's false-positive rate.
  fit(...)              the learning step: re-runs the engine's structure finding over a grid of its own
                        knobs (swing_length, displacement_mult) and scores each against David's labels
                        (recall; precision too where regions exist). Writes engine_data/learn/fit.json and
                        prints the ranking. It NEVER changes config.py — David decides what goes live.

    python3 -m engine.learn report [--sym BITCOIN --tf M15]
    python3 -m engine.learn fit    [--sym ... --tf ...]

Bars come from engine_data/history/<SYM>.json (deep, from engine.history) merged with the live view file
(fresh), so the page works without MT5. With ~200+ labels the same file feeds a real classifier (features
per candidate swing / zone → scikit-learn); fit.json records how many labels there are so far.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import time
from typing import Dict, List, Optional, Tuple

from . import strategy, tools
from .config import DATA_DIR, LIVE_DIR, VIEW_DIR
from .config import STRATEGY as S

LEARN_DIR = os.path.join(DATA_DIR, "learn")
LABELS_FILE = os.path.join(LEARN_DIR, "labels.jsonl")
HIST_DIR = os.path.join(DATA_DIR, "history")
KINDS = ("BOS", "CHoCH", "FVG", "supply", "demand", "swing high", "swing low",
         "support", "resistance", "up trend", "down trend", "sideways", "fib", "line", "region")
TF_MS = {"M5": 300_000, "M15": 900_000, "M30": 1_800_000, "H1": 3_600_000, "H4": 14_400_000}
SYM_RE = re.compile(r"^[A-Za-z0-9._#-]{1,24}$")
BOXES = ("FVG", "supply", "demand")
LINES = ("BOS", "CHoCH")
LEVELS = ("support", "resistance")        # a horizontal level, drawn along it (how humans mark S/R)
TRENDS = ("up trend", "down trend", "sideways")   # a span of bars the drawn trend covers
# David 2026-11-09 "add the fib retracement tool to teach the next version": a fib label is the LEG he measures —
# dragged from the swing's start (t0, p0) to its end (t1, p1); the retracement levels are computed from that, not
# stored. 0 = the end of the leg (where the pullback starts), 1 = its start. S&D David's targets are the same idea
# (T1 = 0.618, T2 = 0.5, T3 = 0.382 between the entry and the move's extreme).
FIB = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0)


def fib_levels(rec: Dict) -> List[Dict]:
    """The price of every FIB ratio for one fib label: 0 at the leg's end (p1), 1 at its start (p0)."""
    p0, p1 = rec.get("p0"), rec.get("p1")
    if p0 is None or p1 is None:
        return []
    return [{"ratio": r, "price": round(p1 + r * (p0 - p1), 8)} for r in FIB]


# ── bars (files only, never MT5) ─────────────────────────────────────────────

def load_bars(sym: str, tf: str, n: int = 3000) -> List[list]:
    """[t_ms, o, h, l, c, v] rows of closed bars: the saved history (deep) + the engine's view file + the /smc page's
    live file (fresh, engine/live.py), newest n. A bar still forming when its file was written is left out — the file
    holds a snapshot of it, not the bar. v = the MT5 tick volume, None where the file has none (history saved before
    2026-10-29)."""
    rows: Dict[int, list] = {}
    for path, t_s, vi, written in ((os.path.join(HIST_DIR, f"{sym}.json"), 1, 6, lambda d: d.get("fetched", 0) * 1000),
                                   (os.path.join(VIEW_DIR, f"{sym}.json"), 1000, 5, lambda d: d.get("updated", 0)),
                                   (os.path.join(LIVE_DIR, f"{sym}.json"), 1, 5, lambda d: d.get("at", 0))):
        try:
            with open(path) as f:
                d = json.load(f)
        except (FileNotFoundError, ValueError):
            continue
        last = written(d) - TF_MS[tf] if written(d) else float("inf")     # the latest bar open that had closed then
        for r in d.get("bars", {}).get(tf, []):
            t = int(r[0] * t_s)
            if t > last:
                continue
            v = r[vi] if len(r) > vi else None
            if v is None and t in rows:                           # a view bar without volume keeps the history's
                v = rows[t][5]
            rows[t] = [t, r[1], r[2], r[3], r[4], v]
    return [rows[t] for t in sorted(rows)][-n:]


def to_dicts(rows: List[list]) -> List[Dict]:
    return [{"t": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4], "v": float(r[5] or 0) if len(r) > 5 else 0.0} for r in rows]


def infer_side(rows: List[list], t0: Optional[int], t1: Optional[int], level: float, tf: str) -> Optional[str]:
    """The direction a drawn BOS / CHoCH line means, from the candles: which side price CAME from. The line is
    drawn from where the level formed to its break, so the first third of the span says what the level was —
    closes above it = a broken support = a sell break; closes below = a broken resistance = a buy break.
    (The break candle's own close cannot decide: David draws the shelf a little past the engine's exact swing,
    so that close often sits between his line and the real level.)"""
    if t0 is None:
        return None
    a, b = sorted((t0, t1 if t1 is not None else t0))
    closes = [r[4] for r in rows if a - TF_MS[tf] <= r[0] <= b + TF_MS[tf]]
    head = closes[:max(1, len(closes) // 3)]
    above = sum(c > level for c in head) - sum(c < level for c in head)
    return "sell" if above > 0 else "buy" if above < 0 else None


# ── the labels file ──────────────────────────────────────────────────────────

def labels(sym: Optional[str] = None, tf: Optional[str] = None) -> List[Dict]:
    out: Dict[str, Dict] = {}
    try:
        fh = open(LABELS_FILE)
    except FileNotFoundError:
        return []
    with fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("op") == "del":
                out.pop(r.get("id"), None)
            elif r.get("op") == "note":
                if r.get("id") in out:
                    out[r["id"]]["note"] = str(r.get("note", ""))[:300]
            elif r.get("op") == "side":
                if r.get("id") in out and r.get("side") in (None, "buy", "sell"):
                    out[r["id"]]["side"] = r.get("side")
            elif r.get("id"):
                out[r["id"]] = r
    keep = [r for r in out.values() if (sym is None or r.get("sym") == sym) and (tf is None or r.get("tf") == tf)]
    for r in keep:
        if r.get("kind") == "fib" and r.get("p1") is not None:
            r["leg"] = "up" if r["p1"] > r["p0"] else "down"
            r["levels"] = fib_levels(r)
    return sorted(keep, key=lambda r: (r.get("sym", ""), r.get("tf", ""), r.get("t0") or 0))


def _append(rec: Dict):
    os.makedirs(LEARN_DIR, exist_ok=True)
    with open(LABELS_FILE, "a") as f:
        f.write(json.dumps(rec) + "\n")


def save_label(r: Dict, by: Optional[str] = None) -> Dict:
    """Validates and appends one drawn label; returns it with its id. Raises ValueError on bad input.
    by = who drew it when not David ("public" = the dashboard's internet copy)."""
    if not SYM_RE.match(str(r.get("sym", ""))) or r.get("tf") not in TF_MS or r.get("kind") not in KINDS:
        raise ValueError("bad sym / tf / kind")
    side = r.get("side")
    if side not in (None, "buy", "sell"):
        raise ValueError("bad side")
    # a drawn BOS / CHoCH gets its direction from the candles, never from a button (David drew 15 lines with
    # the side toggle still on its default, 2026-10-25) — the break candle's close decides
    if r["kind"] in LINES and r.get("p0") is not None:
        side = infer_side(load_bars(r["sym"], r["tf"]), r.get("t0"), r.get("t1"), float(r["p0"]), r["tf"]) or side
    rec = {"id": "L" + secrets.token_hex(4), "sym": r["sym"], "tf": r["tf"], "kind": r["kind"], "side": side,
           "created": int(time.time() * 1000)}
    for k in ("t0", "t1"):
        if r.get(k) is not None:
            rec[k] = int(r[k])
    for k in ("p0", "p1"):
        if r.get(k) is not None:
            rec[k] = float(r[k])
    if rec.get("t0") is None:
        raise ValueError("no time")
    if r.get("note"):
        rec["note"] = str(r["note"])[:300]
    if by:
        rec["by"] = by
    _append(rec)
    return rec


def delete_label(label_id: str, by: Optional[str] = None):
    _append({"op": "del", "id": str(label_id)[:24], **({"by": by} if by else {})})


def note_label(label_id: str, note: str, by: Optional[str] = None):
    _append({"op": "note", "id": str(label_id)[:24], "note": str(note)[:300], **({"by": by} if by else {})})


# ── what the engine sees on the same bars ────────────────────────────────────

def detect(sym: str, tf: str, n: int = 3000, swing_length: Optional[int] = None) -> Dict:
    return detect_rows(load_bars(sym, tf, n), tf, sym, swing_length)


def detect_rows(rows: List[list], tf: str, sym: str = "", swing_length: Optional[int] = None) -> Dict:
    """detect() on given [t_ms, o, h, l, c] rows (the /smc page runs it on the MT5 indicators' own bars)."""
    bars = to_dicts(rows)
    if len(bars) < 10:
        return {"n_bars": len(bars), "swings": [], "events": [], "zones": [], "fvgs": [], "trend": None}
    st = strategy.structure(bars, n=swing_length)
    zones, fvgs, seen = [], [], set()
    for e in st["events"]:
        rec = strategy.setup_for(bars, st, e, tf, sym)
        z = rec.get("zone") or rec.get("mb")
        if z and (z["t"], z["top"], z["bottom"]) not in seen:
            seen.add((z["t"], z["top"], z["bottom"]))
            zones.append({"kind": z.get("kind", "MB"), "top": z["top"], "bottom": z["bottom"], "t": z["t"], "side": rec["side"]})
        for f in rec.get("fvgs") or []:
            if ("f", f["t"], f["top"]) not in seen:
                seen.add(("f", f["t"], f["top"]))
                fvgs.append({"top": f["top"], "bottom": f["bottom"], "t": f["t"], "side": rec["side"]})
    return {"n_bars": len(bars), "trend": st["trend"],
            "swings": [{"t": s["t"], "price": s["price"], "kind": s["kind"], "label": s.get("label")} for s in st["swings"]],
            "events": [{"kind": e["kind"], "side": e["side"], "level": e["level"], "level_t": e["level_t"],
                        "t": e["t"], "close": e["close"]} for e in st["events"]],
            "zones": zones, "fvgs": fvgs,
            "atr": tools.atr(bars[-60:], 14) or 0.0}


# ── labels vs the engine ─────────────────────────────────────────────────────

def _match_line(lb: Dict, det: Dict, tol_p: float, tol_t: int) -> Optional[Dict]:
    """A drawn BOS / CHoCH: the level is p0, the break is around t1 (or t0). Nearest engine event at that level
    and time, the drawn side honoured when given."""
    t = lb.get("t1") or lb["t0"]
    cands = [e for e in det["events"]
             if abs(e["level"] - lb["p0"]) <= tol_p
             and (abs(e["t"] - t) <= tol_t or abs(e["level_t"] - lb["t0"]) <= tol_t or e["level_t"] - tol_t <= t <= e["t"] + tol_t)
             and (lb.get("side") in (None, e["side"]))]
    return min(cands, key=lambda e: abs(e["level"] - lb["p0"]) + abs(e["t"] - t) / max(tol_t, 1) * tol_p) if cands else None


def _match_box(lb: Dict, cands: List[Dict], tol_t: int) -> Optional[Dict]:
    """A drawn FVG / zone box: enough price overlap with an engine box born inside (or near) the drawn span."""
    lo, hi = sorted((lb["p0"], lb.get("p1", lb["p0"])))
    a, b = sorted((lb["t0"], lb.get("t1", lb["t0"])))
    best, score = None, 0.0
    for z in cands:
        if not a - tol_t <= z["t"] <= b + tol_t:
            continue
        ov = min(hi, z["top"]) - max(lo, z["bottom"])
        base = min(hi - lo, z["top"] - z["bottom"]) or 1e-12
        if ov / base > max(score, 0.5):
            best, score = z, ov / base
    return best


def compare(sym: Optional[str] = None, tf: Optional[str] = None, n: int = 3000,
            swing_length: Optional[int] = None, _dets: Optional[Dict] = None) -> Dict:
    """Every label against the engine → per kind {labels, ok, mixed, missed}; extras = engine events inside
    David's "region" spans that match none of his lines (only there can a false positive be counted)."""
    lbs = labels(sym, tf)
    groups: Dict[Tuple[str, str], List[Dict]] = {}
    for r in lbs:
        groups.setdefault((r["sym"], r["tf"]), []).append(r)
    per = {k: {"labels": 0, "ok": 0, "mixed": 0, "missed": 0} for k in KINDS if k not in ("region", "line")}
    details, extras = [], {"BOS": 0, "CHoCH": 0, "checked_ms": 0}
    for (sy, t), rs in sorted(groups.items()):
        det = (_dets or {}).get((sy, t)) or detect(sy, t, n, swing_length)
        # hand-drawn slack (set from David's first 15 lines): he draws the shelf up to ~2 ATR past the exact
        # swing and ends the line up to ~12 bars from the break candle
        tol_p, tol_t = max(det.get("atr", 0.0) * 2.2, 1e-9), 12 * TF_MS[t]
        matched_events = set()
        for lb in rs:
            k = lb["kind"]
            if k in ("region", "line"):
                continue
            per[k]["labels"] += 1
            got, verdict = None, "missed"
            if k in LINES:
                got = _match_line(lb, det, tol_p, tol_t)
                if got:
                    verdict = "ok" if got["kind"] == k else "mixed"
                    matched_events.add((got["t"], got["level"]))
            elif k in BOXES:
                cands = det["fvgs"] if k == "FVG" else det["zones"]
                got = _match_box(lb, cands, tol_t)
                if got:
                    verdict = "ok" if k == "FVG" or got["kind"] in (k, "MB") else "mixed"
            elif k in ("swing high", "swing low"):
                want = "high" if k == "swing high" else "low"
                got = next((s for s in det["swings"] if s["kind"] == want
                            and abs(s["t"] - lb["t0"]) <= 2 * TF_MS[t] and abs(s["price"] - lb["p0"]) <= tol_p), None)
                if got:
                    verdict = "ok"
            elif k in LEVELS and lb.get("p0") is not None:
                # a drawn S/R level: an engine swing at that price inside the drawn span — support should be
                # a swing low, resistance a swing high (the other side's swing there counts as mixed)
                want = "low" if k == "support" else "high"
                a, b = sorted((lb["t0"], lb.get("t1", lb["t0"])))
                near = [s for s in det["swings"]
                        if abs(s["price"] - lb["p0"]) <= tol_p and a - tol_t <= s["t"] <= b + tol_t]
                got = next((s for s in near if s["kind"] == want), None) or (near[0] if near else None)
                if got:
                    verdict = "ok" if got["kind"] == want else "mixed"
            elif k == "fib" and lb.get("p1") is not None:
                # the drawn leg: does the engine have a swing at each end? both = ok, one = mixed, none = missed
                ends = []
                for tt, pp in ((lb["t0"], lb["p0"]), (lb.get("t1", lb["t0"]), lb["p1"])):
                    ends.append(next((s for s in det["swings"]
                                      if abs(s["t"] - tt) <= 2 * TF_MS[t] and abs(s["price"] - pp) <= tol_p), None))
                n_ok = sum(1 for e in ends if e)
                verdict = "ok" if n_ok == 2 else "mixed" if n_ok == 1 else "missed"
                got = {"kind": "swings", "ends": n_ok} if n_ok else None
            elif k in TRENDS:
                # the engine's trend over the drawn span, read the way structure() reads it: the last two
                # swing highs and lows inside the span — both rising = up, both falling = down, else sideways;
                # fewer than two of either = the engine cannot say (missed)
                a, b = sorted((lb["t0"], lb.get("t1", lb["t0"])))
                hs = [s for s in det["swings"] if s["kind"] == "high" and a <= s["t"] <= b][-2:]
                lo = [s for s in det["swings"] if s["kind"] == "low" and a <= s["t"] <= b][-2:]
                if len(hs) == 2 and len(lo) == 2:
                    up = hs[1]["price"] > hs[0]["price"] and lo[1]["price"] > lo[0]["price"]
                    dn = hs[1]["price"] < hs[0]["price"] and lo[1]["price"] < lo[0]["price"]
                    eng = "up trend" if up else "down trend" if dn else "sideways"
                    verdict, got = ("ok" if eng == k else "mixed"), {"kind": eng}
            per[k][verdict] += 1
            details.append({"id": lb["id"], "sym": sy, "tf": t, "kind": k, "verdict": verdict,
                            "engine": got and {q: got[q] for q in got if q in ("kind", "side", "level", "t", "top", "bottom", "price")}})
        for rg in [r for r in rs if r["kind"] == "region"]:
            a, b = sorted((rg["t0"], rg.get("t1", rg["t0"])))
            extras["checked_ms"] += b - a
            for e in det["events"]:
                if a <= e["t"] <= b and (e["t"], e["level"]) not in matched_events:
                    extras[e["kind"]] = extras.get(e["kind"], 0) + 1
    return {"per_kind": per, "extras": extras, "details": details,
            "total": sum(v["labels"] for v in per.values()),
            "ok": sum(v["ok"] for v in per.values())}


# ── the learning step ────────────────────────────────────────────────────────

def fit(sym: Optional[str] = None, tf: Optional[str] = None, n: int = 3000) -> Dict:
    """Re-runs the engine's structure finding over a small grid of its own knobs and scores each setting
    against David's labels. recall = his marks the engine also finds; precision (only where he drew ✓ regions)
    = the engine's finds that he also marked. Writes the ranking to engine_data/learn/fit.json; config.py is
    NOT touched — David / the filters session apply the winner."""
    lbs = labels(sym, tf)
    if not lbs:
        return {"error": "no labels yet: draw on /learn first"}
    pairs = sorted({(r["sym"], r["tf"]) for r in lbs})
    grid = []
    keep_disp, live_sl = S["displacement_mult"], int(S["swing_length"])
    try:
        for sl in (1, 2, 3, 4, 5):
            for disp in sorted({1.2, 1.5, 2.0, float(keep_disp)}):   # the live knobs are always scored (the baseline)
                S["displacement_mult"] = disp
                dets = {(sy, t): detect(sy, t, n, swing_length=sl) for sy, t in pairs}
                c = compare(sym, tf, n, swing_length=sl, _dets=dets)
                found = sum(extra for k, extra in c["extras"].items() if k in ("BOS", "CHoCH")) + c["ok"]
                recall = c["ok"] / c["total"] if c["total"] else 0.0
                prec = c["ok"] / found if c["extras"]["checked_ms"] and found else None
                f1 = (2 * prec * recall / (prec + recall)) if prec not in (None, 0) and recall else None
                grid.append({"swing_length": sl, "displacement_mult": disp, "ok": c["ok"], "of": c["total"],
                             "recall": round(recall, 3), "precision": prec and round(prec, 3), "f1": f1 and round(f1, 3)})
    finally:
        S["displacement_mult"] = keep_disp
    key = lambda g: (g["f1"] if g["f1"] is not None else g["recall"], g["recall"])
    grid.sort(key=key, reverse=True)
    # the baseline: the live config's own score, so David compares the winner against what runs now
    live = next(g for g in grid if g["swing_length"] == live_sl and g["displacement_mult"] == float(keep_disp))
    out = {"at": int(time.time() * 1000), "labels": len(lbs), "pairs": [list(p) for p in pairs],
           "live": live, "best": grid[0], "grid": grid,
           "note": "scored against David's drawings; config.py untouched — apply by hand"
                   + ("" if any(r["kind"] == "region" for r in lbs) else
                      "; no ✓ regions drawn yet, so only recall could be scored (draw regions for precision)")}
    os.makedirs(LEARN_DIR, exist_ok=True)
    with open(os.path.join(LEARN_DIR, "fit.json"), "w") as f:
        json.dump(out, f, indent=1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="train the structure finding from David's drawn labels")
    ap.add_argument("cmd", choices=["report", "fit", "fib"])
    ap.add_argument("--sym")
    ap.add_argument("--tf")
    a = ap.parse_args()
    if a.cmd == "fib":                      # the fib legs David drew, readable: leg, start → end, every level's price
        fibs = [r for r in labels(a.sym, a.tf) if r["kind"] == "fib"]
        if not fibs:
            print("no fib labels yet")
        for r in fibs:
            t = lambda ms: time.strftime("%Y-%m-%d %H:%M", time.gmtime(ms / 1000 + 19800)) + " IST"
            print(f"{r['sym']} {r['tf']} fib {r.get('leg', '?')} leg  {t(r['t0'])} {r['p0']:g} → {t(r.get('t1', r['t0']))} {r['p1']:g}"
                  + (f"  note: {r['note']}" if r.get("note") else "") + f"  [{r['id']}]")
            for lv in r.get("levels", []):
                print(f"    {lv['ratio']:<6g} {lv['price']:g}")
        return 0
    if a.cmd == "report":
        c = compare(a.sym, a.tf)
        print(json.dumps({k: c[k] for k in ("per_kind", "extras", "total", "ok")}, indent=1))
        for d in c["details"]:
            if d["verdict"] != "ok":
                print(f"  {d['sym']} {d['tf']} {d['kind']}: {d['verdict']}")
        return 0
    r = fit(a.sym, a.tf)
    print(json.dumps(r.get("error") or {"labels": r["labels"], "live": r["live"], "best": r["best"], "note": r["note"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
