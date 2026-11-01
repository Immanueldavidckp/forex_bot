"""
shared/toolkit.py — the ONE way every concepter reads the chart, so V5, Claude, GPT and Gemini see the same
structure and the same zones. For now it calls the engine's code (engine/major_structure.py = David's structure
rule, engine/supply_demand.py = the valid S&D zones of /smc). When that code moves, only this file changes.

    structure(bars)      → {trend, events [BOS / CHoCH], protected, bos_level}     (David's rule: BOS at the leg
                           extreme, CHoCH only at the protected swing, no internal BOS)
    zones(bars, m)       → the valid S&D zones, live ones first, nearest price first
    atr(bars)            → ATR(14) of the last bar
    marks_for(...)       → those as chart Marks
"""
from __future__ import annotations

from typing import Dict, List, Optional

from engine.major_structure import atr14, major_structure
from engine import supply_demand as SD

from .contracts import Bar, Mark


def as_dicts(bars: List[Bar]) -> List[Dict]:
    return [{"t": b.t, "o": b.o, "h": b.h, "l": b.l, "c": b.c} for b in bars]


def structure(bars: List[Bar], n: int = 5) -> Dict:
    return major_structure(as_dicts(bars), n)


def atr(bars: List[Bar]) -> Optional[float]:
    a = atr14(as_dicts(bars)) if len(bars) > 15 else []
    return float(a[-1]) if len(a) and a[-1] == a[-1] else None


def zones(bars: List[Bar], m: Optional[Dict] = None, live_only: bool = True) -> List[Dict]:
    d = as_dicts(bars)
    m = m or major_structure(d, 5)
    zs = SD.page(d, m)["zones"]
    if live_only:
        zs = [z for z in zs if z.get("live")]
    px = bars[-1].c
    return sorted(zs, key=lambda z: min(abs(px - z["top"]), abs(px - z["bottom"])))


def marks_for(tf: str, m: Dict, zs: List[Dict], last_events: int = 4) -> List[Mark]:
    out: List[Mark] = []
    for e in m["events"][-last_events:]:
        out.append(Mark(kind=e["kind"].lower(), tf=tf, t0=e["level_t"], t1=e["t"], price=e["level"], side=e["side"],
                        text=e["kind"]))
    for z in zs:
        out.append(Mark(kind="zone", tf=tf, t0=z["t0"], price=z["top"], price2=z["bottom"],
                        side="sell" if z["side"] == "supply" else "buy",
                        text=f"{z['side']} {z['status']} score {z['score']}"))
    return out
