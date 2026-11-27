import enum


class EventStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    ARCHIVED = "ARCHIVED"
    MERGED = "MERGED"


class SelectionTier(enum.StrEnum):
    PRIMARY = "PRIMARY"
    FILLER = "FILLER"
    DROP = "DROP"


class VerificationStatus(enum.StrEnum):
    CONFIRMED = "CONFIRMED"
    CORROBORATED = "CORROBORATED"
    SINGLE_SOURCE = "SINGLE_SOURCE"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"


class AssignmentMethod(enum.StrEnum):
    """How an article was attached to an event."""

    AUTO = "AUTO"
    LLM = "LLM"
    MANUAL = "MANUAL"


class ClusterDecisionKind(enum.StrEnum):
    """Cached pairwise clustering adjudication."""

    SAME = "SAME"
    DIFFERENT = "DIFFERENT"
    UNSURE = "UNSURE"


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


class EventForm(enum.StrEnum):
    """What kind of real-world occurrence an article reports."""

    INCIDENT = "INCIDENT"
    PLANNED_EVENT = "PLANNED_EVENT"
    POLICY_ACTION = "POLICY_ACTION"
    STATEMENT = "STATEMENT"
    REPORT = "REPORT"
    MARKET_MOVE = "MARKET_MOVE"
    OTHER = "OTHER"


class ArticleCertainty(enum.StrEnum):
    """How strongly the article's central claim is established."""

    CONFIRMED = "CONFIRMED"
    REPORTED = "REPORTED"
    ALLEGED = "ALLEGED"
    DISPUTED = "DISPUTED"


class ArticleCategory(enum.StrEnum):
    """Closed category taxonomy shared by labels and event presentation."""

    CONFLICT = "CONFLICT"
    DISASTER = "DISASTER"
    ECONOMY = "ECONOMY"
    POLITICS = "POLITICS"
    TECHNOLOGY = "TECHNOLOGY"
    SCIENCE = "SCIENCE"
    HEALTH = "HEALTH"
    ENVIRONMENT = "ENVIRONMENT"
    SPORTS = "SPORTS"
    ENTERTAINMENT = "ENTERTAINMENT"
    OTHER = "OTHER"


class ArticleBodySource(enum.StrEnum):
    """Where the text sent to the labeler came from."""

    FULL_TEXT = "FULL_TEXT"
    FEED_SUMMARY = "FEED_SUMMARY"


class RejectStage(enum.StrEnum):
    """Why an analyzed article was not allowed into clustering."""

    LABEL = "LABEL"
    GATE = "GATE"


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


class SourceFeedProvider(enum.StrEnum):
    """Where a source's article links originate.

    PUBLISHER feeds carry the publisher's own URLs; GOOGLE_NEWS feeds carry
    opaque news.google.com redirect links; GDELT results come from the GDELT
    document API.
    """

    PUBLISHER = "PUBLISHER"
    GOOGLE_NEWS = "GOOGLE_NEWS"
    GDELT = "GDELT"


class SourceFetchPolicy(enum.StrEnum):
    """How much article text the analyze stage may load for a source."""

    FULL_TEXT = "FULL_TEXT"
    SUMMARY_ONLY = "SUMMARY_ONLY"


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


class EventRelationshipType(enum.StrEnum):
    CAUSED = "CAUSED"
    FOLLOW_UP = "FOLLOW_UP"
    REACTION = "REACTION"
    RELATED = "RELATED"
