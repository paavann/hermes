"""
database models package.

importing all models here serves two purposes:
    1. convenience — other files can do: from hermes_api.db.models import Event, Source
    2. registration — SQLAlchemy needs all models to be imported so it can
       discover them and include them in Base.metadata. If a model is never
       imported, alembic won't generate a migration for it.
"""

from hermes_api.db.models.source import Source
from hermes_api.db.models.event import Event
from hermes_api.db.models.article import Article
from hermes_api.db.models.geocode_cache import GeocodeCache

__all__ = ["Source", "Event", "Article", "GeocodeCache"]