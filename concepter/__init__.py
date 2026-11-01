"""
concepter — the engines (v5 · kronos · claude) and the conductor that runs a strategy with them.

    engine("kronos")                          → the Kronos engine with rules/concept/kronos
    engine("claude", provider="toolkit")      → the Claude engine (provider: toolkit | fake | claude | gpt | gemini)

Light on purpose: importing this package must not load numpy-heavy or GPU code (the Kronos forecaster runs as
`python -m concepter.kronos.signals` in its own venv and imports this package first).
"""
from __future__ import annotations

import importlib

ENGINES = {
    "v5": "concepter.v5.concepter:V5Concepter",
    "kronos": "concepter.kronos.concepter:KronosConcepter",
    "claude": "concepter.claude.concepter:ClaudeConcepter",
}


def engine(name: str, **kw):
    from shared import rules as R
    mod, cls = ENGINES[name].split(":")
    return getattr(importlib.import_module(mod), cls)(R.concept(name), **kw)
