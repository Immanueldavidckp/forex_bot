"""
concepters/llm/providers.py — the model behind an LLM concepter. A provider only turns (system, user) text into
the model's reply text; everything else (the prompt, the rules, checking the answer) is the concepter's job, so
any model plugs in the same way.

    get("fake")      scripted replies: tests and dry runs, no key, no cost
    get("gpt")       OpenAI       TODO (friend): OPENAI_API_KEY, model from LLM_MODEL
    get("gemini")    Google       TODO (friend): GEMINI_API_KEY, model from LLM_MODEL
    get("claude")    Anthropic    TODO (David)

API keys come from the environment (or a .env file that git ignores). NEVER put a key in a file that is committed.
"""
from __future__ import annotations

import json
from typing import Callable, List, Optional, Protocol, Union


class Provider(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str: ...


class FakeProvider:
    """Replies from a list (one per call, the last one repeats) or a function(system, user) -> str.
    With nothing given it always answers 'wait'."""
    name = "fake"

    def __init__(self, replies: Optional[Union[List[str], Callable[[str, str], str]]] = None):
        self.replies = replies if replies is not None else [json.dumps({"action": "wait", "reason": "fake provider"})]
        self.calls: List[dict] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        if callable(self.replies):
            return self.replies(system, user)
        return self.replies[min(len(self.calls), len(self.replies)) - 1]


def get(name: str, **kw) -> Provider:
    if name == "fake":
        return FakeProvider(**kw)
    if name in ("gpt", "openai", "gemini", "google", "claude", "anthropic"):
        raise NotImplementedError(
            f"provider {name!r} is not written yet: add a class with .name and .complete(system, user) -> str to "
            f"concepters/llm/providers.py and return it here (see CONTRIBUTING.md). Ask the model for JSON only.")
    raise ValueError(f"unknown provider {name!r}")
