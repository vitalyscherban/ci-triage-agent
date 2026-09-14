"""Provider protocol: turn a triage request into a diagnosis string."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DiagnosisRequest:
    """Everything a provider needs to diagnose one failing test.

    ``prompt_text`` is the full assembled prompt (cached prefix + repo
    conventions + pruned failure block + code window/compacted tool
    history) - what a real LLM provider actually sends. The other fields are
    the same information already parsed out, available to a rule-based
    offline provider that would rather not re-parse ``prompt_text``.
    """

    test_name: str
    path: str
    line: int
    exc_type: str
    exc_message: str
    code_context: str
    prompt_text: str


class DiagnosisProvider(Protocol):
    """Anything that can turn a diagnosis request into diagnosis text."""

    name: str

    def diagnose(self, request: DiagnosisRequest) -> str:
        """Return a diagnosis (root cause + suggested fix) for one failing test."""
        ...

