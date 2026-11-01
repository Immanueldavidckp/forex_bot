"""
shared/rules.py — read the rules. Rules never run anything; the concepters and the conductor follow them.

    rules/concept/<engine>/     what ONE engine looks for on the chart
        concept.md                in words (David, the friend, and the Claude engine read this)
        params.toml               the same as numbers (the code engines read this)

    rules/strategy/<name>/      one recipe, common to all engines
        strategy.md               in words: which engine gives what · entry · stop loss · take profit · exit
        strategy.toml             the same, in the form concepter/conductor.py carries out (rules/strategy/README.md)

    concept("kronos") → ConceptRules          strategy("kronos_direction_claude_bos") → Strategy
"""
from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_DIR = os.path.join(ROOT, "rules")
CONCEPT_DIR = os.path.join(RULES_DIR, "concept")
STRATEGY_DIR = os.path.join(RULES_DIR, "strategy")
STRATEGY_SECTIONS = ("## Which engine gives what", "## Entry", "## Stop loss", "## Take profit",
                     "## Exit when it goes wrong")
REF = re.compile(r"^([a-z0-9_]+)\.([a-z0-9_]+)\.([a-z0-9_]+)$")        # engine.signal.field


def _get(d: Dict[str, Any], dotted: str, default: Any = None) -> Any:
    cur: Any = d
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _read(path: str) -> str:
    with open(path) as f:
        return f.read()


# ── concept rules: one per engine ───────────────────────────────────────────────────────────────────────────────

@dataclass
class ConceptRules:
    engine: str
    folder: str
    concept: str
    params: Dict[str, Any]
    params_text: str = ""

    @property
    def version(self) -> str:
        return str(_get(self.params, "concept.version", "?"))

    def p(self, dotted: str, default: Any = None) -> Any:
        return _get(self.params, dotted, default)

    def text(self) -> str:
        """Words + numbers in one piece: what an LLM engine is given."""
        return (f"# Concept rules: {self.engine} (version {self.version})\n\n{self.concept.strip()}\n\n"
                f"# The numbers (params.toml; `section.key` in the text above = [section] key here)\n\n"
                f"```toml\n{self.params_text.strip()}\n```\n")


def engines() -> List[str]:
    return sorted(d for d in os.listdir(CONCEPT_DIR) if os.path.isdir(os.path.join(CONCEPT_DIR, d))
                  and not d.startswith(("_", ".")))


def concept(engine: str) -> ConceptRules:
    folder = os.path.join(CONCEPT_DIR, engine)
    for f in ("concept.md", "params.toml"):
        if not os.path.isfile(os.path.join(folder, f)):
            raise FileNotFoundError(f"rules/concept/{engine}/{f} is missing")
    text = _read(os.path.join(folder, "params.toml"))
    return ConceptRules(engine, folder, _read(os.path.join(folder, "concept.md")), tomllib.loads(text), text)


# ── strategies: common to all engines ───────────────────────────────────────────────────────────────────────────

@dataclass
class Strategy:
    name: str
    folder: str
    words: str
    spec: Dict[str, Any]
    spec_text: str = ""
    problems: List[str] = field(default_factory=list)

    def p(self, dotted: str, default: Any = None) -> Any:
        return _get(self.spec, dotted, default)

    @property
    def version(self) -> str:
        return str(self.p("strategy.version", "?"))

    @property
    def timeframe(self) -> str:
        return self.p("strategy.timeframe", "M15")

    @property
    def needs(self) -> List[Dict[str, Any]]:
        return list(self.spec.get("need", []))

    @property
    def engines(self) -> Set[str]:
        """Every engine this strategy asks: the needs + the exit rules."""
        out = {n["engine"] for n in self.needs}
        for c in (self.p("exit.close_on", []) or []) + (self.p("entry.cancel_on", []) or []):
            out.add(c.split(".")[0])
        return out

    def check(self, known: List[str]) -> List[str]:
        """Everything that would stop the conductor from carrying this strategy out."""
        bad = []
        if not self.needs:
            bad.append("no [[need]]: which engine gives what?")
        have = set()
        for i, n in enumerate(self.needs):
            if n.get("engine") not in known:
                bad.append(f"need {i + 1}: engine {n.get('engine')!r} has no rules/concept folder ({known})")
            if not n.get("signal"):
                bad.append(f"need {i + 1}: no signal kind")
            have.add(f"{n.get('engine')}.{n.get('signal')}")
        refs = [self.p("entry.limit_at"), self.p("stop.at"), self.p("target.at")]
        for r in filter(None, refs):
            m = REF.match(r)
            if not m:
                bad.append(f"{r!r} is not engine.signal.field")
            elif f"{m.group(1)}.{m.group(2)}" not in have:
                bad.append(f"{r!r} points at {m.group(1)}.{m.group(2)}, which no [[need]] asks for")
        if self.p("entry.type", "market") not in ("market", "limit"):
            bad.append("entry.type must be market or limit")
        if self.p("entry.type") == "limit" and not self.p("entry.limit_at"):
            bad.append("a limit entry needs entry.limit_at")
        if not (self.p("stop.at") or self.p("stop.atr")):
            bad.append("[stop] needs at = engine.signal.field or atr = k")
        if not (self.p("target.at") or self.p("target.rr") or self.p("target.atr")):
            bad.append("[target] needs at, rr or atr")
        for key in ("exit.close_on", "entry.cancel_on"):
            for c in self.p(key, []) or []:
                if len(c.split(".")) != 2 or c.split(".")[0] not in known:
                    bad.append(f"{key} {c!r} must be engine.signal")
        return bad


def strategies() -> List[str]:
    return sorted(d for d in os.listdir(STRATEGY_DIR) if os.path.isdir(os.path.join(STRATEGY_DIR, d))
                  and not d.startswith(("_", ".")))


def strategy(name: str) -> Strategy:
    folder = os.path.join(STRATEGY_DIR, name)
    for f in ("strategy.md", "strategy.toml"):
        if not os.path.isfile(os.path.join(folder, f)):
            raise FileNotFoundError(f"rules/strategy/{name}/{f} is missing")
    words = _read(os.path.join(folder, "strategy.md"))
    text = _read(os.path.join(folder, "strategy.toml"))
    s = Strategy(name, folder, words, tomllib.loads(text), text)
    s.problems = [f"strategy.md needs the section {h!r}" for h in STRATEGY_SECTIONS if h not in words]
    s.problems += s.check(engines())
    return s
