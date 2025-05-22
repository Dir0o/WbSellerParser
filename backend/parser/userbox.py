from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Sequence

from parser.HTTPClient import AsyncHttpClient
from parser.parser_cfg import settings as ParserConfig
from parser.userboxModels import UsersboxInfo
from parser.userboxFetcher import UsersboxFetcher
from parser.userboxParser import UsersboxParser
from utils.decorators import log_elapsed
from config import USERBOX_KEY

logger = logging.getLogger(__name__)


def _is_valid_inn(value: str) -> bool:
    """Плоская проверка ИНН: 10‑, 12‑, 13‑ или 15‑значная цифровая строка."""
    return value.isdigit() and len(value) in (10, 12)


@log_elapsed()
async def parse_records(inns: Iterable[str]) -> List[UsersboxInfo]:
    """Получает список ИНН → возвращает список `UsersboxInfo`."""
    inns_list = list(inns)
    if not inns_list:
        return []

    headers = {"Authorization": USERBOX_KEY}

    async with AsyncHttpClient(headers=headers) as client:
        raw = await UsersboxFetcher(inns_list, client).fetch()
        return UsersboxParser().parse(raw)


async def parse_me() -> Optional[Dict[str, Any]]:
    url = "https://api.usersbox.ru/v1/getMe"
    headers = {"Authorization": USERBOX_KEY}

    try:
        async with AsyncHttpClient(headers=headers) as client:
            resp = await client.fetch_json(url)
    except Exception as e:
        logger.error("Usersbox /getMe failed: %s", e)
        return None

    if not resp or resp.get("status") != "success":
        logger.warning("Unexpected Usersbox /getMe response: %s", resp)
        return None

    data = resp.get("data")
    if data:
        return data.get('balance')
    else:
        return 0

__all__ = [
    "parse_records",
    "UsersboxInfo",
    "UsersboxFetcher",
    "UsersboxParser",
]

if __name__ == "__main__":
    a = asyncio.run(parse_records(
        ids = [9705088716],
        seller_id=31995
    ))
