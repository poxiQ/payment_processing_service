#!/usr/bin/env python
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from api.routers.payment_api import payments_router
from core.exception_handler import (
    http_exception_handler,
    validation_exception_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger = logging.getLogger("app.client")
    app_logger.setLevel("WARN")
    yield


def get_application():
    app = FastAPI(
        title="Payment API service",
        description="Asynchronous payment processing service",
        version="0.0.1",
        terms_of_service=None,
        contact=None,
        license_info=None,
        lifespan=lifespan,
    )

    app.add_middleware(CORSMiddleware, allow_origins=["*"])

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    app.include_router(payments_router)

    return app


app = get_application()


@app.get("/about", tags=["common"])
def get_deployment_information() -> JSONResponse:
    return JSONResponse(
        {
            "sys.version": sys.version,
        }
    )
