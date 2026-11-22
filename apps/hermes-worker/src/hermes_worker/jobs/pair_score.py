from __future__ import annotations
import math
from dataclasses import dataclass
from datetime import datetime
from hermes_db.enums import EventForm, EventScope
from hermes_db.services import AssignableArticle, EventCandidate, EventPairState
from hermes_worker.jobs.fingerprints import cosine_similarity, normalize_tokens


EMBEDDING_WEIGHT = 0.40
ENTITY_WEIGHT = 0.20
LOCATION_WEIGHT = 0.15
TIME_WEIGHT = 0.15
ACTION_WEIGHT = 0.10

AUTO_ATTACH_THRESHOLD = 0.80
LLM_BAND_THRESHOLD = 0.60

MERGE_AUTO_THRESHOLD = 0.92
MERGE_GRAY_THRESHOLD = 0.85
MERGE_EMBEDDING_WEIGHT = 0.40
MERGE_ENTITY_WEIGHT = 0.20
MERGE_LOCATION_WEIGHT = 0.15
MERGE_TIME_WEIGHT = 0.10
MERGE_CATEGORY_WEIGHT = 0.05
MERGE_FAMILY_WEIGHT = 0.10

TIME_HALF_LIFE_HOURS = 48.0
MAX_TIME_DELTA_DAYS = 7
LOCATION_VETO_METERS = 100_000.0
LOCAL_SCOPES = frozenset({EventScope.CITY, EventScope.LOCAL})

INCOMPATIBLE_FORMS: dict[EventForm, frozenset[EventForm]] = {
    EventForm.INCIDENT: frozenset(
        {EventForm.PLANNED_EVENT, EventForm.POLICY_ACTION, EventForm.MARKET_MOVE}
    ),
    EventForm.PLANNED_EVENT: frozenset(
        {EventForm.INCIDENT, EventForm.MARKET_MOVE, EventForm.STATEMENT}
    ),
    EventForm.POLICY_ACTION: frozenset({EventForm.INCIDENT, EventForm.MARKET_MOVE}),
    EventForm.MARKET_MOVE: frozenset(
        {
            EventForm.INCIDENT,
            EventForm.PLANNED_EVENT,
            EventForm.POLICY_ACTION,
            EventForm.STATEMENT,
            EventForm.REPORT,
        }
    ),
    EventForm.STATEMENT: frozenset(
        {EventForm.INCIDENT, EventForm.MARKET_MOVE, EventForm.PLANNED_EVENT}
    ),
}

ACTION_WORDS = frozenset(
    {
        "announced",
        "approved",
        "arrested",
        "attacked",
        "banned",
        "beat",
        "blocked",
        "bombed",
        "cancelled",
        "captured",
        "charged",
        "closed",
        "collapsed",
        "confirmed",
        "cut",
        "damaged",
        "declared",
        "deployed",
        "destroyed",
        "died",
        "elected",
        "erupted",
        "evacuated",
        "exploded",
        "fired",
        "hit",
        "imposed",
        "injured",
        "killed",
        "landed",
        "launched",
        "lifted",
        "lost",
        "met",
        "opened",
        "passed",
        "protested",
        "raised",
        "rejected",
        "released",
        "resigned",
        "rescued",
        "seized",
        "sentenced",
        "signed",
        "struck",
        "suspended",
        "warned",
        "wounded",
        "won",
    }
)


@dataclass(frozen=True, slots=True)
class GeoLocation:
    name: str
    country_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True, slots=True)
class PairScore:
    score: float
    components: dict[str, float]
    veto: str | None = None
    auto_threshold: float = AUTO_ATTACH_THRESHOLD
    gray_threshold: float = LLM_BAND_THRESHOLD

    @property
    def band(self) -> str:
        if self.veto is not None:
            return "separate"
        if self.score >= self.auto_threshold:
            return "auto"
        if self.score >= self.gray_threshold:
            return "llm"
        return "separate"


def haversine_meters(
    left_lat: float,
    left_lon: float,
    right_lat: float,
    right_lon: float,
) -> float:
    radius = 6_371_000.0
    phi_left = math.radians(left_lat)
    phi_right = math.radians(right_lat)
    delta_phi = math.radians(right_lat - left_lat)
    delta_lambda = math.radians(right_lon - left_lon)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi_left) * math.cos(phi_right) * math.sin(delta_lambda / 2.0) ** 2
    )
    return 2.0 * radius * math.asin(min(1.0, math.sqrt(a)))


