import math
from collections.abc import Sequence
from datetime import datetime

from hermes_db.enums import CredibilityTier, GeopoliticalBloc, ImpactLevel


CREDIBILITY_WEIGHTS: dict[CredibilityTier, float] = {
    CredibilityTier.TIER_1: 3.0,
    CredibilityTier.TIER_2: 2.0,
    CredibilityTier.TIER_3: 1.0,
    CredibilityTier.TIER_4: 0.5,
}

IMPACT_MULTIPLIERS: dict[ImpactLevel, float] = {
    ImpactLevel.CRITICAL: 2.0,
    ImpactLevel.MAJOR: 1.5,
    ImpactLevel.MODERATE: 1.0,
    ImpactLevel.MINOR: 0.8,
}

HALF_LIFE_HOURS: float = 18.0
HOURLY_DECAY_FACTOR: float = 2.0 ** (-1.0 / HALF_LIFE_HOURS)

SOURCE_BLOC_MAP: dict[str, GeopoliticalBloc] = {
    "reuters-wire": GeopoliticalBloc.GLOBAL_WIRE,
    "reuters": GeopoliticalBloc.GLOBAL_WIRE,
    "ap-wire": GeopoliticalBloc.GLOBAL_WIRE,
    "associated-press": GeopoliticalBloc.GLOBAL_WIRE,
    "afp-wire": GeopoliticalBloc.GLOBAL_WIRE,
    "agence-france-presse": GeopoliticalBloc.GLOBAL_WIRE,
    "bbc-world": GeopoliticalBloc.EUROPE,
    "bbc": GeopoliticalBloc.EUROPE,
    "guardian-world": GeopoliticalBloc.EUROPE,
    "the-guardian": GeopoliticalBloc.EUROPE,
    "dw-world": GeopoliticalBloc.EUROPE,
    "deutsche-welle": GeopoliticalBloc.EUROPE,
    "france24-world": GeopoliticalBloc.EUROPE,
    "france-24": GeopoliticalBloc.EUROPE,
    "euronews-world": GeopoliticalBloc.EUROPE,
    "euronews": GeopoliticalBloc.EUROPE,
    "politico-europe": GeopoliticalBloc.EUROPE,
    "pbs-newshour": GeopoliticalBloc.NORTH_AMERICA,
    "nyt-world": GeopoliticalBloc.NORTH_AMERICA,
    "new-york-times": GeopoliticalBloc.NORTH_AMERICA,
    "npr-world": GeopoliticalBloc.NORTH_AMERICA,
    "npr": GeopoliticalBloc.NORTH_AMERICA,
    "cbc-world": GeopoliticalBloc.NORTH_AMERICA,
    "cbc": GeopoliticalBloc.NORTH_AMERICA,
    "wsj-world": GeopoliticalBloc.NORTH_AMERICA,
    "wall-street-journal": GeopoliticalBloc.NORTH_AMERICA,
    "wapo-world": GeopoliticalBloc.NORTH_AMERICA,
    "washington-post": GeopoliticalBloc.NORTH_AMERICA,
    "cnn-world": GeopoliticalBloc.NORTH_AMERICA,
    "cnn": GeopoliticalBloc.NORTH_AMERICA,
    "abc-international": GeopoliticalBloc.NORTH_AMERICA,
    "abc-news": GeopoliticalBloc.NORTH_AMERICA,
    "nhk-world": GeopoliticalBloc.ASIA_PACIFIC,
    "nhk": GeopoliticalBloc.ASIA_PACIFIC,
    "aljazeera": GeopoliticalBloc.MIDDLE_EAST_AFRICA,
    "al-jazeera": GeopoliticalBloc.MIDDLE_EAST_AFRICA,
}


def calculate_shannon_diversity(
    blocs: Sequence[GeopoliticalBloc | str],
) -> float:
    if not blocs or len(blocs) <= 1:
        return 1.0

    counts: dict[str, int] = {}
    for bloc in blocs:
        key = bloc.value if isinstance(bloc, GeopoliticalBloc) else bloc
        counts[key] = counts.get(key, 0) + 1

    total = len(blocs)
    h = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            h -= p * math.log(p)

    multiplier = 1.0 + min(h, 1.0) * 0.5
    return round(multiplier, 4)


def calculate_velocity(
    article_count: int,
    first_reported_at: datetime,
    last_reported_at: datetime,
) -> float:
    if article_count <= 1:
        return 1.0

    t1 = (
        first_reported_at.replace(tzinfo=None)
        if first_reported_at.tzinfo
        else first_reported_at
    )
    t2 = (
        last_reported_at.replace(tzinfo=None)
        if last_reported_at.tzinfo
        else last_reported_at
    )
    delta_hours = max((t2 - t1).total_seconds() / 3600.0, 0.0)
    return round(article_count / max(delta_hours, 1.0), 2)


def calculate_velocity_multiplier(velocity: float) -> float:
    if velocity <= 1.0:
        return 1.0
    return round(1.0 + min((velocity - 1.0) * 0.2, 1.0), 4)
