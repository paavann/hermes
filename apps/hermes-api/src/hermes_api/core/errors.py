import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, StarletteHTTPException
from fastapi.responses import JSONResponse
from hermes_api.core.exceptions import AppException


logger = logging.getLogger(__name__)


def _cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin")
    if origin:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    else:
        return {}


def register_err_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "err_code": exc.err_code,
                "err_msg": exc.message,
                "details": exc.details,
            },
            headers=_cors_headers(request),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=422,
            content={
                "err_code": "VALIDATION_ERROR",
                "err_msg": "Invalid input data.",
                "details": {"errors": exc.errors()},
            },
            headers=_cors_headers(request),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"err_code": "HTTP_ERROR", "err_msg": exc.detail, "details": {}},
            headers=_cors_headers(request),
        )

    @app.exception_handler(Exception)
    async def universal_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled server error.")
        return JSONResponse(
            status_code=500,
            content={
                "err_code": "UNEXPECTED_SERVER_ERROR",
                "err_msg": "Something went wrong internally.",
                "details": {},
            },
            headers=_cors_headers(request),
        )
