import hashlib, json
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    JSON,
    func,
    UniqueConstraint,
)
from database import Base


class CollectionLog(Base):
    __tablename__ = "collection_logs"
    __table_args__ = (
        UniqueConstraint(
            "parser_type",
            "params_hash",
            name="uq_collection_logs_params",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    parser_type = Column(
        String(4),
        nullable=False,
        comment="Тип парсера: 'cat' (дочерняя категория) "
        "или 'all' (материнская категория)",
    )
    params_hash = Column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 хеш нормализованного (без `limit`) "
        "набора параметров запроса",
    )
    params = Column(
        JSON,
        nullable=False,
        comment="Оригинальные параметры запроса "
        "(без поля `limit`), сохранены для наглядности",
    )
    collected_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Момент последнего успешного сбора данных "
        "для данной комбинации параметров",
    )

    @staticmethod
    def _normalize_params(params):
        return {
            k: v for k, v in params.items()
            if k not in ("limit", "regDate", "maxRegDate") and v not in (None, "")
        }

    @classmethod
    def calc_hash(cls, params):
        n = cls._normalize_params(params)
        return hashlib.sha256(json.dumps(n, sort_keys=True, separators=(",", ":")).encode()).hexdigest()