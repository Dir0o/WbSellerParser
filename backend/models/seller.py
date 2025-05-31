from sqlalchemy import Column, Integer, String, DateTime, JSON, func
from database import Base
from sqlalchemy.dialects.postgresql import ARRAY


class Seller(Base):
    __tablename__ = "sellers"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, nullable=False, index=True)
    store_name = Column(String, nullable=True)
    inn = Column(String(12), nullable=False, index=True)
    url = Column(String, nullable=False)
    sale_count = Column(Integer, nullable=False)
    reg_date = Column(DateTime(timezone=True), nullable=False)
    tax_office = Column(String, nullable=False)
    ogrn = Column(String(13), nullable=True)
    ogrnip = Column(String(15), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    phone = Column(ARRAY(String), nullable=True)
    email = Column(ARRAY(String), nullable=True)
    categories = Column(String, nullable=True)