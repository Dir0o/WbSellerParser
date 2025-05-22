from typing import Iterable

def _is_valid_inn(value: str) -> bool:
    """ИНН = только цифры и длина 10 (юр.лицо) или 12 (физ.лицо)."""
    return value.isdigit() and len(value) in (10, 12, 13, 15)

def _css_first(node, selector: str):
    fn = getattr(node, "css_first", None)
    return fn(selector) if callable(fn) else node.select_one(selector)

def _prepare_ids(ids: Iterable[str | int]) -> list[str]:
    seen: set[str] = set()
    uniq: list[str] = []
    for raw in ids:
        s = str(raw).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        uniq.append(s)
    return uniq