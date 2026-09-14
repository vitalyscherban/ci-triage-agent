"""Tests for compacting the per-failure tool-call sequence."""

from __future__ import annotations

from ci_triage_agent.compaction import ToolCallRecord, compact_tool_history, summarize_tool_output
from ci_triage_agent.repo_reader import read_window
from ci_triage_agent.tokens import TokenCounter


def _records(repo_root):
    specs = [
        ("toyshop/inventory.py", 29, "test_available_quantity_missing_reservation"),
        ("toyshop/orders.py", 67, "test_apply_bulk_discount"),
        ("toyshop/payments.py", 30, "test_convert_to_minor_units_unknown_currency"),
        ("toyshop/utils.py", 21, "test_last_n_values_overrun"),
    ]
    return [
        ToolCallRecord(path=path, line=line, test_name=name,
                        raw_text=read_window(repo_root, path, line, radius=40))
        for path, line, name in specs
    ]


def test_summarize_tool_output_is_two_lines_and_names_the_suspect_line(repo_root):
    raw = read_window(repo_root, "toyshop/orders.py", 67, radius=40)
    summary = summarize_tool_output("toyshop/orders.py", 67, raw)
    assert summary.count("\n") == 1
    assert "toyshop/orders.py" in summary and "67" in summary


def test_compact_tool_history_keeps_only_latest_full_fidelity(repo_root):
    counter = TokenCounter()
    records = _records(repo_root)

    compacted = compact_tool_history(records, protected_recent=1)
    uncompacted = [r.raw_text for r in records]

    compacted_tokens = sum(counter.count_text(chunk) for chunk in compacted)
    uncompacted_tokens = sum(counter.count_text(chunk) for chunk in uncompacted)
    assert compacted_tokens < uncompacted_tokens

    for record, sent in zip(records[:-1], compacted[:-1], strict=True):
        assert sent == record.summary
        assert record.raw_text not in sent
    assert compacted[-1] == records[-1].raw_text
