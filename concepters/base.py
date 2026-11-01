"""
concepters/base.py — what every concepter is (David 2026-11-01: "the concepter does all the main things").

A concepter follows ONE strategy from rules/. On every closed bar it gets a View (the chart + its own positions)
and returns a Decision:
    marks       what it sees on the chart (structure, zones, its entry / SL / TP): drawn on the dashboard
    commands    Open / Modify / Close for the executor: take the trade, move its stop, exit it
    notes       why, in words, including why it did nothing

It never talks to MT5 itself. The runner hands its commands to the executor, which carries them out behind
David's account limits. That keeps every concepter testable on recorded bars with the paper executor.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from shared.contracts import Decision, View
from shared.rules import Rules


class Concepter(ABC):
    name: str = "base"            # unique: v5, kronos, claude, gpt, gemini … (it owns its trades by this name)
    timeframes: List[str] = ["M15"]   # the first one is the timeframe it is called on
    lookback: int = 500           # closed bars per timeframe in each View

    def __init__(self, rules: Rules):
        self.rules = rules

    @abstractmethod
    def on_bar(self, view: View) -> Decision:
        """Called when a bar of timeframes[0] closes on view.symbol."""
