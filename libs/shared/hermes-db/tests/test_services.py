from hermes_db.enums import CredibilityTier, EventStatus
from hermes_db.models import Article, Event, Source
from hermes_db.services import (
    ArticleLedgerRow,
    ArticleService,
    EventService,
    SourceService,
    canonical_domain_from_url,
    load_sources_config,
    sync_sources_from_config,
)


def test_models_and_enums_importable():
    assert EventStatus.ACTIVE == "ACTIVE"
    assert CredibilityTier.TIER_1 == "TIER_1"
    assert Event.__tablename__ == "events"
    assert Article.__tablename__ == "articles"
    assert Source.__tablename__ == "sources"


def test_services_importable():
    assert callable(sync_sources_from_config)
    assert callable(load_sources_config)
    assert canonical_domain_from_url("https://www.example.com") == "example.com"
    assert ArticleLedgerRow is not None
    assert hasattr(ArticleService, "insert_ledger_rows")
    assert hasattr(SourceService, "get_due_sources")
    assert hasattr(EventService, "create_event_with_article")
    assert hasattr(EventService, "run_lifecycle_transitions")
