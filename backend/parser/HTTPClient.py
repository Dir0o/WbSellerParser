from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from threading import Lock
from typing import Any, Dict, Protocol, Optional

import aiohttp
from aiohttp import ClientTimeout, ClientResponseError
from fake_useragent import UserAgent

from parser.parser_cfg import settings as ParserConfig
from proxy.manager import get_all_proxies


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


_PROXY_POOL: deque[str] = deque()
_POOL_LOCK = Lock()

_BAD_TTL = 60
_BAD: dict[str, float] = {}


def _canon(px: str | None) -> str:
    """user:pass@ip:port (lower-case, без схемы)."""
    if not px:
        return ""
    px = px.lower()
    for p in ("http://", "https://", "socks5://"):
        if px.startswith(p):
            return px[len(p) :]
    return px

def _wrap(px: str | None) -> str | None:
    """Добавляем http://, если нужно, иначе None."""
    return None if not px else (px if "://" in px else f"http://{px}")

class UserAgentProvider(Protocol):
    def get(self) -> str: ...

class RandomUserAgentProvider:
    """Случайный UA через *fake_useragent*."""
    def __init__(self) -> None:
        self._ua = UserAgent()
    def get(self) -> str:
        return self._ua.random

def _next_proxy(last: str | None) -> str | None:
    """
    round-robin без повторов (кроме last, если очередь «замкнулась»);
    пропускаем IP из бан-листа.
    """
    now = time.time()
    with _POOL_LOCK:

        if not _PROXY_POOL:
            _PROXY_POOL.extend(get_all_proxies())
            if not _PROXY_POOL:
                return None


        for k, ts in list(_BAD.items()):
            if now > ts:
                _BAD.pop(k, None)

        tries = len(_PROXY_POOL)
        while tries:
            px = _PROXY_POOL[0]
            _PROXY_POOL.rotate(-1)
            key = _canon(px)
            if key in _BAD or key == (last or ""):
                tries -= 1
                continue
            return px

        return None

class AsyncHttpClient:
    """aiohttp-обёртка с прокси и retry."""

    def __init__(
        self,
        timeout: int = ParserConfig.TIMEOUT,
        retries: int = ParserConfig.RETRIES,
        backoff: float = ParserConfig.BACKOFF,
        proxy: str | None = ParserConfig.PROXY_URL,   # None | "random" | конкретный
        ua_provider: UserAgentProvider | None = None,
        headers: dict | None = None,
    ) -> None:
        self._timeout_cfg = ClientTimeout(total=timeout)
        self._retries = retries
        self._backoff = backoff
        self._proxy_cfg = proxy
        self._ua_provider = ua_provider or RandomUserAgentProvider()
        self._session: aiohttp.ClientSession | None = None
        self._headers = headers or {}
        self._last_proxy: str | None = None

    # ───────── context mgr ──────────────────────────────────────
    async def __aenter__(self) -> "AsyncHttpClient":
        self._session = aiohttp.ClientSession(
            timeout=self._timeout_cfg,
            connector=aiohttp.TCPConnector(
                limit=ParserConfig.CONN_LIMIT,
                limit_per_host=ParserConfig.PER_HOST_LIMIT,
                ttl_dns_cache=600,
                enable_cleanup_closed=True,
            ),
            headers=self._headers,
        )
        return self

    async def __aexit__(self, *_exc) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def _pick_proxy(self) -> str | None:
        if self._proxy_cfg and self._proxy_cfg not in ("random",):
            return _wrap(self._proxy_cfg)

        if (self._proxy_cfg == "random") or ParserConfig.USE_PROXY:
            px = _next_proxy(self._last_proxy)
            self._last_proxy = _canon(px)
            return _wrap(px)
        return None


    def _ban(self, proxy_url: str | None) -> None:
        if proxy_url:
            _BAD[_canon(proxy_url)] = time.time() + _BAD_TTL

    async def _request_json(self, url: str) -> Dict[str, Any]:
        """GET JSON с retry/back-off."""
        for att in range(1, self._retries + 1):
            proxy_url = self._pick_proxy()
            logger.warning(f"JSON {proxy_url} {url}")
            try:
                async with self._session.get(
                    url,
                    headers={
                        "User-Agent": self._ua_provider.get(),
                        "Accept": "*/*",
                        "x-client-name": "site",
                        "accept-encoding": "br, gzip",
                    },
                    proxy=proxy_url,
                ) as resp:
                    if resp.status == 200:
                        return await resp.json(content_type=None)

                    if resp.status in (400, 404, 422):
                        return {}

                    if resp.status in (429, 403):
                        logger.warning("🚫 %s (%s/%s) %s via %s",
                                       resp.status, att, self._retries, url, proxy_url)
                        self._ban(proxy_url)
                        await asyncio.sleep(self._backoff * att)
                        continue

                    resp.raise_for_status()

            except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
                await asyncio.sleep(self._backoff * att)
            except ClientResponseError as exc:
                if exc.status in (400, 404, 422):
                    return {}
                await asyncio.sleep(self._backoff * att)
        return {}

    async def _request_text(self, url: str, headers: dict | None = None) -> str:
        for att in range(1, self._retries + 1):
            proxy_url = self._pick_proxy()
            logger.warning(f"TEXT {proxy_url} {url}")
            try:
                async with self._session.get(
                    url,
                    headers=headers
                    or {
                        "User-Agent": self._ua_provider.get(),
                        "Accept": "text/html",
                    },
                    proxy=proxy_url,
                ) as resp:
                    if resp.status == 200:
                        return await resp.text()

                    if resp.status in (400, 404, 422):
                        return ""

                    if resp.status in (429, 403):
                        self._ban(proxy_url)
                        await asyncio.sleep(self._backoff * att)
                        continue
                    resp.raise_for_status()
            except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
                await asyncio.sleep(self._backoff * att)
            except ClientResponseError as exc:
                if exc.status in (400, 404, 422):
                    return ""
                await asyncio.sleep(self._backoff * att)
        return ""

    async def _request_head(self, url: str, allow_redirects: bool) -> aiohttp.ClientResponse:
        for att in range(1, self._retries + 1):
            proxy_url = self._pick_proxy()
            logger.warning(f"HEAD {proxy_url} {url}")
            try:
                async with self._session.head(
                    url,
                    headers={
                        "User-Agent": self._ua_provider.get()
                    },
                    allow_redirects=allow_redirects,
                    proxy=proxy_url,
                ) as resp:
                    if resp.status not in (429, 403):
                        return resp
                    self._ban(proxy_url)
                    await asyncio.sleep(self._backoff * att)
            except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
                await asyncio.sleep(self._backoff * att)

        return await self._session.head(url, allow_redirects=allow_redirects)

    async def fetch_json(self, url: str) -> Dict[str, Any]:
        if not self._session:
            raise RuntimeError("use 'async with'")
        return await self._request_json(url)

    async def fetch_text(self, url: str, *, headers: dict | None = None) -> str:
        if not self._session:
            raise RuntimeError("use 'async with'")
        return await self._request_text(url, headers=headers)

    async def head(self, url: str, *, allow_redirects: bool = False) -> aiohttp.ClientResponse:
        if not self._session:
            raise RuntimeError("use 'async with'")
        return await self._request_head(url, allow_redirects=allow_redirects)
