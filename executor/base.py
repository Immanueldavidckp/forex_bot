"""
executor/base.py — what every executor (paper, MT5) offers the concepters.

An executor does what a concepter commands: open, modify, close. It does NOT decide whether a trade is good.
It only refuses what breaks David's account limits (executor/guard.py + limits.toml).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

from shared.contracts import Command, Position, Result, Trade


class Executor(ABC):
    demo: bool = True

    @abstractmethod
    def submit(self, cmd: Command) -> Result:
        """Check the command against the limits, then carry it out (or refuse it, saying why)."""

    @abstractmethod
    def positions(self, concepter: Optional[str] = None, symbol: Optional[str] = None) -> List[Position]:
        """Open + pending positions, optionally only one concepter's / one symbol's."""

    @abstractmethod
    def account(self) -> Dict[str, float]:
        """balance, equity, day_start (balance at the start of the UTC day), day_pnl (realised + open, today)."""

    @abstractmethod
    def quote(self, symbol: str) -> Tuple[float, float]:
        """(bid, ask) now."""

    @abstractmethod
    def info(self, symbol: str) -> Dict:
        """MT5 symbol info: point, digits, trade_tick_size, trade_tick_value, volume_min …"""

    def trades(self) -> List[Trade]:
        """Closed positions (paper keeps them; MT5 reads its deal history)."""
        return []


def money_per_price(info: Dict, lots: float) -> float:
    """Account money per 1.0 price move for `lots` lots (MT5 tick value / tick size)."""
    tick = float(info.get("trade_tick_size") or info.get("point") or 1e-5)
    value = float(info.get("trade_tick_value") or 1.0)
    return value / tick * lots
