"""Tests for hermes_db.enums.

Validates that all enum members are correctly defined as StrEnum variants,
that string equality holds, and that membership / iteration semantics work.
These tests are intentionally lightweight — enums are pure Python data and
require no mocking or async machinery.
"""

import pytest

from hermes_db.enums import (
    ArticleType,
    CredibilityTier,
    EventScope,
    EventStatus,
    EventTlStatus,
    ImpactLevel,
    IngestStatus,
    SelectionTier,
    SourceType,
    ThreadKind,
    ThreadStatus,
    VerificationStatus,
)


# ---------------------------------------------------------------------------
# EventStatus
# ---------------------------------------------------------------------------


class TestEventStatus:
    def test_members_exist(self):
        """All three lifecycle members must be present."""
        assert EventStatus.ACTIVE
        assert EventStatus.STALE
        assert EventStatus.ARCHIVED

    def test_string_equality(self):
        """StrEnum values must compare equal to their raw string counterparts."""
        assert EventStatus.ACTIVE == "ACTIVE"
        assert EventStatus.STALE == "STALE"
        assert EventStatus.ARCHIVED == "ARCHIVED"

    def test_str_coercible(self):
        """StrEnum members must be usable as plain strings."""
        assert str(EventStatus.ACTIVE) == "ACTIVE"

    def test_membership(self):
        """All members are reachable via the enum class."""
        members = {m.value for m in EventStatus}
        assert members == {"ACTIVE", "STALE", "ARCHIVED"}

    @pytest.mark.parametrize(
        "value",
        ["ACTIVE", "STALE", "ARCHIVED"],
    )
    def test_construction_from_string(self, value: str):
        """EventStatus must be constructable from its string value."""
        assert EventStatus(value).value == value


# ---------------------------------------------------------------------------
# EventScope
# ---------------------------------------------------------------------------


class TestEventScope:
    def test_all_members_present(self):
        expected = {"GLOBAL", "COUNTRY", "STATE", "CITY", "LOCAL"}
        assert {m.value for m in EventScope} == expected

    @pytest.mark.parametrize(
        "value",
        ["GLOBAL", "COUNTRY", "STATE", "CITY", "LOCAL"],
    )
    def test_string_equality(self, value: str):
        assert EventScope(value) == value


# ---------------------------------------------------------------------------
# EventTlStatus
# ---------------------------------------------------------------------------


class TestEventTlStatus:
    def test_all_members_present(self):
        expected = {"READY", "GENERATING", "FAILED", "NO_CONTENT"}
        assert {m.value for m in EventTlStatus} == expected

    def test_default_generating(self):
        """GENERATING is used as the server-default in EventTl — it must exist."""
        assert EventTlStatus.GENERATING == "GENERATING"

    def test_no_content_member(self):
        """NO_CONTENT signals that a timeline could not be produced."""
        assert EventTlStatus.NO_CONTENT == "NO_CONTENT"


# ---------------------------------------------------------------------------
# SourceType
# ---------------------------------------------------------------------------


class TestSourceType:
    def test_all_members_present(self):
        expected = {"RSS", "API", "SCRAPE", "GDELT"}
        assert {m.value for m in SourceType} == expected

    def test_rss_is_default_string(self):
        assert SourceType.RSS == "RSS"


# ---------------------------------------------------------------------------
# ImpactLevel
# ---------------------------------------------------------------------------


class TestImpactLevel:
    def test_all_members_present(self):
        expected = {"CRITICAL", "MAJOR", "MODERATE", "MINOR"}
        assert {m.value for m in ImpactLevel} == expected

    @pytest.mark.parametrize(
        ("impact", "expected"),
        [
            (ImpactLevel.CRITICAL, "CRITICAL"),
            (ImpactLevel.MAJOR, "MAJOR"),
            (ImpactLevel.MODERATE, "MODERATE"),
            (ImpactLevel.MINOR, "MINOR"),
        ],
    )
    def test_string_equality(self, impact: ImpactLevel, expected: str):
        assert impact == expected


