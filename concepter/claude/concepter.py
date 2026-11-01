"""
concepter/claude — an engine whose eyes are a language model (Claude; GPT and Gemini plug in the same way),
following rules/concept/claude. It REPORTS what it sees; it never trades.

Each call the model gets:
    system   its job + the concept rules in words and numbers (rules/concept/claude) + the answer format
    user     a chart packet: price, ATR, David's structure from the toolkit (trend, the last BOS / CHoCH with their
             levels and move starts), the live S&D zones nearest price, and the last bars
LLMs read raw candles badly, so the packet hands them the toolkit's structure to judge, plus a short tail of bars.

It answers {"signals": [ ... ]} with any of:
    {"signal": "bos" | "choch", "side": "buy|sell", "level": <the broken price>, "origin": <where the move started>,
     "at": "YYYY-MM-DD HH:MM" (the break candle), "reason": "..."}
    {"signal": "direction", "side": "buy|sell", "reason": "..."}

Every signal is CHECKED against the bars before it counts: a BOS / CHoCH needs a candle that really closed beyond
its level (buy: above, sell: below) in the last `max_age_bars` bars, and the move's start on the right side. A
signal that fails, or an unreadable answer, is dropped and the reason goes in the notes.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from shared.contracts import TF_MS, Bar, Mark, Reading, Signal, View

from .. import toolkit as TK
from ..base import Concepter
from . import providers

ANSWER = """Answer with ONE JSON object and nothing else:
{"signals": [
  {"signal": "bos" or "choch", "side": "buy" or "sell", "level": <price>, "origin": <price>, "at": "YYYY-MM-DD HH:MM", "reason": "..."},
  {"signal": "direction", "side": "buy" or "sell", "reason": "..."}
]}
Report only what the concept rules define. No signal → {"signals": []}."""

ROLE = """You are a chart-reading engine. You do NOT trade. You report what you see on the chart, using ONLY the
concept rules below, exactly as written. If a rule's condition is not clearly met, do not report that signal.
"""


def _iso(t: int) -> str:
    return datetime.fromtimestamp(t / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M")


class ClaudeConcepter(Concepter):
    timeframes = ["M15", "H1"]
    lookback = 500
    signal_kinds = ["bos", "choch", "direction"]

    def __init__(self, rules, provider="toolkit", **provider_kw):
        super().__init__(rules)
        self.provider = providers.get(provider, **provider_kw) if isinstance(provider, str) else provider
        self.name = "claude"
        self.model = getattr(self.provider, "name", "?")

    def system_prompt(self) -> str:
        return f"{ROLE}\n{self.rules.text()}\n{ANSWER}"

    def packet(self, view: View, m: Dict, zs: List[Dict], a: Optional[float]) -> Dict:
        bars = view.bars["M15"]
        last = bars[-1]
        tail = int(self.rules.p("packet.tail_bars", 40))
        return {
            "symbol": view.symbol, "now_utc": _iso(view.now), "bid": last.c, "ask": round(last.c + last.spread, 10),
            "atr14_m15": a,
            "structure_m15": {"trend": m["trend"],
                              "last_events": [{"kind": e["kind"], "side": e["side"], "level": e["level"],
                                               "at": _iso(e["t"]), "move_start": e["origin"]["price"]}
                                              for e in m["events"][-int(self.rules.p("packet.events", 3)):]]},
            "live_zones_m15": [{k: z.get(k) for k in ("side", "top", "bottom", "status", "score")} for z in zs[:5]],
            "bars_m15": [[_iso(b.t), b.o, b.h, b.l, b.c] for b in bars[-tail:]],
            "bars_h1": [[_iso(b.t), b.o, b.h, b.l, b.c] for b in view.bars.get("H1", [])[-20:]],
        }

    def on_bar(self, view: View) -> Reading:
        bars = view.bars["M15"]
        if len(bars) < 60:
            return Reading(notes="not enough bars")
        m = TK.structure(bars)
        zs = TK.zones(bars, m)
        a = TK.atr(bars)
        marks = TK.marks_for("claude", "M15", m, zs[:5])
        try:
            reply = self.provider.complete(self.system_prompt(), json.dumps(self.packet(view, m, zs, a), default=float))
        except Exception as e:                                  # a model / network failure: no signals, never a crash
            return Reading(marks=marks, notes=f"provider {self.model} failed: {e}")
        signals, notes = self.parse(reply, view)
        return Reading(signals=signals, marks=marks, notes=f"[{self.model}] " + "; ".join(notes))

    def parse(self, reply: str, view: View) -> Tuple[List[Signal], List[str]]:
        mt = re.search(r"\{.*\}", reply or "", re.S)
        try:
            a = json.loads(mt.group(0)) if mt else None
        except ValueError:
            a = None
        if not isinstance(a, dict) or not isinstance(a.get("signals"), list):
            return [], [f"unreadable answer: {str(reply)[:200]!r}"]
        out, notes = [], []
        for s in a["signals"]:
            try:
                sig, why = self._check(s, view)
            except (KeyError, TypeError, ValueError) as e:
                sig, why = None, f"bad field {e}"
            if sig:
                out.append(sig)
                notes.append(f"{sig.kind} {sig.side}")
            else:
                notes.append(f"dropped {s}: {why}")
        return out, notes

    def _check(self, s: Dict, view: View) -> Tuple[Optional[Signal], str]:
        kind, side = s.get("signal"), s.get("side")
        if kind not in self.signal_kinds:
            return None, f"unknown signal {kind!r}"
        if side not in ("buy", "sell"):
            return None, f"side {side!r}"
        bars: List[Bar] = view.bars["M15"]
        ms = TF_MS["M15"]
        if kind == "direction":
            return Signal("claude", "direction", view.symbol, "M15", view.now, side, level=bars[-1].c,
                          data={"model": self.model}, text=str(s.get("reason", ""))), ""
        level = float(s["level"])
        origin = float(s["origin"]) if s.get("origin") is not None else None
        if origin is not None and (origin >= level if side == "buy" else origin <= level):
            return None, f"move start {origin} is on the wrong side of the level {level}"
        recent = bars[-int(self.rules.p("check.max_age_bars", 40)):]
        after = 0
        if s.get("at"):
            t_at = int(datetime.strptime(s["at"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp() * 1000)
            after = t_at
        brk = next((b for b in recent if b.t >= after and (b.c > level if side == "buy" else b.c < level)), None)
        if brk is None:
            return None, f"no candle closed {'above' if side == 'buy' else 'below'} {level} in the last {len(recent)} bars"
        return Signal("claude", kind, view.symbol, "M15", brk.t + ms, side, level=level,
                      data={"origin": origin, "close": brk.c, "model": self.model},
                      text=str(s.get("reason", ""))), ""
