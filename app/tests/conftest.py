#!/usr/bin/env python
# conftest.py

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

from api.database.models import Payment, BaseModel
from api.database.db import get_session
from api.enums import PaymentStatus
from core.config import settings
from main import app


# ──────────────────────────────────────────────────────────────
# Вспомогательная функция — создать / удалить БД
# Подключаемся к дефолтной БД postgres (не к test!)
# ──────────────────────────────────────────────────────────────
async def create_test_database():
    """Создаём тестовую БД если не существует."""
    # URL к дефолтной БД (postgres) для выполнения CREATE DATABASE
    root_url = settings.PROD_DB_URL.rsplit("/", 1)[0] + "/postgres"

    engine = create_async_engine(
        root_url,
        isolation_level="AUTOCOMMIT",  # CREATE DATABASE требует autocommit
        echo=False,
    )
    async with engine.connect() as conn:
        # Проверяем существует ли БД
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db"),
            {"db": "backend_test"},
        )
        exists = result.scalar()
        if not exists:
            await conn.execute(text("CREATE DATABASE backend_test"))
    await engine.dispose()


async def drop_test_database():
    """Удаляем тестовую БД после всех тестов."""
    root_url = settings.PROD_DB_URL.rsplit("/", 1)[0] + "/postgres"

    engine = create_async_engine(
        root_url,
        isolation_level="AUTOCOMMIT",
        echo=False,
    )
    async with engine.connect() as conn:
        # Отключаем все активные соединения к БД перед удалением
        await conn.execute(
            text("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'backend_test'
              AND pid <> pg_backend_pid()
        """)
        )
        await conn.execute(text("DROP DATABASE IF EXISTS backend_test"))
    await engine.dispose()


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Создаём тестовую БД один раз на всю сессию."""
    await create_test_database()
    yield
    await drop_test_database()


@pytest.fixture(scope="function")
async def test_engine(setup_test_database):
    """Создаём таблицы перед тестом, удаляем после."""
    engine = create_async_engine(settings.TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def client(test_engine):  # ← берём engine, не session
    """
    Каждый HTTP запрос получает свою сессию из пула.
    Критично для конкурентных тестов.
    """
    async_session_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
    )

    async def override_get_session():
        async with async_session_factory() as session:  # ← новая сессия каждый раз
            yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def db_session(test_engine):
    """Отдельная сессия для прямых операций с БД в тестах."""
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
def valid_headers():
    return {
        "X-API-Key": settings.API_KEY,
        "Idempotency-Key": str(uuid.uuid4()),
    }


@pytest.fixture
def payment_payload():
    return {
        "amount": "100.00",
        "currency": "USD",
        "description": "Test payment",
        "metadata": {"order_id": "ord-123"},
        "webhook_url": "https://example.com/webhook",
    }


@pytest.fixture
async def existing_payment(db_session) -> Payment:
    payment = Payment(
        amount="250.00",
        currency="USD",
        description="Existing payment",
        payment_metadata={},
        status=PaymentStatus.PENDING.value,
        idempotency_key=str(uuid.uuid4()),
        webhook_url="https://example.com/webhook",
    )
    db_session.add(payment)
    await db_session.commit()
    await db_session.refresh(payment)
    return payment
