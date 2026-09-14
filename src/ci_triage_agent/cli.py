"""Command-line entry point for ci-triage-agent.

Usage:
    ci-triage-agent run --log path/to/ci.log --repo path/to/repo
    python -m ci_triage_agent run --log ... --repo ...

Runs fully offline by default (``--provider mock``); pass ``--provider
openai`` (with ``OPENAI_API_KEY`` set) to have a real model produce the
diagnoses instead of the deterministic rule-based ones.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agent import TriageAgent
from .cache import PromptPrefixCache
from .providers.mock import MockProvider
from .providers.openai_compatible import MissingApiKeyError, OpenAIProvider
from .report import render_markdown, render_text
from .tokens import TokenCounter

DEFAULT_CACHE_STATE_PATH = Path.home() / ".cache" / "ci-triage-agent" / "prefix_cache.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ci-triage-agent")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Triage a CI log against a repo checkout")
    run.add_argument("--log", required=True, type=Path, help="Path to a pytest-style CI log")
    run.add_argument(
        "--repo", required=True, type=Path, help="Path to the repo the log ran against"
    )
    run.add_argument("--provider", choices=["mock", "openai"], default="mock")
    run.add_argument("--model", default="gpt-4o-mini", help="Model name (openai provider only)")
    run.add_argument("--radius", type=int, default=40, help="Lines of context around each failure")
    run.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    run.add_argument(
        "--cache-state",
        type=Path,
        default=DEFAULT_CACHE_STATE_PATH,
        help="Where to persist prompt-prefix cache warmth across runs "
        "(so a second CI run of the day sees a warm cache for real)",
    )
    run.add_argument("--fresh-cache", dest="fresh_cache", action="store_true", default=False,
                      help="ignore/clear persisted cache state, simulating a cold cache "
                      "(default: reuse persisted state across runs)")
    run.add_argument("--no-pruning", dest="enable_pruning", action="store_false", default=True)
    run.add_argument("--no-targeted-reads", dest="enable_targeted_reads", action="store_false",
                      default=True)
    run.add_argument("--no-compaction", dest="enable_compaction", action="store_false",
                      default=True)
    run.add_argument("--no-prompt-cache", dest="enable_prompt_cache", action="store_false",
                      default=True)
    return parser


def _build_provider(args: argparse.Namespace):
    if args.provider == "openai":
        try:
            return OpenAIProvider(model=args.model)
        except MissingApiKeyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            raise SystemExit(2) from exc
    return MockProvider()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        log_text = args.log.read_text(encoding="utf-8", errors="replace")
        provider = _build_provider(args)

        cache_state = None if args.fresh_cache else args.cache_state
        prefix_cache = PromptPrefixCache(state_path=cache_state)

        agent = TriageAgent(
            repo_root=args.repo,
            provider=provider,
            counter=TokenCounter(args.model),
            prefix_cache=prefix_cache,
            radius=args.radius,
            enable_pruning=args.enable_pruning,
            enable_targeted_reads=args.enable_targeted_reads,
            enable_compaction=args.enable_compaction,
            enable_prompt_cache=args.enable_prompt_cache,
        )
        report = agent.run(log_text)

        if args.format == "markdown":
            print(render_markdown(report))
        elif args.format == "json":
            import json

            payload = {
                "provider": report.provider_name,
                "token_backend": report.token_backend,
                "failing_tests": report.failing_tests,
                "total_tokens": report.total_tokens,
                "naive_total_tokens": report.naive_total_tokens,
                "tokens_saved": report.tokens_saved,
                "pct_saved": report.pct_saved,
                "diagnoses": [
                    {
                        "test_name": d.frame.test_name,
                        "path": d.frame.path,
                        "line": d.frame.line,
                        "exc_type": d.frame.exc_type,
                        "diagnosis": d.diagnosis,
                        "cache_warm": d.cache_warm,
                    }
                    for d in report.diagnoses
                ],
            }
            print(json.dumps(payload, indent=2))
        else:
            print(render_text(report))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
