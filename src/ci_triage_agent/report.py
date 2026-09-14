"""Render a TriageReport as console text or Markdown."""

from __future__ import annotations

from .agent import TriageReport
from .cache import CACHE_READ_DISCOUNT

DEFAULT_RATE_PER_1K_TOKENS = 0.0042


def estimate_cost_usd(tokens: int, rate_per_1k: float = DEFAULT_RATE_PER_1K_TOKENS) -> float:
    """Illustrative dollar estimate for a token count - not tied to any
    single vendor's live pricing, just a stable unit for the report."""
    return round(tokens / 1000 * rate_per_1k, 4)


def render_text(report: TriageReport) -> str:
    lines = [
        f"CI triage report - provider={report.provider_name} "
        f"token backend={report.token_backend}",
        f"failing tests: {report.failing_tests}",
        "",
    ]
    for i, diag in enumerate(report.diagnoses, start=1):
        f = diag.frame
        cache_note = "warm cache read" if diag.cache_warm else "cold / full price"
        lines.append(f"[{i}] {f.test_name}  ({f.path}:{f.line}, {f.exc_type})")
        lines.append(f"    {diag.diagnosis}")
        lines.append(
            f"    tokens: prefix={diag.prefix_tokens_billed} ({cache_note}), "
            f"context={diag.context_tokens_billed}"
        )
        lines.append("")

    lines.append(
        f"total tokens: {report.total_tokens} "
        f"(prefix={report.prefix_tokens}, log={report.log_tokens}, tool={report.tool_tokens})"
    )
    lines.append(f"naive baseline: {report.naive_total_tokens} tokens")
    lines.append(f"saved: {report.tokens_saved} tokens ({report.pct_saved}%)")
    lines.append(
        f"estimated cost: ${estimate_cost_usd(report.total_tokens)} "
        f"(naive: ${estimate_cost_usd(report.naive_total_tokens)})"
    )
    return "\n".join(lines)


def render_markdown(report: TriageReport) -> str:
    lines = [
        "# CI Triage Report",
        "",
        f"- Provider: `{report.provider_name}`",
        f"- Token backend: `{report.token_backend}`",
        f"- Failing tests: **{report.failing_tests}**",
        f"- Total tokens: **{report.total_tokens}** "
        f"(prefix {report.prefix_tokens}, log {report.log_tokens}, tool {report.tool_tokens})",
        f"- Naive baseline: {report.naive_total_tokens} tokens",
        f"- Saved: **{report.tokens_saved} tokens ({report.pct_saved}%)**",
        f"- Estimated cost: ${estimate_cost_usd(report.total_tokens)} "
        f"(naive ${estimate_cost_usd(report.naive_total_tokens)})",
        f"- Prompt-prefix cache discount on a warm hit: {int((1 - CACHE_READ_DISCOUNT) * 100)}%",
        "",
        "## Failures",
        "",
    ]
    for i, diag in enumerate(report.diagnoses, start=1):
        f = diag.frame
        lines.append(f"### {i}. `{f.test_name}` - {f.exc_type} at `{f.path}:{f.line}`")
        lines.append("")
        lines.append(diag.diagnosis)
        lines.append("")
    return "\n".join(lines)
