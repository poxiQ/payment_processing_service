#!/usr/bin/env python
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select
from api.database.models import Payment, OutboxEvent
from api.enums import PaymentStatus


class TestCreatePayment:
    """
    POST /api/v1/payments
    Status: 202 Accepted
    """

    @pytest.mark.asyncio
    async def test_create_payment_success(
        self, client: AsyncClient, valid_headers, payment_payload, db_session
    ):
        response = await client.post(
            "/api/v1/payments",
            json=payment_payload,
            headers=valid_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert "payment_id" in data
        assert data["status"] == PaymentStatus.PENDING.value
        assert "created_at" in data

        payment = await db_session.get(Payment, uuid.UUID(data["payment_id"]))
        assert payment is not None
        assert payment.status == PaymentStatus.PENDING.value
        assert str(payment.amount) == payment_payload["amount"]
        assert payment.currency.value == payment_payload["currency"]

    @pytest.mark.asyncio
    async def test_outbox_event_created_on_payment(
        self, client: AsyncClient, valid_headers, payment_payload, db_session
    ):
        response = await client.post(
            "/api/v1/payments",
            json=payment_payload,
            headers=valid_headers,
        )
        assert response.status_code == 202
        payment_id = response.json()["payment_id"]

        result = await db_session.execute(
            select(OutboxEvent).where(OutboxEvent.payment_id == uuid.UUID(payment_id))
        )
        event = result.scalar_one_or_none()

        assert event is not None
        assert event.published is False
        assert event.event_type == "payment.new"
        assert event.payload["payment_id"] == payment_id
        assert event.payload["amount"] == payment_payload["amount"]
        assert event.payload["currency"] == payment_payload["currency"]

    @pytest.mark.asyncio
    async def test_missing_idempotency_key_returns_422(
        self, client: AsyncClient, payment_payload
    ):
        from core.config import settings

        response = await client.post(
            "/api/v1/payments",
            json=payment_payload,
            headers={"X-API-Key": settings.API_KEY},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_amount_returns_422(self, client: AsyncClient, valid_headers):
        response = await client.post(
            "/api/v1/payments",
            json={
                "amount": "not-a-number",
                "currency": "USD",
                "description": "Bad payload",
                "webhook_url": "https://example.com/webhook",
            },
            headers=valid_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_webhook_url_returns_422(
        self, client: AsyncClient, valid_headers
    ):
        response = await client.post(
            "/api/v1/payments",
            json={
                "amount": "100.00",
                "currency": "USD",
                "description": "Test",
                "webhook_url": "not-a-url",
            },
            headers=valid_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_currency_returns_422(
        self, client: AsyncClient, valid_headers
    ):
        response = await client.post(
            "/api/v1/payments",
            json={
                "amount": "100.00",
                "currency": "ZZZ",
                "description": "Test",
                "webhook_url": "https://example.com/webhook",
            },
            headers=valid_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_amount_returns_422(
        self, client: AsyncClient, valid_headers
    ):
        response = await client.post(
            "/api/v1/payments",
            json={
                "amount": "-50.00",
                "currency": "USD",
                "description": "Negative",
                "webhook_url": "https://example.com/webhook",
            },
            headers=valid_headers,
        )
        assert response.status_code == 422
