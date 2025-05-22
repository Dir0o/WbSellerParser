from pydantic import BaseModel, Field, HttpUrl, validator
from datetime import datetime
from typing import Optional
class SellerStats(BaseModel):
    """Полная сводка по продавцу WB."""
    seller_id: int = Field(alias="id")
    sale_item_quantity: int = Field(alias="saleItemQuantity")
    registration_date: datetime = Field(alias="registrationDate")

    inn: Optional[str] = None
    ogrn: Optional[str] = None
    ogrnip: Optional[str] = None
    trademark: Optional[str] = None

    @property
    def saleItemQuantity(self) -> int:
        return self.sale_item_quantity

    @property
    def registrationDate(self) -> datetime:
        return self.registration_date

    @property
    def url(self) -> HttpUrl:
        return f"https://www.wildberries.ru/seller/{self.seller_id}"

    @validator("registration_date", pre=True)
    def _normalize_zulu(cls, v: str | datetime) -> datetime:
        if isinstance(v, datetime):
            return v
        return datetime.fromisoformat(v.replace("Z", "+00:00"))