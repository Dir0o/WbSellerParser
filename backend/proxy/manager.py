from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import List

import requests
from config import PROXY_KEY
import itertools, asyncio

_proxy_cycle_lock = asyncio.Lock()
_proxy_cycle = None

_CACHE_FILE = Path(__file__).with_suffix(".cache.json")
_TTL = 24 * 3600


def _save_cache(proxies: List[str]) -> None:
    _CACHE_FILE.write_text(
        json.dumps({"ts": int(time.time()), "proxies": proxies}, ensure_ascii=False)
    )


def _load_cache() -> List[str]:
    if not _CACHE_FILE.exists():
        return []
    try:
        data = json.loads(_CACHE_FILE.read_text())
        if int(time.time()) - data.get("ts", 0) < _TTL:
            return data.get("proxies", [])
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _fetch_from_api() -> List[str]:
    url = f"https://panel.proxyline.net/api/proxies/?api_key={PROXY_KEY}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    items = resp.json().get("results", [])
    proxies = [
        f"{p['user']}:{p['password']}@{p['ip']}:{p['port_http']}" for p in items
    ]
    if proxies:
        _save_cache(proxies)
    return proxies


def get_random_proxy() -> str | None:
    proxies = _load_cache()
    if not proxies:
        try:
            proxies = _fetch_from_api()
        except Exception:
            proxies = _load_cache()
    return random.choice(proxies) if proxies else None


def get_all_proxies() -> list[str]:
    """Возвращает текущий список прокси (из кэша или API)."""
    proxies = _load_cache()
    if proxies:
        return proxies
    try:
        return _fetch_from_api()
    except Exception:
        return []

async def get_next_proxy() -> str | None:
    global _proxy_cycle
    async with _proxy_cycle_lock:
        if _proxy_cycle is None:
            proxies = _load_cache() or _fetch_from_api()
            random.shuffle(proxies)
            _proxy_cycle = itertools.cycle(proxies) if proxies else itertools.cycle([None])
        return next(_proxy_cycle)