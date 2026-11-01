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
    signal_kinds = ["bos", "choch", "direction", "setup"]

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
        for s in [s for s in signals if s.kind == "bos"]:
            setup, why = self._setup(s, view, m, zs, a)
            if setup:
                signals.append(setup)
                marks += [Mark("zone", "M15", setup.data["zone_t0"], setup.data["top"], price2=setup.data["bottom"],
                               side=setup.side, text=f"Claude setup zone ({setup.data['zone_kind']})", engine="claude"),
                          Mark("tp", "M15", setup.t, setup.data["leg_extreme"], side=setup.side, text="leg extreme",
                               engine="claude")]
            elif why:
                notes.append(f"no setup for the {s.side} BOS at {s.level:g}: {why}")
        return Reading(signals=signals, marks=marks, notes=f"[{self.model}] " + "; ".join(notes))

    def _setup(self, bos: Signal, view: View, m: Dict, zs: List[Dict], a: Optional[float]) -> Tuple[Optional[Signal], str]:
        """rules/concept/claude [setup]: a BOS Claude reported → the supply / demand zone that started its move (the
        valid ORIGIN zone of that break, still fresh) → the leg's extreme once a pullback has confirmed it
        (setup.leg_confirm_bars closed bars without a new extreme). Reported on the bar the leg is confirmed."""
        bars: List[Bar] = view.bars["M15"]
        ms = TF_MS["M15"]
        t_break = bos.t - ms
        x = next((i for i in range(len(bars) - 1, -1, -1) if bars[i].t == t_break), None)
        if x is None:
            return None, ""
        if len(bars) - 1 - x > int(self.rules.p("setup.max_bos_age_bars", 48)):
            return None, ""                                       # too old to still be a setup: no note
        want = "demand" if bos.side == "buy" else "supply"
        roles = self.rules.p("setup.zone_roles", ["origin", "origin+last"])
        z = next((z for z in zs if z["side"] == want and z["t_break"] == t_break and z["role"] in roles), None)
        if z is None:
            return None, f"no valid {want} origin zone for this break"
        if z["status"] not in self.rules.p("setup.zone_status", ["fresh"]):
            return None, f"the zone is {z['status']}"
        later = [e for e in m["events"] if e["t"] > t_break and e["side"] != bos.side]
        if later:
            return None, f"a {later[0]['kind']} against it since"
        buy = bos.side == "buy"
        seg = bars[x:]
        j = max(range(len(seg)), key=lambda i: seg[i].h) if buy else min(range(len(seg)), key=lambda i: seg[i].l)
        k = int(self.rules.p("setup.leg_confirm_bars", 3))
        if len(seg) - 1 - j < k:
            return None, ""                                       # the leg is still running: wait, no note
        extreme = seg[j].h if buy else seg[j].l
        t_conf = seg[j + k].t + ms                               # the close of the bar that confirmed the leg
        entry = z["entry"]
        distal = z["bottom"] if buy else z["top"]
        proximal = z["top"] if buy else z["bottom"]
        risk = abs(entry - distal)
        data = {"entry": entry, "proximal": proximal, "distal": distal, "top": z["top"], "bottom": z["bottom"],
                "leg_extreme": extreme, "bos_level": bos.level, "origin": bos.get("origin"),
                "zone_kind": z["kind"], "zone_score": z["score"], "zone_t0": z["t0"], "t_break": t_break,
                "rr_to_extreme": round(abs(extreme - entry) / risk, 2) if risk else None,
                "atr": round(a, 6) if a else None}
        return Signal("claude", "setup", view.symbol, "M15", t_conf, bos.side, level=entry, data=data,
                      text=f"BOS {bos.side} {bos.level:g} → {want} {z['bottom']:g}-{z['top']:g} → leg {extreme:g}"), ""

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
        if kind not in ("bos", "choch", "direction"):            # a setup is never taken from the model: it is built
                                                                 # from a checked BOS by _setup()
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
