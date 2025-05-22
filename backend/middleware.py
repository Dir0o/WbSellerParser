import logging, time
from datetime import datetime
import os
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse, FileResponse
from uvicorn.logging import AccessFormatter
from config import settings
import json
from fastapi.middleware.cors import CORSMiddleware


def register_middleware(app: FastAPI):
    logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)
    access_logger = logging.getLogger("uvicorn.access")
    for h in access_logger.handlers:
        h.setFormatter(
            AccessFormatter(
                fmt="%(levelprefix)s %(asctime)s %(client_addr)s - \"%(request_line)s\" %(status_code)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
    @app.middleware("http")
    async def add_process_time(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        if request.url.path.startswith(("/docs", "/openapi", "/redoc", "/auth/token")): # Эндпоинты, которые игнорируются
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

    raw = os.getenv("CORS_ORIGINS", "")
    allow_origins = [u.strip() for u in raw.split(",") if u.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )