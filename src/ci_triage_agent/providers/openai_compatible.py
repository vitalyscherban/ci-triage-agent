"""A real diagnosis provider: calls an OpenAI-compatible chat completions
endpoint over HTTP. This is what makes the agent "real" beyond token
accounting - when configured with an API key, it actually asks a model to
read the pruned failure and targeted code window and explain the bug.

Requires an API key (``OPENAI_API_KEY`` by default, overridable). Makes a
real network call - never used by the test suite, which sticks to
:class:`ci_triage_agent.providers.mock.MockProvider`.
"""

from __future__ import annotations

import os

from .base import DiagnosisRequest

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You are a CI triage agent. Given a test-failure report and a small "
    "excerpt of the surrounding source code, identify the root cause in one "
    "sentence and propose a minimal, concrete fix in one or two sentences. "
    "Only use the excerpt provided - do not invent line numbers or APIs that "
    "are not shown to you."
)


class MissingApiKeyError(RuntimeError):
    pass


class OpenAIProvider:
    """Real provider: one chat-completions call per diagnosed failure."""

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        api_key_env: str = "OPENAI_API_KEY",
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.environ.get(api_key_env)
        if not self.api_key:
            raise MissingApiKeyError(
                f"No API key found. Set {api_key_env} or pass api_key= explicitly, "
                "or use --provider mock to run fully offline."
            )
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def diagnose(self, request: DiagnosisRequest) -> str:
        import httpx

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": request.prompt_text},
                ],
                "temperature": 0,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
