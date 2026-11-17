"""Tests for the guarded local database reset helper."""

import asyncio
from unittest.mock import AsyncMock
import pytest
from hermes_worker.services.reset import (
    RESET_STATEMENTS,
    ResetGuardError,
    reset_local_schema,
    validate_reset_target,
)


@pytest.mark.parametrize(
    "host",
    ["localhost", "127.0.0.1", "::1", "[::1]", "hermes-db", " LOCALHOST "],
)
def test_validate_allows_local_hosts(host: str) -> None:
    validate_reset_target(env="development", db_host=host, db_name="hermes")


@pytest.mark.parametrize("env", ["staging", "production", ""])
def test_validate_rejects_non_development_env(env: str) -> None:
    with pytest.raises(ResetGuardError, match="ENV must be 'development'"):
        validate_reset_target(env=env, db_host="localhost", db_name="hermes")


@pytest.mark.parametrize(
    "host",
    ["db.example.com", "10.0.0.5", "hermes-db.prod.internal", "0.0.0.0"],
)
def test_validate_rejects_remote_hosts(host: str) -> None:
    with pytest.raises(ResetGuardError, match="not a local database host"):
        validate_reset_target(env="development", db_host=host, db_name="hermes")


def test_reset_executes_statements_in_order_and_commits() -> None:
    session = AsyncMock()

    asyncio.run(reset_local_schema(session))

    statements = [str(call.args[0]) for call in session.execute.call_args_list]
    assert statements == list(RESET_STATEMENTS)
    session.commit.assert_awaited_once()
