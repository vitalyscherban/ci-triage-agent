"""Shared, cross-service helper utilities for the toy shop service."""

from __future__ import annotations

from collections.abc import Sequence


def last_n_values(values: Sequence, n: int) -> list:
    """Return the last n values from a sequence, most-recent first.

    Callers should get back at most ``len(values)`` items even if ``n`` is
    larger than the sequence.
    """
    result = []
    for i in range(n):
        # BUG: once i exceeds len(values) - 1, -1 - i wraps past index 0 and
        # starts reading from the *end* of the list again instead of
        # stopping, so this raises no error for small overruns but produces
        # wrong data, and raises IndexError once the wrap lands on a
        # duplicate negative index beyond -len(values).
        result.append(values[-1 - i])
    return result


def chunked(values: Sequence, size: int) -> list[list]:
    """Split a sequence into consecutive chunks of at most ``size`` items."""
    if size <= 0:
        raise ValueError("size must be positive")
    return [list(values[i : i + size]) for i in range(0, len(values), size)]


def dedupe_preserve_order(values: Sequence) -> list:
    """Remove duplicates from a sequence while preserving first-seen order."""
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def clamp(value: float, low: float, high: float) -> float:
    """Clamp a value to the inclusive [low, high] range."""
    return max(low, min(high, value))


def first_n_values(values: Sequence, n: int) -> list:
    """Return the first n values from a sequence (safe for n > len(values))."""
    return list(values[:n])


def flatten(nested: Sequence[Sequence]) -> list:
    """Flatten one level of nesting in a sequence of sequences."""
    result = []
    for group in nested:
        result.extend(group)
    return result


def is_blank(text: str) -> bool:
    """Return whether a string is empty or contains only whitespace."""
    return not text or text.isspace()


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to at most ``max_length`` characters, appending a suffix."""
    if len(text) <= max_length:
        return text
    cut = max(0, max_length - len(suffix))
    return text[:cut] + suffix


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide two numbers, returning ``default`` instead of raising on zero."""
    if denominator == 0:
        return default
    return numerator / denominator


def percentage(part: float, whole: float) -> float:
    """Compute what percentage ``part`` is of ``whole``, safe against zero."""
    return round(safe_divide(part, whole) * 100, 2)


def group_by(values: Sequence, key_fn) -> dict:
    """Group values into a dict keyed by ``key_fn(value)``, preserving order."""
    groups: dict = {}
    for value in values:
        groups.setdefault(key_fn(value), []).append(value)
    return groups


def moving_average(values: Sequence[float], window: int) -> list[float]:
    """Compute a simple trailing moving average over a numeric sequence."""
    if window <= 0:
        raise ValueError("window must be positive")
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        chunk = values[start : i + 1]
        result.append(round(sum(chunk) / len(chunk), 4))
    return result


def unique_sorted(values: Sequence) -> list:
    """Return the sorted, de-duplicated values from a sequence."""
    return sorted(set(values))


def pairwise(values: Sequence) -> list[tuple]:
    """Return consecutive overlapping pairs from a sequence."""
    return [(values[i], values[i + 1]) for i in range(len(values) - 1)]


def retry_with_backoff_schedule(max_attempts: int, base: float = 0.5) -> list[float]:
    """Generic exponential-backoff schedule usable by any retrying caller."""
    return [round(base * (2**i), 2) for i in range(max_attempts)]


def format_bytes(num_bytes: int) -> str:
    """Format a byte count as a human-readable size string."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"
