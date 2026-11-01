"""
compare.py — run the six ports on GOLD / EURUSD M15 + H1 (last 3,000 bars) and compare them with each other and
with David's validity gate (major_structure.py, read-only via sys.path).

Per tool: zones per 100 bars, mean height in ATR14, % touched / broken (a CLOSE beyond the far edge) within 50 and
200 bars of the bar the tool first draws the zone, % still fresh at the end, % passing David's gate, and pairwise
agreement (a zone of tool A is "matched" by tool B when B has a same-side zone whose price range overlaps A's and
whose anchor bar is within ±40 bars).

David's gate (BRIEF: "the displacement must break a valid previous confirmed swing low / high with a candle close,
= BOS, only then the zone is VALID"): the zone's anchor bar lies inside the leg of a major BOS / CHoCH of the
matching side — origin.idx <= zone.idx <= event.idx (demand <-> buy, supply <-> sell) — i.e. the move leaving the
zone is the one that closed through the level. gate_strict additionally asks the zone to sit at the leg's start:
zone.idx - origin.idx <= 10 bars (David's zone_lookback_bars 5 + the base).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, "/home/david/forex/engine")          # read-only use of David's structure rule
import major_structure as ms                            # noqa: E402

import ports                                            # noqa: E402

HIST = "/home/david/forex/engine_data/history/{}.json"
N_BARS = 3000
MATCH_BARS = 40
TOOLS = ["shved", "cmike", "svopex", "flux", "bigbeluga", "sdzpro"]
SERVER_TZ = ZoneInfo("Europe/Athens")                   # FxPro server time (sdzpro's session filter)


def load(sym, tf):
    raw = json.load(open(HIST.format(sym)))["bars"][tf][-N_BARS:]
    a = np.array([r[:5] for r in raw], dtype=float)
    v = np.array([r[6] if len(r) > 6 else 1.0 for r in raw], dtype=float)
    bars = [{"t": int(r[0]), "o": r[1], "h": r[2], "l": r[3], "c": r[4]} for r in raw]
    hours = np.array([dt.datetime.fromtimestamp(r[0] / 1000, tz=dt.timezone.utc).astimezone(SERVER_TZ).hour for r in raw])
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3], a[:, 4], v, bars, hours


def run_tools(o, h, l, c, v, hours, tf_minutes):
    out = {}
    out["shved"] = [z for z in ports.shved(o, h, l, c, tf_minutes=tf_minutes, include_busted=True) ]
    out["cmike"] = ports.cmike(o, h, l, c, v)
    out["svopex"] = ports.svopex(o, h, l, c)
    out["flux"] = ports.flux(o, h, l, c)
    out["bigbeluga"] = ports.bigbeluga(o, h, l, c, v)
    out["sdzpro"] = ports.sdzpro(o, h, l, c, hours=hours)
    return out


def track(z, h, l, c, horizons=(50, 200)):
    """generic life of a zone after the bar it is first drawn: first touch, first CLOSE beyond the far edge"""
    n = len(c)
    k0 = min(z["known_idx"], n - 1)
    top, bot = z["top"], z["bottom"]
    touch = broken = None
    for i in range(k0 + 1, n):
        if touch is None and h[i] >= bot and l[i] <= top:
            touch = i
        if (z["side"] == "supply" and c[i] > top) or (z["side"] == "demand" and c[i] < bot):
            broken = i
            break
    z["g_touch"], z["g_broken"] = touch, broken
    for H in horizons:
        z[f"touch{H}"] = touch is not None and touch - k0 <= H
        z[f"broken{H}"] = broken is not None and broken - k0 <= H
    z["fresh_end"] = touch is None
    z["bars_left"] = n - 1 - k0


def gate(z, events):
    side = "buy" if z["side"] == "demand" else "sell"
    z["gate"] = z["gate_strict"] = False
    z["gate_kind"] = None
    for e in events:
        if e["side"] == side and e["origin"]["idx"] <= z["idx"] <= e["idx"]:
            z["gate"] = True
            z["gate_kind"] = e["kind"]
            if z["idx"] - e["origin"]["idx"] <= 10:
                z["gate_strict"] = True
                break
    return z["gate"]


def agreement(zs_a, zs_b):
    if not zs_a:
        return float("nan")
    hit = 0
    for a in zs_a:
        for b in zs_b:
            if a["side"] == b["side"] and abs(a["idx"] - b["idx"]) <= MATCH_BARS and a["bottom"] <= b["top"] and a["top"] >= b["bottom"]:
                hit += 1
                break
    return 100.0 * hit / len(zs_a)


def pct(xs):
    xs = list(xs)
    return 100.0 * sum(1 for x in xs if x) / len(xs) if xs else float("nan")


def main():
    rows, agree, status = [], {}, {}
    for sym in ("GOLD", "EURUSD"):
        for tf, tfm in (("M15", 15), ("H1", 60)):
            _t, o, h, l, c, v, bars, hours = load(sym, tf)
            n = len(c)
            A = np.array(ms.atr14(bars))
            m = ms.major_structure(bars)
            ev = m["events"]
            res = run_tools(o, h, l, c, v, hours, tfm)
            key = f"{sym} {tf}"
            print(f"\n=== {key}: {n} bars, major events {len(ev)} (BOS {sum(e['kind']=='BOS' for e in ev)}, CHoCH {sum(e['kind']=='CHoCH' for e in ev)})")
            for t in TOOLS:
                zs = [z for z in res[t] if z["known_idx"] < n]
                for z in zs:
                    track(z, h, l, c)
                    gate(z, ev)
                    z["h_atr"] = (z["top"] - z["bottom"]) / A[min(z["idx"], n - 1)]
                # evaluable = zones with at least 200 bars of life left
                ev200 = [z for z in zs if z["bars_left"] >= 200]
                row = {"key": key, "tool": t, "n": len(zs), "per100": 100.0 * len(zs) / n,
                       "h_atr": float(np.mean([z["h_atr"] for z in zs])) if zs else float("nan"),
                       "h_atr_med": float(np.median([z["h_atr"] for z in zs])) if zs else float("nan"),
                       "touch50": pct(z["touch50"] for z in ev200), "broken50": pct(z["broken50"] for z in ev200),
                       "touch200": pct(z["touch200"] for z in ev200), "broken200": pct(z["broken200"] for z in ev200),
                       "fresh_end": pct(z["fresh_end"] for z in zs),
                       "gate": pct(z["gate"] for z in zs), "gate_strict": pct(z["gate_strict"] for z in zs),
                       "n_gate": sum(z["gate"] for z in zs), "n_gate_strict": sum(z["gate_strict"] for z in zs)}
                rows.append(row)
                print(f"{t:10s} n={row['n']:4d} /100b={row['per100']:5.2f} h/ATR mean={row['h_atr']:5.2f} med={row['h_atr_med']:5.2f} "
                      f"touch50={row['touch50']:5.1f}% broken50={row['broken50']:5.1f}% touch200={row['touch200']:5.1f}% "
                      f"broken200={row['broken200']:5.1f}% fresh@end={row['fresh_end']:5.1f}% gate={row['gate']:5.1f}% ({row['n_gate']}) "
                      f"strict={row['gate_strict']:5.1f}% ({row['n_gate_strict']})")
            # tool-specific status tables
            st = {}
            sh = res["shved"]
            st["shved"] = {k: sum(1 for z in sh if z["strength"] == k) for k in ("weak", "untested", "verified", "proven", "turncoat", "busted")}
            st["shved_drawn"] = sum(1 for z in sh if z.get("shown"))
            st["shved_gate_by_strength"] = {k: pct(z["gate"] for z in sh if z["strength"] == k) for k in ("weak", "untested", "verified", "proven", "turncoat", "busted")}
            st["shved_broken200_by_strength"] = {k: pct(z["broken200"] for z in sh if z["strength"] == k and z["bars_left"] >= 200) for k in ("weak", "untested", "verified", "proven", "turncoat")}
            cm = res["cmike"]
            st["cmike_types"] = {k: sum(1 for z in cm if z["type"] == k) for k in ("RBD", "DBD", "DBR", "RBR")}
            st["cmike_fresh"] = pct(z["fresh"] for z in cm)
            st["cmike_stale"] = pct(z["stale"] for z in cm)
            st["cmike_conf_mean"] = float(np.mean([z["confidence"] for z in cm])) if cm else float("nan")
            st["cmike_gate_by_conf"] = {"<0.6": pct(z["gate"] for z in cm if z["confidence"] < 0.6), ">=0.6": pct(z["gate"] for z in cm if z["confidence"] >= 0.6)}
            st["cmike_broken200_by_conf"] = {"<0.6": pct(z["broken200"] for z in cm if z["confidence"] < 0.6 and z["bars_left"] >= 200), ">=0.6": pct(z["broken200"] for z in cm if z["confidence"] >= 0.6 and z["bars_left"] >= 200)}
            sv = res["svopex"]
            st["svopex_removed_first_touch"] = pct(z["removed_idx"] is not None for z in sv)
            st["svopex_base_n"] = {k: sum(1 for z in sv if z["base_n"] == k) for k in (1, 2, 3)}
            fl = res["flux"]
            st["flux_retests_mean"] = float(np.mean([z["retests"] for z in fl])) if fl else float("nan")
            st["flux_flipped"] = pct(z["flip_idx"] is not None for z in fl)
            st["flux_held_pct"] = 100.0 * sum(z["held"] for z in fl) / max(1, sum(z["resolved"] for z in fl))
            st["flux_gate_by_quality"] = {"q<0.5": pct(z["gate"] for z in fl if z["quality"] < 0.5), "q>=0.5": pct(z["gate"] for z in fl if z["quality"] >= 0.5)}
            bb = res["bigbeluga"]
            st["bigbeluga_deleted_close"] = pct(z["deleted_idx"] is not None and not z["removed_overlap"] and not z["evicted"] for z in bb)
            st["bigbeluga_mitigated"] = pct(z["mitigated_idx"] is not None for z in bb)
            st["bigbeluga_overlap_removed"] = pct(z["removed_overlap"] for z in bb)
            sp = res["sdzpro"]
            st["sdzpro_broken"] = pct(z["broken"] for z in sp)
            st["sdzpro_retests_mean"] = float(np.mean([z["retests"] for z in sp])) if sp else float("nan")
            st["sdzpro_strength_hist"] = {k: sum(1 for z in sp if z["strength"] == k) for k in range(0, 11)}
            st["sdzpro_gate_by_strength"] = {"<=5": pct(z["gate"] for z in sp if z["strength"] <= 5), ">5": pct(z["gate"] for z in sp if z["strength"] > 5)}
            st["sdzpro_broken200_by_strength"] = {"<=5": pct(z["broken200"] for z in sp if z["strength"] <= 5 and z["bars_left"] >= 200), ">5": pct(z["broken200"] for z in sp if z["strength"] > 5 and z["bars_left"] >= 200)}
            status[key] = st
            for k, vv in st.items():
                print(f"   {k}: {vv}")
            # agreement matrix
            mat = {}
            for a in TOOLS:
                for b in TOOLS:
                    if a != b:
                        mat[(a, b)] = agreement(res[a], res[b])
            agree[key] = mat
            print("   agreement (% of row tool's zones matched by column tool, same side, overlapping, |idx diff| <= 40):")
            print("   " + " " * 10 + "".join(f"{b:>10s}" for b in TOOLS))
            for a in TOOLS:
                print("   " + f"{a:10s}" + "".join(f"{mat[(a, b)]:10.1f}" if a != b else " " * 9 + "-" for b in TOOLS))
            # the gate the other way round: how many major events have a zone of each tool at their origin?
            cov = {}
            for t in TOOLS:
                hit = 0
                for e in ev:
                    side = "demand" if e["side"] == "buy" else "supply"
                    if any(z["side"] == side and e["origin"]["idx"] <= z["idx"] <= min(e["idx"], e["origin"]["idx"] + 10) for z in res[t]):
                        hit += 1
                cov[t] = 100.0 * hit / len(ev) if ev else float("nan")
            status[key]["event_coverage"] = cov
            print("   % of major BOS/CHoCH whose leg start (origin..origin+10) carries a zone of the tool:", {k: round(v, 1) for k, v in cov.items()})
    json.dump({"rows": rows, "agree": {k: {f"{a}>{b}": v for (a, b), v in m.items()} for k, m in agree.items()}, "status": status},
              open("compare_results.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
