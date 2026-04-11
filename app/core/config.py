#!/usr/bin/env python
import logging
from typing import ClassVar, Union

from pydantic import ConfigDict, SecretStr
from pydantic_settings import BaseSettings


class RequestContentFilter(logging.Filter):
    def __init__(self, debug: bool) -> None:
        super().__init__()
        self.debug = debug

    def filter(self, record: logging.LogRecord) -> bool:
        if not self.debug and "Content" in record.msg:
            record.msg = "\n".join(record.msg.split("\n")[:-1])
        return True


class PostgresSettings(BaseSettings):
    USER: str = "postgres"
    PASSWORD: SecretStr = "postgres"
    HOST: str = "localhost"
    PORT: int = 5432
    DB: str = "payment"

    model_config = ConfigDict(env_prefix="POSTGRES_")


class Settings(BaseSettings):
    API_HEADERS: dict = {
        "Content-Type": "application/json",
        "User-Agent": "Payment App Python/httpx",
    }
    API_PREFIX: str = "/api/v1"

    TESTING: bool = False
    DEBUG: bool = False

    POSTGRES: PostgresSettings = PostgresSettings()
    PROD_DB_URL: str = f"postgresql+asyncpg://{POSTGRES.USER}:{POSTGRES.PASSWORD.get_secret_value()}@{POSTGRES.HOST}:{POSTGRES.PORT}/{POSTGRES.DB}"
    TEST_DB_URL: str = f"{PROD_DB_URL}_test"



settings = Settings()
