from pydantic import BaseModel, HttpUrl

class CompanyInfo(BaseModel):
    inn: str | None = None
    ogrn: str | None = None
    ogrnip: str | None = None
    tax_office: str
    director: str | None = None
    seller_id: int | None = None