from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from hermes_db.enums import ArticleCertainty, VerificationStatus


@dataclass(frozen=True, slots=True)
class MemberEvidence:
    """The independence signals of one member article."""

    article_id: uuid.UUID
    family_id: uuid.UUID | None
    family_origin_group: str | None
    source_id: uuid.UUID | None
    source_origin_group: str | None
    source_slug: str | None
    certainty: ArticleCertainty | None


@dataclass(frozen=True, slots=True)
class VerificationResult:
    status: VerificationStatus
    family_count: int
    source_count: int
    independent_origin_count: int
    reason: str


def _origin_key(member: MemberEvidence) -> str:
    if member.family_id is not None:
        group = member.family_origin_group or member.source_origin_group
        return f"family:{(group or member.family_id).strip().lower()}"
    group = member.source_origin_group or member.source_slug
    if group:
        return f"origin:{group.strip().lower()}"
    return f"article:{member.article_id}"


def compute_verification(
    members: Sequence[MemberEvidence],
) -> VerificationResult:
    """Derive verification from syndication families and origin groups.

    A family is one piece of evidence regardless of how many outlets published
    the same copy. Two independent origins corroborate; an authoritative
    CONFIRMED label promotes corroboration to CONFIRMED. A DISPUTED central
    claim overrides everything else.
    """
    if not members:
        return VerificationResult(
            status=VerificationStatus.UNVERIFIED,
            family_count=0,
            source_count=0,
            independent_origin_count=0,
            reason="no_members",
        )

    family_keys = {
        f"family:{member.family_id}" if member.family_id else f"article:{member.article_id}"
        for member in members
    }
    sources = {member.source_id for member in members if member.source_id is not None}
    origins = {_origin_key(member) for member in members}

    if any(member.certainty == ArticleCertainty.DISPUTED for member in members):
        status = VerificationStatus.CONFLICTING
        reason = "disputed_claim"
    elif len(origins) >= 2:
        if any(member.certainty == ArticleCertainty.CONFIRMED for member in members):
            status = VerificationStatus.CONFIRMED
            reason = "independent_origins_confirmed"
        else:
            status = VerificationStatus.CORROBORATED
            reason = "independent_origins"
    else:
        status = VerificationStatus.SINGLE_SOURCE
        reason = "single_origin"

    return VerificationResult(
        status=status,
        family_count=len(family_keys),
        source_count=len(sources),
        independent_origin_count=len(origins),
        reason=reason,
    )
