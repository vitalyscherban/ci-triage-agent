"""ci-triage-agent: a real CI test-failure triage agent.

Given a pytest-style CI log and a path to the repo it ran against, this
agent prunes the log to just the failures, resolves each failure's stack
frame, reads a small targeted window of real source around it, and asks a
(pluggable, optionally offline) model to diagnose the root cause - while
applying four token-efficiency techniques: pruning, targeted reads, prompt
prefix caching, and tool-output compaction.
"""

from __future__ import annotations

from .agent import TriageAgent, TriageReport
from .cache import CACHE_READ_DISCOUNT, PromptPrefixCache
from .providers import DiagnosisProvider, DiagnosisRequest, MockProvider, OpenAIProvider
from .tokens import TokenCounter

__all__ = [
    "CACHE_READ_DISCOUNT",
    "DiagnosisProvider",
    "DiagnosisRequest",
    "MockProvider",
    "OpenAIProvider",
    "PromptPrefixCache",
    "TokenCounter",
    "TriageAgent",
    "TriageReport",
]
