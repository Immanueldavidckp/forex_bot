"""
shared/contracts.py — the language the three parts speak (David's architecture, 2026-11-01):

    rules/        the strategy, written down. Never runs. Tells a concepter what to look for and how to trade it.
    concepters/   the active part (V5 engine, Kronos, Claude, GPT, Gemini …): reads the chart + the rules, draws the
                  concept on the chart, and commands the executor to open, move and close trades.
    executor/     carries the commands out (paper or MT5), behind fixed account safety limits.

Everything that crosses between them is one of the types below, and each one is plain JSON (to_dict / from_dict),
so it can be logged, replayed, sent to an LLM, or drawn by the dashboard. Change this file only with both
sides agreeing: every concepter and executor depends on it.

Prices are the broker's BID prices (MT5 bars are bid); times are UTC milliseconds.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional, Union

Side = Literal["buy", "sell"]
SIDES = ("buy", "sell")
TF_MS = {"M1": 60_000, "M5": 300_000, "M15": 900_000, "M30": 1_800_000, "H1": 3_600_000, "H4": 14_400_000,
         "D1": 86_400_000}


def _side(s: str) -> str:
    if s not in SIDES:
        raise ValueError(f"side must be buy or sell, not {s!r}")
    return s


@dataclass(frozen=True)
class Bar:
    t: int                      # bar OPEN time, UTC ms
    o: float
    h: float
    l: float
    c: float
    spread: float = 0.0         # in price units (ask = bid + spread)
    v: float = 0.0              # tick volume

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Mark:
    """One thing a concepter draws on the chart.
    kind: bos | choch | swing | zone | fvg | line | label | entry | sl | tp | forecast"""
    kind: str
    tf: str
    t0: int
    price: float                        # the level, or a zone's top
    t1: Optional[int] = None            # where the drawing ends (None = to the right edge)
    price2: Optional[float] = None      # a zone's bottom
    side: Optional[str] = None
    text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── commands: concepter → executor ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Open:
    concepter: str
    symbol: str
    side: str
    sl: float                           # required: no trade without a stop (the executor refuses one)
    tp: float
    order: str = "market"               # market | limit
    price: Optional[float] = None       # the limit price; for a market order the price the concepter expects
    lots: Optional[float] = None        # None → the executor's sizing (limits.toml)
    setup_id: str = ""                  # the concepter's name for the setup, so its later commands can refer to it
    reason: str = ""                    # which rule fired, in words (logged, shown on the chart)
    kind: str = field(default="open", init=False)

    def __post_init__(self):
        _side(self.side)
        if self.order not in ("market", "limit"):
            raise ValueError(f"order must be market or limit, not {self.order!r}")
        if self.order == "limit" and self.price is None:
            raise ValueError("a limit order needs a price")


@dataclass
class Modify:
    concepter: str
    ticket: int
    sl: Optional[float] = None          # None = leave as it is
    tp: Optional[float] = None
    reason: str = ""
    kind: str = field(default="modify", init=False)


@dataclass
class Close:
    concepter: str
    ticket: int
    reason: str = ""                    # e.g. "exit rule: CHoCH against the trade" — rules/<strategy>/trade.md
    kind: str = field(default="close", init=False)


Command = Union[Open, Modify, Close]
_COMMANDS = {"open": Open, "modify": Modify, "close": Close}


def command_to_dict(c: Command) -> Dict[str, Any]:
    return asdict(c)


def command_from_dict(d: Dict[str, Any]) -> Command:
    d = dict(d)
    cls = _COMMANDS.get(d.pop("kind", None))
    if cls is None:
        raise ValueError(f"unknown command kind in {d}")
    return cls(**d)


# ── what the executor reports back ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Position:
    ticket: int
    concepter: str                      # who owns it: only this concepter may modify or close it
    symbol: str
    side: str
    lots: float
    entry: float
    sl: float
    tp: float
    opened_t: int
    status: str = "open"                # pending (a limit not filled yet) | open
    setup_id: str = ""
    reason: str = ""
    sl0: float = 0.0                    # the stop at entry: 1R = |entry − sl0|

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Result:
    ok: bool
    command: Dict[str, Any]
    ticket: Optional[int] = None
    why: str = ""                       # the refusal, or what happened

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Trade:
    """A closed position."""
    ticket: int
    concepter: str
    symbol: str
    side: str
    lots: float
    entry: float
    exit: float
    opened_t: int
    closed_t: int
    pnl: float                          # account currency
    r: float                            # result in R (risk at entry)
    exit_reason: str                    # sl | tp | close: <the concepter's reason>
    setup_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── what a concepter sees and returns ───────────────────────────────────────────────────────────────────────────

@dataclass
class View:
    """The chart and the account as one concepter sees them at time `now` (only CLOSED bars, only its own positions)."""
    symbol: str
    now: int                                        # UTC ms: the close of the newest bar
    bars: Dict[str, List[Bar]]                      # timeframe → closed bars, oldest first
    positions: List[Position]                       # this concepter's open + pending positions on this symbol
    info: Dict[str, Any] = field(default_factory=dict)      # point, digits, contract size … (MT5 symbol info)
    account: Dict[str, float] = field(default_factory=dict)  # balance, equity

    def last(self, tf: str) -> Bar:
        return self.bars[tf][-1]


@dataclass
class Decision:
    marks: List[Mark] = field(default_factory=list)
    commands: List[Command] = field(default_factory=list)
    notes: str = ""                                 # why, in words (also: why nothing)

    def to_dict(self) -> Dict[str, Any]:
        return {"marks": [m.to_dict() for m in self.marks], "commands": [command_to_dict(c) for c in self.commands],
                "notes": self.notes}
