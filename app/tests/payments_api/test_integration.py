#!/usr/bin/env python
import pytest
import uuid
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from api.database.models import Payment
from api.enums import PaymentStatus
from datetime import datetime, timezone


class TestIntegration:
    """
    End-to-end tests: create → check status → process.
    Mocking external dependencies (gateway, webhook).
    """

    @pytest.mark.asyncio
    async def test_payment_lifecycle_success(
        self,
        client: AsyncClient,
        valid_headers: dict,
        payment_payload: dict,
        db_session,
    ):
        create_resp = await client.post(
            "/api/v1/payments",
            json=payment_payload,
            headers=valid_headers,
        )
        assert create_resp.status_code == 202
        payment_id = create_resp.json()["payment_id"]

        get_resp = await client.get(
            f"/api/v1/payments/{payment_id}",
            headers={"X-API-Key": valid_headers["X-API-Key"]},
        )

        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == PaymentStatus.PENDING.value

        # Emulate consumer
        payment = await db_session.get(Payment, uuid.UUID(payment_id))
        payment.status = PaymentStatus.SUCCEEDED.value
        payment.processed_at = datetime.now(timezone.utc)
        await db_session.commit()

        final_resp = await client.get(
            f"/api/v1/payments/{payment_id}",
            headers={"X-API-Key": valid_headers["X-API-Key"]},
        )

        assert final_resp.status_code == 200
        assert final_resp.json()["status"] == PaymentStatus.SUCCEEDED.value
        assert final_resp.json()["processed_at"] is not None

    @pytest.mark.asyncio
    async def test_payment_lifecycle_failure(
        self,
        client: AsyncClient,
        valid_headers: dict,
        payment_payload: dict,
        db_session,
    ):
        create_resp = await client.post(
            "/api/v1/payments",
            json=payment_payload,
            headers=valid_headers,
        )
        payment_id = create_resp.json()["payment_id"]

        payment = await db_session.get(Payment, uuid.UUID(payment_id))
        from datetime import datetime, timezone

        payment.status = PaymentStatus.FAILED.value
        payment.processed_at = datetime.now(timezone.utc)
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/payments/{payment_id}",
            headers={"X-API-Key": valid_headers["X-API-Key"]},
        )
        assert resp.json()["status"] == PaymentStatus.FAILED.value

    @pytest.mark.asyncio
    async def test_concurrent_requests_same_idempotency_key(
        self,
        client: AsyncClient,
        payment_payload: dict,
        db_session,
    ):
        import asyncio
        from core.config import settings

        idempotency_key = str(uuid.uuid4())
        headers = {
            "X-API-Key": settings.API_KEY,
            "Idempotency-Key": idempotency_key,
        }

        tasks = [
            client.post("/api/v1/payments", json=payment_payload, headers=headers)
            for _ in range(5)
        ]

        responses = await asyncio.wait_for(
            asyncio.gather(*tasks),
            timeout=10.0,
        )

        assert all(r.status_code == 202 for r in responses)
        payment_ids = {r.json()["payment_id"] for r in responses}
        assert len(payment_ids) == 1

    @pytest.mark.asyncio
    async def test_end_to_end_with_mocked_gateway(
        self,
        client: AsyncClient,
        valid_headers: dict,
        payment_payload: dict,
    ):
        with (
            patch("broker.consumer.emulate_gateway", new_callable=AsyncMock) as mock_gw,
            patch("broker.consumer.send_webhook", new_callable=AsyncMock) as mock_wh,
        ):
            mock_gw.return_value = True

            create_resp = await client.post(
                "/api/v1/payments",
                json=payment_payload,
                headers=valid_headers,
            )
            assert create_resp.status_code == 202

            payment_id = create_resp.json()["payment_id"]
            assert uuid.UUID(payment_id)
