#!/usr/bin/env python
import traceback

from api.schemas import ErrorResponse
from fastapi import Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

from core.config import settings

common_responses = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
}


def get_error_response(exc, request=None) -> dict:
    """
    Generic error handling function
    """
    msg = exc
    if isinstance(exc, HTTPException):
        msg = exc.detail

    error_response = {"error": True, "message": str(msg)}

    # Return traceback info if debug mode is on
    if settings.DEBUG:
        error_response["traceback"] = "".join(
            traceback.format_exception(exc, value=exc, tb=exc.__traceback__)
        )

    return error_response


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handling error in validating requests
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=get_error_response(request=request, exc=exc),
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=get_error_response(request=request, exc=exc),
    )


async def debug_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=get_error_response(request=request, exc=exc),
    )
