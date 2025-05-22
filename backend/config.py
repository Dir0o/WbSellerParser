from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from datetime import timedelta
import os
from dotenv import load_dotenv
from typing import Union, List

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
CORS_ORIGINS = [x for x in os.environ.get("CORS_ORIGINS").split(',')]


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_NAME: str
    DB_PASS: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CACHE_TTL: timedelta = timedelta(minutes=10)
    PROXY_KEY: str
    USERBOX_KEY: str

    CORS_ORIGINS: Union[List[str], str] = Field(default="")

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def _normalise_cors(cls, v: Union[List[str], str]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin]
        return list(v)

    @property
    def DATABASE_URL(self):
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"

settings = Settings()

