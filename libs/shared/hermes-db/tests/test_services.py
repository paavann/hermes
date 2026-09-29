from hermes_db.enums import CredibilityTier, EventStatus
from hermes_db.models import Article, Event, Source
from hermes_db.services import EventService, sync_sources_from_config


def test_models_and_enums_importable():
    assert EventStatus.ACTIVE == "ACTIVE"
    assert CredibilityTier.TIER_1 == "TIER_1"
    assert Event.__tablename__ == "events"
    assert Article.__tablename__ == "articles"
    assert Source.__tablename__ == "sources"


def test_services_importable():
    assert callable(sync_sources_from_config)
    assert hasattr(EventService, "create_event_with_article")
    assert hasattr(EventService, "run_lifecycle_transitions")
