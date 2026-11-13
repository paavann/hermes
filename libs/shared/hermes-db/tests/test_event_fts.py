"""Tests for the immutable events full-text search expression index."""

import importlib.util
from pathlib import Path
from types import ModuleType

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from hermes_db.models.event import Event


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "c2d3e4f5a6b7_add_events_fts_index.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("fts_migration", MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _index_expression(sql: str) -> str:
    _, _, expression = sql.lower().partition("using gin")
    return "".join(
        char for char in expression if not char.isspace() and char not in "()"
    )


def test_fts_index_registered_in_metadata() -> None:
    index = next(i for i in Event.__table__.indexes if i.name == "idx_events_fts")

    assert index.dialect_options["postgresql"]["using"] == "gin"
    assert index.expressions


def test_metadata_expression_matches_migration() -> None:
    index = next(i for i in Event.__table__.indexes if i.name == "idx_events_fts")
    compiled = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
    migration = _load_migration()

    assert _index_expression(compiled) == _index_expression(migration.CREATE_FTS_INDEX)
    assert "concurrently" in migration.CREATE_FTS_INDEX.lower()
    assert "if not exists" in migration.CREATE_FTS_INDEX.lower()
    assert "concurrently" in migration.DROP_FTS_INDEX.lower()
    assert "if exists" in migration.DROP_FTS_INDEX.lower()
