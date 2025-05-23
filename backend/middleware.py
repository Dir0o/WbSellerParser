import logging, time
from datetime import datetime
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse, FileResponse
from uvicorn.logging import AccessFormatter
from config import settings
import json
from fastapi.middleware.cors import CORSMiddleware
import logging

def register_middleware(app: FastAPI):
    logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)
    access_logger = logging.getLogger("uvicorn.access")
    for h in access_logger.handlers:
        h.setFormatter(
            AccessFormatter(
                fmt=(
                  "%(asctime)s | worker-%(process)d | "
                  "%(levelprefix)s | %(client_addr)s - "
                  "\"%(request_line)s\" %(status_code)s"
                ),
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
    @app.middleware("http")
    async def add_process_time(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        if request.url.path.startswith(("/docs", "/openapi", "/redoc", "/auth/token", "/parse", "/wb")): # Эндпоинты, которые игнорируются
            return response
        duration_ms = int((time.time() - start) * 1000)
        if response.headers.get("content-type", "").startswith("application/json"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            try:
                data = json.loads(body)
            except Exception:
                data = body.decode(errors="ignore")
            payload = {"time": f"{duration_ms}ms", "data": data}
            headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in ("content-length", "transfer-encoding")
            }
            return JSONResponse(content=payload, status_code=response.status_code, headers=headers)
        return response

    logging.warning(f"{settings.CORS_ORIGINS}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )