"""Orchestration: the actual CI triage run.

Ties together log parsing, targeted reads, compaction, prompt-prefix
caching, and a pluggable diagnosis provider into one real triage pass over a
real log and a real repo on disk.

Design of the "session": the agent handles the failing tests in the order
they were reported. Each failing test is one tool call (a targeted code
read) followed by one model call (a diagnosis). By the time test *i* is
diagnosed, every *earlier* test's code read has been compacted to a 2-line
summary in the sent context; only test *i*'s own read stays at full
fidelity. The static system prompt + repo-conventions prefix is billed via
:class:`~ci_triage_agent.cache.PromptPrefixCache` on every call, so the
*first* call of a cold cache pays full price and every later call - within
this run, and on every subsequent CI run once the cache state file exists -
pays the discounted rate.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from .cache import PromptPrefixCache
from .compaction import ToolCallRecord, compact_tool_history
from .log_parser import StackFrame, extract_failure_blocks, extract_stack_frames
from .providers.base import DiagnosisProvider, DiagnosisRequest
from .repo_reader import discover_python_files, full_repo_dump, read_whole_file, read_window
from .tokens import TokenCounter

STATIC_SYSTEM_PROMPT = (
    "You are a CI triage agent. Given a test-failure report and a small "
    "excerpt of the surrounding source code, identify the root cause in one "
    "sentence and propose a minimal, concrete fix in one or two sentences. "
    "Only use the excerpt provided - do not invent line numbers or APIs that "
    "are not shown to you."
)

DEFAULT_REPO_CONVENTIONS = (
    "House conventions for this repo:\n"
    "- Prefer .get(key, default) over bare indexing on data that may be partial.\n"
    "- Guard denominators before dividing; guard indices before indexing.\n"
    "- Every public function should have a one-line docstring describing its contract."
)


def _failure_blocks_by_test(log: str) -> dict[str, str]:
    """Map each failing test's name to its own individual FAILURES block."""
    blocks = extract_failure_blocks(log)
    result = {}
    for block in blocks[:-1]:  # last entry is the short-summary block
        first_line = block.splitlines()[0] if block else ""
        name = first_line.strip("_ ").strip()
        result[name] = block
    return result


@dataclass
class FailingTestDiagnosis:
    frame: StackFrame
    diagnosis: str
    prefix_tokens_billed: int
    context_tokens_billed: int
    cache_warm: bool


@dataclass
class TriageReport:
    provider_name: str
    diagnoses: list[FailingTestDiagnosis] = field(default_factory=list)
    prefix_tokens: int = 0
    log_tokens: int = 0
    tool_tokens: int = 0
    naive_total_tokens: int = 0
    token_backend: str = "heuristic"

    @property
    def failing_tests(self) -> int:
        return len(self.diagnoses)

    @property
    def total_tokens(self) -> int:
        return self.prefix_tokens + self.log_tokens + self.tool_tokens

    @property
    def tokens_saved(self) -> int:
        return max(0, self.naive_total_tokens - self.total_tokens)

    @property
    def pct_saved(self) -> float:
        if not self.naive_total_tokens:
            return 0.0
        return round(self.tokens_saved / self.naive_total_tokens * 100, 2)


class TriageAgent:
    def __init__(
        self,
        repo_root: Path,
        provider: DiagnosisProvider,
        counter: TokenCounter | None = None,
        prefix_cache: PromptPrefixCache | None = None,
        repo_conventions: str = DEFAULT_REPO_CONVENTIONS,
        radius: int = 40,
        enable_pruning: bool = True,
        enable_targeted_reads: bool = True,
        enable_compaction: bool = True,
        enable_prompt_cache: bool = True,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.provider = provider
        self.counter = counter or TokenCounter()
        self.prefix_cache = prefix_cache or PromptPrefixCache()
        self.repo_conventions = repo_conventions
        self.radius = radius
        self.enable_pruning = enable_pruning
        self.enable_targeted_reads = enable_targeted_reads
        self.enable_compaction = enable_compaction
        self.enable_prompt_cache = enable_prompt_cache

    def _prefix_text(self) -> str:
        return STATIC_SYSTEM_PROMPT + "\n" + self.repo_conventions

    def _prefix_key(self) -> str:
        return hashlib.sha256(self._prefix_text().encode("utf-8")).hexdigest()

    def run(self, log_text: str) -> TriageReport:
        counter = self.counter
        report = TriageReport(provider_name=self.provider.name, token_backend=counter.backend)

        frames = extract_stack_frames(log_text)
        blocks_by_test = _failure_blocks_by_test(log_text) if self.enable_pruning else {}
        prefix_text = self._prefix_text()
        prefix_full_tokens = counter.count_text(prefix_text)
        prefix_key = self._prefix_key()

        records: list[ToolCallRecord] = []
        for frame in frames:
            if self.enable_targeted_reads:
                raw = read_window(self.repo_root, frame.path, frame.line, radius=self.radius)
            else:
                raw = read_whole_file(self.repo_root, frame.path)
            records.append(
                ToolCallRecord(path=frame.path, line=frame.line, test_name=frame.test_name,
                               raw_text=raw)
            )

            if self.enable_compaction:
                sent_chunks = compact_tool_history(records, protected_recent=1)
            else:
                sent_chunks = [r.raw_text for r in records]
            context_text = "\n\n".join(sent_chunks)

            if self.enable_pruning:
                failure_block = blocks_by_test.get(frame.test_name, "")
            else:
                failure_block = log_text

            if self.enable_prompt_cache:
                billed_prefix, warm = self.prefix_cache.charge(prefix_key, prefix_full_tokens)
            else:
                billed_prefix, warm = prefix_full_tokens, False

            prompt_text = "\n\n".join([prefix_text, failure_block, context_text])
            request = DiagnosisRequest(
                test_name=frame.test_name,
                path=frame.path,
                line=frame.line,
                exc_type=frame.exc_type,
                exc_message=frame.exc_message,
                code_context=records[-1].raw_text,
                prompt_text=prompt_text,
            )
            diagnosis_text = self.provider.diagnose(request)

            report.diagnoses.append(
                FailingTestDiagnosis(
                    frame=frame,
                    diagnosis=diagnosis_text,
                    prefix_tokens_billed=billed_prefix,
                    context_tokens_billed=counter.count_text(context_text),
                    cache_warm=warm,
                )
            )
            report.prefix_tokens += billed_prefix
            report.log_tokens += counter.count_text(failure_block)
            report.tool_tokens += counter.count_text(context_text)

        report.naive_total_tokens = self._naive_total_tokens(log_text, frames)
        return report

    def _naive_total_tokens(self, log_text: str, frames: list[StackFrame]) -> int:
        """What a naive agent would spend in one CI run: the static prefix
        (never cached), the full unpruned log, and a full dump of every
        Python file in the repo (not just the ones with reported failures)."""
        counter = self.counter
        prefix_tokens = counter.count_text(self._prefix_text())
        log_tokens = counter.count_text(log_text)
        all_paths = discover_python_files(self.repo_root) or [f.path for f in frames]
        dump_tokens = counter.count_text(full_repo_dump(self.repo_root, all_paths))
        return prefix_tokens + log_tokens + dump_tokens
