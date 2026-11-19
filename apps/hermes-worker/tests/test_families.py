import uuid
from datetime import UTC, datetime, timedelta
from hermes_db.services import FamilyCandidate
from hermes_worker.jobs.families import find_family, origin_group
from hermes_worker.jobs.fingerprints import simhash_hex


NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


def _candidate(
    *,
    title: str = "Earthquake strikes coastal city",
    body: str | None = "Rescue teams searched collapsed buildings.",
    embedding: tuple[float, ...] | None = None,
    representative_time: datetime | None = NOW,
    origin_group: str = "example",
) -> FamilyCandidate:
    title_hash = simhash_hex(title)
    assert title_hash is not None
    return FamilyCandidate(
        family_id=uuid.uuid4(),
        representative_article_id=uuid.uuid4(),
        title_simhash=title_hash,
        body_simhash=simhash_hex(body) if body else None,
        origin_group=origin_group,
        representative_time=representative_time,
        representative_embedding=embedding,
    )


def test_find_family_matches_normalized_title() -> None:
    candidate = _candidate()
    title_hash = simhash_hex("EARTHQUAKE strikes coastal city!")
    assert title_hash is not None

    match = find_family(
        [candidate],
        title_simhash=title_hash,
        body_simhash=None,
        embedding=None,
        event_time=NOW,
    )

    assert match is not None
    assert match.family_id == candidate.family_id
    assert match.rule == "title"
    assert match.representative_time == NOW


def test_find_family_rejects_rewritten_title_without_other_signals() -> None:
    candidate = _candidate()
    title_hash = simhash_hex(
        "Earthquake strikes coastal city, officials say"
    )
    assert title_hash is not None

    match = find_family(
        [candidate],
        title_simhash=title_hash,
        body_simhash=None,
        embedding=None,
        event_time=NOW,
    )

    assert match is None


def test_find_family_rejects_candidates_outside_event_window() -> None:
    candidate = _candidate(representative_time=NOW - timedelta(days=5))
    title_hash = simhash_hex("Earthquake strikes coastal city")
    assert title_hash is not None

    match = find_family(
        [candidate],
        title_simhash=title_hash,
        body_simhash=None,
        embedding=None,
        event_time=NOW,
    )

    assert match is None


def test_find_family_matches_body_when_title_differs() -> None:
    body = (
        "Rescue teams searched collapsed buildings after a magnitude 6.1 "
        "earthquake struck the region on Tuesday."
    )
    candidate = _candidate(title="Quake hits region", body=body)
    body_hash = simhash_hex(
        "Rescue teams searched collapsed buildings after a magnitude 6.1 "
        "earthquake struck the region on Tuesday, officials said."
    )
    assert body_hash is not None
    title_hash = simhash_hex("Completely different headline about markets")
    assert title_hash is not None

    match = find_family(
        [candidate],
        title_simhash=title_hash,
        body_simhash=body_hash,
        embedding=None,
        event_time=NOW,
    )

    assert match is not None
    assert match.rule == "body"


def test_find_family_matches_embedding_near_duplicate() -> None:
    candidate = _candidate(
        title="One headline",
        body=None,
        embedding=(1.0, 0.0, 0.0),
    )
    title_hash = simhash_hex("Unrelated words entirely")
    assert title_hash is not None

    match = find_family(
        [candidate],
        title_simhash=title_hash,
        body_simhash=None,
        embedding=(0.999, 0.01, 0.0),
        event_time=NOW,
    )

    assert match is not None
    assert match.rule == "embedding"


def test_find_family_returns_none_for_unrelated_article() -> None:
    candidate = _candidate()
    title_hash = simhash_hex(
        "Central bank raises interest rates at policy meeting"
    )
    assert title_hash is not None

    match = find_family(
        [candidate],
        title_simhash=title_hash,
        body_simhash=None,
        embedding=None,
        event_time=NOW,
    )

    assert match is None


def test_origin_group_normalizes_and_falls_back() -> None:
    assert origin_group(source_origin_group=" Example ", source_slug="x") == "example"
    assert origin_group(source_origin_group=None, source_slug="Slug") == "slug"
    assert origin_group(source_origin_group=None, source_slug=None) == "unknown"
    assert origin_group(source_origin_group="", source_slug="") == "unknown"