def normalize_entities(raw: object) -> frozenset[str]:
    names: set[str] = set()
    if isinstance(raw, (list, tuple)):
        for item in raw:
            if isinstance(item, dict):
                name = item.get("name")
            elif isinstance(item, str):
                name = item
            else:
                name = None
            if isinstance(name, str) and name.strip():
                names.add(_normalize_name(name))
    return frozenset(names)


def _normalize_name(value: str) -> str:
    cleaned = " ".join(value.casefold().split())
    return cleaned.removeprefix("the ")


def article_entities(article: AssignableArticle) -> frozenset[str]:
    return normalize_entities(article.entities)


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 0.5
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.5
    return len(left & right) / len(union)


def _time_proximity(
    article_time: datetime | None,
    event_time: datetime | None,
) -> tuple[float, bool]:
    if article_time is None or event_time is None:
        return 0.5, False
    delta_hours = abs((article_time - event_time).total_seconds()) / 3600.0
    if delta_hours > MAX_TIME_DELTA_DAYS * 24:
        return 0.0, True
    return math.exp(-delta_hours / TIME_HALF_LIFE_HOURS), False


def _location_match(
    *,
    article: AssignableArticle,
    location: GeoLocation | None,
    candidate: EventCandidate,
) -> tuple[float, bool]:
    event_locations = [item for item in candidate.locations if isinstance(item, dict)]
    has_event_location = bool(event_locations) or (
        candidate.latitude is not None and candidate.longitude is not None
    )
    if location is None and not has_event_location:
        return 0.5, False
    if location is None or not has_event_location:
        return 0.4, False

    best = 0.0
    veto = False
    article_name = _normalize_name(location.name)
    for item in event_locations:
        raw_name = item.get("name")
        event_name = _normalize_name(raw_name) if isinstance(raw_name, str) else ""
        if article_name and event_name and article_name == event_name:
            return 1.0, False
        country = item.get("country_code")
        if (
            location.country_code
            and isinstance(country, str)
            and location.country_code.upper() == country.upper()
        ):
            best = max(best, 0.6)
        elif (
            article_name
            and event_name
            and (article_name in event_name or event_name in article_name)
        ):
            best = max(best, 0.5)

    if (
        location.latitude is not None
        and location.longitude is not None
        and candidate.latitude is not None
        and candidate.longitude is not None
    ):
        distance = haversine_meters(
            location.latitude,
            location.longitude,
            candidate.latitude,
            candidate.longitude,
        )
        if distance <= 50_000.0:
            best = max(best, 1.0)
        elif distance <= LOCATION_VETO_METERS:
            best = max(best, 0.7)
        elif (
            article.scope in LOCAL_SCOPES
            and candidate.scope in LOCAL_SCOPES
            and distance > LOCATION_VETO_METERS
        ):
            veto = True

    if (
        not veto
        and article.scope in LOCAL_SCOPES
        and candidate.scope in LOCAL_SCOPES
        and location.country_code
        and candidate.country_code
        and location.country_code.upper() != candidate.country_code.upper()
    ):
        veto = True

    return best, veto


def _action_overlap(article: AssignableArticle, candidate: EventCandidate) -> float:
    left = {token for token in normalize_tokens(article.fact) if token in ACTION_WORDS}
    right = {
        token
        for token in normalize_tokens(
            f"{candidate.ai_headline} {candidate.ai_summary or ''}"
        )
        if token in ACTION_WORDS
    }
    if not left and not right:
        return 0.5
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def _event_location_match(
    left: EventPairState,
    right: EventPairState,
) -> tuple[float, bool]:
    if (
        left.country_code
        and right.country_code
        and left.country_code.upper() != right.country_code.upper()
    ):
        return 0.0, True
    if (
        left.latitude is not None
        and left.longitude is not None
        and right.latitude is not None
        and right.longitude is not None
    ):
        distance = haversine_meters(
            left.latitude,
            left.longitude,
            right.latitude,
            right.longitude,
        )
        if distance > LOCATION_VETO_METERS:
            return 0.0, True
        return 1.0 - distance / LOCATION_VETO_METERS, False
    if (
        left.location_name
        and right.location_name
        and _normalize_name(left.location_name) == _normalize_name(right.location_name)
    ):
        return 1.0, False
    if left.country_code and left.country_code == right.country_code:
        return 0.6, False
    return 0.4, False


