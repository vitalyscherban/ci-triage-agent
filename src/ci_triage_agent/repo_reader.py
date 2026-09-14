"""Targeted file reads: a bounded window around a reported line, not the
whole file - this is what makes triage-by-stack-trace cheap."""

from __future__ import annotations

from pathlib import Path


def read_window(repo_root: Path, path: str, line: int, radius: int = 40) -> str:
    """Return lines ``[line - radius, line + radius]`` of ``repo_root/path``
    (clamped to file bounds), with line-number prefixes - not the whole file.

    Reads a real file from disk. Returns a clear placeholder string (not an
    exception) if the path doesn't exist under ``repo_root``, since a stale
    or renamed path in an old stack trace shouldn't crash the whole triage
    run.
    """
    file_path = repo_root / path
    if not file_path.is_file():
        return f"# {path} not found under {repo_root}"

    lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(1, line - radius)
    end = min(len(lines), line + radius)
    return "\n".join(f"{n:5d}: {lines[n - 1]}" for n in range(start, end + 1))


def read_whole_file(repo_root: Path, path: str) -> str:
    """Read a full file's contents - what a naive agent would send instead
    of a targeted window."""
    file_path = repo_root / path
    if not file_path.is_file():
        return f"# {path} not found under {repo_root}"
    return file_path.read_text(encoding="utf-8", errors="replace")


def full_repo_dump(repo_root: Path, paths: list[str]) -> str:
    """Concatenate the full contents of every given path - the naive
    counterfactual an agent without targeted reads would send."""
    parts = []
    for path in paths:
        parts.append(f"# ===== {path} =====\n{read_whole_file(repo_root, path)}")
    return "\n\n".join(parts)


def discover_python_files(repo_root: Path) -> list[str]:
    """List every ``.py`` file under ``repo_root`` (repo-relative, forward
    slashes), skipping common non-source directories."""
    skip_dirs = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"}
    paths = []
    for file_path in sorted(repo_root.rglob("*.py")):
        if any(part in skip_dirs for part in file_path.relative_to(repo_root).parts):
            continue
        paths.append(file_path.relative_to(repo_root).as_posix())
    return paths
