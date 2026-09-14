"""Fully offline, deterministic diagnosis provider.

Produces a rule-based root-cause explanation from the exception type and the
suspect source line - no network, no API key, no randomness. This is the
default provider so the agent is runnable and testable with zero setup; it
also means the "ablation"/"no LLM configured" path still produces a genuinely
useful triage report instead of an empty one.
"""

from __future__ import annotations

from .base import DiagnosisRequest

_RULES: dict[str, tuple[str, str]] = {
    "ZeroDivisionError": (
        "a division whose denominator can be (or always is) zero",
        "guard the denominator - check it is non-zero before dividing, or "
        "restructure the formula so it can't reduce to zero",
    ),
    "KeyError": (
        "an unchecked dict lookup on a key that may legitimately be absent",
        "use `.get(key, default)` (or check `key in mapping` first) instead "
        "of indexing the dict directly",
    ),
    "IndexError": (
        "a sequence index computed from a loop counter that can run past "
        "the sequence's bounds",
        "clamp the index/length to the sequence's actual size before "
        "indexing, or stop the loop once the bound is reached",
    ),
    "AttributeError": (
        "a call/attribute access on a value that can be None or of an "
        "unexpected type",
        "add a type/None check before the access, or fix the code path that "
        "produces the wrong type",
    ),
    "TypeError": (
        "an operation applied to a value of an unexpected type",
        "validate/convert the input's type before the operation, or fix the "
        "caller that passes the wrong type",
    ),
    "AssertionError": (
        "a value produced by the code under test does not match what the "
        "test expects",
        "compare the actual and expected values in the assertion and trace "
        "back which one is wrong",
    ),
}

_DEFAULT_RULE = (
    "an exception raised by the code at the reported line",
    "inspect the code window above and trace the failing statement's inputs",
)


class MockProvider:
    """Deterministic, offline, rule-based diagnosis - no network calls."""

    name = "mock"

    def diagnose(self, request: DiagnosisRequest) -> str:
        root_cause, fix = _RULES.get(request.exc_type, _DEFAULT_RULE)
        suspect_line = _find_suspect_line(request.code_context, request.line)
        return (
            f"Test `{request.test_name}` fails with "
            f"{request.exc_type}: {request.exc_message or '(no message captured)'}.\n"
            f"Likely root cause: {root_cause}, at {request.path}:{request.line}"
            f"{f' (`{suspect_line}`)' if suspect_line else ''}.\n"
            f"Suggested fix: {fix}."
        )


def _find_suspect_line(code_context: str, line: int) -> str:
    prefix = f"{line:5d}: "
    for raw_line in code_context.splitlines():
        if raw_line.startswith(prefix):
            return raw_line[len(prefix) :].strip()
    return ""
