from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = os.environ.get("ALGORITHM")
PROXY_KEY = os.environ.get("PROXY_KEY")
USERBOX_KEY = os.environ.get("USERBOX_KEY")

class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_NAME: str
    DB_PASS: str

    CORS_ORIGINS: list[str] = Field(
        default_factory=list,
        env="CORS_ORIGINS"
    )
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CACHE_TTL: timedelta = timedelta(minutes=10)
    PROXY_KEY: str
    USERBOX_KEY: str

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors_origins(cls, v):
        """
        Если из env пришла строка, разбиваем по запятым.
        Если список — возвращаем как есть.
        """
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @property
    def DATABASE_URL(self):
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"

settings = Settings()

