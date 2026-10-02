"""Unit tests for hermes_worker.core.config Settings and db_url generation."""

import pytest
from sqlalchemy import URL
from hermes_worker.core.config import Settings, get_settings


def _make_settings(**overrides) -> Settings:
    defaults = {
        "DB_PASSWORD": "worker-secret-pass",
        "DB_USER": "postgres",
        "DB_HOST": "localhost",
        "DB_PORT": 5432,
        "DB_NAME": "hermes",
    }
    defaults.update(overrides)
    return Settings(**defaults)


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

    def test_sync_interval_defaults(self):
        s = _make_settings()
        assert s.RSS_FETCH_INTERVAL_MIN == 15
        assert s.SYNC_INTERVAL_MIN == 360
        assert s.EVENT_STALE_HOURS == 24
        assert s.EVENT_ARCHIVE_HOURS == 48

    def test_db_password_is_required(self, monkeypatch):
        from pydantic import ValidationError

        monkeypatch.delenv("DB_PASSWORD", raising=False)
        with pytest.raises(ValidationError):
            Settings(_env_file=None)


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

    def test_ssl_query_parameter_logic(self):
        # Local hosts do not require ssl
        for host in ["localhost", "127.0.0.1", "hermes-db"]:
            s = _make_settings(DB_HOST=host)
            assert "ssl" not in s.db_url.query

        # Remote host requires ssl
        remote_s = _make_settings(DB_HOST="db.aws.neon.tech")
        assert remote_s.db_url.query.get("ssl") == "require"


class TestGetSettings:
    def test_returns_settings_instance(self):
        s = get_settings()
        assert isinstance(s, Settings)
