"""Tests for hermes_db.core.config — Settings and db_url property.

All tests patch environment variables or pydantic-settings internals so
that no real .env file or DB connection is needed.  The lru_cache on
``get_settings`` is cleared between tests to ensure isolation.
"""

import pytest
from sqlalchemy import URL

from hermes_db.core.config import Settings, get_settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides) -> Settings:
    """Build a Settings instance with a known DB_PASSWORD, plus optional overrides."""
    defaults = {
        "DB_PASSWORD": "test-pass",
        "DB_HOST": "localhost",
        "DB_PORT": 5432,
        "DB_NAME": "hermes_test",
        "DB_USER": "postgres",
    }
    defaults.update(overrides)
    return Settings(**defaults)


# ---------------------------------------------------------------------------
# Settings defaults
# ---------------------------------------------------------------------------


class TestSettingsDefaults:
    def test_env_default(self):
        s = _make_settings()
        assert s.ENV == "development"

    def test_db_host_default(self):
        s = _make_settings()
        assert s.DB_HOST == "localhost"

    def test_db_port_default(self):
        s = _make_settings()
        assert s.DB_PORT == 5432

    def test_db_name_default(self):
        s = _make_settings()
        assert s.DB_NAME == "hermes_test"

    def test_db_user_default(self):
        s = _make_settings()
        assert s.DB_USER == "postgres"

    def test_event_stale_hrs_default(self):
        s = _make_settings()
        assert s.EVENT_STALE_HRS == 24

    def test_event_archive_hrs_default(self):
        s = _make_settings()
        assert s.EVENT_ARCHIVE_HRS == 48

    def test_db_password_is_required(self, monkeypatch):
        """DB_PASSWORD has no default — pydantic must raise if omitted."""
        from pydantic import ValidationError

        monkeypatch.delenv("DB_PASSWORD", raising=False)
        with pytest.raises(ValidationError):
            Settings()  # no DB_PASSWORD provided

    def test_db_password_cannot_be_empty(self):
        """DB_PASSWORD cannot be an empty string — min_length=1 enforced."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(DB_PASSWORD="")


# ---------------------------------------------------------------------------
# db_url property
# ---------------------------------------------------------------------------


class TestDbUrlProperty:
    def test_returns_sqlalchemy_url_object(self):
        s = _make_settings()
        assert isinstance(s.db_url, URL)

    def test_drivername_is_asyncpg(self):
        s = _make_settings()
        assert s.db_url.drivername == "postgresql+asyncpg"

    def test_credentials_embedded_in_url(self):
        s = _make_settings(DB_USER="hermes_user", DB_PASSWORD="s3cr3t")
        url = s.db_url
        assert url.username == "hermes_user"
        assert url.password == "s3cr3t"

    def test_host_and_port_in_url(self):
        s = _make_settings(DB_HOST="db.hermes.io", DB_PORT=5433)
        url = s.db_url
        assert url.host == "db.hermes.io"
        assert url.port == 5433

    def test_database_name_in_url(self):
        s = _make_settings(DB_NAME="hermes_prod")
        assert s.db_url.database == "hermes_prod"

    def test_localhost_has_no_ssl(self):
        """No ssl=require should be added for localhost connections."""
        for host in ("localhost", "127.0.0.1", "hermes-db"):
            s = _make_settings(DB_HOST=host)
            query = dict(s.db_url.query)
            assert "ssl" not in query, f"Expected no SSL for host={host}"

    def test_remote_host_requires_ssl(self):
        """External hostnames must trigger ssl=require in the query string."""
        s = _make_settings(DB_HOST="db.example.com")
        query = dict(s.db_url.query)
        assert query.get("ssl") == "require"

    @pytest.mark.parametrize(
        "host",
        ["localhost", "127.0.0.1", "hermes-db"],
    )
    def test_known_local_hosts_skip_ssl(self, host: str):
        s = _make_settings(DB_HOST=host)
        assert "ssl" not in dict(s.db_url.query)


# ---------------------------------------------------------------------------
# get_settings (lru_cache behaviour)
# ---------------------------------------------------------------------------


class TestGetSettings:
    def test_returns_settings_instance(self, monkeypatch):
        """get_settings() must return a Settings object."""
        monkeypatch.setenv("DB_PASSWORD", "cached-pass")
        # Clear cached result so this test is independent.
        get_settings.cache_clear()
        result = get_settings()
        assert isinstance(result, Settings)
        get_settings.cache_clear()

    def test_cache_returns_same_instance(self, monkeypatch):
        """Subsequent calls should return the identical cached object."""
        monkeypatch.setenv("DB_PASSWORD", "cached-pass")
        get_settings.cache_clear()
        a = get_settings()
        b = get_settings()
        assert a is b
        get_settings.cache_clear()
