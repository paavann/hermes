"""Tests for the single authoritative importance score and tier selection."""

import uuid
from datetime import UTC, datetime, timedelta

from hermes_db.enums import (
    ArticleType,
    CredibilityTier,
    ImpactLevel,
    SelectionTier,
    VerificationStatus,
)
from hermes_db.services.event_membership import MemberRecord
from hermes_db.services.event_scoring import (
    BREAKING_MIN_SCORE,
    FILLER_THRESHOLD,
    PRIMARY_THRESHOLD,
    SINGLE_SOURCE_CAP,
    compute_score,
    select_tier,
)


NOW = datetime(2026, 11, 20, 12, 0, 0, tzinfo=UTC)


def _member(
    *,
    credibility: CredibilityTier = CredibilityTier.TIER_1,
    family_id: uuid.UUID | None = None,
    article_type: ArticleType = ArticleType.DEVELOPMENT,
    specificity: int = 5,
    consequence: int = 5,
    published_at: datetime | None = None,
) -> MemberRecord:
    return MemberRecord(
        event_id=uuid.uuid4(),
        article_id=uuid.uuid4(),
        family_id=family_id or uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_name="Example",
        source_origin_group="example",
        source_slug="example",
        source_credibility=credibility,
        published_at=published_at or NOW,
        embedding=None,
        embedding_model=None,
        input_quality=None,
        article_type=article_type,
        fact="A fact.",
        certainty=None,
        consequence=consequence,
        specificity=specificity,
        scale_facts=(),
        entities=(),
        locations=(),
    )


def test_no_members_scores_zero() -> None:
    result = compute_score(
        members=[],
        impact=ImpactLevel.CRITICAL,
        verification=VerificationStatus.CONFIRMED,
        latest_published_at=NOW,
        event_time=NOW,
        now=NOW,
    )

    assert result.score == 0.0
    assert result.breakdown["reason"] == "no_members"
    assert result.capped is False


def test_strength_counts_each_family_once_at_its_best_credibility() -> None:
    family = uuid.uuid4()
    members = [
        _member(credibility=CredibilityTier.TIER_1, family_id=family),
        _member(credibility=CredibilityTier.TIER_2, family_id=family),
        _member(credibility=CredibilityTier.TIER_2),
        _member(credibility=CredibilityTier.TIER_3),
    ]

    result = compute_score(
        members=members,
        impact=ImpactLevel.MINOR,
        verification=VerificationStatus.CORROBORATED,
        latest_published_at=NOW,
        event_time=NOW,
        now=NOW,
    )

    # Families: TIER_1 (3.0), TIER_2 (2.0), TIER_3 (1.0) -> 6/9.
    assert result.strength == 6.0 / 9.0
    assert result.breakdown["family_count"] == 3


def test_strength_is_capped_at_one() -> None:
    members = [_member(credibility=CredibilityTier.TIER_1) for _ in range(4)]

    result = compute_score(
        members=members,
        impact=ImpactLevel.MAJOR,
        verification=VerificationStatus.CONFIRMED,
        latest_published_at=NOW,
        event_time=NOW,
        now=NOW,
    )

    assert result.strength == 1.0


def test_base_combines_strength_impact_verification_and_quality() -> None:
    members = [_member(credibility=CredibilityTier.TIER_1)]

    result = compute_score(
        members=members,
        impact=ImpactLevel.CRITICAL,
        verification=VerificationStatus.CONFIRMED,
        latest_published_at=NOW,
        event_time=NOW,
        now=NOW,
    )

    expected_base = 100.0 * (0.40 * (1.0 / 3.0) + 0.30 * 1.0 + 0.15 * 1.0 + 0.15 * 1.0)
    assert round(result.base, 4) == round(expected_base, 4)
    assert result.score == round(expected_base, 2)


def test_freshness_decays_with_impact_specific_half_life() -> None:
    members = [_member()]
    published = NOW - timedelta(hours=18)

    critical = compute_score(
        members=members,
        impact=ImpactLevel.CRITICAL,
        verification=VerificationStatus.CONFIRMED,
        latest_published_at=published,
        event_time=published,
        now=NOW,
    )
    minor = compute_score(
        members=members,
        impact=ImpactLevel.MINOR,
        verification=VerificationStatus.CONFIRMED,
        latest_published_at=published,
        event_time=published,
        now=NOW,
    )

    assert critical.half_life_hours == 18.0
    assert round(critical.freshness, 4) == 0.3679
    assert minor.half_life_hours == 72.0
    assert minor.freshness > critical.freshness


