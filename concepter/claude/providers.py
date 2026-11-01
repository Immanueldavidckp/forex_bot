"""
concepter/claude/providers.py — the model behind the Claude engine. A provider only turns (system, user) text into
the model's reply; everything else (the prompt, the concept rules, checking the answer) is the engine's job, so any
model plugs in the same way and their answers can be compared on the same rules.

    get("toolkit")   NO model: reports the BOS / CHoCH exactly as David's structure rule finds them. The baseline
                     every model has to beat, and what paper runs use until a model is connected.
    get("fake")      scripted replies: tests, no key, no cost
    get("claude")    Anthropic    TODO (David)
    get("gpt")       OpenAI       TODO (friend): OPENAI_API_KEY, model from LLM_MODEL
    get("gemini")    Google       TODO (friend): GEMINI_API_KEY, model from LLM_MODEL

API keys come from the environment (or a .env file that git ignores). NEVER put a key in a committed file.
"""
from __future__ import annotations

import json
from typing import Callable, List, Optional, Protocol, Union


class Provider(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str: ...


class ToolkitProvider:
    """No model. Answers with the structure events the toolkit already put in the packet (structure_m15)."""
    name = "toolkit"

    def complete(self, system: str, user: str) -> str:
        pk = json.loads(user)
        out = [{"signal": e["kind"].lower(), "side": e["side"], "level": e["level"], "origin": e["move_start"],
                "at": e["at"], "reason": "David's structure rule (toolkit), no model"}
               for e in pk["structure_m15"]["last_events"]]
        trend = pk["structure_m15"]["trend"]
        if trend in ("up", "down"):
            out.append({"signal": "direction", "side": "buy" if trend == "up" else "sell",
                        "reason": f"major structure trend {trend}"})
        return json.dumps({"signals": out})


class FakeProvider:
    """Replies from a list (one per call, the last one repeats) or a function(system, user) -> str."""
    name = "fake"

    def __init__(self, replies: Optional[Union[List[str], Callable[[str, str], str]]] = None):
        self.replies = replies if replies is not None else [json.dumps({"signals": []})]
        self.calls: List[dict] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        if callable(self.replies):
            return self.replies(system, user)
        return self.replies[min(len(self.calls), len(self.replies)) - 1]


def get(name: str, **kw) -> Provider:
    if name == "toolkit":
        return ToolkitProvider()
    if name == "fake":
        return FakeProvider(**kw)
    if name in ("claude", "anthropic", "gpt", "openai", "gemini", "google"):
        raise NotImplementedError(
            f"provider {name!r} is not written yet: add a class with .name and .complete(system, user) -> str to "
            f"concepter/claude/providers.py and return it here (CONTRIBUTING.md). Ask the model for JSON only.")
    raise ValueError(f"unknown provider {name!r}")
