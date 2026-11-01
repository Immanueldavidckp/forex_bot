"""
concepters/checks.py — does a command follow the STRATEGY's rules? (The executor's guard only checks the account
limits.) Every concepter should run its commands through these, and an LLM concepter must: a model's answer is a
proposal until the numbers agree with rules/<strategy>/params.toml.
"""
from __future__ import annotations

from typing import List

from shared.contracts import Close, Modify, Open, View
from shared.rules import Rules


def check_open(c: Open, view: View, rules: Rules) -> List[str]:
    bar = view.last(view_tf(view))
    bid, ask = bar.c, bar.c + bar.spread
    entry = c.price if c.order == "limit" else (ask if c.side == "buy" else bid)
    problems = []
    if c.side == "buy" and not (c.sl < entry < c.tp):
        problems.append(f"a buy needs SL < entry < TP (SL {c.sl}, entry {entry}, TP {c.tp})")
    if c.side == "sell" and not (c.tp < entry < c.sl):
        problems.append(f"a sell needs TP < entry < SL (TP {c.tp}, entry {entry}, SL {c.sl})")
    if c.order == "limit" and (c.side == "buy" and c.price > ask or c.side == "sell" and c.price < bid):
        problems.append(f"a {c.side} limit at {c.price} is on the wrong side of the price (bid {bid}, ask {ask})")
    risk = abs(entry - c.sl)
    min_rr = rules.p("stops.min_rr")
    if risk and min_rr is not None and not problems:
        rr = abs(c.tp - entry) / risk
        if rr < float(min_rr) - 1e-9:
            problems.append(f"RR {rr:.2f} < the strategy's min_rr {min_rr}")
    if any(p.symbol == c.symbol and p.side != c.side for p in view.positions):
        problems.append(f"already holds the other side on {c.symbol}")
    if not c.reason:
        problems.append("no reason: say which rule fired")
    return problems


def check_manage(c, view: View) -> List[str]:
    if isinstance(c, (Modify, Close)) and not any(p.ticket == c.ticket for p in view.positions):
        return [f"ticket {c.ticket} is not one of this concepter's positions on {view.symbol}"]
    if isinstance(c, Close) and not c.reason:
        return ["a close needs the exit rule that fired"]
    return []


def view_tf(view: View) -> str:
    """The timeframe the view was built on (its first one)."""
    return next(iter(view.bars))
