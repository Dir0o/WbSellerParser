from sqlalchemy import Column, Integer, String, DateTime, JSON, func
from database import Base
from sqlalchemy.dialects.postgresql import ARRAY


class ParseData(Base):
    __tablename__ = "parse_data"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    category = Column(String, nullable=False)
    shard = Column(String, nullable=False)
    region_id = Column(String, nullable=False)
    sale_item_count = Column(Integer, nullable=False)
    max_sale_count = Column(Integer, nullable=False)
    reg_date = Column(DateTime(timezone=True), nullable=False)
    max_reg_date = Column(DateTime(timezone=True), nullable=False)
    data = Column(JSON, nullable=False)