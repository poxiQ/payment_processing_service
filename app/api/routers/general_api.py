#!/usr/bin/env python
import sys

import aiofiles
from core.config import settings
from exception_handler import common_responses
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from schemas.general_schemas import GetDeploymentInformationResponse
from starlette.responses import PlainTextResponse

general_router = APIRouter(
    prefix=f"{settings.API_PREFIX}/general",
    tags=["general"],
)


@general_router.get(
    "/about",
    name="general:get_deployment_information",
    response_model=GetDeploymentInformationResponse,
    responses={**common_responses},
)
def get_deployment_information() -> JSONResponse:
    content = {
        "python_version": sys.version,
    }
    return JSONResponse(content=content, status_code=status.HTTP_200_OK)


@general_router.get(
    "/check",
    name="general:check",
)
async def healthcheck() -> PlainTextResponse:
    async with aiofiles.open("/commit.txt", mode="r") as f:
        return PlainTextResponse(status_code=status.HTTP_200_OK, content=await f.read())
