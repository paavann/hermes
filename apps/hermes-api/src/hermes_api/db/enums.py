import enum


class EventStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    ARCHIVED = "ARCHIVED"


class EventScope(str, enum.Enum):
    GLOBAL = "GLOBAL"
    COUNTRY = "COUNTRY"
    STATE = "STATE"
    CITY = "CITY"
    LOCAL = "LOCAL"


class SourceType(str, enum.Enum):
    RSS = "RSS"
    API = "API"
    SCRAPE = "SCRAPE"


class CredibilityTier(str, enum.Enum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"
    TIER_4 = "TIER_4"
