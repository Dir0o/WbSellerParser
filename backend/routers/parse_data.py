from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from database import SessionLocal
from models.parse_data import ParseData
from pydantic import BaseModel


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter()

class ParseDataBase(BaseModel):
    id: int
    created_at: datetime
    category: str
    shard: str
    region_id: str
    sale_item_count: int
    max_sale_count: int
    reg_date: datetime
    max_reg_date: datetime
    rows: int          # вычисляем длину data

    class Config:
        orm_mode = True

@router.get("/", response_model=List[ParseDataBase])
def list_parse_data(db: Session = Depends(get_db)):
    rows = db.query(ParseData).order_by(ParseData.created_at.desc()).all()
    return [
        ParseDataBase(
            **r.__dict__,
            rows=len(r.data)
        ) for r in rows
    ]

@router.get("/{parse_id}", response_model=ParseDataBase)
def get_parse_data(parse_id: int, db: Session = Depends(get_db)):
    r = db.query(ParseData).filter(ParseData.id == parse_id).first()
    if not r:
        raise HTTPException(404)
    return ParseDataBase(**r.__dict__, rows=len(r.data))
