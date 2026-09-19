from typing import Optional, Union
from fastapi import status





class AppException(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    err_code: str = "INTERNAL_SERVER_ERROR"
    message: str = "An unexpected error occurred. Please try again later."

    def __init__(self, message: Optional[str] = None, details: Optional[dict] = None):
        if message:
            self.message = message
        self.details = details or {}
        super().__init__(self.message)



class EventNotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    err_code = "EVENT_NOT_FOUND"
    message = "The requested event could not be found."

    def __init__(self, event_id: Union[str, object]):
        super().__init__(details={ "event_id": str(event_id) })



class TlGenErr(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    err_code = "TIMELINE_GENERATION_ERROR"
    message = "An error occurred while generating the timeline. Please try again later."

    def __init__(self, event_id: Union[str, object]):
        super().__init__(details={ "event_id": str(event_id) })



class WikiSearchException(AppException):
    status_code = status.HTTP_502_BAD_GATEWAY
    err_code = "WIKIPEDIA_SEARCH_ERROR"
    message = "An error occurred while searching Wikipedia. Please try again later."

    def __init__(self, query: str):
        super().__init__(details={ "query": query })
