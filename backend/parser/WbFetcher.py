from typing import Optional, Union, List, Dict, Tuple, Sequence, Iterable, Mapping, Any
import asyncio
import aiohttp

from .HTTPClient import AsyncHttpClient
from .WbModels import SellerStats


class WBProductFetcher:
    _BASE_URL = "https://catalog.wb.ru/catalog/{shard}/v2/catalog?{category}"

    def __init__(
        self,
        category: str,
        shard: str,
        pages: int,
        client: AsyncHttpClient,
        concurrency: int = 10,  # ограничим число одновременных запросов
    ) -> None:
        self._category = category
        self._shard = shard
        self._pages = pages
        self._client = client
        self._sem = asyncio.Semaphore(concurrency)

    def _build_urls(self) -> list[str]:
        return [
            (
                f"{self._BASE_URL.format(shard=self._shard, category=self._category)}"
                f"&ab_testing=false&hide_dtype=13&appType=1&curr=rub&dest=-364001"
                f"&lang=ru&page={page}&sort=popular&spp=30"
            )
            for page in range(1, self._pages + 1)
        ]

    async def fetch(self) -> list[Dict[str, Any]]:
        """
        Фетчим страницы с ограничением по concurrency, чтобы не перегружать API и контролировать потребление памяти.
        """
        async def _one(url: str) -> Dict[str, Any]:
            async with self._sem:
                return await self._client.fetch_json(url)

        urls = self._build_urls()
        # Запускаем батчи задач, чтобы не создавать слишком много одновременных корутин
        tasks = [_one(u) for u in urls]
        results = []
        # Выполняем сгруппированные gather, если хочется ещё сильнее контролировать
        for i in range(0, len(tasks), self._sem._value):  # группируем в блоки size=concurrency
            batch = tasks[i : i + self._sem._value]
            results.extend(await asyncio.gather(*batch))
        return results



class WBProductParser:
    def parse(self, responses: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        products: List[Dict[str, Any]] = []
        for resp in responses:
            products.extend(resp.get("data", {}).get("products", []))
        return products


class WBSellerInnFetcher:
    _URL = "https://static-basket-01.wbbasket.ru/vol0/data/supplier-by-id/{sellerId}.json"
    _CONCURRENCY = 50

    def __init__(self, seller_ids: Sequence[int], client: AsyncHttpClient) -> None:
        self._ids = list(seller_ids)
        self._client = client

    async def fetch(self) -> List[Dict[str, Any]]:
        sem = asyncio.Semaphore(self._CONCURRENCY)
        async def one(sid: int) -> Dict[str, Any]:
            url = self._URL.format(sellerId=sid)
            async with sem:
                return await self._client.fetch_json(url)
        return await asyncio.gather(*(one(s) for s in self._ids))


class WBSellerInnParser:
    """Парсит ИНН, ОГРН, ОГРНИП и название магазина."""
    def parse(self, responses: Iterable[Mapping[str, Any]]) -> Dict[int, Dict[str, str]]:
        out: Dict[int, Dict[str, str]] = {}
        for resp in responses:

            inn = resp.get("inn") or resp.get("taxpayerCode")
            if not inn:
                continue
            out[resp["supplierId"]] = {
                "inn": inn,
                "ogrn": resp.get("ogrn", ""),
                "ogrnip": resp.get("ogrnip", ""),
                "trademark": resp.get("trademark") or resp.get("brand") or resp.get("supplierName") or "",
            }
        return out


class WBSellerFetcher:
    _URL = "https://suppliers-shipment-2.wildberries.ru/api/v1/suppliers/{sellerId}"
    _CONCURRENCY = 50

    def __init__(self, seller_ids: Sequence[int], client: AsyncHttpClient) -> None:
        self._ids = list(seller_ids)
        self._client = client

    async def fetch(self) -> List[Dict[str, Any]]:
        sem = asyncio.Semaphore(self._CONCURRENCY)
        async def one(sid: int) -> Dict[str, Any]:
            url = self._URL.format(sellerId=sid)
            async with sem:
                return await self._client.fetch_json(url)
        return await asyncio.gather(*(one(s) for s in self._ids))


class WBSellerParser:
    def parse(self, responses: Iterable[Mapping[str, Any]]) -> List[SellerStats]:
        stats: List[SellerStats] = []
        for resp in responses:
            if not resp:
                continue
            try:
                stats.append(SellerStats.parse_obj(resp))
            except Exception:
                logger.warning("Skip malformed seller payload")
        return stats