#!/usr/bin/env python
import asyncio
import json
import logging
import random
import uuid
from datetime import datetime, timezone

import aio_pika
import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.database.db import db_url
from api.database.models import Payment
from api.enums import PaymentStatus
from core.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

MAX_WEBHOOK_RETRIES = 3
WEBHOOK_RETRY_BASE = 2  # seconds


async def emulate_gateway(payment_id: str) -> bool:
    """Emulate external payment gateway: 2-5s delay, 90% success."""
    delay = random.uniform(2, 5)
    await asyncio.sleep(delay)
    success = random.random() < 0.9
    logger.info(
        f"Gateway response for {payment_id}: "
        f"{'SUCCESS' if success else 'FAIL'} (took {delay})"
    )
    return success


async def send_webhook(webhook_url: str, payload: dict, attempt: int = 1) -> None:
    """Send a webhook with a retry delay"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(1, MAX_WEBHOOK_RETRIES + 1):
            try:
                resp = await client.post(webhook_url, json=payload)
                resp.raise_for_status()
                logger.info(f"Webhook delivered to {webhook_url} (attempt {attempt})")
                return
            except Exception as exc:
                wait = WEBHOOK_RETRY_BASE**attempt
                logger.warning(
                    f"Webhook attempt{attempt} failed ({exc}), retrying in {wait}s…"
                )

                if attempt < MAX_WEBHOOK_RETRIES:
                    await asyncio.sleep(wait)

    logger.error(f"All webhook attempts exhausted for {webhook_url}")


async def process_message(
    message: aio_pika.abc.AbstractIncomingMessage,
    async_session: async_sessionmaker,
) -> None:
    async with message.process(requeue=False):
        try:
            data = json.loads(message.body)
            payment_id = uuid.UUID(data["payment_id"])
            webhook_url = data["webhook_url"]

            async with async_session() as session:
                payment: Payment | None = await session.get(Payment, payment_id)
                if not payment:
                    logger.error(f"Payment {payment_id} not found in DB")
                    return

                # Skip already-processed payments (idempotency)
                if payment.status != PaymentStatus.PENDING:
                    logger.info(f"Payment {payment_id} already processed, skipping")
                    return

                success = await emulate_gateway(str(payment_id))
                payment.status = (
                    PaymentStatus.SUCCEEDED if success else PaymentStatus.FAILED
                )
                payment.processed_at = datetime.now(timezone.utc)
                await session.commit()

            webhook_payload = {
                "payment_id": str(payment_id),
                "status": payment.status.value,
                "processed_at": payment.processed_at.isoformat(),
                "amount": str(data["amount"]),
                "currency": data["currency"],
            }
            await send_webhook(webhook_url, webhook_payload)

        except Exception as exc:
            logger.exception(f"Failed to process message: {exc}")
            raise  # RabbitMQ will route to DLQ after x-delivery-limit


async def main() -> None:
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    queue = await channel.declare_queue(
        "payments.new",
        durable=True,
        arguments={
            "x-queue-type": "quorum",
            "x-dead-letter-exchange": "payments.dlx",
            "x-dead-letter-routing-key": "payments.dlq",
            "x-delivery-limit": 3,
        },
    )

    logger.info("Consumer started, waiting for messages…")
    await queue.consume(lambda msg: process_message(msg, async_session))
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
