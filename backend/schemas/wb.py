from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class WBParams(BaseModel):
    cat: str
    shard: str
    region_id: str = Field(..., pattern=r"^\d{2}(?:[,;]\d{2})*$")
    saleItemCount: int = Field(0, ge=0)
    maxSaleCount: Optional[int] = Field(None, ge=0)
    pages: int = Field(1, ge=1)
    regDate: Optional[str]
    maxRegDate: Optional[str]

class SellerOut(BaseModel):
    seller_id: int
    store_name: Optional[str]
    inn: str
    url: str
    saleCount: int
    reg_date: datetime
    tax_office: str
    director: Optional[str] = None
    ogrn: Optional[str]
    ogrnip: Optional[str]
    phone: list[str] = []
    email: list[str] = []
    categories: Optional[str] = None
