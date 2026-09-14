"""Smoke tests for the CLI entry point (mock provider only - no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_triage_agent.cli import main


def _run_cli(capsys, tmp_path: Path, repo_root: Path, sample_log: str, *extra_args: str) -> str:
    log_path = tmp_path / "ci.log"
    log_path.write_text(sample_log, encoding="utf-8")
    cache_path = tmp_path / "cache.json"

    exit_code = main([
        "run", "--log", str(log_path), "--repo", str(repo_root),
        "--cache-state", str(cache_path), *extra_args,
    ])
    assert exit_code == 0
    return capsys.readouterr().out


def test_cli_text_output_lists_all_failures(capsys, tmp_path, repo_root, sample_log):
    out = _run_cli(capsys, tmp_path, repo_root, sample_log)
    assert "failing tests: 4" in out
    assert "total tokens:" in out
    assert "naive baseline:" in out


def test_cli_markdown_output(capsys, tmp_path, repo_root, sample_log):
    out = _run_cli(capsys, tmp_path, repo_root, sample_log, "--format", "markdown")
    assert out.startswith("# CI Triage Report")
    assert "## Failures" in out


def test_cli_json_output_is_valid_and_complete(capsys, tmp_path, repo_root, sample_log):
    out = _run_cli(capsys, tmp_path, repo_root, sample_log, "--format", "json")
    payload = json.loads(out)
    assert payload["failing_tests"] == 4
    assert len(payload["diagnoses"]) == 4
    assert payload["total_tokens"] < payload["naive_total_tokens"]


def test_cli_openai_provider_without_key_exits_cleanly(monkeypatch, tmp_path, repo_root,
                                                          sample_log):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    log_path = tmp_path / "ci.log"
    log_path.write_text(sample_log, encoding="utf-8")

    with pytest.raises(SystemExit):
        main(["run", "--log", str(log_path), "--repo", str(repo_root), "--provider", "openai"])
