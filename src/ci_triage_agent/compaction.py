"""Compaction of the per-failure tool-call sequence within one triage run.

Mirrors the ``protected_recent`` idea used for chat-history compaction in
agentic loops generally, applied here to sequential file-read tool calls: by
the time the agent has moved on to diagnosing failure N, the raw file window
it read for failure N-1 is no longer needed at full fidelity - a 2-line
summary is enough to keep for audit/continuity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_LINE_RE = re.compile(r"^\s*(\d+):\s?(.*)$")


@dataclass
class ToolCallRecord:
    path: str
    line: int
    test_name: str
    raw_text: str
    summary: str = ""

    def __post_init__(self) -> None:
        if not self.summary:
            self.summary = summarize_tool_output(self.path, self.line, self.raw_text)


def summarize_tool_output(path: str, line: int, raw_text: str) -> str:
    """A deterministic, rule-based 2-line summary standing in for a raw
    read-window tool result once a newer tool call has superseded it."""
    matches = [m for m in (_LINE_RE.match(ln) for ln in raw_text.splitlines()) if m]
    if matches:
        start, end = int(matches[0].group(1)), int(matches[-1].group(1))
        count = len(matches)
        suspect = next((m.group(2).strip() for m in matches if int(m.group(1)) == line), "")
    else:
        start = end = line
        count = 0
        suspect = ""
    return (
        f"Read {path}:{start}-{end} ({count} lines around line {line}).\n"
        f"Suspect statement at {path}:{line}: {suspect[:100] or '<not captured>'}"
    )


def compact_tool_history(records: list[ToolCallRecord], protected_recent: int = 1) -> list[str]:
    """Return the sent/billed context for a sequence of tool calls: only the
    most recent ``protected_recent`` results stay at full fidelity, earlier
    ones collapse to their 2-line summary."""
    cutoff = len(records) - protected_recent
    return [r.raw_text if i >= cutoff else r.summary for i, r in enumerate(records)]
