from __future__ import annotations
from typing import List, Optional, Tuple, Dict, Set
from datetime import datetime, timedelta, timezone
import asyncio
import logging

from config import settings
from schemas.wb import WBParams, SellerOut
from parser.wb_parser import parse_sellers, SellerStats
from parser.rusprofile import parse_companies
from parser.userbox import parse_records as parse_usersbox
from utils.contacts import collect_contacts
from services import db_utils as dbu

logger = logging.getLogger(__name__)

_cache: dict[str, Tuple[datetime, List[SellerOut], int]] = {}

def _make_key(params: WBParams) -> str:
    return "|".join(map(str, [
        params.cat, params.shard, params.region_id,
        params.saleItemCount, params.maxSaleCount or "",
        params.pages, params.regDate or "", params.maxRegDate or ""
    ]))

async def _contacts_from_usersbox(inn: str) -> Tuple[Set[str], Set[str]]:
    """Один запрос → Usersbox → (phones, emails). Ошибки = пустые множества."""
    try:
        infos = await parse_usersbox([inn])
        if not infos:
            return set(), set()
        phone, email = collect_contacts(i.payload for i in infos)
        return phone, email
    except Exception as e:
        logger.exception("Usersbox parse failed for %s: %s", inn, e)
        return set(), set()


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


async def collect_data(
    params: WBParams,
    region_id: str,
    limit: Optional[int] = None,
) -> Tuple[List[SellerOut], bool]:

    flag_limit = False
    key = _make_key(params)
    now = _utc_now()

    if key in _cache:
        ts, cached, cached_limit = _cache[key]
        if now - ts < settings.CACHE_TTL and cached_limit == limit:
            return cached, True

    region_list = [r.strip() for r in region_id.replace(";", ",").split(",") if r.strip()]

    new_stats, already_full_ids = await parse_sellers(
        category=params.cat,
        shard=params.shard,
        pages=params.pages,
        regions=region_list,
        min_sales=params.saleItemCount,
        max_sales=params.maxSaleCount,
        min_registration_date=params.regDate,
        max_registration_date=params.maxRegDate,
    )

    data: List[SellerOut] = []
    contact_tasks: Dict[int, asyncio.Task[Tuple[Set[str], Set[str]]]] = {}
    tmp_models: Dict[int, dict] = {}

    THRESHOLD_DAYS = 30
    retry_deadline = now - timedelta(days=THRESHOLD_DAYS)


    for seller in new_stats:
        if limit is not None and (len(data) + len(tmp_models)) >= limit:
            flag_limit = True
            break

        sid = seller.seller_id

        if sid in already_full_ids:
            continue

        cache_rec = dbu.get_cached(sid)
        if cache_rec and cache_rec.last_try_at > retry_deadline:
            dbu.touch_cache(sid)
            continue

        if seller.ogrn and len(seller.ogrn) == 13:
            query = f"{seller.ogrn}&type=ul"
        elif seller.ogrnip and len(seller.ogrnip) == 15:
            query = f"{seller.ogrnip}&type=ip"
        else:
            query = seller.inn

        seller_tax = await parse_companies(ids=[query], seller_id=sid)
        if not seller_tax:
            continue

        inn_for_contacts = seller_tax[0].inn or seller.inn


        contact_tasks[sid] = asyncio.create_task(
            _contacts_from_usersbox(inn_for_contacts)
        )


        tmp_models[sid] = dict(
            seller_id=sid,
            tax_office=seller_tax[0].tax_office,
            store_name=seller.trademark or None,
            inn=seller_tax[0].inn,
            url=f"https://www.wildberries.ru/seller/{sid}",
            reg_date=seller.registration_date,
            saleCount=seller.sale_item_quantity,
            ogrn=seller.ogrn or None,
            ogrnip=seller.ogrnip or None,
        )


    if contact_tasks:
        done = await asyncio.gather(*contact_tasks.values())
        for sid, (phones, emails) in zip(contact_tasks.keys(), done):
            base_kwargs = tmp_models[sid]

            if phones or emails:

                sModel = SellerOut(
                    **base_kwargs,
                    phone=sorted(phones),
                    email=sorted(emails),
                )
                dbu.add_seller(sModel)
                dbu.remove_from_cache(sid)
                data.append(sModel)
            else:

                sModel = SellerOut(
                    **base_kwargs,
                    phone=[],
                    email=[],
                )
                if dbu.get_cached(sid):
                    dbu.touch_cache(sid)
                else:
                    dbu.add_to_cache(sModel)

    _cache[key] = (now, data, limit)
    return data, flag_limit
