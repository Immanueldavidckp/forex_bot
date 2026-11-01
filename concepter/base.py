"""
concepter/base.py — what every engine is (v5 · kronos · claude).

An engine follows its OWN concept rules (rules/concept/<engine>/): what to look for on the chart. On every closed
bar it gets a View (closed bars only) and returns a Reading:
    signals    what it sees: a direction, a BOS / CHoCH, a complete setup … (shared/contracts.py Signal)
    marks      the same, drawn on the chart
    notes      why, in words

An engine does not decide trades. A strategy (rules/strategy/<name>/) says which engine's signal it takes,
and concepter/conductor.py turns the signals into entry · stop loss · take profit · exit and sends them to the
executor. So the same engine can serve many strategies, and a strategy can mix engines ("direction from Kronos,
BOS from Claude").
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from shared.contracts import Reading, View
from shared.rules import ConceptRules


class Concepter(ABC):
    name: str = "base"                  # = its folder in rules/concept/ and concepter/
    timeframes: List[str] = ["M15"]     # the bars it reads
    lookback: int = 500                 # closed bars per timeframe in each View
    signal_kinds: List[str] = []        # the kinds of Signal it can report

    def __init__(self, rules: ConceptRules):
        self.rules = rules

    @abstractmethod
    def on_bar(self, view: View) -> Reading:
        """Called when a bar closes on view.symbol. Report every signal that is still current; the strategy picks
        the ones young enough for it."""
