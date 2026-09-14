"""Tests for the on-disk-persisted prompt-prefix cache."""

from __future__ import annotations

from pathlib import Path

from ci_triage_agent.cache import CACHE_READ_DISCOUNT, PromptPrefixCache


def test_first_charge_is_full_price():
    cache = PromptPrefixCache()
    billed, warm = cache.charge("key", 1000)
    assert warm is False
    assert billed == 1000


def test_second_charge_for_same_key_is_discounted():
    cache = PromptPrefixCache()
    cache.charge("key", 1000)
    billed, warm = cache.charge("key", 1000)
    assert warm is True
    assert billed == round(1000 * CACHE_READ_DISCOUNT)
    assert billed < 1000


def test_different_keys_are_independent():
    cache = PromptPrefixCache()
    cache.charge("a", 500)
    billed, warm = cache.charge("b", 500)
    assert warm is False
    assert billed == 500


def test_cache_state_persists_across_instances(tmp_path: Path):
    state_path = tmp_path / "cache.json"

    first = PromptPrefixCache(state_path=state_path)
    first.charge("key", 1000)

    second = PromptPrefixCache(state_path=state_path)
    billed, warm = second.charge("key", 1000)
    assert warm is True
    assert billed == round(1000 * CACHE_READ_DISCOUNT)


def test_clear_removes_persisted_state(tmp_path: Path):
    state_path = tmp_path / "cache.json"
    cache = PromptPrefixCache(state_path=state_path)
    cache.charge("key", 1000)
    assert state_path.exists()

    cache.clear()
    assert not state_path.exists()

    _, warm = cache.charge("key", 1000)
    assert warm is False
