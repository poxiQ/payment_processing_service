#!/usr/bin/env python
import pytest
import uuid
from httpx import AsyncClient
from api.database.models import Payment
from api.enums import PaymentStatus


class TestGetPayment:
    """
    GET /api/v1/payments/{payment_id}
    """

    @pytest.mark.asyncio
    async def test_get_existing_payment(
        self,
        client: AsyncClient,
        valid_headers,
        existing_payment: Payment,
    ):
        response = await client.get(
            f"/api/v1/payments/{existing_payment.id}",
            headers={"X-API-Key": valid_headers["X-API-Key"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(existing_payment.id)
        assert data["status"] == existing_payment.status
        assert data["amount"] == str(existing_payment.amount)
        assert data["currency"] == existing_payment.currency.value

    @pytest.mark.asyncio
    async def test_get_nonexistent_payment_returns_404(
        self, client: AsyncClient, valid_headers
    ):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/payments/{fake_id}",
            headers={"X-API-Key": valid_headers["X-API-Key"]},
        )

        assert response.status_code == 404
        assert str(fake_id) in response.json()["message"]

    @pytest.mark.asyncio
    async def test_get_payment_invalid_uuid_returns_422(
        self, client: AsyncClient, valid_headers
    ):
        response = await client.get(
            "/api/v1/payments/not-a-valid-uuid",
            headers={"X-API-Key": valid_headers["X-API-Key"]},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_succeeded_payment_has_processed_at(
        self, client: AsyncClient, valid_headers, db_session
    ):
        from datetime import datetime, timezone

        payment = Payment(
            amount="500.00",
            currency="USD",
            description="Succeeded",
            payment_metadata={},
            status=PaymentStatus.SUCCEEDED.value,
            idempotency_key=str(uuid.uuid4()),
            webhook_url="https://example.com/wh",
            processed_at=datetime.now(timezone.utc),
        )
        db_session.add(payment)
        await db_session.commit()
        await db_session.refresh(payment)

        response = await client.get(
            f"/api/v1/payments/{payment.id}",
            headers={"X-API-Key": valid_headers["X-API-Key"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == PaymentStatus.SUCCEEDED.value
        assert data["processed_at"] is not None

    @pytest.mark.asyncio
    async def test_get_payment_without_api_key_returns_401(
        self, client: AsyncClient, existing_payment: Payment
    ):
        response = await client.get(f"/api/v1/payments/{existing_payment.id}")
        assert response.status_code == 401
