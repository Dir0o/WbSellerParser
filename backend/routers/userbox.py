from fastapi import APIRouter, HTTPException
from datetime import datetime
import requests
from parser.userbox import parse_me

router = APIRouter()

@router.get("/balance", summary="Получить текущий баланс Usersbox")
async def get_usersbox_balance():
    try:
        balance = await parse_me()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return balance
