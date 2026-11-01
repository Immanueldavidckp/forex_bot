"""
concepter/conductor.py — carries out ONE strategy (rules/strategy/<name>/strategy.toml) with the engines it names.

On every closed bar of the strategy's timeframe, for one symbol:

  1. manage its open trades            [exit]  hold_bars · close_on (an engine reports a break AGAINST the trade) ·
                                                breakeven_at_r · flat_at_utc ;  [entry] expires_bars for a limit
  2. no trade on the symbol → ask the engines in the order of the [[need]] list. Each need = one engine's signal
     (kind, young enough, same side as the first need, min / max on its numbers). The first need that fails stops
     the round, so a later engine is not even asked: put the cheap engine first (Kronos) and the costly one last
     (Claude): Claude is then only asked when Kronos already agrees.
  3. all needs met → entry · stop · target from [entry] [stop] [target], which can point at any needed signal's
     numbers ("claude.bos.origin", "v5.setup.tp"); every number checked (stop side, max_atr, min_rr, spread) → Open
     → the executor (which still checks David's account limits).

The same signals never open a second trade. Nothing here is specific to an engine: a new strategy is a new
strategy.toml, not new code (the words in rules/strategy/README.md).
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from shared.contracts import TF_MS, Close, Decision, Modify, Open, Position, Reading, Signal, View
from shared.rules import REF, Strategy

from .base import Concepter
from .toolkit import atr as toolkit_atr

# view_for(symbol, now, timeframes, lookback) -> View: the runner (paper) or the live loop builds the chart
ViewFor = Callable[[str, int, List[str], int], View]


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


class Conductor:
    def __init__(self, strategy: Strategy, engines: Dict[str, Concepter], executor):
        if strategy.problems:
            raise ValueError(f"rules/strategy/{strategy.name} cannot run: " + "; ".join(strategy.problems))
        missing = strategy.engines - set(engines)
        if missing:
            raise ValueError(f"strategy {strategy.name} needs the engines {sorted(missing)}")
        self.s, self.engines, self.ex = strategy, engines, executor
        self.tf = strategy.timeframe
        self.used: Dict[str, set] = {}            # symbol → signal keys that already made a trade

    # ── one bar ─────────────────────────────────────────────────────────────────────────────────────────────────
    def step(self, symbol: str, now: int, view_for: Callable[[str, int, List[str], int], View]) -> Tuple[Decision, list]:
        """Decide, then send the commands to the executor. → (decision, results)"""
        d = self.on_bar(symbol, now, view_for)
        return d, [self.ex.submit(c) for c in d.commands]

    def on_bar(self, symbol: str, now: int, view_for: Callable[[str, int, List[str], int], View]) -> Decision:
        readings: Dict[str, Reading] = {}

        def read(engine: str) -> Reading:
            if engine not in readings:
                e = self.engines[engine]
                readings[engine] = e.on_bar(view_for(symbol, now, e.timeframes, e.lookback))
            return readings[engine]

        base = view_for(symbol, now, [self.tf], 200)
        bars = base.bars[self.tf]
        d = Decision()
        if len(bars) < 20:
            d.notes = "not enough bars"
            return d
        last = bars[-1]
        mine = self.ex.positions(owner=self.s.name, symbol=symbol)
        for p in mine:
            d.commands += self._manage(p, now, last, read)
        if not mine:
            self._enter(symbol, now, last, toolkit_atr(bars), read, d)
        for name, r in readings.items():
            d.marks += r.marks
            if r.notes:
                d.notes += f" | {name}: {r.notes}"
        return d

    # ── 1. managing ─────────────────────────────────────────────────────────────────────────────────────────────
    def _manage(self, p: Position, now: int, last, read) -> list:
        S, ms, name = self.s, TF_MS[self.tf], self.s.name
        if p.status == "pending":
            exp = S.p("entry.expires_bars")
            if exp and now - p.placed_t >= int(exp) * ms:
                return [Close(name, p.ticket, reason=f"limit not filled in {exp} bars")]
            return []
        hold = S.p("exit.hold_bars")
        if hold and now - p.opened_t >= int(hold) * ms:
            return [Close(name, p.ticket, reason=f"time exit: {hold} bars")]
        flat = S.p("exit.flat_at_utc")
        if flat:
            mod = (now // 60_000) % 1440
            if _minutes(flat) <= mod < _minutes(flat) + ms // 60_000:
                return [Close(name, p.ticket, reason=f"flat at {flat} UTC")]
        for ref in S.p("exit.close_on", []) or []:
            engine, kind = ref.split(".")
            against = [s for s in read(engine).signals if s.kind == kind and s.side != p.side and s.t == now
                       and s.t > p.opened_t]
            if against:
                return [Close(name, p.ticket, reason=f"{engine} {kind} {against[0].side} against the trade")]
        be = S.p("exit.breakeven_at_r")
        if be:
            risk = abs(p.entry - p.sl0)
            gain = (last.c - p.entry) if p.side == "buy" else (p.entry - (last.c + last.spread))
            not_yet = p.sl < p.entry if p.side == "buy" else p.sl > p.entry
            if risk and not_yet and gain >= float(be) * risk:
                return [Modify(name, p.ticket, sl=p.entry, reason=f"+{be}R: stop to break-even")]
        return []

    # ── 2 + 3. entering ─────────────────────────────────────────────────────────────────────────────────────────
    def _enter(self, symbol: str, now: int, last, a: Optional[float], read, d: Decision) -> None:
        S, ms = self.s, TF_MS[self.tf]
        mod = (now // 60_000) % 1440
        win = S.p("entry.no_entry_utc")
        if win and _minutes(win[0]) <= mod < _minutes(win[1]):
            d.notes = f"no entries {win[0]}–{win[1]} UTC"
            return
        fri = S.p("entry.friday_last_utc")
        weekday = (now // 86_400_000 + 3) % 7                  # Monday = 0 (1970-01-01 was a Thursday)
        if fri and weekday == 4 and mod >= _minutes(fri):
            d.notes = f"no entries on Friday after {fri} UTC"
            return
        picked: Dict[str, Signal] = {}
        side = None
        for i, n in enumerate(S.needs):
            engine, kind = n["engine"], n["signal"]
            age = int(n.get("max_age_bars", 1))
            cands = [s for s in read(engine).signals
                     if s.kind == kind and s.t <= now and now - s.t < age * ms + ms]
            if side and n.get("same_side", True):
                cands = [s for s in cands if s.side == side]
            for f, v in (n.get("min") or {}).items():
                cands = [s for s in cands if s.get(f) is not None and s.get(f) >= v]
            for f, v in (n.get("max") or {}).items():
                cands = [s for s in cands if s.get(f) is not None and s.get(f) <= v]
            if not cands:
                d.notes = f"need {i + 1} not met: {engine} {kind}" + (f" {side}" if side else "") + \
                          f" within {age} bars" + (f" with {n.get('min') or ''}{n.get('max') or ''}" if n.get("min") or n.get("max") else "")
                return
            s = max(cands, key=lambda x: x.t)
            picked[f"{engine}.{kind}"] = s
            side = side or s.side
            d.signals.append(s)
        keys = "+".join(sorted(s.key for s in picked.values()))
        if keys in self.used.setdefault(symbol, set()):
            d.notes = "these signals already made a trade"
            return

        def ref(path: str) -> Optional[float]:
            m = REF.match(path)
            v = picked[f"{m.group(1)}.{m.group(2)}"].get(m.group(3))
            return None if v is None else float(v)

        bid, ask = last.c, last.c + last.spread
        spread = last.spread
        limit = S.p("entry.type", "market") == "limit"
        entry = ref(S.p("entry.limit_at")) if limit else (ask if side == "buy" else bid)
        sign = 1 if side == "buy" else -1
        why = self._levels(side, sign, entry, a, spread, ref)
        if isinstance(why, str):
            d.notes = f"{side} refused: {why}"
            return
        sl, tp = why
        if limit and (side == "buy" and entry > ask or side == "sell" and entry < bid):
            d.notes = f"{side} limit {entry:g} is already through the price (bid {bid:g}): missed"
            return
        self.used[symbol].add(keys)
        d.commands.append(Open(S.name, symbol, side, sl=sl, tp=tp, order="limit" if limit else "market",
                               price=entry if limit else None, setup_id=keys,
                               reason="; ".join(f"{s.engine} {s.kind} {s.side}" + (f" ({s.text})" if s.text else "")
                                                for s in picked.values())))
        d.notes = f"{side}: entry {entry:g} SL {sl:g} TP {tp:g}"

    def _levels(self, side, sign, entry, a, spread, ref):
        S = self.s
        if S.p("stop.at"):
            sl = ref(S.p("stop.at"))
            if sl is None:
                return f"{S.p('stop.at')} has no value"
            if S.p("stop.buffer_atr"):
                if not a:
                    return "no ATR for the stop buffer"
                sl -= sign * float(S.p("stop.buffer_atr")) * a
            if S.p("stop.plus_spread"):
                sl -= sign * spread
        else:
            if not a:
                return "no ATR for the stop"
            sl = entry - sign * float(S.p("stop.atr")) * a
        risk = (entry - sl) * sign
        if risk <= 0:
            return f"stop {sl:g} is not {'below' if side == 'buy' else 'above'} the entry {entry:g}"
        if S.p("stop.max_atr") and a and risk > float(S.p("stop.max_atr")) * a:
            return f"stop {risk / a:.1f} ATR away (max {S.p('stop.max_atr')})"
        if S.p("stop.min_spread_x") and risk < float(S.p("stop.min_spread_x")) * spread:
            return f"stop {risk:g} < {S.p('stop.min_spread_x')} × spread {spread:g}"
        if S.p("stop.max_spread_frac") and spread > float(S.p("stop.max_spread_frac")) * risk:
            return f"spread {spread:g} > {S.p('stop.max_spread_frac')} × the stop distance {risk:g}"
        if S.p("target.at"):
            tp = ref(S.p("target.at"))
            if tp is None:
                return f"{S.p('target.at')} has no value (no target in reach)"
        elif S.p("target.rr"):
            tp = entry + sign * float(S.p("target.rr")) * risk
        else:
            if not a:
                return "no ATR for the target"
            tp = entry + sign * float(S.p("target.atr")) * a
        reward = (tp - entry) * sign
        if reward <= 0:
            return f"target {tp:g} is not {'above' if side == 'buy' else 'below'} the entry {entry:g}"
        if S.p("target.min_rr") and reward / risk < float(S.p("target.min_rr")) - 1e-9:
            return f"RR {reward / risk:.2f} < {S.p('target.min_rr')}"
        if S.p("target.min_spread_x") and spread and reward < float(S.p("target.min_spread_x")) * spread:
            return f"target only {reward / spread:.1f} spreads away (min {S.p('target.min_spread_x')})"
        return sl, tp
