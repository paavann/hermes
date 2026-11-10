"""Import-isolation tests for the lazy chat engine boundary."""

import os
import subprocess
import sys


def _run(code: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("DB_PASSWORD", "mock_test_password")
    env.setdefault("API_PORT", "8000")
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_imports_do_not_load_chat_stack() -> None:
    code = """
import sys
import hermes_ai
import hermes_worker

loaded = sorted(
    name
    for name in ("langchain_core", "langchain_litellm", "langchain_tavily", "langgraph")
    if name in sys.modules
)
assert loaded == [], loaded
print("isolated")
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr
    assert "isolated" in result.stdout


def test_accessing_chat_loads_engine() -> None:
    code = """
import sys
from hermes_ai import AiConfig, HermesAi, ModelRoute, ModelTarget

ai = HermesAi(
    AiConfig(
        routes={
            "extractor": ModelRoute(
                primary=ModelTarget(model="mistral/ministral-8b-latest", api_key="test-key")
            ),
            "chat": ModelRoute(
                primary=ModelTarget(model="mistral/chat-model", api_key="chat-key")
            ),
            "plan": ModelRoute(
                primary=ModelTarget(model="mistral/plan-model", api_key="plan-key")
            ),
        }
    )
)
assert "hermes_ai.chat.engine" not in sys.modules
class _DummyRetriever:
    async def retrieve(self, query, *, scope, filters=None, recency_intent=False): pass
engine = ai.create_chat_engine(_DummyRetriever())
assert "hermes_ai.chat.engine" in sys.modules
assert type(engine).__name__ == "ChatEngine"
print("loaded")
"""
    result = _run(code)
    assert result.returncode == 0, result.stderr
    assert "loaded" in result.stdout
