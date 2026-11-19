from __future__ import annotations
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from hermes_db.services import FamilyCandidate
from hermes_worker.jobs.fingerprints import cosine_similarity, hamming_distance_hex


MAX_TITLE_DISTANCE = 3
MAX_BODY_DISTANCE = 6
MIN_EMBEDDING_SIMILARITY = 0.97
MAX_DAY_DELTA = timedelta(hours=36)


@dataclass(frozen=True, slots=True)
class FamilyMatch:
    family_id: uuid.UUID
    rule: str
    score: float
    representative_time: datetime | None = None


def _same_window(
    left: datetime | None,
    right: datetime | None,
    *,
    max_delta: timedelta,
) -> bool:
    if left is None or right is None:
        return True
    return abs(left - right) <= max_delta


def find_family(
    candidates: Sequence[FamilyCandidate],
    *,
    title_simhash: str,
    body_simhash: str | None,
    embedding: Sequence[float] | None,
    event_time: datetime | None,
    max_title_distance: int = MAX_TITLE_DISTANCE,
    max_body_distance: int = MAX_BODY_DISTANCE,
    min_embedding_similarity: float = MIN_EMBEDDING_SIMILARITY,
    max_day_delta: timedelta = MAX_DAY_DELTA,
) -> FamilyMatch | None:
    """Return the strongest syndication-family match, if any.

    Families group copies of one published story. Matching requires the
    representative to fall inside the same event window, so a recurring
    headline from an older cycle cannot absorb a new incident.
    """
    best: FamilyMatch | None = None
    for candidate in candidates:
        if not _same_window(
            event_time,
            candidate.representative_time,
            max_delta=max_day_delta,
        ):
            continue

        title_distance = hamming_distance_hex(
            title_simhash,
            candidate.title_simhash,
        )
        if title_distance <= max_title_distance:
            score = 1.0 - title_distance / 64
            if best is None or score > best.score:
                best = FamilyMatch(
                    candidate.family_id,
                    "title",
                    score,
                    candidate.representative_time,
                )

        if body_simhash and candidate.body_simhash:
            body_distance = hamming_distance_hex(
                body_simhash,
                candidate.body_simhash,
            )
            if body_distance <= max_body_distance:
                score = 1.0 - body_distance / 64
                if best is None or score > best.score:
                    best = FamilyMatch(
                        candidate.family_id,
                        "body",
                        score,
                        candidate.representative_time,
                    )

        if embedding and candidate.representative_embedding:
            similarity = cosine_similarity(
                embedding,
                candidate.representative_embedding,
            )
            if similarity >= min_embedding_similarity and (
                best is None or similarity > best.score
            ):
                best = FamilyMatch(
                    candidate.family_id,
                    "embedding",
                    similarity,
                    candidate.representative_time,
                )

    return best


def origin_group(
    *,
    source_origin_group: str | None,
    source_slug: str | None,
) -> str:
    value = source_origin_group or source_slug or "unknown"
    return value.strip().lower()[:64] or "unknown"
