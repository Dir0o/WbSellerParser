from datetime import datetime, timezone
from parser.WbModels import SellerStats
from typing import List, Optional, Dict, Any
import json
from pathlib import Path

async def check_region(seller_list, regions: List[str]) -> List:
    """
    Фильтрует продавцов по списку кодов регионов (строки '77', '50', …).
    """
    result = []
    for x in seller_list:
        code = None
        if x.ogrn and len(x.ogrn) >= 5:
            code = x.ogrn[3:5]
        elif x.ogrnip and len(x.ogrnip) >= 5:
            code = x.ogrnip[3:5]

        if code and code in regions:
            result.append(x)
    return result

def _to_dt(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    parts = value.replace("-", " ").split()

    if len(parts) != 3:
        raise ValueError("registration_date: ожидаю 'YYYY-MM-DD'")
    y, m, d = map(int, parts)
    return datetime(y, m, d, tzinfo=timezone.utc)



def ok_sales(s: SellerStats, max_sales: int, min_sales: int) -> bool:
    if s.sale_item_quantity < min_sales:
        return False
    if max_sales is not None and s.sale_item_quantity > max_sales:
        return False
    return True

def ok_date(s: SellerStats, min_dt: datetime, max_dt: datetime) -> bool:
    rd = s.registration_date
    if min_dt and rd < min_dt:
        return False
    if max_dt and rd > max_dt:
        return False
    return True


def _load_categories() -> List[Dict[str, Any]]:
    path = Path(__file__).parent / "../categories.json"
    return json.loads(path.read_text(encoding="utf-8"))

def _collect_subcategories(main_id: int) -> List[Dict[str, Any]]:
    cats = _load_categories()
    leaves: List[Dict[str, Any]] = []

    def _recurse(node: Dict[str, Any]):
        children = node.get("childs") or []
        if not children:
            leaves.append(node)
        else:
            for child in children:
                _recurse(child)

    for cat in cats:
        if cat.get("id") == main_id:
            for child in cat.get("childs") or []:
                _recurse(child)
            break

    return leaves

