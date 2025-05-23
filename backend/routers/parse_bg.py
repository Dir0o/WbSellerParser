import asyncio
from uuid import uuid4
from typing import List, Optional, Dict, Any
import json
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Depends
from fastapi.responses import FileResponse

from schemas.wb import WBParams, SellerOut
from services.wb_service import collect_data
from services.collection_log_utils import touch_collection
from utils.wb_utils import _collect_subcategories
from utils.excel import generate_excel

router = APIRouter()

IGNORED_KEYS = {"limit", "regDate", "maxRegDate"}
def get_redis(request: Request):
    return request.app.state.redis

@router.post(
    "/",
    summary="Запустить фоновый парсинг по main_id",
)
async def start_parse(
    background_tasks: BackgroundTasks,
    main_id: int = Query(..., description="ID главной категории"),
    pages: int = Query(1, ge=1, description="Страниц на каждую подкатегорию"),
    region_id: str = Query(
        ..., pattern=r"^\d{2}(?:[,;]\d{2})*$", description="Код региона"
    ),
    saleItemCount: int = Query(0, ge=0, description="Мин. количество продаж"),
    maxSaleCount: Optional[int] = Query(
        None, ge=0, description="Макс. количество продаж"
    ),
    regDate: Optional[str] = Query(
        None, description="Мин. дата регистрации YYYY-MM-DD"
    ),
    maxRegDate: Optional[str] = Query(
        None, description="Макс. дата регистрации YYYY-MM-DD"
    ),
    limit: Optional[int] = Query(
        None, ge=1, description="Максимальное число продавцов"
    ),
    concurrency: int = Query(
        3, ge=1, le=20, description="Одновременных запросов к WB API"
    ),
    redis=Depends(get_redis),
):
    """
    Запускает задачу парсинга в фоне и возвращает job_id для отслеживания.
    """
    job_id = str(uuid4())
    await redis.set(
            f"job:{job_id}",
            json.dumps({"status": "pending", "result": None, "error": None}, default=str)
    )

    background_tasks.add_task(
            run_parse_job,
            job_id,
            redis,
            main_id,
            pages,
            region_id,
            saleItemCount,
            maxSaleCount,
            regDate,
            maxRegDate,
            limit,
            concurrency,
    )
    return {"job_id": job_id}

async def run_parse_job(
    job_id: str,
    redis,
    main_id: int,
    pages: int,
    region_id: str,
    saleItemCount: int,
    maxSaleCount: Optional[int],
    regDate: Optional[str],
    maxRegDate: Optional[str],
    limit: Optional[int],
    concurrency: int,
):

    raw = await redis.get(f"job:{job_id}")
    job = json.loads(raw)
    job["status"] = "in_progress"
    await redis.set(f"job:{job_id}", json.dumps(job, default=str))
    try:
        results: List[SellerOut] = []
        remaining = limit

        sem = asyncio.Semaphore(concurrency)

        async def fetch_cat(cat_query: dict) -> List[SellerOut]:
            params = WBParams(
                cat=cat_query["query"],
                shard=cat_query["shard"],
                region_id=region_id,
                saleItemCount=saleItemCount,
                maxSaleCount=maxSaleCount,
                pages=pages,
                regDate=regDate,
                maxRegDate=maxRegDate,
            )
            async with sem:
                data, _ = await collect_data(
                    params,
                    region_id=region_id,
                    limit=remaining,
                )
                return data

        subcats = list(_collect_subcategories(main_id))
        tasks = [asyncio.create_task(fetch_cat(cat)) for cat in subcats]

        for coro in asyncio.as_completed(tasks):
            data = await coro
            for item in data:
                results.append(item)
                if remaining is not None:
                    remaining -= 1
                if remaining == 0:
                    break
            if remaining == 0:
                break

        for t in tasks:
            if not t.done():
                t.cancel()

        if results:
            touch_collection(
                "all",
                {
                    "main_id": main_id,
                    "pages": pages,
                    "region_id": region_id,
                    "saleItemCount": saleItemCount,
                    "maxSaleCount": maxSaleCount,
                },
            )

        job["status"] = "finished"
        job["result"] = [item.dict() for item in results]
        await redis.set(f"job:{job_id}", json.dumps(job, default=str))
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        await redis.set(f"job:{job_id}", json.dumps(job, default=str))

@router.get(
    "/jobs/{job_id}/status",
    summary="Статус фоновой задачи",
)
async def get_job_status(job_id: str,
                         redis=Depends(get_redis)):
    raw = await redis.get(f"job:{job_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Job not found")
    job = json.loads(raw)
    return {"job_id": job_id, "status": job["status"], "error": job.get("error")}

@router.get(
    "/jobs/{job_id}/result",
    response_model=List[SellerOut],
    summary="Результат фоновой задачи",
)
async def get_job_result(job_id: str,
                         redis=Depends(get_redis)):
    raw = await redis.get(f"job:{job_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Job not found")
    job = json.loads(raw)
    if job["status"] in ("pending", "in_progress"):
        raise HTTPException(status_code=202, detail="Job still in progress")
    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=f"Job failed: {job.get('error')}" )
    return job["result"]

@router.get(
    "/jobs/{job_id}/excel",
    summary="Скачать результат парсинга в Excel",
)
async def download_job_excel(job_id: str,
                             redis=Depends(get_redis)):
    raw = await redis.get(f"job:{job_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Job not found")
    job = json.loads(raw)
    if job["status"] in ("pending", "in_progress"):
        raise HTTPException(status_code=202, detail="Job still in progress")
    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=f"Job failed: {job.get('error')}" )

    data: List[SellerOut] = job.get("result") or []
    filename = f"sellers_{job_id}.xlsx"
    generate_excel(data, filename)
    return FileResponse(
        path=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )
