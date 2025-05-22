from __future__ import annotations

import asyncio
import logging
import re
from typing import Iterable, List, Sequence

from .parser_cfg import settings as ParserConfig
from pydantic import BaseModel, HttpUrl
from .HTTPClient import AsyncHttpClient
from utils.decorators import log_elapsed
from .RusprofileModels import CompanyInfo
from utils.rusprofile_utils import _is_valid_inn, _css_first, _prepare_ids

try:
    from selectolax.parser import HTMLParser
    def _soup(html: str) -> "HTMLParser":
        return HTMLParser(html)
    def _text(node, default: str = "") -> str:
        return node.text(strip=True) if node else default
    _FIND_ALL = lambda soup, css: soup.css(css)  # noqa: E731
except ModuleNotFoundError:
    from bs4 import BeautifulSoup
    def _soup(html: str) -> "BeautifulSoup":
        return BeautifulSoup(html, "html.parser")
    def _text(node, default: str = "") -> str:
        return node.get_text(strip=True) if node else default
    def _FIND_ALL(soup, css):
        tag, cls = css.split(".")
        return soup.find_all(tag, class_=cls)


class RPSearchFetcher:
    _URL = "https://www.rusprofile.ru/search?query={query}"
    def __init__(self, queries: Sequence[str], client: AsyncHttpClient) -> None:
        self._queries = list(queries)
        self._client = client
    async def fetch_raw(self) -> List[str]:
        sem = asyncio.Semaphore(ParserConfig.SEARCH_CONCURRENCY)
        async def one(q: str) -> str:
            url = self._URL.format(query=q)
            async with sem:
                return await self._client.fetch_text(
                    url,
                    headers={
                        "User-Agent": self._client._ua_provider.get(),
                        "Accept": "text/html",
                    },
                )
        return await asyncio.gather(*(one(q) for q in self._queries))


class RPSearchParser:
    _COMPANY_RE = re.compile(r"^/id/\d+")
    def parse(self, pages: Iterable[str]) -> List[str]:
        links: List[str] = []
        for html in pages:
            soup = _soup(html)

            canon = soup.css_first("link[rel=canonical]") if hasattr(soup, "css_first") else None
            if canon:
                href = canon.attributes.get("href") if hasattr(canon, "attributes") else canon.get("href")
                links.append(href)
                continue

            for div in _FIND_ALL(soup, "div.company-item__title"):
                a = div.css_first("a") if hasattr(div, "css_first") else div.find("a")
                href = a.attributes.get("href") if hasattr(a, "attributes") else a.get("href")
                if self._COMPANY_RE.match(href):
                    links.append("https://www.rusprofile.ru" + href)
        return links

class RPCardFetcher:
    _CONCURRENCY = ParserConfig.CARD_CONCURRENCY
    def __init__(self, urls: Sequence[str], client: AsyncHttpClient) -> None:
        self._urls = urls
        self._client = client
    async def fetch_raw(self) -> List[str]:
        sem = asyncio.Semaphore(self._CONCURRENCY)
        async def one(url: str) -> str:
            async with sem:
                return await self._client.fetch_text(
                    url,
                    headers={
                        "User-Agent": self._client._ua_provider.get(),
                        "Accept": "text/html",
                    },
                )
        return await asyncio.gather(*(one(u) for u in self._urls))

class RPCardParser:
    def parse(self, pages: Iterable[str]) -> List[CompanyInfo]:
        out: List[CompanyInfo] = []
        for html in pages:
            soup = _soup(html)

            ogrn_text = _text(_css_first(soup, "#req_ogrn") or _css_first(soup, "#clip_ogrn"))
            ogrnip_text = _text(_css_first(soup, "#req_ogrnip") or _css_first(soup, "#clip_ogrnip"))
            inn = _text(_css_first(soup, "#req_inn") or _css_first(soup, "#clip_inn"))


            tax = ""
            for dl in _FIND_ALL(soup, "dl.requisites-ip__list"):
                dt = _text(dl.css_first("dt") if hasattr(dl, "css_first") else dl.find("dt"))
                dd = _text(dl.css_first("dd") if hasattr(dl, "css_first") else dl.find("dd"))
                if dt in {"Налоговый орган", "Регистратор"}:
                    tax = dd
                    break
            if not tax:
                for row in _FIND_ALL(soup, "div.company-row"):
                    title = _text(_css_first(row, ".company-info__title"))
                    if any(title.startswith(k) for k in ("Налоговый орган", "Регистратор")):
                        tax = _text(_css_first(row, ".company-info__text"))
                        break

            out.append(CompanyInfo(
                tax_office= tax,
                ogrn= ogrn_text if ogrn_text else None,
                ogrnip= ogrnip_text if ogrnip_text else None,
                inn = inn if inn else None
            ))
        return out