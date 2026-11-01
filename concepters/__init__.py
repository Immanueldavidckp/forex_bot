"""
concepters — the active part. Each one follows a strategy from rules/ and commands the executor.

    make("demo", rules)                       the plumbing demo (NOT a strategy)
    make("llm", rules, provider="gpt")        an LLM reading the chart + the rules (Claude / GPT / Gemini)

MAGIC: each concepter's MT5 magic number, so its trades on the broker are told apart from the others'.
"""
from __future__ import annotations

import importlib

MAGIC = {
    "v5": 5050505,        # the V5 engine (engine/), live on demo
    "kronos": 5050600,    # Kronos (engine/kronos_book.py), forecast-only now
    "claude": 5050700,    # new
    "gpt": 5050701,       # new (friend)
    "gemini": 5050702,    # new (friend)
    "demo": 5050999,      # the plumbing demo, paper only
}
# The magic 24102099 belongs to the mt5 MCP tools (Claude's hand trades), not to a concepter.

REGISTRY = {
    "demo": "concepters.demo.concepter:DemoConcepter",
    "llm": "concepters.llm.concepter:LLMConcepter",
}


def make(name: str, rules, **kw):
    mod, cls = REGISTRY[name].split(":")
    return getattr(importlib.import_module(mod), cls)(rules, **kw)
