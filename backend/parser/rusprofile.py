from __future__ import annotations

import asyncio
import logging
import re
from typing import Iterable, List, Sequence

from .parser_cfg import settings as ParserConfig
from .HTTPClient import AsyncHttpClient
from utils.decorators import log_elapsed
from .RusprofileFetcher import (
    RPCardParser,
    RPSearchParser,
    RPCardFetcher,
    RPSearchFetcher
)
from .RusprofileModels import CompanyInfo
from utils.rusprofile_utils import _is_valid_inn, _css_first, _prepare_ids

logger = logging.getLogger(__name__)

def _is_valid_inn(value: str) -> bool:
    """ИНН = только цифры и длина 10 (юр.лицо) или 12 (физ.лицо)."""
    return value.isdigit() and len(value) in (10, 12, 13, 15)

@log_elapsed()
async def parse_companies(ids: Iterable[str | int], seller_id: int) -> List[CompanyInfo]:
    """
    :param ids: строки вида "1234567890&type=ul" или "123456789012&type=ip"
    :return: список CompanyInfo
    """

    uniq: List[str] = []
    seen: set[str] = set()
    for raw in ids:
        s = str(raw).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        num = s.split("&", 1)[0]
        if not _is_valid_inn(num):
            logger.debug("Skip %s: invalid INN", s)
            continue
        uniq.append(s)
    if not uniq:
        return []

    sem_search = asyncio.Semaphore(ParserConfig.SEARCH_CONCURRENCY)
    sem_card = asyncio.Semaphore(ParserConfig.CARD_CONCURRENCY)
    timeout = ParserConfig.COMPANY_TIMEOUT
    results: List[CompanyInfo] = []

    async def process_one(query: str, client: AsyncHttpClient) -> CompanyInfo | None:
        try:

            search_url = f"https://www.rusprofile.ru/search?query={query}"
            async with sem_search:
                head = await client.head(search_url, allow_redirects=False)
            loc = head.headers.get("Location")
            if head.status in (301, 302) and loc:
                card_url = loc if loc.startswith("http") else f"https://www.rusprofile.ru{loc}"
            else:
                async with sem_search:
                    html = await client.fetch_text(search_url, headers={"Accept": "text/html"})

                links = RPSearchParser().parse([html])
                if not links:
                    return None
                card_url = links[0]

            async with sem_card:
                card_html = await client.fetch_text(card_url, headers={"Accept": "text/html"})

            infos = RPCardParser().parse([card_html])
            return infos[0] if infos else None

        except Exception as e:
            logger.error("Error parsing rusprofile for %s: %s", query, e)
            return None

    async with AsyncHttpClient(proxy="random") as client:
        tasks = [
            asyncio.create_task(
                asyncio.wait_for(process_one(q, client), timeout)
            )
            for q in uniq
        ]

        completed = await asyncio.gather(*tasks, return_exceptions=True)
        for res in completed:
            if isinstance(res, CompanyInfo):
                res.seller_id = seller_id
                results.append(res)
            elif isinstance(res, asyncio.TimeoutError):
                logger.warning("Timeout parsing rusprofile for a company query, skipping")
            elif isinstance(res, Exception):
                logger.error("Failed parsing rusprofile query: %s", res)
    return results