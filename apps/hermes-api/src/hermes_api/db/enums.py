import enum


class EventStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    ARCHIVED = "ARCHIVED"


class EventScope(enum.StrEnum):
    GLOBAL = "GLOBAL"
    COUNTRY = "COUNTRY"
    STATE = "STATE"
    CITY = "CITY"
    LOCAL = "LOCAL"


class SourceType(enum.StrEnum):
    RSS = "RSS"
    API = "API"
    SCRAPE = "SCRAPE"


class CredibilityTier(enum.StrEnum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"
    TIER_4 = "TIER_4"


class EventTlStatus(enum.StrEnum):
    READY = "READY"
    GENERATING = "GENERATING"
    FAILED = "FAILED"
    NO_CONTENT = "NO_CONTENT"
