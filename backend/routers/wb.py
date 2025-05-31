from fastapi import APIRouter, Depends, Query, Request, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
import json, tempfile, os, uuid, asyncio
from typing import List, Optional
from datetime import datetime

from dependencies import get_current_user
from schemas.wb import WBParams, SellerOut

from services.wb_service import collect_data
from services.db_utils import get_seller, update_seller_sale_count
from services.collection_log_utils import get_last_collection, touch_collection

from utils.excel import generate_excel
from utils.wb_utils import _collect_subcategories
from utils.db_utils import _save_parse_data

from parser.rusprofile import parse_companies
from parser.HTTPClient import AsyncHttpClient

router = APIRouter()

def get_redis(request: Request):
    return request.app.state.redis

@router.post("/cat/jobs", summary="Запустить фоновый парсинг одной категории")
async def start_cat_parse(
    background_tasks: BackgroundTasks,
    params: WBParams = Depends(),
    region_id: str = Query(..., pattern=r"^\d{2}(?:[,;]\d{2})*$"),
    limit: Optional[int] = Query(None, ge=0),
    redis=Depends(get_redis),
):
    job_id = uuid.uuid4().hex

    initial = {"status": "pending", "result": None, "error": None}
    await redis.set(f"job:{job_id}", json.dumps(initial, default=str))

    background_tasks.add_task(
        run_cat_parse_job,
        job_id,
        redis,
        params,
        region_id,
        limit,
    )
    return {"job_id": job_id}

async def run_cat_parse_job(
    job_id: str,
    redis,
    params: WBParams,
    region_id: str,
    limit: Optional[int],
):

    raw = await redis.get(f"job:{job_id}")
    job = json.loads(raw)
    job["status"] = "in_progress"
    await redis.set(f"job:{job_id}", json.dumps(job, default=str))

    try:

        data, _log = await collect_data(params, region_id=region_id, limit=limit)

        touch_collection("cat", {**params.dict(exclude_none=True), "region_id": region_id})
        _save_parse_data(
            {
                "category": params.cat,
                "shard": params.shard,
                "region_id": region_id,
                "sale_item_count": params.saleItemCount,
                "max_sale_count": params.maxSaleCount or 0,
                "reg_date": params.regDate or datetime.utcnow(),
                "max_reg_date": params.maxRegDate or datetime.utcnow(),
                "data": [item.dict() for item in data],
            }
        )

        job["status"] = "finished"
        job["result"] = [item.dict() for item in data]
        await redis.set(f"job:{job_id}", json.dumps(job, default=str))

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        await redis.set(f"job:{job_id}", json.dumps(job, default=str))

@router.get("/cat/jobs/{job_id}/status", summary="Статус задачи парсинга категории")
async def get_cat_job_status(
    job_id: str,
    redis=Depends(get_redis),
):
    raw = await redis.get(f"job:{job_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Job not found")
    job = json.loads(raw)
    return {"job_id": job_id, "status": job["status"], "error": job.get("error")}

@router.get(
    "/cat/jobs/{job_id}/result",
    response_model=List[SellerOut],
    summary="Результат задачи парсинга категории",
)
async def get_cat_job_result(
    job_id: str,
    redis=Depends(get_redis),
):
    raw = await redis.get(f"job:{job_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Job not found")
    job = json.loads(raw)
    if job["status"] in ("pending", "in_progress"):
        raise HTTPException(status_code=202, detail="Job still in progress")
    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=f"Job failed: {job.get('error')}")
    return job["result"]

@router.get("/cat/jobs/{job_id}/excel", summary="Скачать Excel задачи парсинга категории")
async def download_cat_job_excel(
    job_id: str,
    redis=Depends(get_redis),
):
    raw = await redis.get(f"job:{job_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Job not found")
    job = json.loads(raw)
    if job["status"] in ("pending", "in_progress"):
        raise HTTPException(status_code=202, detail="Job still in progress")
    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=f"Job failed: {job.get('error')}")

    data = job.get("result") or []
    filename = f"sellers_{job_id}.xlsx"
    generate_excel(data, filename)
    return FileResponse(
        path=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )

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
    limit: Optional[int] = Query(None, ge=1, description="Максимальное число продавцов"),
    concurrency: int = Query(3, ge=1, le=20, description="Одновременных запросов к WB API"),
    # user=Depends(get_current_user),
):
    """
    Параллельный парсинг всех подкатегорий с контролем limit и concurrency.
    """

    subcats = list(_collect_subcategories(main_id))

    sem = asyncio.Semaphore(concurrency)
    results: List[SellerOut] = []

    async def fetch_cat(cat_query: dict) -> List[SellerOut]:
        params = WBParams(
            cat=cat_query['query'], shard=cat_query['shard'],
            region_id=region_id, saleItemCount=saleItemCount,
            maxSaleCount=maxSaleCount, pages=pages,
            regDate=regDate, maxRegDate=maxRegDate,
        )

        async with sem:
            data, _ = await collect_data(params, region_id=region_id, limit=limit and max(0, limit - len(results)))
            return data

    tasks = {asyncio.create_task(fetch_cat(cat)): cat for cat in subcats}

    try:
        for coro in asyncio.as_completed(tasks):
            data = await coro
            for d in data:
                results.append(d)
                if limit and len(results) >= limit:
                    break
            if limit and len(results) >= limit:
                break
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

    if results:
        payload = _clean_params({
            "main_id": main_id,
            "pages": pages,
            "region_id": region_id,
            "saleItemCount": saleItemCount,
            "maxSaleCount": maxSaleCount,
        })
        touch_collection("all", payload)

    return results


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