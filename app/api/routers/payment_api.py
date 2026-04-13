#!/usr/bin/env python
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.db import get_session
from api.database.models import Payment, OutboxEvent
from api.enums import PaymentStatus
from api.schemas import (
    CreatePaymentResponse,
    CreatePaymentRequest,
    ErrorResponse,
    GetPaymentResponse,
)
from core.config import settings
from core.exception_handler import common_responses

payments_router = APIRouter(
    prefix=f"{settings.API_PREFIX}/payments",
    tags=["payments"],
)


@payments_router.post(
    "",
    name="payments:create_payment",
    response_model=CreatePaymentResponse,
    responses={
        **common_responses,
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    },
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a new payment",
)
async def create_payment(
    request_data: CreatePaymentRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    session: AsyncSession = Depends(get_session),
) -> CreatePaymentResponse:
    existing = await session.scalar(
        select(Payment).where(Payment.idempotency_key == idempotency_key)
    )

    if existing:
        return CreatePaymentResponse(
            payment_id=existing.id,
            status=existing.status,
            created_at=existing.created_at,
        )

    payment = Payment(
        amount=request_data.amount,
        currency=request_data.currency,
        description=request_data.description,
        payment_metadata=request_data.metadata,
        status=PaymentStatus.PENDING.value,
        idempotency_key=idempotency_key,
        webhook_url=str(request_data.webhook_url),
    )

    session.add(payment)
    await session.flush()

    outbox = OutboxEvent(
        payment_id=payment.id,
        event_type="payment.new",
        payload={
            "payment_id": str(payment.id),
            "amount": str(payment.amount),
            "currency": payment.currency.value,
            "description": payment.description,
            "metadata": payment.payment_metadata,
            "webhook_url": str(request_data.webhook_url),
        },
        published=False,
    )
    session.add(outbox)
    await session.commit()
    await session.refresh(payment)

    return CreatePaymentResponse(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
    )


@payments_router.get(
    "/{payment_id}",
    response_model=GetPaymentResponse,
    summary="Get payment details",
)
async def get_payment(
    payment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> GetPaymentResponse:
    payment = await session.get(Payment, payment_id)

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {payment_id} not found",
        )

    return GetPaymentResponse.model_validate(payment)