def test_single_source_is_capped_at_45() -> None:
    members = [_member(credibility=CredibilityTier.TIER_1)]

    result = compute_score(
        members=members,
        impact=ImpactLevel.CRITICAL,
        verification=VerificationStatus.SINGLE_SOURCE,
        latest_published_at=NOW,
        event_time=NOW,
        now=NOW,
    )

    assert result.capped is True
    assert result.score == SINGLE_SOURCE_CAP
    assert result.breakdown["capped"] is True


def test_conflicting_verification_scores_lower_than_corroborated() -> None:
    members = [_member()]

    corroborated = compute_score(
        members=members,
        impact=ImpactLevel.MAJOR,
        verification=VerificationStatus.CORROBORATED,
        latest_published_at=NOW,
        event_time=NOW,
        now=NOW,
    )
    conflicting = compute_score(
        members=members,
        impact=ImpactLevel.MAJOR,
        verification=VerificationStatus.CONFLICTING,
        latest_published_at=NOW,
        event_time=NOW,
        now=NOW,
    )

    assert conflicting.score < corroborated.score


def test_breaking_override_requires_recent_breaking_major_story() -> None:
    members = [_member(article_type=ArticleType.BREAKING, credibility=CredibilityTier.TIER_1)]

    recent = compute_score(
        members=members,
        impact=ImpactLevel.MAJOR,
        verification=VerificationStatus.CORROBORATED,
        latest_published_at=NOW - timedelta(minutes=30),
        event_time=NOW - timedelta(minutes=30),
        now=NOW,
    )
    stale = compute_score(
        members=members,
        impact=ImpactLevel.MAJOR,
        verification=VerificationStatus.CORROBORATED,
        latest_published_at=NOW - timedelta(hours=4),
        event_time=NOW - timedelta(hours=4),
        now=NOW,
    )

    assert recent.breaking_override is True
    assert recent.score >= BREAKING_MIN_SCORE
    assert stale.breaking_override is False


def test_quality_is_clamped_to_floor() -> None:
    members = [_member(specificity=1, consequence=1)]

    result = compute_score(
        members=members,
        impact=ImpactLevel.MINOR,
        verification=VerificationStatus.SINGLE_SOURCE,
        latest_published_at=NOW,
        event_time=NOW,
        now=NOW,
    )

    assert result.quality == 0.5


def test_select_tier_initial_assignment() -> None:
    assert select_tier(60.0, previous=None) == (SelectionTier.PRIMARY, "initial_primary")
    assert select_tier(40.0, previous=None) == (SelectionTier.FILLER, "initial_filler")
    assert select_tier(20.0, previous=None) == (SelectionTier.DROP, "initial_drop")


def test_select_tier_breaking_override_promotes_to_primary() -> None:
    assert select_tier(10.0, previous=SelectionTier.DROP, breaking_override=True) == (
        SelectionTier.PRIMARY,
        "breaking_override",
    )


def test_select_tier_hysteresis_holds_primary_within_band() -> None:
    assert select_tier(
        PRIMARY_THRESHOLD - 4.0, previous=SelectionTier.PRIMARY
    ) == (SelectionTier.PRIMARY, "primary_held")


def test_select_tier_hysteresis_demotes_primary_below_band() -> None:
    assert select_tier(
        PRIMARY_THRESHOLD - 6.0, previous=SelectionTier.PRIMARY
    ) == (SelectionTier.FILLER, "demoted_from_primary")


def test_select_tier_drop_promotes_filler_only_above_upper_band() -> None:
    assert select_tier(
        FILLER_THRESHOLD + 4.0, previous=SelectionTier.DROP
    ) == (SelectionTier.DROP, "drop_held")
    assert select_tier(
        FILLER_THRESHOLD + 6.0, previous=SelectionTier.DROP
    ) == (SelectionTier.FILLER, "promoted_to_filler")


def test_select_tier_filler_drops_below_lower_band() -> None:
    assert select_tier(
        FILLER_THRESHOLD - 6.0, previous=SelectionTier.FILLER
    ) == (SelectionTier.DROP, "dropped_from_filler")