# ---------------------------------------------------------------------------
# CredibilityTier
# ---------------------------------------------------------------------------


class TestCredibilityTier:
    def test_all_tiers_present(self):
        expected = {"TIER_1", "TIER_2", "TIER_3", "TIER_4"}
        assert {m.value for m in CredibilityTier} == expected

    @pytest.mark.parametrize(
        ("tier", "expected"),
        [
            (CredibilityTier.TIER_1, "TIER_1"),
            (CredibilityTier.TIER_2, "TIER_2"),
            (CredibilityTier.TIER_3, "TIER_3"),
            (CredibilityTier.TIER_4, "TIER_4"),
        ],
    )
    def test_string_equality(self, tier: CredibilityTier, expected: str):
        assert tier == expected

    def test_tier_ordering_by_value(self):
        """Tiers are named in descending credibility order (TIER_1 is best)."""
        tiers = [t.value for t in CredibilityTier]
        assert tiers.index("TIER_1") < tiers.index("TIER_4")


# ---------------------------------------------------------------------------
# IngestStatus
# ---------------------------------------------------------------------------


class TestIngestStatus:
    def test_all_members_present(self):
        expected = {"NEW", "NORMALIZED", "LABELED", "CLUSTERED", "REJECTED"}
        assert {m.value for m in IngestStatus} == expected

    @pytest.mark.parametrize(
        "value",
        ["NEW", "NORMALIZED", "LABELED", "CLUSTERED", "REJECTED"],
    )
    def test_string_equality(self, value: str):
        assert IngestStatus(value) == value

    def test_new_is_default(self):
        assert IngestStatus.NEW == "NEW"


# ---------------------------------------------------------------------------
# ArticleType
# ---------------------------------------------------------------------------


class TestArticleType:
    def test_all_members_present(self):
        expected = {
            "BREAKING",
            "DEVELOPMENT",
            "ANALYSIS",
            "FEATURE",
            "OPINION",
            "LISTICLE",
            "OTHER",
        }
        assert {m.value for m in ArticleType} == expected

    @pytest.mark.parametrize(
        "value",
        [
            "BREAKING",
            "DEVELOPMENT",
            "ANALYSIS",
            "FEATURE",
            "OPINION",
            "LISTICLE",
            "OTHER",
        ],
    )
    def test_string_equality(self, value: str):
        assert ArticleType(value) == value

    def test_non_event_types_available(self):
        """Feature, opinion, and listicle must be available for PRIMARY gating."""
        assert ArticleType.FEATURE
        assert ArticleType.OPINION
        assert ArticleType.LISTICLE


# ---------------------------------------------------------------------------
# SelectionTier
# ---------------------------------------------------------------------------


class TestSelectionTier:
    def test_all_members_present(self):
        assert {m.value for m in SelectionTier} == {"PRIMARY", "FILLER", "DROP"}

    def test_drop_is_safe_default(self):
        assert SelectionTier.DROP == "DROP"
        assert SelectionTier.PRIMARY == "PRIMARY"
        assert SelectionTier.FILLER == "FILLER"


# ---------------------------------------------------------------------------
# VerificationStatus
# ---------------------------------------------------------------------------


class TestVerificationStatus:
    def test_all_members_present(self):
        expected = {"CONFIRMED", "SINGLE_SOURCE", "UNVERIFIED"}
        assert {m.value for m in VerificationStatus} == expected

    def test_single_source_is_explicit(self):
        assert VerificationStatus.SINGLE_SOURCE == "SINGLE_SOURCE"


# ---------------------------------------------------------------------------
# ThreadKind / ThreadStatus
# ---------------------------------------------------------------------------


class TestThreadKind:
    def test_all_members_present(self):
        assert {m.value for m in ThreadKind} == {"DEVELOPING", "TOPIC"}


class TestThreadStatus:
    def test_all_members_present(self):
        assert {m.value for m in ThreadStatus} == {"ACTIVE", "DORMANT", "ENDED"}
