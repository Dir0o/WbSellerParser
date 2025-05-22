from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from pydantic import BaseModel
import tempfile, os, uuid

from database import SessionLocal
from models.seller import Seller
from utils.excel import generate_excel_search

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter()

class SellerSuggestion(BaseModel):
    id: int
    store_name: str

class SellerDetail(BaseModel):
    id: int
    seller_id: int
    store_name: str
    url: str
    inn: str
    ogrn: Optional[str] = None
    ogrnip: Optional[str] = None
    tax_office: str
    saleCount: Optional[int] = None
    reg_date: Optional[date] = None
    phone: Optional[list] = None
    email: Optional[list] = None

@router.get("/", response_model=List[SellerSuggestion], tags=["search"])
def search_sellers(
    q: Optional[str] = Query(None, min_length=1),
    region: Optional[str] = Query(None),
    salesFrom: Optional[int] = Query(None, ge=0),
    salesTo: Optional[int] = Query(None, ge=0),
    dateFrom: Optional[date] = Query(None),
    dateTo: Optional[date] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query_stmt = db.query(Seller.id, Seller.store_name)
    if q:
        pattern = f"%{q}%"
        query_stmt = query_stmt.filter(Seller.store_name.ilike(pattern))
    # Регион
    if region:
        conds = []
        conds.append(
            and_(Seller.ogrn.isnot(None), func.substr(Seller.ogrn, 4, 2) == region)
        )
        conds.append(
            and_(Seller.ogrnip.isnot(None), func.substr(Seller.ogrnip, 4, 2) == region)
        )
        conds.append(
            and_(Seller.ogrn.is_(None), Seller.ogrnip.is_(None), func.substr(Seller.inn, 1, 2) == region)
        )
        query_stmt = query_stmt.filter(or_(*conds))
    # Продажи
    if salesFrom is not None:
        query_stmt = query_stmt.filter(Seller.sale_count >= salesFrom)
    if salesTo is not None:
        query_stmt = query_stmt.filter(Seller.sale_count <= salesTo)
    # Дата регистрации
    if dateFrom:
        query_stmt = query_stmt.filter(Seller.reg_date >= dateFrom)
    if dateTo:
        query_stmt = query_stmt.filter(Seller.reg_date <= dateTo)

    results = query_stmt.limit(limit).all()
    return [SellerSuggestion(id=r.id, store_name=r.store_name) for r in results]

@router.get("/results", response_model=List[SellerDetail], tags=["search"])
def search_seller_details(
    q: Optional[str] = Query(None, min_length=1),
    region: Optional[str] = Query(None),
    salesFrom: Optional[int] = Query(None, ge=0),
    salesTo: Optional[int] = Query(None, ge=0),
    dateFrom: Optional[date] = Query(None),
    dateTo: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    query_stmt = db.query(Seller)
    if q:
        pattern = f"%{q}%"
        query_stmt = query_stmt.filter(Seller.store_name.ilike(pattern))
    if region:
        conds = []
        conds.append(and_(Seller.ogrn.isnot(None), func.substr(Seller.ogrn, 4, 2) == region))
        conds.append(and_(Seller.ogrnip.isnot(None), func.substr(Seller.ogrnip, 4, 2) == region))
        conds.append(and_(Seller.ogrn.is_(None), Seller.ogrnip.is_(None), func.substr(Seller.inn, 1, 2) == region))
        query_stmt = query_stmt.filter(or_(*conds))
    if salesFrom is not None:
        query_stmt = query_stmt.filter(Seller.sale_count >= salesFrom)
    if salesTo is not None:
        query_stmt = query_stmt.filter(Seller.sale_count <= salesTo)
    if dateFrom:
        query_stmt = query_stmt.filter(Seller.reg_date >= dateFrom)
    if dateTo:
        query_stmt = query_stmt.filter(Seller.reg_date <= dateTo)

    sellers = query_stmt.all()
    result_list = []
    for s in sellers:
        reg_date_val = None
        if s.reg_date is not None:
            reg_date_val = s.reg_date.date() if hasattr(s.reg_date, 'date') else s.reg_date

        store_name_val = s.store_name if s.store_name is not None else ""

        result_list.append(
            SellerDetail(
                id=s.id,
                store_name=store_name_val,
                seller_id=s.supplier_id,
                url=s.url,
                inn=s.inn,
                ogrn=s.ogrn,
                ogrnip=s.ogrnip,
                tax_office=s.tax_office,
                saleCount=s.sale_count,
                reg_date=reg_date_val,
                phone=s.phone,
                email=s.email
            )
        )
    return result_list

@router.get("/xlsx", summary="Скачать результаты поиска в Excel")
async def download_search_excel(
    q: Optional[str] = Query(None, min_length=1),
    region: Optional[str] = Query(None),
    salesFrom: Optional[int] = Query(None, ge=0),
    salesTo: Optional[int] = Query(None, ge=0),
    dateFrom: Optional[date] = Query(None),
    dateTo: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    # user = Depends(get_current_user),
):

    query_stmt = db.query(Seller)
    if q:
        pattern = f"%{q}%"
        query_stmt = query_stmt.filter(Seller.store_name.ilike(pattern))
    if region:
        conds = [
            and_(Seller.ogrn.isnot(None), func.substr(Seller.ogrn, 4, 2) == region),
            and_(Seller.ogrnip.isnot(None), func.substr(Seller.ogrnip, 4, 2) == region),
            and_(Seller.ogrn.is_(None), Seller.ogrnip.is_(None), func.substr(Seller.inn, 1, 2) == region),
        ]
        query_stmt = query_stmt.filter(or_(*conds))
    if salesFrom is not None:
        query_stmt = query_stmt.filter(Seller.sale_count >= salesFrom)
    if salesTo is not None:
        query_stmt = query_stmt.filter(Seller.sale_count <= salesTo)
    if dateFrom:
        query_stmt = query_stmt.filter(Seller.reg_date >= dateFrom)
    if dateTo:
        query_stmt = query_stmt.filter(Seller.reg_date <= dateTo)

    sellers = query_stmt.all()

    details = []
    for s in sellers:
        reg_date_val = s.reg_date.date() if hasattr(s.reg_date, "date") else s.reg_date
        details.append(
            SellerDetail(
                id=s.id,
                seller_id=s.supplier_id,
                store_name=s.store_name or "",
                url=s.url,
                inn=s.inn,
                ogrn=s.ogrn,
                ogrnip=s.ogrnip,
                tax_office=s.tax_office,
                saleCount=s.sale_count,
                reg_date=reg_date_val,
                phone=s.phone,
                email=s.email,
            )
        )

    # Генерация файла
    path = os.path.join(
        tempfile.gettempdir(),
        f"search_{uuid.uuid4().hex}.xlsx"
    )
    generate_excel_search(details, filename=path)

    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="search_results.xlsx"
    )