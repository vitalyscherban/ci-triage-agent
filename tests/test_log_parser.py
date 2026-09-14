"""Tests for parsing a real, genuinely-captured pytest CI log."""

from __future__ import annotations

from ci_triage_agent.log_parser import extract_failure_blocks, extract_stack_frames
from ci_triage_agent.tokens import TokenCounter

EXPECTED_BUGS = {
    "toyshop/inventory.py": (29, "KeyError"),
    "toyshop/orders.py": (67, "ZeroDivisionError"),
    "toyshop/payments.py": (30, "KeyError"),
    "toyshop/utils.py": (21, "IndexError"),
}


def test_extract_failure_blocks_finds_exactly_the_real_failures(sample_log: str):
    blocks = extract_failure_blocks(sample_log)
    # 4 real failing tests + 1 short-summary block.
    assert len(blocks) == 5
    assert "short test summary info" in blocks[-1]
    assert blocks[-1].count("FAILED") == 4


def test_pruning_is_dramatically_smaller_than_the_full_log(sample_log: str):
    counter = TokenCounter()
    full_tokens = counter.count_text(sample_log)
    pruned_tokens = counter.count_text("\n".join(extract_failure_blocks(sample_log)))

    assert pruned_tokens < full_tokens
    # The real log has ~3000 noise lines from test_noise.py around 4 failures.
    assert pruned_tokens < full_tokens * 0.1


def test_extract_stack_frames_resolves_every_real_bug(sample_log: str):
    frames = extract_stack_frames(sample_log)
    assert len(frames) == 4

    resolved = {f.path: (f.line, f.exc_type) for f in frames}
    assert resolved == EXPECTED_BUGS


def test_extract_stack_frames_captures_exception_messages(sample_log: str):
    frames = extract_stack_frames(sample_log)
    messages = {f.path: f.exc_message for f in frames}
    assert messages["toyshop/payments.py"] == "'AUD'"
    assert messages["toyshop/inventory.py"] == "'SKU-404'"
    assert "division by zero" in messages["toyshop/orders.py"]


def test_extract_stack_frames_works_on_pruned_blocks_too(sample_log: str):
    blocks = extract_failure_blocks(sample_log)
    assert extract_stack_frames(blocks) == extract_stack_frames(sample_log)


def test_extract_failure_blocks_is_noop_on_a_log_with_no_failures():
    log = "===== test session starts =====\n1 passed\n"
    assert extract_failure_blocks(log) == [log]


def test_extract_stack_frames_is_empty_on_a_log_with_no_failures():
    log = "===== test session starts =====\n1 passed\n"
    assert extract_stack_frames(log) == []
