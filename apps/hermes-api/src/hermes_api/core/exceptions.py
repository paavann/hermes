from fastapi import status


class AppException(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    err_code: str = "INTERNAL_SERVER_ERROR"
    message: str = "An unexpected error occurred. Please try again later."

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ):
        if message:
            self.message = message
        self.details = details or {}
        self.headers = headers or {}
        super().__init__(self.message)


class EventNotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    err_code = "EVENT_NOT_FOUND"
    message = "The requested event could not be found."

    def __init__(self, event_id: str | object):
        super().__init__(details={"event_id": str(event_id)})


class TlGenErr(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    err_code = "TIMELINE_GENERATION_ERROR"
    message = "An error occurred while generating the timeline. Please try again later."

    def __init__(self, event_id: str | object):
        super().__init__(details={"event_id": str(event_id)})


class WikiSearchException(AppException):
    status_code = status.HTTP_502_BAD_GATEWAY
    err_code = "WIKIPEDIA_SEARCH_ERROR"
    message = "An error occurred while searching Wikipedia. Please try again later."

    def __init__(self, query: str):
        super().__init__(details={"query": query})


class ChatRateLimitExceeded(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    err_code = "CHAT_RATE_LIMIT_EXCEEDED"
    message = "Too many chat requests. Please retry shortly."

    def __init__(
        self,
        retry_after_seconds: int,
        *,
        limit: int | None = None,
        remaining: int = 0,
        headers: dict[str, str] | None = None,
    ) -> None:
        retry_after = max(1, int(retry_after_seconds))
        merged = {
            "Retry-After": str(retry_after),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Reset": str(retry_after),
        }
        if limit is not None:
            merged["X-RateLimit-Limit"] = str(limit)
        if headers:
            merged.update(headers)
        super().__init__(
            details={"retry_after": retry_after},
            headers=merged,
        )


class ChatBudgetExhausted(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    err_code = "CHAT_BUDGET_EXHAUSTED"
    message = "The daily chat budget is exhausted. Please retry after the reset."

    def __init__(
        self,
        retry_after_seconds: int,
        *,
        limit: int | None = None,
        used: int | None = None,
        reserved: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        retry_after = max(1, int(retry_after_seconds))
        merged = {
            "Retry-After": str(retry_after),
            "X-RateLimit-Reset": str(retry_after),
        }
        if headers:
            merged.update(headers)
        details: dict[str, object] = {"retry_after": retry_after}
        if limit is not None:
            details["limit"] = limit
        if used is not None:
            details["used"] = used
        if reserved is not None:
            details["reserved"] = reserved
        super().__init__(details=details, headers=merged)


class ChatUnavailable(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    err_code = "CHAT_UNAVAILABLE"
    message = "Conversational chat is currently unavailable."

    def __init__(
        self,
        reason: str | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        details: dict[str, object] = {}
        if reason:
            details["reason"] = reason
        super().__init__(details=details, headers=headers)


class ChatBusy(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    err_code = "CHAT_BUSY"
    message = "The chat service is busy. Please retry shortly."

    def __init__(
        self,
        retry_after_seconds: int = 1,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        retry_after = max(1, int(retry_after_seconds))
        merged = {"Retry-After": str(retry_after)}
        if headers:
            merged.update(headers)
        super().__init__(
            details={"retry_after": retry_after},
            headers=merged,
        )
