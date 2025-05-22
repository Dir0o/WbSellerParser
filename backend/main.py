from fastapi import FastAPI
from config import settings
from middleware import register_middleware
from routers import wb, auth, search, userbox


app = FastAPI(title="INNParser", version="1.0")

register_middleware(app)

# Роутеры
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(wb.router, prefix="/wb", tags=["wb"])
app.include_router(search.router, prefix="/search", tags=['search'])
app.include_router(userbox.router, prefix = "/usersbox", tags = ["usersbox"])
