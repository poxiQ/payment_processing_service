#!/usr/bin/env python
import asyncio
import json
import logging
from datetime import datetime, timezone

import aio_pika
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.database.db import db_url
from api.database.models import OutboxEvent
from core.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

POLL_INTERVAL = 2  # seconds


async def publish_pending_events(
    session: AsyncSession,
    exchange: aio_pika.abc.AbstractExchange,
) -> None:
    result = await session.execute(
        select(OutboxEvent)
        .where(OutboxEvent.published == False)
        .order_by(OutboxEvent.created_at)
        .limit(100)
        .with_for_update(skip_locked=True)
    )
    events = result.scalars().all()

    for event in events:
        message = aio_pika.Message(
            body=json.dumps(event.payload).encode(),
            content_type="application/json",
            message_id=str(event.id),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key="payments.new")

        event.published = True
        event.published_at = datetime.now(timezone.utc)
        logger.info(f"Published outbox event {event.id} for payment {event.payment_id}")

    if events:
        await session.commit()


async def main() -> None:
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()

    dlq_exchange = await channel.declare_exchange(
        "payments.dlx", aio_pika.ExchangeType.DIRECT, durable=True
    )
    dlq = await channel.declare_queue(
        "payments.dlq",
        durable=True,
        arguments={"x-queue-type": "quorum"},
    )
    await dlq.bind(dlq_exchange, routing_key="payments.dlq")

    exchange = await channel.declare_exchange(
        "payments", aio_pika.ExchangeType.DIRECT, durable=True
    )
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
    await queue.bind(exchange, routing_key="payments.new")

    logger.info(f"Outbox publisher started, polling every {POLL_INTERVAL} seconds…")

    while True:
        try:
            async with async_session() as session:
                await publish_pending_events(session, exchange)
        except Exception as exc:
            logger.exception(f"Outbox publisher error: {exc}")

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
