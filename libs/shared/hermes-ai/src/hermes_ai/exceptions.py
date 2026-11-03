"""Typed exception hierarchy for hermes-ai."""


class HermesAiError(Exception):
    """Base exception for all errors raised by the hermes-ai library."""


class ConfigurationError(HermesAiError, ValueError):
    """Raised when required model credentials or configurations are invalid or missing."""


class ModelExecutionError(HermesAiError, RuntimeError):
    """Raised when upstream LLM calls fail across all router deployments."""

    def __init__(
        self,
        message: str,
        schema_name: str | None = None,
        original_exception: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.schema_name = schema_name
        self.original_exception = original_exception


class SchemaValidationError(HermesAiError, ValueError):
    """Raised when LLM output cannot be validated into the requested schema."""

    def __init__(
        self,
        message: str,
        schema_name: str | None = None,
        validation_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.schema_name = schema_name
        self.validation_error = validation_error


class RateLimitExceededError(HermesAiError, RuntimeError):
    """Raised when rate limit capacity is exhausted and non-blocking retry is unavailable."""


class CircuitBreakerOpenError(RateLimitExceededError):
    """Raised when the rate limiter's circuit breaker is active and requests are blocked."""

    def __init__(
        self,
        message: str = "circuit breaker is open.",
        cooldown_remaining: float | None = None,
    ) -> None:
        super().__init__(message)
        self.cooldown_remaining = cooldown_remaining


class GeocodingError(HermesAiError, RuntimeError):
    """Raised when geocoding fails or upstream geocoding resilience triggers an abort."""

    def __init__(
        self,
        message: str,
        location_name: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.location_name = location_name
        self.status_code = status_code
