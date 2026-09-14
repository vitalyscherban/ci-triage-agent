"""Prompt-prefix caching: a repeated *prefix* (system prompt + repo
conventions) with a *varying* suffix (this run's log/trace/tool output).

This mirrors real provider-side prompt-prefix caching (Anthropic's
``cache_control`` blocks, OpenAI's automatic prefix caching): a cache "hit"
still bills a discounted fraction of the prefix, every time - it does not
zero out the cost like an exact-match full-response cache, because the
model still runs and the suffix always differs.

State is persisted to a small JSON file on disk so that running this agent
twice as two separate CI jobs - the realistic case - actually observes a
warm cache on the second run, not just within one process.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Real per-provider prompt caching discounts the token *cost* of a repeated
# prefix on a hit; it is not free. This constant documents that discount.
CACHE_READ_DISCOUNT = 0.1


@dataclass
class PromptPrefixCache:
    state_path: Path | None = None
    _warm_keys: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.state_path and self.state_path.exists():
            try:
                self._warm_keys = set(json.loads(self.state_path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                self._warm_keys = set()

    def charge(self, prefix_key: str, prefix_tokens: int) -> tuple[int, bool]:
        """Bill ``prefix_tokens`` for a prefix identified by ``prefix_key``.

        Returns ``(billed_tokens, was_warm)``. The first call for a given key
        is billed at full price (a cache write); every later call for the
        same key is billed at :data:`CACHE_READ_DISCOUNT` of the full price.
        """
        warm = prefix_key in self._warm_keys
        self._warm_keys.add(prefix_key)
        self._save()
        billed = round(prefix_tokens * CACHE_READ_DISCOUNT) if warm else prefix_tokens
        return billed, warm

    def _save(self) -> None:
        if self.state_path:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps(sorted(self._warm_keys)), encoding="utf-8")

    def clear(self) -> None:
        self._warm_keys.clear()
        if self.state_path and self.state_path.exists():
            self.state_path.unlink()
