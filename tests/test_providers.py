"""Tests for the diagnosis providers."""

from __future__ import annotations

import pytest

from ci_triage_agent.providers.base import DiagnosisRequest
from ci_triage_agent.providers.mock import MockProvider
from ci_triage_agent.providers.openai_compatible import MissingApiKeyError, OpenAIProvider


def _request(exc_type: str, exc_message: str, line: int, code_context: str) -> DiagnosisRequest:
    return DiagnosisRequest(
        test_name="test_x", path="toyshop/orders.py", line=line,
        exc_type=exc_type, exc_message=exc_message, code_context=code_context,
        prompt_text="irrelevant",
    )


def test_mock_provider_is_deterministic_for_known_exception_types():
    ctx = f"{67:5d}: per_item_share = subtotal_cents / (item_count - item_count)"
    request = _request("ZeroDivisionError", "division by zero", 67, ctx)
    provider = MockProvider()
    assert provider.diagnose(request) == provider.diagnose(request)
    result = provider.diagnose(request)
    assert "ZeroDivisionError" in result
    assert "per_item_share" in result


def test_mock_provider_falls_back_to_default_rule_for_unknown_exception():
    ctx = f"{1:5d}: raise RuntimeError('boom')"
    request = _request("RuntimeError", "boom", 1, ctx)
    result = MockProvider().diagnose(request)
    assert "RuntimeError" in result
    assert "inspect the code window" in result


def test_openai_provider_requires_an_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MissingApiKeyError):
        OpenAIProvider()


def test_openai_provider_accepts_explicit_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIProvider(api_key="sk-test")
    assert provider.api_key == "sk-test"
    assert provider.name == "openai"
