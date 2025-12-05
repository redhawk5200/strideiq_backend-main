from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.exceptions.errors import ApplicationException
import logging

logger = logging.getLogger(__name__)

async def application_exception_handler(request: Request, exc: ApplicationException):
    logger.warning(f"Application error: {exc.message}")
    return exc.to_response()

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {repr(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred"}
    )