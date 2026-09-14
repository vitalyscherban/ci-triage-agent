"""Parsing for real pytest-style CI logs.

Handles the two things a real log actually needs from a triage agent:

1. Pruning the FAILURES + short-summary sections out of a (possibly huge)
   log, discarding PASSED/collection noise.
2. Resolving each failing test to a ``(path, line, test_name)`` stack frame
   from pytest's ``path/to/file.py:LINE: ExceptionType`` location-echo line,
   which pytest emits at the end of every failure block in both its default
   ("long") and ``--tb=short`` traceback styles.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_FAILURES_HEADER_RE = re.compile(r"^=+\s*FAILURES\s*=+\s*$", re.MULTILINE)
_SUMMARY_HEADER_RE = re.compile(r"^=+\s*short test summary info\s*=+\s*$", re.MULTILINE)
_SUB_HEADER_RE = re.compile(r"^_{5,} (.+?) _{5,}$", re.MULTILINE)
# Matches pytest's location-echo line, e.g. "toyshop\inventory.py:29: KeyError"
# or "toyshop/inventory.py:29: KeyError". Anchored at line start/end so it
# doesn't accidentally match a path mentioned mid-sentence in a docstring.
_LOCATION_RE = re.compile(r"^([\w./\\-]+\.py):(\d+): ?(\w+)?\s*$", re.MULTILINE)
# Matches pytest's "E   ExceptionType: message" summary line inside a block.
_EXC_MESSAGE_RE = re.compile(r"^E\s+(\w+): ?(.*)$", re.MULTILINE)


@dataclass(frozen=True)
class StackFrame:
    path: str
    line: int
    test_name: str
    exc_type: str = ""
    exc_message: str = ""


def extract_failure_blocks(log: str) -> list[str]:
    """Prune a pytest log down to the FAILURES sub-blocks (one per failing
    test) followed by the short test summary section, discarding the
    (potentially many thousands of) PASSED/collection lines in between.

    Returns a list whose first N entries are individual per-test failure
    blocks and whose final entry is the short test summary section. If the
    log has no FAILURES section (nothing failed, or it's not a pytest log),
    returns ``[log]`` unchanged so callers always have something to send.
    """
    failures_match = _FAILURES_HEADER_RE.search(log)
    summary_match = _SUMMARY_HEADER_RE.search(log)
    if not failures_match or not summary_match:
        return [log]

    failures_section = log[failures_match.end() : summary_match.start()]
    summary_section = log[summary_match.start() :].rstrip("\n")

    sub_headers = list(_SUB_HEADER_RE.finditer(failures_section))
    blocks: list[str] = []
    for i, header in enumerate(sub_headers):
        start = header.start()
        end = sub_headers[i + 1].start() if i + 1 < len(sub_headers) else len(failures_section)
        blocks.append(failures_section[start:end].strip("\n"))

    blocks.append(summary_section)
    return blocks


def extract_stack_frames(blocks_or_log: list[str] | str) -> list[StackFrame]:
    """Resolve a ``StackFrame`` for every failing test's location-echo line.

    Accepts either the raw full log or the list produced by
    :func:`extract_failure_blocks` - finding the frames is metadata-only and
    costs no prompt tokens either way; only what gets *sent* to the model
    (the log/blocks text itself) has a token cost.

    A failure block can contain more than one ``path.py:line:`` line (pytest
    prints one per stack frame under ``--tb=short``/``--tb=long`` with
    ``--showlocals``); the *last* one in each block is the actual raise site
    pytest reports in its short summary, so that is the one resolved here.
    """
    text = "\n".join(blocks_or_log) if isinstance(blocks_or_log, list) else blocks_or_log
    headers = [(m.start(), m.group(1)) for m in _SUB_HEADER_RE.finditer(text)]
    if not headers:
        return []

    frames: list[StackFrame] = []
    for i, (start, test_name) in enumerate(headers):
        end = headers[i + 1][0] if i + 1 < len(headers) else len(text)
        block = text[start:end]
        matches = list(_LOCATION_RE.finditer(block))
        if not matches:
            continue
        last = matches[-1]
        exc_matches = list(_EXC_MESSAGE_RE.finditer(block))
        exc_message = exc_matches[-1].group(2).strip() if exc_matches else ""
        frames.append(
            StackFrame(
                path=last.group(1).replace("\\", "/"),
                line=int(last.group(2)),
                test_name=test_name,
                exc_type=last.group(3) or "",
                exc_message=exc_message,
            )
        )
    return frames
