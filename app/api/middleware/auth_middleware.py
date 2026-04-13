#!/usr/bin/env python
from typing import Any

from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.config import settings


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, blacklist_urls: list):
        super().__init__(app)
        self.blacklist_urls = blacklist_urls or []

    async def dispatch(self, request: Request, call_next) -> Any:
        x_api_key = request.headers.get("X-API-Key")
        path = request.url.path
        if path not in self.blacklist_urls and x_api_key != settings.API_KEY:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid API key"},
            )
        return await call_next(request)
