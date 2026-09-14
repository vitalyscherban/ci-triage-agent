"""Providers that turn an assembled triage prompt into a diagnosis.

Two implementations:

- :class:`MockProvider` - fully offline, deterministic, rule-based. Runs with
  zero network calls and no API key, which is what the test suite and the
  default CLI experience use.
- :class:`OpenAIProvider` - a real HTTP call to an OpenAI-compatible chat
  completions endpoint. Used when the caller has an API key configured; this
  is what makes the agent "real" beyond token accounting - it can actually
  ask a model to read the pruned failure + targeted code window and explain
  the bug.
"""

from __future__ import annotations

from .base import DiagnosisProvider, DiagnosisRequest
from .mock import MockProvider
from .openai_compatible import OpenAIProvider

__all__ = ["DiagnosisProvider", "DiagnosisRequest", "MockProvider", "OpenAIProvider"]
