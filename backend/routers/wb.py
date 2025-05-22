from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
import tempfile, os, uuid
from typing import List, Optional
from datetime import datetime

from dependencies import get_current_user
from schemas.wb import WBParams, SellerOut

from services.wb_service import collect_data
from services.db_utils import get_seller, update_seller_sale_count
from services.collection_log_utils import get_last_collection, touch_collection

from utils.excel import generate_excel
from utils.wb_utils import _collect_subcategories

from parser.rusprofile import parse_companies
from parser.HTTPClient import AsyncHttpClient

router = APIRouter()

@router.get(
    "/cat",
    summary="Получить список продавцов и сохранить в БД",
)
async def get_sellers(
    params: WBParams = Depends(),
    region_id: str = Query(..., pattern=r"^\d{2}(?:[,;]\d{2})*$", description="Код региона"),
    limit: Optional[int] = Query(None, ge=0, description="Максимальное число продавцов"),
    #user=Depends(get_current_user),
):
    if limit == 0:
        limit = None

    data, flag_limit = await collect_data(
        params,
        region_id=region_id,
        limit=limit
    )
    payload = _clean_params(
        {
            **params.dict(exclude_none=True),
            "region_id": region_id,
        }
    )
    touch_collection("cat", payload)
    return data

@router.get("/cat/xlsx")
async def download_sellers_excel(
    params: WBParams = Depends(),
    region_id: str = Query(..., pattern=r"^\d{2}(?:[,;]\d{2})*$", description="Код региона"),
    limit: Optional[int] = Query(None, ge=0, description="Максимальное число продавцов"),
    user=Depends(get_current_user),
):
    data, flag = await collect_data(params, region_id=region_id, limit=limit)
    path = os.path.join(
        tempfile.gettempdir(),
        f"sellers_{uuid.uuid4().hex}.xlsx"
    )
    generate_excel(data, filename=path)

    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="sellers.xlsx"
    )

@router.get(
    "/all",
    response_model=List[SellerOut],
    summary="Парсинг всех вложенных категорий по main_id",
)
async def get_all_categories(
    main_id: int = Query(..., description="ID главной категории"),
    pages: int = Query(1, ge=1, description="Страниц на каждую подкатегорию"),
    region_id: str = Query(..., pattern=r"^\d{2}(?:[,;]\d{2})*$", description="Код региона"),
    saleItemCount: int = Query(0, ge=0, description="Мин. количество продаж"),
    maxSaleCount: Optional[int] = Query(None, ge=0, description="Макс. количество продаж"),
    regDate: Optional[str] = Query(None, description="Мин. дата регистр. YYYY-MM-DD"),
    maxRegDate: Optional[str] = Query(None, description="Макс. дата регистр. YYYY-MM-DD"),
    limit: Optional[int] = Query(None, ge=0, description="Максимальное число продавцов"),
    #user=Depends(get_current_user),
):
    if limit == 0:
        limit = None
    result = []
    for cat in _collect_subcategories(main_id):
        if limit and limit>0:
            limit=limit-len(result)
        params = WBParams(
            cat=cat.get('query'),
            shard=cat.get('shard'),
            region_id=region_id,
            saleItemCount=saleItemCount,
            maxSaleCount=maxSaleCount,
            pages=pages,
            regDate=regDate,
            maxRegDate=maxRegDate,
        )
        data, flag_limit = await collect_data(
            params,
            region_id=region_id,
            limit=limit
        )
        for d in data:
            result.append(d)
        if flag_limit or limit and len(result) >= limit:
            break
    if result:
        payload = _clean_params({
            "main_id": main_id,
            "pages": pages,
            "region_id": region_id,
            "saleItemCount": saleItemCount,
            "maxSaleCount": maxSaleCount,
        })
        touch_collection("all", payload)
    return result


