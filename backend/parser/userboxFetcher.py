from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Sequence

from parser.HTTPClient import AsyncHttpClient
from parser.parser_cfg import settings as ParserConfig

__all__ = ["UsersboxFetcher"]

class UsersboxFetcher:

    _URL = "https://api.usersbox.ru/v1/search?q={inn}"

    _CONCURRENCY = ParserConfig.CARD_CONCURRENCY

    def __init__(self, inns: Sequence[str], client: AsyncHttpClient) -> None:
        self._inns = list(inns)
        self._client = client

    async def fetch(self) -> List[Dict[str, Any]]:
        sem = asyncio.Semaphore(self._CONCURRENCY)

        async def _one(inn: str) -> Dict[str, Any]:
            async with sem:
                return await self._client.fetch_json(self._URL.format(inn=inn))

        return await asyncio.gather(*(_one(i) for i in self._inns))