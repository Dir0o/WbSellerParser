import asyncio
import pprint
from datetime import datetime, timedelta
from typing import Optional, List, Union, Tuple

from .HTTPClient import AsyncHttpClient
from .WbFetcher import (
    WBProductFetcher,
    WBSellerFetcher,
    WBSellerInnFetcher,
    WBProductParser,
    WBSellerParser,
    WBSellerInnParser
)
from .WbModels import SellerStats
from services.db_utils import get_existing_seller_ids
from utils.wb_utils import (
    check_region,
    _to_dt,
    ok_date,
    ok_sales
)
from utils.decorators import log_elapsed

@log_elapsed()
async def parse_sellers(
    category: str,
    shard: str,
    pages: int = 1,
    *,
    regions: List[str],
    max_sales: int,
    min_sales: int,
    min_registration_date: Optional[Union[str, datetime]] = None,
    max_registration_date: Optional[Union[str, datetime]] = None,
    client: AsyncHttpClient | None = None,
) -> Tuple[List[SellerStats], List[int]]:
    if client is None:
        async with AsyncHttpClient(proxy="random") as session:
            return await parse_sellers(
                category=category,
                shard=shard,
                pages=pages,
                regions=regions,
                max_sales=max_sales,
                min_sales=min_sales,
                min_registration_date=min_registration_date,
                max_registration_date=max_registration_date,
                client=session,
            )

    pages_data = await WBProductFetcher(category, shard, pages, client).fetch()
    products = WBProductParser().parse(pages_data)

    seller_ids = list({p.get("supplierId") for p in products if isinstance(p.get("supplierId"), int)})
    if not seller_ids:
        return [], []

    existing_objs = get_existing_seller_ids(seller_ids)
    existing_objs = await check_region(existing_objs, regions)
    existing_ids = [x[0] for x in existing_objs]

    new_ids = [sid for sid in seller_ids if sid not in existing_ids]
    if not new_ids:
        return [], existing_ids

    min_dt = _to_dt(min_registration_date)
    max_dt = _to_dt(max_registration_date)

    creds_map = WBSellerInnParser().parse(await WBSellerInnFetcher(new_ids, client).fetch())

    region_codes_set = set(regions)
    filtered_ids: List[int] = []
    for sid, info in creds_map.items():
        ogrn = info.get("ogrn")
        ogrnip = info.get("ogrnip")
        inn = info.get("inn")

        if ogrn and ogrn[3:5] in region_codes_set:
            filtered_ids.append(sid)
        elif ogrnip and ogrnip[3:5] in region_codes_set:
            filtered_ids.append(sid)
        elif inn and inn[:2] in region_codes_set:
            filtered_ids.append(sid)

    if not filtered_ids:
        return [], existing_ids

    ship_resps = await WBSellerFetcher(filtered_ids, client).fetch()
    stats = WBSellerParser().parse(ship_resps)

    new_stats: List[SellerStats] = []
    for s in stats:
        if s.seller_id not in filtered_ids:
            continue
        if not ok_sales(s, max_sales=max_sales, min_sales=min_sales):
            continue
        if not ok_date(s, min_dt=min_dt, max_dt=max_dt):
            continue

        info = creds_map.get(s.seller_id)
        s.inn = info["inn"]
        s.ogrn = info.get("ogrn") or None
        s.ogrnip = info.get("ogrnip") or None
        s.trademark = info.get("trademark") or None

        new_stats.append(s)

    return new_stats, existing_ids
