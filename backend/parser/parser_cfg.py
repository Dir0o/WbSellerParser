from typing import Optional

from pydantic import HttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ParserConfig(BaseSettings):

    SEARCH_CONCURRENCY: int = Field(
        25,
        description="Максимум одновременных HEAD/GET запросов к search",
        ge=1,
    )
    CARD_CONCURRENCY: int = Field(
        50,
        description="Максимум параллельных запросов к карточкам",
        ge=1,
    )
    COMPANY_TIMEOUT: int = Field(
        5,
        description="Таймаут запроса (секунды) к rusprofile",
        ge=1
    )

    TIMEOUT: int = Field(
        5,
        description="Общий таймаут запроса (секунды) | Default: 20",
        ge=1,
    )
    RETRIES: int = Field(
        5,
        description="Количество повторов при ошибке | Default: 5",
        ge=0,
        le=10,
    )
    BACKOFF: float = Field(
        2,
        description="Множитель back-off между повторами | Default: 2.0",
        ge=0.1,
    )
    CONN_LIMIT: int = Field(
        200,
        description="Максимум открытых TCP-соединений | Default: 200",
        ge=1,
    )
    PER_HOST_LIMIT: int = Field(
        50,
        description="Одновременных соединений на один хост | Default: 50",
        ge=1,
    )

    USE_PROXY: bool = Field(
        True,
        description="Включить ли использование прокси | Default: False",
    )
    PROXY_URL: Optional[HttpUrl] = Field(
        None,
        description="URI вида http://user:pass@host:port",
    )

    MIN_SALES: int = Field(
        0,
        description="Минимальное количество продаж для фильтра | В данный момент не используется",
        ge=0,
    )
    MIN_DATE: Optional[str] = Field(
        None,
        description="Фильтр по дате регистрации магазина (YYYY-MM-DD) | В данный момент не используется",
    )

settings = ParserConfig()

__all__ = ['settings']