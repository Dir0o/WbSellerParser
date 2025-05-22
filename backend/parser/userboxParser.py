from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from .userboxModels import UsersboxInfo

class UsersboxParser:
    """Разворачивает `data.items` и кладёт каждый элемент в UsersboxInfo."""

    def _dig_inn(self, payload: Mapping[str, Any]) -> Optional[str]:
        """Грубо ищем поле `inn` в глубину (первое встретившееся)."""
        if "inn" in payload and isinstance(payload["inn"], str):
            return payload["inn"]
        for v in payload.values():
            if isinstance(v, Mapping):
                inn = self._dig_inn(v)
                if inn:
                    return inn
            elif isinstance(v, (list, tuple)):
                for item in v:
                    if isinstance(item, Mapping):
                        inn = self._dig_inn(item)
                        if inn:
                            return inn
        return None

    def parse(self, responses: Iterable[Mapping[str, Any]]) -> List[UsersboxInfo]:
        out: List[UsersboxInfo] = []
        for resp in responses:
            if not resp or resp.get("status") != "success":
                continue

            items = resp.get("data", {}).get("items", [])
            if not items:
                continue

            for part in items:
                if not isinstance(part, Mapping):
                    continue
                inn = self._dig_inn(part)
                out.append(UsersboxInfo(inn=inn, payload=dict(part)))
 
        return out