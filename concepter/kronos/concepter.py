"""
concepter/kronos — Kronos as an engine that REPORTS a direction (rules/concept/kronos).

The forecasting itself is the GPU forecaster in this folder (signals.py, its own venv ~/opt/kronos-venv): every new
M15 bar it draws 16 Kronos-base paths of the next 8 bars. This file only READS those forecasts, so it runs with
the system Python, on any laptop:

    source="live"       engine_data/kronos/signals.json (the newest forecast per symbol, written by signals.py)
    source="recorded"   marketdata/sample/kronos_<SYMBOL>.jsonl.gz (paper runs; forecasts made live 10-26 → 10-28)

    direction   side = where most paths end (buy when p_up ≥ 0.5), level = the last close
                data: p (share of paths on that side) · p_up · move (median end − last) · move_atr · move_spread_x ·
                      horizon_bars
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from marketdata import data as MD
from shared.contracts import TF_MS, Mark, Reading, Signal, View

from ..base import Concepter
from ..toolkit import atr

LIVE_FILE = os.path.join(MD.DATA_DIR, "kronos", "signals.json")


class KronosConcepter(Concepter):
    name = "kronos"
    timeframes = ["M15"]
    lookback = 60
    signal_kinds = ["direction"]

    def __init__(self, rules, source: str = "recorded", data_dir: str = MD.SAMPLE_DIR):
        super().__init__(rules)
        self.source, self.data_dir = source, data_dir
        self._recorded: Dict[str, List[Dict]] = {}

    def forecast(self, symbol: str, now: int) -> Optional[Dict]:
        """The newest forecast whose bar has closed by `now`."""
        tf_ms = TF_MS[self.rules.p("forecast.tf", "M15")]
        if self.source == "live":
            try:
                with open(LIVE_FILE) as f:
                    fc = json.load(f).get(symbol)
            except (FileNotFoundError, ValueError):
                return None
            return fc if fc and fc["bar_t"] + tf_ms <= now else None
        if symbol not in self._recorded:
            self._recorded[symbol] = MD.load_kronos(symbol, self.data_dir)
        done = [fc for fc in self._recorded[symbol] if fc["bar_t"] + tf_ms <= now]
        return done[-1] if done else None

    def on_bar(self, view: View) -> Reading:
        fc = self.forecast(view.symbol, view.now)
        if not fc:
            return Reading(notes="no Kronos forecast for this symbol yet")
        tf = self.rules.p("forecast.tf", "M15")
        p_up = float(fc["p_up"])
        side = "buy" if p_up >= 0.5 else "sell"
        move = float(fc["median"][-1]) - float(fc["last"])
        bars = view.bars.get(tf, [])
        a = atr(bars) if bars else None
        spread = bars[-1].spread if bars else 0.0
        t_close = int(fc["bar_t"]) + TF_MS[tf]
        sig = Signal("kronos", "direction", view.symbol, tf, t_close, side, level=float(fc["last"]),
                     data={"p": round(max(p_up, 1 - p_up), 4), "p_up": p_up, "move": move,
                           "move_atr": round(abs(move) / a, 3) if a else None,
                           "move_spread_x": round(abs(move) / spread, 2) if spread else None,
                           "horizon_bars": int(fc.get("horizon", self.rules.p("forecast.horizon", 8)))},
                     text=f"Kronos {side} p {max(p_up, 1 - p_up):.0%}")
        end_t = t_close + sig.data["horizon_bars"] * TF_MS[tf]
        marks = [Mark("forecast", tf, t_close, float(fc["median"][-1]), t1=end_t, side=side,
                      text=f"Kronos median, p_up {p_up:.0%}", engine="kronos")]
        return Reading(signals=[sig], marks=marks)
