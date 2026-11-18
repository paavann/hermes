"""Unit tests for hermes_worker.core.config Settings and db_url generation."""

import pytest
from pydantic import ValidationError
from sqlalchemy import URL
from hermes_worker.core.config import Settings, get_settings


def _make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "DB_PASSWORD": "worker-secret-pass",
        "DB_USER": "postgres",
        "DB_HOST": "localhost",
        "DB_PORT": 5432,
        "DB_NAME": "hermes",
        "DB_SSL_MODE": None,
        "ENV": "development",
        "LLM_API": "",
        "LLM_MODEL": "",
        "EMBED_API": "",
        "EMBED_MODEL": "",
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


class TestWorkerSettingsDefaults:
    def test_app_and_env_defaults(self):
        s = _make_settings()
        assert s.APP == "hermes-worker"
        assert s.ENV == "development"
        assert s.VERSION == "1.0.0"

    def test_db_defaults(self, monkeypatch):
        monkeypatch.delenv("DB_USER", raising=False)
        monkeypatch.delenv("DB_HOST", raising=False)
        monkeypatch.delenv("DB_PORT", raising=False)
        monkeypatch.delenv("DB_NAME", raising=False)
        s = Settings(DB_PASSWORD="pass", _env_file=None)
        assert s.DB_HOST == "localhost"
        assert s.DB_PORT == 5432
        assert s.DB_USER == "postgres"
        assert s.DB_NAME == "hermes"

    def test_rate_limit_defaults(self):
        s = _make_settings()
        assert s.RPM_LIMIT == 26
        assert s.EMBED_RPM_LIMIT == 90

    def test_lifecycle_defaults(self):
        s = _make_settings()
        assert s.EVENT_STALE_HOURS == 24
        assert s.EVENT_ARCHIVE_HOURS == 48

    def test_claim_queue_defaults(self):
        s = _make_settings()
        assert s.ARTICLE_CLAIM_BATCH_SIZE == 50
        assert s.ARTICLE_CLAIM_STALE_MINUTES == 30
        assert s.ARTICLE_MAX_ATTEMPTS == 3
        assert s.MAX_LLM_CALLS_PER_RUN == 120

    def test_claim_batch_size_must_be_positive(self):
        with pytest.raises(ValidationError):
            _make_settings(ARTICLE_CLAIM_BATCH_SIZE=0)
        with pytest.raises(ValidationError):
            _make_settings(MAX_LLM_CALLS_PER_RUN=0)

    def test_claim_max_attempts_must_be_at_least_one(self):
        with pytest.raises(ValidationError):
            _make_settings(ARTICLE_MAX_ATTEMPTS=0)

    def test_db_password_is_required(self, monkeypatch):
        monkeypatch.delenv("DB_PASSWORD", raising=False)
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_archive_cutoff_must_follow_stale_cutoff(self):
        with pytest.raises(ValidationError, match="EVENT_ARCHIVE_HOURS"):
            _make_settings(EVENT_STALE_HOURS=48, EVENT_ARCHIVE_HOURS=24)

        with pytest.raises(ValidationError, match="EVENT_ARCHIVE_HOURS"):
            _make_settings(EVENT_STALE_HOURS=24, EVENT_ARCHIVE_HOURS=24)

    def test_production_requires_llm_credentials(self):
        with pytest.raises(
            ValidationError, match="Missing required production settings"
        ):
            _make_settings(ENV="production")


class TestWorkerDbUrl:
    def test_returns_url_object(self):
        s = _make_settings()
        assert isinstance(s.db_url, URL)
        assert s.db_url.drivername == "postgresql+asyncpg"
        assert s.db_url.username == "postgres"
        assert s.db_url.password == "worker-secret-pass"
        assert s.db_url.host == "localhost"
        assert s.db_url.port == 5432
        assert s.db_url.database == "hermes"

    def test_development_does_not_force_ssl(self):
        for host in ["localhost", "127.0.0.1", "hermes-db", "db.aws.neon.tech"]:
            s = _make_settings(DB_HOST=host)
            assert "ssl" not in s.db_url.query

    def test_non_development_requires_ssl_by_default(self):
        s = _make_settings(ENV="staging")
        assert s.db_url.query.get("ssl") == "require"

    def test_explicit_ssl_mode_overrides_environment(self):
        for mode in ("disable", "allow", "prefer", "require"):
            s = _make_settings(ENV="staging", DB_SSL_MODE=mode)
            assert s.db_url.query.get("ssl") == mode

    def test_production_with_credentials_still_requires_ssl(self):
        s = _make_settings(
            ENV="production",
            LLM_API="llm-key",
            LLM_MODEL="mistral/mistral-large",
            EMBED_API="embed-key",
            EMBED_MODEL="nvidia_nim/nvidia/nemotron-3-embed-1b",
        )
        assert s.db_url.query.get("ssl") == "require"


class TestGetSettings:
    def test_returns_settings_instance(self):
        s = get_settings()
        assert isinstance(s, Settings)
