#!/usr/bin/env python
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select, func
from api.database.models import Payment, OutboxEvent


class TestIdempotency:
    """
    Verify that a repeat request with the same Idempotency Key
    returns the same payment, without creating duplicates.
    """

    @pytest.mark.asyncio
    async def test_duplicate_request_returns_same_payment(
        self,
        client: AsyncClient,
        payment_payload: dict,
        db_session,
    ):
        from core.config import settings

        idempotency_key = str(uuid.uuid4())
        headers = {
            "X-API-Key": settings.API_KEY,
            "Idempotency-Key": idempotency_key,
        }

        response1 = await client.post(
            "/api/v1/payments", json=payment_payload, headers=headers
        )
        assert response1.status_code == 202
        payment_id_1 = response1.json()["payment_id"]

        response2 = await client.post(
            "/api/v1/payments", json=payment_payload, headers=headers
        )
        assert response2.status_code == 202
        payment_id_2 = response2.json()["payment_id"]

        assert payment_id_1 == payment_id_2

    @pytest.mark.asyncio
    async def test_duplicate_request_creates_single_payment_in_db(
        self,
        client: AsyncClient,
        payment_payload: dict,
        db_session,
    ):
        from core.config import settings

        idempotency_key = str(uuid.uuid4())
        headers = {
            "X-API-Key": settings.API_KEY,
            "Idempotency-Key": idempotency_key,
        }

        await client.post("/api/v1/payments", json=payment_payload, headers=headers)
        await client.post("/api/v1/payments", json=payment_payload, headers=headers)
        await client.post("/api/v1/payments", json=payment_payload, headers=headers)

        result = await db_session.execute(
            select(func.count(Payment.id)).where(
                Payment.idempotency_key == idempotency_key
            )
        )
        count = result.scalar()
        assert count == 1

    @pytest.mark.asyncio
    async def test_duplicate_request_creates_single_outbox_event(
        self,
        client: AsyncClient,
        payment_payload: dict,
        db_session,
    ):
        from core.config import settings

        idempotency_key = str(uuid.uuid4())
        headers = {
            "X-API-Key": settings.API_KEY,
            "Idempotency-Key": idempotency_key,
        }

        r = await client.post("/api/v1/payments", json=payment_payload, headers=headers)
        payment_id = uuid.UUID(r.json()["payment_id"])

        await client.post("/api/v1/payments", json=payment_payload, headers=headers)

        result = await db_session.execute(
            select(func.count(OutboxEvent.id)).where(
                OutboxEvent.payment_id == payment_id
            )
        )
        count = result.scalar()
        assert count == 1

    @pytest.mark.asyncio
    async def test_different_idempotency_keys_create_different_payments(
        self,
        client: AsyncClient,
        payment_payload: dict,
        db_session,
    ):
        from core.config import settings

        def make_headers():
            return {
                "X-API-Key": settings.API_KEY,
                "Idempotency-Key": str(uuid.uuid4()),
            }

        resp_1 = await client.post(
            "/api/v1/payments", json=payment_payload, headers=make_headers()
        )
        resp_2 = await client.post(
            "/api/v1/payments", json=payment_payload, headers=make_headers()
        )

        assert resp_1.json()["payment_id"] != resp_2.json()["payment_id"]
