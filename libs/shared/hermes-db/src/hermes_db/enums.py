import enum


class EventStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    ARCHIVED = "ARCHIVED"


class SelectionTier(enum.StrEnum):
    PRIMARY = "PRIMARY"
    FILLER = "FILLER"
    DROP = "DROP"


class VerificationStatus(enum.StrEnum):
    CONFIRMED = "CONFIRMED"
    SINGLE_SOURCE = "SINGLE_SOURCE"
    UNVERIFIED = "UNVERIFIED"


class ThreadKind(enum.StrEnum):
    DEVELOPING = "DEVELOPING"
    TOPIC = "TOPIC"


class ThreadStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    DORMANT = "DORMANT"
    ENDED = "ENDED"


class EventScope(enum.StrEnum):
    GLOBAL = "GLOBAL"
    COUNTRY = "COUNTRY"
    STATE = "STATE"
    CITY = "CITY"
    LOCAL = "LOCAL"


class IngestStatus(enum.StrEnum):
    NEW = "NEW"
    NORMALIZED = "NORMALIZED"
    ANALYZING = "ANALYZING"
    LABELED = "LABELED"
    CLUSTERED = "CLUSTERED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ArticleType(enum.StrEnum):
    BREAKING = "BREAKING"
    DEVELOPMENT = "DEVELOPMENT"
    ANALYSIS = "ANALYSIS"
    FEATURE = "FEATURE"
    OPINION = "OPINION"
    LISTICLE = "LISTICLE"
    OTHER = "OTHER"


class EventTlStatus(enum.StrEnum):
    READY = "READY"
    GENERATING = "GENERATING"
    FAILED = "FAILED"
    NO_CONTENT = "NO_CONTENT"


class SourceType(enum.StrEnum):
    RSS = "RSS"
    API = "API"
    SCRAPE = "SCRAPE"
    GDELT = "GDELT"


class ImpactLevel(enum.StrEnum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MODERATE = "MODERATE"
    MINOR = "MINOR"


class CredibilityTier(enum.StrEnum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"
    TIER_4 = "TIER_4"


class GeopoliticalBloc(enum.StrEnum):
    NORTH_AMERICA = "NORTH_AMERICA"
    EUROPE = "EUROPE"
    ASIA_PACIFIC = "ASIA_PACIFIC"
    MIDDLE_EAST_AFRICA = "MIDDLE_EAST_AFRICA"
    LATIN_AMERICA = "LATIN_AMERICA"
    GLOBAL_WIRE = "GLOBAL_WIRE"
