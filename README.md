# ci-triage-agent

A **real** CI test-failure triage agent: it reads an actual pytest log and an
actual repo checkout on disk, resolves each failure to its faulting line, and
asks a pluggable diagnosis provider (a deterministic offline `MockProvider`,
or a real `OpenAIProvider` over HTTP) to explain the bug and suggest a fix -
using a fraction of the tokens a naive "dump everything into the prompt"
agent would need.

This is a standalone, dedicated project. It is a sibling to (and shares the
same four token-efficiency *ideas* as) the `tokenmax` demo scenario at the
repo root, but everything here is grounded in genuine data instead of an
in-memory synthetic construct:

| | `tokenmax` scenario (repo root) | `ci-triage-agent` (this project) |
|---|---|---|
| CI log | synthetically generated in-memory | **actually captured** by running `pytest -v` on a real toy repo |
| Repo files | a `dict[str, list[str]]` of strings | **real `.py` files on disk**, read via `Path` |
| Diagnosis | not produced (token accounting only) | a real rule-based `MockProvider`, or a real HTTP call to an OpenAI-compatible endpoint |
| Cache | in-memory, one run vs. the next | a JSON file on disk, so warmth genuinely persists across separate CLI invocations (separate CI jobs) |

## Install

```powershell
cd ci-triage-agent
..\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

(Reuses the repo's existing `.venv`; a dedicated venv works the same way.)
Add the `tiktoken` extra (`.[tiktoken]`) for exact, provider-accurate token
counts - without it, a documented word-count heuristic is used instead, same
honesty pattern as the rest of this repo.

## Run it

```powershell
ci-triage-agent run --log examples\sample_ci.log --repo examples\sample_repo
```

`examples/sample_ci.log` is a **real, captured** pytest run (`pytest -v`) of
`examples/sample_repo`, a small toy "orders/payments/inventory" service with
four genuine, intentional bugs (a `ZeroDivisionError`, two `KeyError`s, and
an `IndexError`) plus 3,000 real parametrized passing tests, so the log is
CI-scale (3,150 lines) rather than a toy-sized handful of lines.

Flags: `--provider {mock,openai}` (mock is default, fully offline),
`--format {text,markdown,json}`, `--radius N` (read-window size),
`--cache-state PATH` / `--fresh-cache`, and `--no-pruning` /
`--no-targeted-reads` / `--no-compaction` / `--no-prompt-cache` to disable
each technique individually.

## Real measured numbers

From actually running the command above against the checked-in log and repo:

| Run | Total tokens | vs. naive | Estimated cost* |
|---|---:|---:|---:|
| Naive (full log + full repo dump, every call) | 73,134 | - | $0.3072 |
| Optimized, cold cache (first CI run of the day) | 5,738 | **92.15% saved** | $0.0241 |
| Optimized, warm cache (next CI run) | 5,605 | **92.34% saved** | $0.0235 |

\* Illustrative only, at `$0.0042 / 1k tokens` - not tied to any vendor's
live pricing; see `estimate_cost_usd` in `report.py`.

All four failures are correctly resolved to their real `(path, line)` and
given a concrete diagnosis in every run above - the savings do not come at
the expense of the triage result.

## The four techniques, and where they live

| Technique | What it does here | Implementation |
|---|---|---|
| Pruning | Regex-extracts just the `FAILURES` blocks + short summary from the real log, discarding thousands of `PASSED` lines | `log_parser.extract_failure_blocks` |
| Targeted reads | Reads only `±radius` lines around the real faulting line from the real file on disk, not the whole file | `repo_reader.read_window` |
| Prompt-prefix caching | Charges the static system prompt + repo conventions at full price once, then a fixed discount on every later call - **persisted to a JSON file on disk**, so a second real CI run sees a genuinely warm cache | `cache.PromptPrefixCache` (`CACHE_READ_DISCOUNT = 0.1`) |
| Compaction | After each per-failure tool call, every earlier read collapses to a 2-line summary; only the most recent stays full-fidelity | `compaction.compact_tool_history` / `summarize_tool_output` |

`agent.TriageAgent.run()` ties these together, one model call per failing
test; `agent.TriageAgent._naive_total_tokens()` computes the same
counterfactual "what would a naive agent have spent" baseline used above.

## Tests

```powershell
..\.venv\Scripts\python.exe -m pytest -q
```

37 tests, fully offline (the real `OpenAIProvider` is never exercised by the
suite - only its "missing API key" error path is), running against the real
checked-in `examples/sample_repo` and `examples/sample_ci.log` fixtures.
