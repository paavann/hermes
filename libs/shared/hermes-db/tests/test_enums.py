"""Tests for hermes_db.enums.

Validates that all enum members are correctly defined as StrEnum variants,
that string equality holds, and that membership / iteration semantics work.
These tests are intentionally lightweight — enums are pure Python data and
require no mocking or async machinery.
"""

import pytest

from hermes_db.enums import (
    CredibilityTier,
    EventScope,
    EventStatus,
    EventTlStatus,
    SourceType,
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
        expected = {"RSS", "API", "SCRAPE"}
        assert {m.value for m in SourceType} == expected

    def test_rss_is_default_string(self):
        assert SourceType.RSS == "RSS"


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
