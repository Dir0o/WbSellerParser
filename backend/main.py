from fastapi import FastAPI
from config import settings
from middleware import register_middleware
from routers import wb, auth, search, userbox, parse_bg, parse_data
import os
import redis.asyncio as aioredis


app = FastAPI(
    title="INNParser",
    version="1.0",
    redoc_url=None,
    docs_url=None,
    openapi_url=None
)

@app.on_event("startup")
async def on_startup():
   app.state.redis = aioredis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True
    )

@app.on_event("shutdown")
async def on_shutdown():
    await app.state.redis.close()

register_middleware(app)

# Роутеры
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(wb.router, prefix="/wb", tags=["wb"])
app.include_router(search.router, prefix="/search", tags=['search'])
app.include_router(userbox.router, prefix = "/usersbox", tags = ["usersbox"])
app.include_router(parse_bg.router, prefix = "/parse", tags = ["jobs"])
app.include_router(parse_data.router, prefix = "/parse-data", tags = ["parse-data"])