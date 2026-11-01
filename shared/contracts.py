"""
shared/contracts.py — the language the parts speak (David's layout, 2026-11-01):

    marketdata/     prices (MT5 live, or recorded bars for paper runs)
    concepter/      the engines: v5 · kronos · claude. Each one reads the chart by its concept rules
                    (rules/concept/<engine>/) and REPORTS what it sees as Signals: a direction, a BOS, a setup …
                    It also draws what it sees (Marks).
    rules/strategy/ one recipe, common to all engines: which engine gives which signal ("direction from Kronos,
                    BOS from Claude"), and how that becomes entry · stop loss · take profit · exit.
                    concepter/conductor.py carries a recipe out and sends the trade to the executor.
    executor/       places and manages the orders, behind David's account limits.

Everything that crosses between them is one of the types below, and each one is plain JSON, so it can be logged,
replayed, sent to an LLM, or drawn by the dashboard. Change this file only with everyone agreeing.

Prices are the broker's BID prices (MT5 bars are bid); times are UTC milliseconds.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Union

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


# ── what an engine (concepter) reports ──────────────────────────────────────────────────────────────────────────

@dataclass
class Signal:
    """One thing an engine sees on the chart, by its concept rules.

    kind      direction (where price goes next) · bos · choch (a close beyond structure) · setup (a complete trade
              idea: zone + FVG + entry / sl / tp) · zone
    t         when it became true: the CLOSE time of the bar that made it (UTC ms)
    level     the price it is about: the broken level, the zone edge, the entry
    data      everything else, named, so a strategy can point at it as "<engine>.<kind>.<name>":
              origin (where the breaking move started) · top / bottom · entry / sl / tp · p (probability) · …"""
    engine: str
    kind: str
    symbol: str
    tf: str
    t: int
    side: str
    level: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)
    text: str = ""

    def __post_init__(self):
        _side(self.side)

    def get(self, name: str) -> Any:
        return self.level if name == "level" else self.data.get(name)

    @property
    def key(self) -> str:
        return f"{self.engine}.{self.kind}.{self.side}.{self.t}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Mark:
    """One thing to draw on the chart.
    kind: bos | choch | swing | zone | fvg | line | label | entry | sl | tp | forecast"""
    kind: str
    tf: str
    t0: int
    price: float                        # the level, or a zone's top
    t1: Optional[int] = None            # where the drawing ends (None = to the right edge)
    price2: Optional[float] = None      # a zone's bottom
    side: Optional[str] = None
    text: str = ""
    engine: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Reading:
    """What one engine returns for one bar: what it sees (signals), what to draw (marks), and why (notes)."""
    signals: List[Signal] = field(default_factory=list)
    marks: List[Mark] = field(default_factory=list)
    notes: str = ""


# ── commands: conductor → executor ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Open:
    owner: str                          # the strategy that places it (rules/strategy/<name>): it owns the trade
    symbol: str
    side: str
    sl: float                           # required: no trade without a stop (the executor refuses one)
    tp: float
    order: str = "market"               # market | limit
    price: Optional[float] = None       # the limit price
    lots: Optional[float] = None        # None → the executor's sizing (limits.toml)
    setup_id: str = ""                  # the signals it came from
    reason: str = ""                    # which engines said what, in words
    kind: str = field(default="open", init=False)

    def __post_init__(self):
        _side(self.side)
        if self.order not in ("market", "limit"):
            raise ValueError(f"order must be market or limit, not {self.order!r}")
        if self.order == "limit" and self.price is None:
            raise ValueError("a limit order needs a price")


@dataclass
class Modify:
    owner: str
    ticket: int
    sl: Optional[float] = None          # None = leave as it is
    tp: Optional[float] = None
    reason: str = ""
    kind: str = field(default="modify", init=False)


@dataclass
class Close:
    owner: str
    ticket: int
    reason: str = ""                    # the exit rule that fired (rules/strategy/<name> [exit])
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
    owner: str                          # only this strategy may modify or close it
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
    placed_t: int = 0                   # when the order was sent (a limit's expiry counts from here)

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
    owner: str
    symbol: str
    side: str
    lots: float
    entry: float
    exit: float
    opened_t: int
    closed_t: int
    pnl: float                          # account currency
    r: float                            # result in R (risk at entry)
    exit_reason: str                    # sl | tp | close: <the strategy's reason>
    setup_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── what an engine sees ─────────────────────────────────────────────────────────────────────────────────────────

@dataclass
class View:
    """The chart as an engine sees it at time `now`: only CLOSED bars."""
    symbol: str
    now: int                                        # UTC ms: the close of the newest bar
    bars: Dict[str, List[Bar]]                      # timeframe → closed bars, oldest first
    info: Dict[str, Any] = field(default_factory=dict)      # point, digits, contract size … (MT5 symbol info)

    def last(self, tf: str) -> Bar:
        return self.bars[tf][-1]


@dataclass
class Decision:
    """What the conductor did on one bar of one symbol."""
    commands: List[Command] = field(default_factory=list)
    signals: List[Signal] = field(default_factory=list)     # the signals the strategy used / looked at
    marks: List[Mark] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"commands": [command_to_dict(c) for c in self.commands], "signals": [s.to_dict() for s in self.signals],
                "marks": [m.to_dict() for m in self.marks], "notes": self.notes}
