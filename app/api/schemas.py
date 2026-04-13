# app/schemas.py
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator
from pydantic.dataclasses import dataclass

from api.enums import PaymentStatus, PaymentCurrency


class CreatePaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2, examples=["100.00"])
    currency: PaymentCurrency
    description: str = Field(min_length=1, max_length=500)
    metadata: dict[str, Any] | None = None
    webhook_url: HttpUrl

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v


class CreatePaymentResponse(BaseModel):
    payment_id: uuid.UUID
    status: PaymentStatus
    created_at: datetime


class GetPaymentResponse(BaseModel):
    id: uuid.UUID
    amount: Decimal
    currency: PaymentCurrency
    description: str
    payment_metadata: dict[str, Any] | None = None
    status: PaymentStatus
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    error: bool = Field(
        ...,
    )
    message: str = Field(
        ...,
    )
    traceback: str = Field(
        None,
    )


@dataclass
class GetDeploymentInformationResponse:
    python_version: str = Field(
        default=None,
        title="Версия python",
        description="Версия python",
        examples=[
            "3.13.2 (tags/v3.13.2:4f8bb39, Feb  4 2025, 15:23:48) [MSC v.1942 64 bit (AMD64)]",
        ],
    )
