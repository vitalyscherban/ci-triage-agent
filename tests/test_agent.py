"""End-to-end test: TriageAgent against the real sample repo + real captured
CI log, with the offline MockProvider (no network in tests)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ci_triage_agent.agent import TriageAgent
from ci_triage_agent.cache import PromptPrefixCache
from ci_triage_agent.providers.mock import MockProvider

EXPECTED_BUGS = {
    "toyshop/inventory.py": (29, "KeyError"),
    "toyshop/orders.py": (67, "ZeroDivisionError"),
    "toyshop/payments.py": (30, "KeyError"),
    "toyshop/utils.py": (21, "IndexError"),
}


def _agent(repo_root: Path, **overrides) -> TriageAgent:
    return TriageAgent(repo_root=repo_root, provider=MockProvider(),
                        prefix_cache=PromptPrefixCache(), **overrides)


def test_run_finds_all_four_real_failures_with_correct_locations(repo_root, sample_log):
    report = _agent(repo_root).run(sample_log)
    assert report.failing_tests == 4

    resolved = {d.frame.path: (d.frame.line, d.frame.exc_type) for d in report.diagnoses}
    assert resolved == EXPECTED_BUGS
    for diagnosis in report.diagnoses:
        assert diagnosis.diagnosis  # non-empty, real diagnosis text


def test_first_call_cold_rest_warm_within_one_run(repo_root, sample_log):
    report = _agent(repo_root).run(sample_log)
    assert report.diagnoses[0].cache_warm is False
    assert all(d.cache_warm for d in report.diagnoses[1:])


def test_optimized_run_uses_far_fewer_tokens_than_naive_baseline(repo_root, sample_log):
    report = _agent(repo_root).run(sample_log)
    assert report.total_tokens < report.naive_total_tokens
    assert report.pct_saved >= 80.0


def test_disabling_every_technique_costs_meaningfully_more_tokens(repo_root, sample_log):
    optimized = _agent(repo_root).run(sample_log)
    degraded = _agent(
        repo_root,
        enable_pruning=False,
        enable_targeted_reads=False,
        enable_compaction=False,
        enable_prompt_cache=False,
    ).run(sample_log)
    assert degraded.total_tokens > optimized.total_tokens


@pytest.mark.parametrize(
    "flag", ["enable_pruning", "enable_targeted_reads", "enable_compaction", "enable_prompt_cache"]
)
def test_each_technique_individually_reduces_tokens_vs_all_off(repo_root, sample_log, flag):
    all_off = dict(enable_pruning=False, enable_targeted_reads=False,
                    enable_compaction=False, enable_prompt_cache=False)
    baseline = _agent(repo_root, **all_off).run(sample_log)

    one_on = dict(all_off)
    one_on[flag] = True
    improved = _agent(repo_root, **one_on).run(sample_log)

    assert improved.total_tokens <= baseline.total_tokens


def test_naive_total_tokens_is_stable_regardless_of_optimization_flags(repo_root, sample_log):
    a = _agent(repo_root).run(sample_log)
    b = _agent(repo_root, enable_pruning=False, enable_targeted_reads=False,
               enable_compaction=False, enable_prompt_cache=False).run(sample_log)
    assert a.naive_total_tokens == b.naive_total_tokens
