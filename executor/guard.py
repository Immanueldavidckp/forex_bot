"""
executor/guard.py — David's account limits (executor/limits.toml), checked before EVERY command of EVERY strategy.
The guard never judges a setup. It only keeps the account safe and each strategy inside its own trades.

    Guard().check(cmd, executor) -> None (allowed) | "the reason it is refused"
"""
from __future__ import annotations

import os
import tomllib
from typing import Any, Dict, Optional

from shared.contracts import Close, Command, Modify, Open

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LIMITS_FILE = os.path.join(HERE, "limits.toml")


def load_limits(path: str = LIMITS_FILE) -> Dict[str, Any]:
    with open(path, "rb") as f:
        return tomllib.load(f)


class Guard:
    def __init__(self, limits: Optional[Dict[str, Any]] = None):
        self.L = limits or load_limits()

    def lim(self, dotted: str, default: Any = None) -> Any:
        cur: Any = self.L
        for k in dotted.split("."):
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    def halted(self) -> bool:
        hf = self.lim("account.halt_file")
        return bool(hf) and os.path.exists(hf if os.path.isabs(hf) else os.path.join(ROOT, hf))

    def lots_for(self, cmd: Open) -> float:
        lots = cmd.lots if cmd.lots is not None else float(self.lim("order.default_lots", 0.01))
        return min(lots, float(self.lim("order.max_lots", lots)))

    def check(self, cmd: Command, ex) -> Optional[str]:
        if isinstance(cmd, Open):
            return self._open(cmd, ex)
        if isinstance(cmd, (Modify, Close)):
            return self._owned(cmd, ex) or (self._modify(cmd, ex) if isinstance(cmd, Modify) else None)
        return f"unknown command {cmd!r}"

    # ── open ────────────────────────────────────────────────────────────────────────────────────────────────────
    def _open(self, c: Open, ex) -> Optional[str]:
        if self.halted():
            return "halted: the kill-switch file exists"
        if self.lim("account.demo_only", True) and not ex.demo:
            return "demo_only: this executor is on a real account"
        if self.lim("order.require_sl", True) and not c.sl:
            return "no stop loss"
        bid, ask = ex.quote(c.symbol)
        entry = c.price if c.order == "limit" else (ask if c.side == "buy" else bid)
        if c.side == "buy" and not (c.sl < entry):
            return f"buy needs SL below the entry (SL {c.sl}, entry {entry})"
        if c.side == "sell" and not (c.sl > entry):
            return f"sell needs SL above the entry (SL {c.sl}, entry {entry})"
        if c.tp and (c.side == "buy" and c.tp <= entry or c.side == "sell" and c.tp >= entry):
            return f"TP {c.tp} is on the wrong side of the entry {entry}"
        lots = self.lots_for(c)
        if lots <= 0:
            return "lot size 0"
        acc = ex.account()
        from .base import money_per_price
        risk = abs(entry - c.sl) * money_per_price(ex.info(c.symbol), lots)
        max_risk = float(self.lim("order.max_risk_pct", 0)) / 100 * acc["balance"]
        if max_risk and risk > max_risk:
            return f"risk {risk:.2f} > {self.lim('order.max_risk_pct')} % of the balance ({max_risk:.2f})"
        dl = float(self.lim("loss.daily_loss_limit_pct", 0))
        if dl and acc["day_pnl"] <= -dl / 100 * acc["day_start"]:
            return f"daily loss limit: {acc['day_pnl']:.2f} today (limit {dl} % of {acc['day_start']:.2f})"
        mine = ex.positions()
        mx = int(self.lim("positions.max_open", 0))
        if mx and len(mine) >= mx:
            return f"{len(mine)} positions open (limit {mx})"
        mpc = int(self.lim("positions.max_per_owner", 0))
        if mpc and len([p for p in mine if p.owner == c.owner]) >= mpc:
            return f"{c.owner} has {mpc} positions open (limit)"
        if self.lim("positions.block_opposite_same_symbol", True):
            other = [p for p in mine if p.symbol == c.symbol and p.side != c.side]
            if other:
                return f"{other[0].owner} holds a {other[0].side} on {c.symbol} (ticket {other[0].ticket})"
        return None

    # ── modify / close ──────────────────────────────────────────────────────────────────────────────────────────
    def _owned(self, c, ex) -> Optional[str]:
        p = next((p for p in ex.positions() if p.ticket == c.ticket), None)
        if p is None:
            return f"no open position {c.ticket}"
        if p.owner != c.owner:
            return f"position {c.ticket} belongs to {p.owner}, not {c.owner}"
        return None

    def _modify(self, c: Modify, ex) -> Optional[str]:
        p = next(p for p in ex.positions() if p.ticket == c.ticket)
        if c.sl is None:
            return None
        if self.lim("manage.stops_only_tighten", True) and p.status == "open":
            worse = c.sl < p.sl if p.side == "buy" else c.sl > p.sl
            if worse:
                return f"stops only move toward profit (SL {p.sl} → {c.sl})"
        bid, ask = ex.quote(p.symbol)
        if p.status == "open" and (p.side == "buy" and c.sl >= bid or p.side == "sell" and c.sl <= ask):
            return f"new SL {c.sl} is past the current price (bid {bid}, ask {ask}): close the trade instead"
        return None
