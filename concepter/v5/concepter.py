"""
concepter/v5 — David's V5 engine as an engine that REPORTS (rules/concept/v5).

    bos / choch   V5's own structure (engine/strategy.py structure(): what the live engine trades on today)
    setup         a complete V5 setup not reached yet: BOS → supply / demand (or mitigation block) in the BOS move →
                  the FVG cluster → entry 10 % into the nearest FVG.
                  data: entry · sl (zone + sl_buffer_points) · tp (the nearest untouched opposite swing on M15 / H1 /
                  H4) · top / bottom (the zone) · fvg_top / fvg_bottom · rr

This is the PAPER version: it calls the live engine's own functions, but the live engine (engine/run.py + book.py)
also has the gates (filters.py, profit.py), the M5 confirmation, the layer and Mode A / B management. Those move
here in ARCHITECTURE.md step 3; until then the live trades come from engine/, not from this file.
"""
from __future__ import annotations

from typing import Dict, List

from engine import strategy as V5
from shared.contracts import TF_MS, Mark, Reading, Signal, View

from ..base import Concepter
from ..toolkit import as_dicts


class V5Concepter(Concepter):
    name = "v5"
    timeframes = ["M15", "H1", "H4"]
    lookback = 400
    signal_kinds = ["bos", "choch", "setup"]

    def on_bar(self, view: View) -> Reading:
        tf = self.timeframes[0]
        bars = as_dicts(view.bars[tf])
        if len(bars) < 50:
            return Reading(notes="not enough bars")
        ms = TF_MS[tf]
        st = V5.structure(bars)
        r = Reading()
        for e in st["events"][-6:]:
            r.signals.append(Signal("v5", e["kind"].lower(), view.symbol, tf, e["t"] + ms, e["side"], level=e["level"],
                                    data={"origin": e["origin"]["price"], "close": e["close"]}, text=e["kind"]))
            r.marks.append(Mark(e["kind"].lower(), tf, e["level_t"], e["level"], t1=e["t"], side=e["side"],
                                text=f"V5 {e['kind']}", engine="v5"))
        point = float(view.info.get("point") or 0.00001)
        series = [(name, as_dicts(view.bars.get(name, []))) for name in self.timeframes]
        for s in V5.bos_setups(bars, st, tf, view.symbol):
            if not s.get("complete"):
                continue
            later = bars[s["formed_idx"] + 1:]
            if V5.pullback(s, later) is not None:          # price has already been back to the entry: used
                continue
            side, entry = s["side"], s["entry"]
            sl = V5.stop_price(s, point)
            ahead = [p for p, _ in V5.opposite_levels(side, *series) if (p > entry if side == "buy" else p < entry)]
            tp = min(ahead, key=lambda p: abs(p - entry)) if ahead else None
            risk = abs(entry - sl)
            data: Dict = {"entry": entry, "sl": sl, "tp": tp, "rr": round(abs(tp - entry) / risk, 2) if tp and risk else None,
                          "top": s["poi"]["top"], "bottom": s["poi"]["bottom"], "zone_kind": s["kind"],
                          "fvg_top": s["fvg"]["top"], "fvg_bottom": s["fvg"]["bottom"], "id": s["id"]}
            r.signals.append(Signal("v5", "setup", view.symbol, tf, s["formed_t"] + ms, side, level=entry, data=data,
                                    text=f"V5 {s['kind']} + FVG setup"))
            r.marks.append(Mark("zone", tf, s["poi"]["t"] if "t" in s["poi"] else s["formed_t"], s["poi"]["top"],
                                price2=s["poi"]["bottom"], side=side, text=f"V5 {s['kind']}", engine="v5"))
            r.marks.append(Mark("entry", tf, s["formed_t"], entry, side=side, text="V5 entry", engine="v5"))
        return r
