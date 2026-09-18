import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exceptions import StarletteHTTPException
from hermes_api.core.exceptions import AppException

logger = logging.getLogger(__name__)



def register_err_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "err_code": exc.err_code,
                "err_msg": exc.message,
                "details": exc.details,
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "err_code": "VALIDATION_ERROR",
                "err_msg": "Invalid input data.",
                "details": { "errors": exc.errors() },
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "err_code": "HTTP_ERROR",
                "err_msg": exc.detail,
                "details": {}
            }
        )
    
    @app.exception_handler(Exception)
    async def universal_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled server error.")
        return JSONResponse(
            status_code=500,
            content={
                "err_code": "UNEXPECTED_SERVER_ERROR",
                "err_msg": "Something went wrong internally.",
                "details": {}
            }
        )