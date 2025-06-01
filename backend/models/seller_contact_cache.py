from sqlalchemy import (
    Column, Integer, String, DateTime, func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from database import Base


class SellerContactCache(Base):
    """
    Продавцы, у которых при последнем запросе не было телефона/почты.
    Храним дату последней попытки, чтобы раз в 30 дней пробовать повторно.
    """
    __tablename__ = "seller_contacts_cache"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, nullable=False, unique=True, index=True)

    store_name = Column(String, nullable=True)
    inn = Column(String(12), nullable=False, index=True)
    url = Column(String, nullable=False)
    sale_count = Column(Integer, nullable=False)
    reg_date = Column(DateTime(timezone=True), nullable=False)
    tax_office = Column(String, nullable=False)
    director = Column(String, nullable=True)
    ogrn = Column(String(13), nullable=True)
    ogrnip = Column(String(15), nullable=True)

    first_seen_at = Column(DateTime(timezone=True),
                            server_default=func.now(), nullable=False)
    last_try_at = Column(DateTime(timezone=True),
                          server_default=func.now(), nullable=False)
