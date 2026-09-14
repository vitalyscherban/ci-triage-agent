"""Token counting with tiktoken when available, a deterministic heuristic
otherwise. Kept dependency-free by default so this agent runs and is testable
without any extra install; ``pip install ci-triage-agent[tiktoken]`` gets
exact provider-accurate counts.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache

# Per-message framing overhead charged by chat APIs (role, delimiters). Only
# relevant when counting a list of chat messages rather than raw text.
MESSAGE_OVERHEAD_TOKENS = 4

_WORD_RE = re.compile(r"\w+|[^\w\s]")


@lru_cache
def _tiktoken_encoder(model: str):
    try:
        import tiktoken
    except ImportError:  # pragma: no cover - exercised only without the extra
        return None
    try:
        return tiktoken.encoding_for_model(model)
    except Exception:
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:  # pragma: no cover
            return None


class TokenCounter:
    """Counts tokens with tiktoken when available, otherwise with a stable
    word-count heuristic. The heuristic keeps this agent runnable with zero
    extra dependencies; both paths produce the same *relative* savings."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model
        self._encoder = _tiktoken_encoder(model)

    @property
    def backend(self) -> str:
        return "tiktoken" if self._encoder else "heuristic"

    def count_text(self, text: str) -> int:
        if not text:
            return 0
        if self._encoder is not None:
            return len(self._encoder.encode(text))
        # ~1.3 tokens per word-or-punctuation-run, floored at 1 for non-empty text.
        return max(1, round(len(_WORD_RE.findall(text)) * 1.3))

    def count_messages(self, messages: Iterable[str]) -> int:
        return sum(MESSAGE_OVERHEAD_TOKENS + self.count_text(m) for m in messages)
