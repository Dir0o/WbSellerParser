from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel

__all__ = ["UsersboxInfo"]

class UsersboxInfo(BaseModel):
    """Единица информации, полученная с usersbox.ru (или аналога)."""

    inn: Optional[str] = None
    payload: Dict[str, Any]
    seller_id: Optional[int] = None