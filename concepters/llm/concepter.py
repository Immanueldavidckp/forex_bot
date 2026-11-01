"""
concepters/llm — a concepter whose decisions come from a language model (Claude, GPT, Gemini). One class for all
of them: only the provider differs, so their results on the same rules can be compared fairly.

Each call the model gets:
    system   its job + the strategy's rules in words (rules/<strategy>/concept.md + trade.md) + the answer format
    user     a chart packet: price, ATR, David's structure (trend, the last BOS / CHoCH), the valid S&D zones nearest
             price (shared toolkit), the last bars, and its own open positions
LLMs read raw candles badly, so the packet gives them the toolkit's marks to reason over, plus a short tail of bars.

It answers ONE JSON object:
    {"action": "wait"}
    {"action": "open",   "side": "buy|sell", "order": "market|limit", "price": <limit price>, "sl": .., "tp": ..,
                         "reason": "<which rule fired>"}
    {"action": "modify", "ticket": .., "sl": .., "tp": .., "reason": ".."}
    {"action": "close",  "ticket": .., "reason": "<which exit rule fired>"}

The answer is checked against the strategy's numbers (concepters/checks.py) before it becomes a command. A broken
answer becomes "wait" with the reason in the notes. To save cost the model is only asked when price is near a live
zone or a position is open (ask="near_zone"), or on every bar (ask="every_bar").
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Dict, Optional

from shared import toolkit as TK
from shared.contracts import Close, Decision, Modify, Open, View

from ..base import Concepter
from ..checks import check_manage, check_open
from . import providers

ANSWER = """Answer with ONE JSON object and nothing else:
{"action": "wait", "reason": "..."}
{"action": "open", "side": "buy" or "sell", "order": "market" or "limit", "price": <limit price or null>, "sl": <price>, "tp": <price>, "reason": "<the rule that fired>"}
{"action": "modify", "ticket": <int>, "sl": <price or null>, "tp": <price or null>, "reason": "..."}
{"action": "close", "ticket": <int>, "reason": "<the exit rule that fired>"}"""

ROLE = """You are a trading concepter. You follow ONE strategy, written below, exactly as written.
- Open a trade only when EVERY condition of the concept and the entry is met. If anything is missing, wait.
- Stop loss and take profit come from the rules, never from your own judgement.
- Close a trade early only for an exit rule listed under "Exit when it goes wrong". Do not invent reasons.
- If a rule is unclear, wait and say what is unclear in the reason.
"""


class LLMConcepter(Concepter):
    timeframes = ["M15", "H1"]
    lookback = 500

    def __init__(self, rules, provider="fake", ask: str = "near_zone", tail_bars: int = 40, near_atr: float = 1.0,
                 **provider_kw):
        super().__init__(rules)
        self.provider = providers.get(provider, **provider_kw) if isinstance(provider, str) else provider
        self.name = getattr(self.provider, "name", "llm")
        self.ask, self.tail_bars, self.near_atr = ask, tail_bars, near_atr

    def system_prompt(self) -> str:
        return f"{ROLE}\n{self.rules.text()}\n{ANSWER}"

    def packet(self, view: View, m: Dict, zs, atr: Optional[float]) -> Dict:
        last = view.last("M15")
        iso = lambda t: datetime.fromtimestamp(t / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")
        return {
            "symbol": view.symbol, "now_utc": iso(view.now), "bid": last.c, "ask": round(last.c + last.spread, 10),
            "atr14_m15": atr,
            "structure_m15": {"trend": m["trend"],
                              "last_events": [{"kind": e["kind"], "side": e["side"], "level": e["level"],
                                               "at": iso(e["t"]), "move_start": e["origin"]["price"]}
                                              for e in m["events"][-3:]]},
            "live_zones_m15": [{k: z.get(k) for k in ("side", "top", "bottom", "entry", "status", "score", "event")}
                               | {"fvg": z.get("fvg"), "formed": iso(z["t0"])} for z in zs[:5]],
            "bars_m15": [[iso(b.t), b.o, b.h, b.l, b.c] for b in view.bars["M15"][-self.tail_bars:]],
            "bars_h1": [[iso(b.t), b.o, b.h, b.l, b.c] for b in view.bars.get("H1", [])[-20:]],
            "my_positions": [{"ticket": p.ticket, "side": p.side, "status": p.status, "entry": p.entry, "sl": p.sl,
                              "tp": p.tp, "opened": iso(p.opened_t), "reason": p.reason} for p in view.positions],
        }

    def on_bar(self, view: View) -> Decision:
        bars = view.bars["M15"]
        if len(bars) < 60:
            return Decision(notes="not enough bars")
        m = TK.structure(bars)
        zs = TK.zones(bars, m)
        atr = TK.atr(bars)
        d = Decision(marks=TK.marks_for("M15", m, zs[:5]))
        px = bars[-1].c
        near = atr and any(min(abs(px - z["top"]), abs(px - z["bottom"])) <= self.near_atr * atr
                           or z["bottom"] <= px <= z["top"] for z in zs)
        if self.ask == "near_zone" and not near and not view.positions:
            d.notes = "not asked: no live zone within reach and no position"
            return d
        user = json.dumps(self.packet(view, m, zs, atr), default=float)
        try:
            reply = self.provider.complete(self.system_prompt(), user)
        except Exception as e:                                     # a model / network failure is a wait, never a crash
            d.notes = f"provider failed: {e}"
            return d
        cmd, why = self.parse(reply, view)
        if cmd is not None:
            d.commands.append(cmd)
        d.notes = why
        return d

    def parse(self, reply: str, view: View):
        """The model's text → (command or None, notes)."""
        mt = re.search(r"\{.*\}", reply or "", re.S)
        try:
            a = json.loads(mt.group(0)) if mt else None
        except ValueError:
            a = None
        if not isinstance(a, dict):
            return None, f"unreadable answer, treated as wait: {reply[:200]!r}"
        act, reason = a.get("action"), str(a.get("reason") or "")
        try:
            if act == "wait":
                return None, f"wait: {reason}"
            if act == "open":
                c = Open(self.name, view.symbol, a["side"], sl=float(a["sl"]), tp=float(a["tp"]),
                         order=a.get("order") or "market",
                         price=float(a["price"]) if a.get("order") == "limit" and a.get("price") is not None else None,
                         reason=reason)
                bad = check_open(c, view, self.rules)
            elif act in ("modify", "close"):
                c = (Modify(self.name, int(a["ticket"]), sl=_f(a.get("sl")), tp=_f(a.get("tp")), reason=reason)
                     if act == "modify" else Close(self.name, int(a["ticket"]), reason=reason))
                bad = check_manage(c, view)
            else:
                return None, f"unknown action {act!r}, treated as wait"
        except (KeyError, TypeError, ValueError) as e:
            return None, f"answer missing or bad field ({e}), treated as wait: {a}"
        if bad:
            return None, f"refused ({'; '.join(bad)}): {a}"
        return c, f"{act}: {reason}"


def _f(x):
    return None if x is None else float(x)
