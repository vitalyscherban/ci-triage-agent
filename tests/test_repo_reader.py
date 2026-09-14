"""Tests for reading real files from a real repo on disk."""

from __future__ import annotations

from pathlib import Path

from ci_triage_agent.repo_reader import (
    discover_python_files,
    full_repo_dump,
    read_whole_file,
    read_window,
)
from ci_triage_agent.tokens import TokenCounter


def test_read_window_is_bounded_and_contains_the_target_line(repo_root: Path):
    window = read_window(repo_root, "toyshop/orders.py", 67, radius=10)
    numbered_lines = window.splitlines()

    assert len(numbered_lines) <= 21
    assert any(line.strip().startswith("67:") for line in numbered_lines)
    assert "per_item_share" in window


def test_read_window_is_much_smaller_than_the_whole_file(repo_root: Path):
    counter = TokenCounter()
    whole = read_whole_file(repo_root, "toyshop/orders.py")
    window = read_window(repo_root, "toyshop/orders.py", 67, radius=10)
    assert counter.count_text(window) < counter.count_text(whole)


def test_read_window_clamps_to_file_bounds(repo_root: Path):
    window = read_window(repo_root, "toyshop/utils.py", line=1, radius=40)
    first_line_no = int(window.splitlines()[0].split(":", 1)[0])
    assert first_line_no == 1


def test_read_window_missing_file_returns_placeholder_not_exception(repo_root: Path):
    result = read_window(repo_root, "toyshop/does_not_exist.py", 10)
    assert "not found" in result


def test_discover_python_files_finds_real_source_and_test_files(repo_root: Path):
    paths = discover_python_files(repo_root)
    assert "toyshop/orders.py" in paths
    assert "tests/test_orders.py" in paths
    assert not any("__pycache__" in p for p in paths)


def test_full_repo_dump_contains_every_file_in_full(repo_root: Path):
    paths = ["toyshop/orders.py", "toyshop/payments.py"]
    dump = full_repo_dump(repo_root, paths)
    assert "apply_bulk_discount" in dump
    assert "convert_to_minor_units" in dump
