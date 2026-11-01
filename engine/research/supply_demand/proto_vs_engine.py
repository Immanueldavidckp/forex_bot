#!/usr/bin/env python3
"""
proto_vs_engine.py — the research prototype (sd_proto.py) and the shipped module (engine/supply_demand.py) must
find the same zones. The spec in method_report.md was written against the prototype; this is what ties it to the
code the /smc page runs.

    python3 proto_vs_engine.py            # GOLD / EURUSD, M15 + H1, last 3,000 bars each
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/david/forex")

import sd_proto as P                                                                           # noqa: E402
from engine import supply_demand as S                                                          # noqa: E402
from engine.major_structure import major_structure                                             # noqa: E402

HIST = "/home/david/forex/engine_data/history/{}.json"
KEYS = ("side", "kind", "top", "bottom", "entry", "d", "base_n", "status", "touches", "score", "role")
fails = []

for sym in ("GOLD", "EURUSD"):
    for tf in ("M15", "H1"):
        rows = json.load(open(HIST.format(sym)))["bars"][tf][-3000:]
        bars = [{"t": r[0], "o": r[1], "h": r[2], "l": r[3], "c": r[4]} for r in rows]
        m = major_structure(bars, 5)
        a = [z for z in P.zones(bars, m) if z["valid"]]
        b = [z for z in S.zones(bars, m) if z["valid"]]
        same = len(a) == len(b) and all(tuple(x[k] for k in KEYS) == tuple(y[k] for k in KEYS) for x, y in zip(a, b))
        parts = all(x["score_parts"] == y["score_parts"] for x, y in zip(a, b))
        why_a = sorted((z.get("why") or "") for z in P.zones(bars, m) if not z["valid"])
        why_b = sorted((z.get("why") or "") for z in S.zones(bars, m) if not z.get("valid"))
        print(f"  [{'ok' if same and parts and why_a == why_b else 'FAIL'}] {sym} {tf}: prototype {len(a)} valid zones, "
              f"engine {len(b)}; boxes, kinds, life cycle, score and every filtered reason identical")
        if not (same and parts and why_a == why_b):
            fails.append(f"{sym} {tf}")

print()
print(f"{len(fails)} mismatched: {fails}" if fails else "ALL OK — the page runs the researched algorithm")
sys.exit(1 if fails else 0)
