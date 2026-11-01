"""
shared/rules.py — load one strategy from rules/<name>/:

    concept.md    what the setup looks like on the chart (words: for David, his friend and the LLM concepters)
    trade.md      how to trade it: entry · stop loss · take profit · exit when it goes wrong
    params.toml   the same rules as numbers (for the code concepters); [strategy] name / version / status

Rules never run anything. A concepter loads them and follows them.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_DIR = os.path.join(ROOT, "rules")
FILES = ("concept.md", "trade.md", "params.toml")
TRADE_SECTIONS = ("## Entry", "## Stop loss", "## Take profit", "## Exit when it goes wrong")


@dataclass
class Rules:
    name: str
    folder: str
    concept: str
    trade: str
    params: Dict[str, Any]
    params_text: str = ""

    @property
    def version(self) -> str:
        return str(self.params.get("strategy", {}).get("version", "?"))

    def p(self, dotted: str, default: Any = None) -> Any:
        """params value by 'section.key' (e.g. rules.p('stops.min_rr'))."""
        cur: Any = self.params
        for k in dotted.split("."):
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    def text(self) -> str:
        """The written rules in one piece, words + numbers: what an LLM concepter is given. The words name their
        numbers as `section.key`, which are the keys of the params.toml below."""
        return (f"# Strategy: {self.name} (version {self.version})\n\n{self.concept.strip()}\n\n{self.trade.strip()}\n\n"
                f"# The numbers (params.toml; `section.key` in the text above = [section] key here)\n\n"
                f"```toml\n{self.params_text.strip()}\n```\n")


def available() -> List[str]:
    return sorted(d for d in os.listdir(RULES_DIR)
                  if not d.startswith(("_", ".")) and os.path.isdir(os.path.join(RULES_DIR, d)))


def load(name: str, rules_dir: str = RULES_DIR) -> Rules:
    folder = os.path.join(rules_dir, name)
    missing = [f for f in FILES if not os.path.isfile(os.path.join(folder, f))]
    if missing:
        raise FileNotFoundError(f"rules/{name} is missing {', '.join(missing)}")
    with open(os.path.join(folder, "concept.md")) as f:
        concept = f.read()
    with open(os.path.join(folder, "trade.md")) as f:
        trade = f.read()
    with open(os.path.join(folder, "params.toml")) as f:
        params_text = f.read()
    params = tomllib.loads(params_text)
    absent = [s for s in TRADE_SECTIONS if s not in trade]
    if absent:
        raise ValueError(f"rules/{name}/trade.md needs the sections {', '.join(absent)}")
    return Rules(name=name, folder=folder, concept=concept, trade=trade, params=params, params_text=params_text)
