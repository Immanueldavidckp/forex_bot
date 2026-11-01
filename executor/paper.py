"""
executor/paper.py — a pretend broker on recorded bars. No MT5 needed: this is what the friend's laptop and every
backtest use. Same commands, same guard as the real one.

Fills (bars are BID prices, ask = bid + the bar's spread):
  market     buy at the ask, sell at the bid, of the bar the command came on (its close)
  limit      filled when a later bar's ask (buy) / bid (sell) reaches the price
  SL / TP    a buy exits on the bid, a sell on the ask; when one bar touches both, the STOP counts (the safe guess)
No slippage and no swap: real results will be a little worse.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from shared.contracts import Bar, Close, Command, Modify, Open, Position, Result, Trade, command_to_dict

from .base import Executor, money_per_price
from .guard import Guard

DAY_MS = 86_400_000


class PaperExecutor(Executor):
    demo = True

    def __init__(self, infos: Dict[str, Dict], balance: float = 10_000.0, guard: Optional[Guard] = None):
        self.infos = infos
        self.balance = balance
        self.guard = guard or Guard()
        self.bar: Dict[str, Bar] = {}
        self.now = 0
        self.open: List[Position] = []
        self.closed: List[Trade] = []
        self.next_ticket = 1
        self.day = None
        self.day_start = balance

    # ── market data ─────────────────────────────────────────────────────────────────────────────────────────────
    def on_bar(self, symbol: str, bar: Bar, close_t: int) -> List[Trade]:
        """A bar of `symbol` has closed: fill limits, hit stops and targets. → the trades closed by it."""
        self.bar[symbol] = bar
        self.now = max(self.now, close_t)
        day = close_t // DAY_MS
        if day != self.day:
            self.day, self.day_start = day, self.balance + self._floating()
        done: List[Trade] = []
        for p in [p for p in self.open if p.symbol == symbol]:
            if p.status == "pending":
                touched = (bar.l + bar.spread <= p.entry) if p.side == "buy" else (bar.h >= p.entry)
                if not touched:
                    continue
                p.status, p.opened_t = "open", close_t
            hit_sl = (bar.l <= p.sl) if p.side == "buy" else (bar.h + bar.spread >= p.sl)
            hit_tp = bool(p.tp) and ((bar.h >= p.tp) if p.side == "buy" else (bar.l + bar.spread <= p.tp))
            if hit_sl:
                done.append(self._exit(p, p.sl, "sl"))
            elif hit_tp:
                done.append(self._exit(p, p.tp, "tp"))
        return done

    def quote(self, symbol: str) -> Tuple[float, float]:
        b = self.bar[symbol]
        return b.c, b.c + b.spread

    def info(self, symbol: str) -> Dict:
        return self.infos[symbol]

    # ── commands ────────────────────────────────────────────────────────────────────────────────────────────────
    def submit(self, cmd: Command) -> Result:
        why = self.guard.check(cmd, self)
        if why:
            return Result(False, command_to_dict(cmd), why=why)
        if isinstance(cmd, Open):
            bid, ask = self.quote(cmd.symbol)
            limit = cmd.order == "limit"
            entry = cmd.price if limit else (ask if cmd.side == "buy" else bid)
            p = Position(ticket=self.next_ticket, concepter=cmd.concepter, symbol=cmd.symbol, side=cmd.side,
                         lots=self.guard.lots_for(cmd), entry=entry, sl=cmd.sl, tp=cmd.tp, opened_t=self.now,
                         status="pending" if limit else "open", setup_id=cmd.setup_id, reason=cmd.reason, sl0=cmd.sl)
            self.next_ticket += 1
            self.open.append(p)
            return Result(True, command_to_dict(cmd), ticket=p.ticket, why=f"{p.status} at {entry:g}")
        p = next(p for p in self.open if p.ticket == cmd.ticket)
        if isinstance(cmd, Modify):
            if cmd.sl is not None:
                p.sl = cmd.sl
            if cmd.tp is not None:
                p.tp = cmd.tp
            return Result(True, command_to_dict(cmd), ticket=p.ticket, why=f"SL {p.sl:g} TP {p.tp:g}")
        if p.status == "pending":
            self.open.remove(p)
            return Result(True, command_to_dict(cmd), ticket=p.ticket, why="pending order cancelled")
        bid, ask = self.quote(p.symbol)
        t = self._exit(p, bid if p.side == "buy" else ask, f"close: {cmd.reason}")
        return Result(True, command_to_dict(cmd), ticket=p.ticket, why=f"closed at {t.exit:g}, {t.r:+.2f}R")

    # ── state ───────────────────────────────────────────────────────────────────────────────────────────────────
    def positions(self, concepter: Optional[str] = None, symbol: Optional[str] = None) -> List[Position]:
        return [p for p in self.open if (concepter is None or p.concepter == concepter)
                and (symbol is None or p.symbol == symbol)]

    def account(self) -> Dict[str, float]:
        eq = self.balance + self._floating()
        return {"balance": self.balance, "equity": eq, "day_start": self.day_start, "day_pnl": eq - self.day_start}

    def trades(self) -> List[Trade]:
        return list(self.closed)

    def _floating(self) -> float:
        tot = 0.0
        for p in self.open:
            if p.status != "open" or p.symbol not in self.bar:
                continue
            bid, ask = self.quote(p.symbol)
            px = bid if p.side == "buy" else ask
            tot += (px - p.entry) * (1 if p.side == "buy" else -1) * money_per_price(self.infos[p.symbol], p.lots)
        return tot

    def _exit(self, p: Position, price: float, why: str) -> Trade:
        sign = 1 if p.side == "buy" else -1
        pnl = (price - p.entry) * sign * money_per_price(self.infos[p.symbol], p.lots)
        risk = abs(p.entry - p.sl0) or 1e-12
        t = Trade(ticket=p.ticket, concepter=p.concepter, symbol=p.symbol, side=p.side, lots=p.lots, entry=p.entry,
                  exit=price, opened_t=p.opened_t, closed_t=self.now, pnl=round(pnl, 2),
                  r=round((price - p.entry) * sign / risk, 3), exit_reason=why, setup_id=p.setup_id)
        self.balance += pnl
        self.open.remove(p)
        self.closed.append(t)
        return t