@router.get("/all/xlsx")
async def download_all_categories_excel(
    main_id: int = Query(..., description="ID главной категории"),
    pages: int = Query(1, ge=1, description="Страниц на каждую подкатегорию"),
    region_id: str = Query(..., pattern=r"^\d{2}(?:[,;]\d{2})*$", description="Код региона"),
    saleItemCount: int = Query(0, ge=0, description="Мин. количество продаж"),
    maxSaleCount: Optional[int] = Query(None, ge=0, description="Макс. количество продаж"),
    regDate: Optional[str] = Query(None, description="Мин. дата регистр. YYYY-MM-DD"),
    maxRegDate: Optional[str] = Query(None, description="Макс. дата регистр. YYYY-MM-DD"),
    limit: Optional[int] = Query(None, ge=0, description="Максимальное число продавцов"),
    user=Depends(get_current_user),
):
    result = []
    for cat in _collect_subcategories(main_id):
        limit = limit - len(result)
        params = WBParams(
            cat=cat.get('query'),
            shard=cat.get('shard'),
            region_id=region_id,
            saleItemCount=saleItemCount,
            maxSaleCount=maxSaleCount,
            pages=pages,
            regDate=regDate,
            maxRegDate=maxRegDate,
        )
        data, flag_limit = await collect_data(
            params,
            region_id=region_id,
            limit=limit
        )
        for d in data:
            result.append(d)

        if flag_limit or len(result) >= limit:
            break

    path = os.path.join(
        tempfile.gettempdir(),
        f"sellers_{uuid.uuid4().hex}.xlsx"
    )
    generate_excel(result, filename=path)

    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="sellers.xlsx"
    )


@router.get(
    "/seller_info",
    summary="Получает информацию о продавце по запросу с Rusprofile",
)
async def get_all_categories(
    query: str = Query(..., description="OGRN/OGRNIP &type=ul/&type=ip"),
    seller_id: int = Query(..., description="Айди продавца")

):
    a = await parse_companies(
        ids = [query],
        seller_id = seller_id
    )

    return a

IGNORED_KEYS = {"limit", "regDate", "maxRegDate"}

def _clean_params(raw: dict) -> dict:
    """убираем лишние ключи и приводим '0' → 0, '12' → 12"""
    out = {}
    for k, v in raw.items():
        if k in IGNORED_KEYS or v in (None, ""):
            continue
        # строка-число → int
        if isinstance(v, str) and v.isdigit():
            out[k] = int(v)
        else:
            out[k] = v
    return out

@router.get("/cat/last")
async def last_cat(request: Request):
    params = _clean_params(dict(request.query_params))
    ts = get_last_collection("cat", params)
    return {"last_collected": ts}

@router.get("/all/last")
async def last_all(request: Request):
    params = _clean_params(dict(request.query_params))
    ts = get_last_collection("all", params)
    return {"last_collected": ts}

@router.post(
    "/update_seller_data",
    summary="Разовый запрос к WB, обновляет saleItemQuantity в БД",
)
async def update_seller_data(
    seller_id: int = Query(..., ge=1, description="ID продавца Wildberries"),
):
    """
    • Делаем один GET на
      https://suppliers-shipment-2.wildberries.ru/api/v1/suppliers/{seller_id}

    • Берём поле `saleItemQuantity` и сохраняем в БД.

    • Отдаём новое значение в ответе.
    """
    url = (
        "https://suppliers-shipment-2.wildberries.ru/api/v1/suppliers/"
        f"{seller_id}"
    )

    async with AsyncHttpClient(proxy="random") as client:
        payload = await client.fetch_json(url)

    sale_q = payload.get("saleItemQuantity")
    if sale_q is None:
        return {"status": "error", "detail": "saleItemQuantity not found"}

    try:
        update_seller_sale_count(seller_id, sale_q)
    except Exception as e:
        return {"status": "error", "detail": str(e)}

    return {"status": "ok", "saleItemQuantity": sale_q}