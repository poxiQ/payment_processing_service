#!/usr/bin/env python

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
    JSON,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import declarative_base

from api.enums import PaymentCurrency, PaymentStatus

BaseModel = declarative_base()


class Payment(BaseModel):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[PaymentCurrency] = mapped_column(
        Enum(
            PaymentCurrency,
            name="currency_enum",
            values_callable=lambda objects: [o.value for o in objects],
        ),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    payment_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(
            PaymentStatus,
            name="payment_status_enum",
            values_callable=lambda objects: [o.value for o in objects],
        ),
        nullable=False,
        default=PaymentStatus.PENDING.value,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    outbox_events: Mapped[list["OutboxEvent"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Payment(uuid={self.id}, sum={self.amount}, currency={self.currency})>"


class OutboxEvent(BaseModel):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    published: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    payment: Mapped["Payment"] = relationship(back_populates="outbox_events")

    def __repr__(self):
        return f"<OutboxEvent(uuid={self.id}, payment_id={self.payment_id}, created_at={self.created_at})>"
