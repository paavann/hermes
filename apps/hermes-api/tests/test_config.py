"""Unit tests for chat-related application settings."""

from hermes_api.core.config import Settings


def _settings(**overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        DB_PASSWORD="test-password",
        API_PORT=8000,
        **overrides,
    )


def test_settings_load_without_chat_variables() -> None:
    cfg = _settings()
    assert cfg.CHAT_ENABLED is True
    assert cfg.CHAT_MODEL == ""
    assert cfg.CHAT_API == ""
    assert cfg.PLAN_MODEL == ""
    assert cfg.PLAN_API == ""
    assert cfg.TAVILY_API_KEY == ""
    assert cfg.CHAT_RATE_LIMIT_REQUESTS == 10
    assert cfg.CHAT_RATE_LIMIT_WINDOW_SECONDS == 60
    assert cfg.CHAT_DAILY_TOKEN_BUDGET == 500_000
    assert cfg.CHAT_MAX_CONCURRENT == 4
    assert cfg.CHAT_RETRIEVAL_TOP_K == 8
    assert cfg.CHAT_MIN_LOCAL_RESULTS == 2
    assert cfg.CHAT_MIN_SEMANTIC_SIMILARITY == 0.20
    assert cfg.CHAT_FRESHNESS_HOURS == 24
    assert cfg.CHAT_MAX_MESSAGE_CHARS == 4000
    assert cfg.CHAT_MAX_OUTPUT_TOKENS == 1200
    assert cfg.CHAT_WEB_TIMEOUT_SECONDS == 8.0
    assert cfg.CHAT_STREAM_INCLUDE_USAGE is True
    assert cfg.LANGFUSE_MASK_CONTENT is True
    assert cfg.TRUST_PROXY_HEADERS is False
    assert cfg.CHECKPOINT_DB_URL == ""


def test_settings_with_chat_variables() -> None:
    cfg = _settings(
        CHAT_MODEL="provider/chat",
        CHAT_API="chat-key",
        CHAT_MODEL_1="provider/chat-fallback",
        CHAT_API_1="chat-fallback-key",
        PLAN_MODEL="provider/plan",
        PLAN_API="plan-key",
        PLAN_MODEL_1="provider/plan-fallback",
        PLAN_API_1="plan-fallback-key",
        TAVILY_API_KEY="tavily-key",
        CHAT_RPM_LIMIT=30,
        CHAT_QUEUE_TIMEOUT_SECONDS=2.5,
        TRUST_PROXY_HEADERS=True,
    )
    assert cfg.CHAT_MODEL == "provider/chat"
    assert cfg.CHAT_API == "chat-key"
    assert cfg.CHAT_MODEL_1 == "provider/chat-fallback"
    assert cfg.PLAN_MODEL == "provider/plan"
    assert cfg.PLAN_API_1 == "plan-fallback-key"
    assert cfg.TAVILY_API_KEY == "tavily-key"
    assert cfg.CHAT_RPM_LIMIT == 30
    assert cfg.CHAT_QUEUE_TIMEOUT_SECONDS == 2.5
    assert cfg.TRUST_PROXY_HEADERS is True


def test_chat_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("CHAT_ENABLED", "false")
    cfg = _settings()
    assert cfg.CHAT_ENABLED is False


def test_checkpoint_url_derives_from_db_settings() -> None:
    cfg = _settings(
        DB_HOST="db.example.com",
        DB_PORT=6543,
        DB_USER="hermes",
        DB_NAME="hermes",
    )

    url = cfg.checkpoint_db_url

    assert url.startswith("postgresql://hermes:")
    assert "@db.example.com:6543/hermes" in url
    assert "sslmode=require" in url


def test_checkpoint_url_uses_local_db_without_ssl() -> None:
    cfg = _settings(DB_HOST="localhost")

    url = cfg.checkpoint_db_url

    assert url.startswith("postgresql://")
    assert "@localhost:5432/" in url
    assert "sslmode" not in url


def test_checkpoint_url_honors_explicit_override() -> None:
    cfg = _settings(
        CHECKPOINT_DB_URL="postgresql://other:secret@checkpoints:5432/state"
    )

    assert cfg.checkpoint_db_url == "postgresql://other:secret@checkpoints:5432/state"
