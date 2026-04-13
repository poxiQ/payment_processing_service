#!/usr/bin/env python
import pytest
import uuid
from httpx import AsyncClient


class TestAuthMiddleware:
    """
    Tests for AuthMiddleware
    Check that protected routes require an X-API Key,
    and public routes (blacklist_urls) are accessible without a key
    """

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_401(
        self, client: AsyncClient, payment_payload
    ):
        response = await client.post(
            "/api/v1/payments",
            json=payment_payload,
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

    @pytest.mark.asyncio
    async def test_wrong_api_key_returns_401(
        self, client: AsyncClient, payment_payload
    ):
        response = await client.post(
            "/api/v1/payments",
            json=payment_payload,
            headers={
                "X-API-Key": "totally-wrong-key-xyz",
                "Idempotency-Key": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_empty_api_key_returns_401(
        self, client: AsyncClient, payment_payload
    ):
        response = await client.post(
            "/api/v1/payments",
            json=payment_payload,
            headers={
                "X-API-Key": "",
                "Idempotency-Key": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path", ["/api/v1/general/check", "/docs", "/openapi.json"]
    )
    async def test_public_routes_accessible_without_api_key(
        self, client: AsyncClient, path: str
    ):
        response = await client.get(path)
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_valid_api_key_grants_access(
        self, client: AsyncClient, valid_headers, payment_payload
    ):
        response = await client.post(
            "/api/v1/payments",
            json=payment_payload,
            headers=valid_headers,
        )
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_get_payment_without_api_key_returns_401(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/payments/{fake_id}")
        assert response.status_code == 401
