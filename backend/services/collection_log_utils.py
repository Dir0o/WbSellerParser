from typing import Any, Dict, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import SessionLocal
from models.collection_log import CollectionLog

def _session(db: Optional[Session]):
    if db is not None:
        return db, False
    return SessionLocal(), True

def get_last_collection(parser_type: str, params: Dict[str, Any], db: Optional[Session] = None):
    db, close = _session(db)
    try:
        h = CollectionLog.calc_hash(params)
        row = (
            db.query(CollectionLog.collected_at)
            .filter(CollectionLog.parser_type == parser_type, CollectionLog.params_hash == h)
            .first()
        )
        return row[0] if row else None
    finally:
        if close:
            db.close()


def touch_collection(parser_type: str, params: Dict[str, Any], db: Optional[Session] = None):
    db, close = _session(db)
    try:
        n = CollectionLog._normalize_params(params)
        h = CollectionLog.calc_hash(n)
        rec = (
            db.query(CollectionLog)
            .filter(CollectionLog.parser_type == parser_type, CollectionLog.params_hash == h)
            .first()
        )
        if rec:
            rec.collected_at = func.now()
        else:
            db.add(CollectionLog(parser_type=parser_type, params_hash=h, params=n))
        db.commit()
    finally:
        if close:
            db.close()