def score_event_pair(
    left: EventPairState,
    right: EventPairState,
    *,
    left_entities: frozenset[str],
    right_entities: frozenset[str],
    shared_families: int,
) -> PairScore:
    """Score whether two events describe the same incident."""
    time_score, time_veto = _time_proximity(
        left.event_time or left.latest_published_at,
        right.event_time or right.latest_published_at,
    )
    if time_veto:
        return PairScore(score=0.0, components={"veto": 0.0}, veto="time_window")

    location_score, location_veto = _event_location_match(left, right)
    if location_veto:
        return PairScore(score=0.0, components={"veto": 0.0}, veto="location")

    if left_entities and right_entities and not (left_entities & right_entities):
        return PairScore(score=0.0, components={"veto": 0.0}, veto="entities")

    embedding_score = 0.0
    if (
        left.embedding is not None
        and right.embedding is not None
        and left.embedding_model == right.embedding_model
    ):
        embedding_score = max(
            0.0,
            cosine_similarity(left.embedding, right.embedding),
        )

    components = {
        "embedding": round(embedding_score, 4),
        "entities": round(_jaccard(left_entities, right_entities), 4),
        "location": round(location_score, 4),
        "time": round(time_score, 4),
        "category": 1.0 if left.category == right.category else 0.0,
        "family": round(min(1.0, shared_families / 2.0), 4),
    }
    score = (
        MERGE_EMBEDDING_WEIGHT * components["embedding"]
        + MERGE_ENTITY_WEIGHT * components["entities"]
        + MERGE_LOCATION_WEIGHT * components["location"]
        + MERGE_TIME_WEIGHT * components["time"]
        + MERGE_CATEGORY_WEIGHT * components["category"]
        + MERGE_FAMILY_WEIGHT * components["family"]
    )
    return PairScore(
        score=round(score, 4),
        components=components,
        auto_threshold=MERGE_AUTO_THRESHOLD,
        gray_threshold=MERGE_GRAY_THRESHOLD,
    )


def score_pair(
    article: AssignableArticle,
    candidate: EventCandidate,
    *,
    article_location: GeoLocation | None,
) -> PairScore:
    components: dict[str, float] = {}

    if (
        article.event_form is not None
        and candidate.event_form is not None
        and article.event_form in INCOMPATIBLE_FORMS
        and candidate.event_form in INCOMPATIBLE_FORMS[article.event_form]
    ):
        return PairScore(score=0.0, components={"veto": 0.0}, veto="event_form")

    time_score, time_veto = _time_proximity(
        article.effective_time,
        candidate.event_time or candidate.latest_published_at,
    )
    if time_veto:
        return PairScore(score=0.0, components={"veto": 0.0}, veto="time_window")

    location_score, location_veto = _location_match(
        article=article,
        location=article_location,
        candidate=candidate,
    )
    if location_veto:
        return PairScore(score=0.0, components={"veto": 0.0}, veto="location")

    article_entity_set = article_entities(article)
    event_entity_set = candidate.entities
    if (
        article_entity_set
        and event_entity_set
        and not (article_entity_set & event_entity_set)
    ):
        return PairScore(score=0.0, components={"veto": 0.0}, veto="entities")

    embedding_score = 0.0
    if (
        article.embedding is not None
        and candidate.embedding is not None
        and article.embedding_model == candidate.embedding_model
    ):
        embedding_score = max(
            0.0,
            cosine_similarity(article.embedding, candidate.embedding),
        )

    components = {
        "embedding": round(embedding_score, 4),
        "entities": round(_jaccard(article_entity_set, event_entity_set), 4),
        "location": round(location_score, 4),
        "time": round(time_score, 4),
        "action": round(_action_overlap(article, candidate), 4),
    }
    score = (
        EMBEDDING_WEIGHT * components["embedding"]
        + ENTITY_WEIGHT * components["entities"]
        + LOCATION_WEIGHT * components["location"]
        + TIME_WEIGHT * components["time"]
        + ACTION_WEIGHT * components["action"]
    )
    return PairScore(score=round(score, 4), components=components)
