import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)

LOCAL_DB_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "hermes-db"})

RESET_STATEMENTS = (
    "DROP EXTENSION IF EXISTS vector CASCADE",
    "DROP EXTENSION IF EXISTS postgis CASCADE",
    "DROP SCHEMA IF EXISTS public CASCADE",
    "CREATE SCHEMA public",
    "CREATE EXTENSION IF NOT EXISTS postgis",
    "CREATE EXTENSION IF NOT EXISTS vector",
)


class ResetGuardError(RuntimeError):
    """Raised when a reset target is not clearly a local development database."""


def _normalize_host(db_host: str) -> str:
    host = db_host.strip().lower()
    if host.startswith("[") and host.endswith("]"):
        return host[1:-1]
    return host


def validate_reset_target(*, env: str, db_host: str, db_name: str) -> None:
    if env != "development":
        raise ResetGuardError(
            f"refusing to reset database '{db_name}': ENV must be 'development', "
            f"got '{env}'."
        )
    host = _normalize_host(db_host)
    if host not in LOCAL_DB_HOSTS:
        raise ResetGuardError(
            f"refusing to reset database '{db_name}': DB_HOST '{db_host}' is not "
            "a local database host."
        )


async def reset_local_schema(session: AsyncSession) -> None:
    logger.warning("dropping local database objects and re-creating extensions.")
    for statement in RESET_STATEMENTS:
        await session.execute(text(statement))
    await session.commit()
