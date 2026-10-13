"""Tests for hermes_db.base — declarative base mixins.

Validates that:
* ``UUIDPrimaryKeyMixin`` supplies a UUID primary key with a uuid4 default.
* ``TimestampMixin`` wires ``created_at`` / ``updated_at`` server defaults.
* ``Base`` is a concrete SQLAlchemy ``DeclarativeBase``.

Because these are SQLAlchemy ORM mapping classes, the tests inspect the
mapped column metadata rather than instantiating ORM rows (which would
require a live database).  Where instantiation is safe (e.g., default
factories), we test it directly.
"""

import uuid

from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase

from hermes_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


# ---------------------------------------------------------------------------
# Helper — minimal concrete model for testing mixins
# ---------------------------------------------------------------------------


class _SampleModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Minimal model used only inside this test module."""

    __tablename__ = "_test_sample_base"

    # SQLAlchemy needs at least one non-PK mapped column to be happy.
    # We piggyback on the mixin columns — no extra column needed.


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class TestBase:
    def test_is_declarative_base(self):
        """Base must be a DeclarativeBase subclass (the SQLAlchemy 2.x way)."""
        assert issubclass(Base, DeclarativeBase)

    def test_metadata_accessible(self):
        """Base.metadata must be a SQLAlchemy MetaData object."""
        from sqlalchemy import MetaData

        assert isinstance(Base.metadata, MetaData)


# ---------------------------------------------------------------------------
# UUIDPrimaryKeyMixin
# ---------------------------------------------------------------------------


class TestUUIDPrimaryKeyMixin:
    def test_id_column_is_primary_key(self):
        """The id column must be the primary key."""
        mapper = inspect(_SampleModel)
        pk_cols = [c.name for c in mapper.primary_key]
        assert "id" in pk_cols

    def test_id_has_callable_default_configured(self):
        """In SQLAlchemy 2.x, mapped_column(default=uuid.uuid4) registers a
        CallableColumnDefault.  We verify the default is callable and produces UUIDs."""
        col = inspect(_SampleModel).columns["id"]
        assert col.default is not None
        assert col.default.is_callable

    def test_id_default_callable_produces_uuid(self):
        """Calling the configured default function must return a valid UUID.

        SQLAlchemy wraps the callable so it must be invoked with a context
        argument (None is acceptable for in-process invocation).
        """
        col = inspect(_SampleModel).columns["id"]
        result = col.default.arg(None)
        assert isinstance(result, uuid.UUID)

    def test_id_default_callable_produces_unique_values(self):
        """Each invocation of the default callable must return a distinct UUID."""
        col = inspect(_SampleModel).columns["id"]
        fn = col.default.arg
        assert fn(None) != fn(None)

    def test_id_type_annotation(self):
        """The mapped type annotation must be uuid.UUID."""
        mapper = inspect(_SampleModel)
        col = mapper.columns["id"]
        # SQLAlchemy 2 wraps UUID in its own type; the Python type must be UUID.
        assert col.type.python_type is uuid.UUID


# ---------------------------------------------------------------------------
# TimestampMixin
# ---------------------------------------------------------------------------


class TestTimestampMixin:
    def test_created_at_column_present(self):
        """created_at must appear in the mapped columns."""
        mapper = inspect(_SampleModel)
        assert "created_at" in mapper.columns

    def test_updated_at_column_present(self):
        """updated_at must appear in the mapped columns."""
        mapper = inspect(_SampleModel)
        assert "updated_at" in mapper.columns

    def test_created_at_has_server_default(self):
        """created_at must carry a server_default so the DB fills it in."""
        col = inspect(_SampleModel).columns["created_at"]
        assert col.server_default is not None

    def test_updated_at_has_server_default(self):
        """updated_at must carry a server_default."""
        col = inspect(_SampleModel).columns["updated_at"]
        assert col.server_default is not None

    def test_updated_at_has_onupdate(self):
        """updated_at must carry an onupdate hook so it refreshes on writes."""
        col = inspect(_SampleModel).columns["updated_at"]
        assert col.onupdate is not None
