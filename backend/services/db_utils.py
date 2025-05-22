from typing import List, Tuple, Set, Optional
from sqlalchemy.orm import Session
from sqlalchemy.engine import Row
import logging
from datetime import datetime, timezone, timedelta

from models.seller import Seller as SellerModel
from models.seller_contact_cache import SellerContactCache as CacheModel
from database import SessionLocal
from schemas.wb import SellerOut

logger = logging.getLogger(__name__)

def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)

def get_cached(supplier_id: int) -> Optional[CacheModel]:
    with SessionLocal() as db:
        return (
            db.query(CacheModel)
              .filter(CacheModel.supplier_id == supplier_id)
              .first()
        )

def get_existing_seller_ids(seller_ids: List[int]) -> List[Row]:
    """Возвращает Row‑объекты (supplier_id, ogrn, ogrnip) для фильтрации по региону."""
    with SessionLocal() as db:
        rows: List[Row] = (
            db.query(
                SellerModel.supplier_id,
                SellerModel.ogrn,
                SellerModel.ogrnip,
            ).filter(SellerModel.supplier_id.in_(seller_ids)).all()
        )
    return rows

def add_to_cache(s: SellerOut) -> None:
    with SessionLocal() as db:
        db.merge(
            CacheModel(
                supplier_id=s.seller_id,
                store_name=s.store_name,
                inn=s.inn,
                url=s.url,
                sale_count=s.saleCount,
                reg_date=s.reg_date,
                tax_office=s.tax_office,
                ogrn=s.ogrn if s.ogrn and len(s.ogrn) == 13 else None,
                ogrnip=s.ogrnip if s.ogrnip and len(s.ogrnip) == 15 else None,
                last_try_at=_now_utc(),
            )
        )
        db.commit()

def touch_cache(supplier_id: int) -> None:
    """Обновляет last_try_at у записи-кэша."""
    with SessionLocal() as db:
        rec = (
            db.query(CacheModel)
              .filter(CacheModel.supplier_id == supplier_id)
              .first()
        )
        if rec:
            rec.last_try_at = _now_utc()
            db.commit()

def remove_from_cache(supplier_id: int) -> None:
    with SessionLocal() as db:
        db.query(CacheModel).filter(
            CacheModel.supplier_id == supplier_id
        ).delete(synchronize_session=False)
        db.commit()

def add_sellers(resp: list):
    db = SessionLocal()
    try:
        for s in resp:
            db.add(SellerModel(
                supplier_id=s.seller_id,
                store_name=s.store_name,
                inn=s.inn,
                url=s.url,
                sale_count=s.saleCount,
                reg_date=s.reg_date,
                tax_office=s.tax_office,
                ogrn=s.ogrn,
                ogrnip=s.ogrnip,
            ))
        db.commit()
    except Exception as err:
        log
    finally:
        db.close()

def add_seller(s: SellerOut) -> None:
    with SessionLocal() as db:
        db.merge(
            SellerModel(
                supplier_id=s.seller_id,
                store_name=s.store_name,
                inn=s.inn,
                url=s.url,
                sale_count=s.saleCount,
                reg_date=s.reg_date,
                tax_office=s.tax_office,
                ogrn=s.ogrn if s.ogrn and len(s.ogrn) == 13 else None,
                ogrnip=s.ogrnip if s.ogrnip and len(s.ogrnip) == 15 else None,
                phone=s.phone or None,
                email=s.email or None,
            )
        )
        db.commit()


def get_seller(supplier_id: int) -> Optional[SellerModel]:
    with SessionLocal() as db:
        return (
            db.query(SellerModel)
              .filter(SellerModel.supplier_id == supplier_id)
              .first()
        )

def update_seller_sale_count(seller_id: int, sale_count: int) -> None:
    with SessionLocal() as db:
        rec = (
            db.query(SellerModel)
              .filter(SellerModel.supplier_id == seller_id)
              .first()
        )
        if rec:
            rec.sale_count = sale_count
            db.commit()