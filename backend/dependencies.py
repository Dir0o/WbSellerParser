from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from typing import Optional
from config import settings
from database import SessionLocal
from models.user import User as UserModel
from schemas.auth import UserRead

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserRead:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user:
        raise credentials_exception
    return UserRead(username=user.username)


def _make_cache_key(
    cat: str, shard: str, region_id: str,
    min_sales: int, max_sales: Optional[int],
    pages: int,
    regDate: Optional[str], maxRegDate: Optional[str],
) -> str:
    return "|".join(map(str, [
        cat, shard, region_id, min_sales, max_sales or "", pages,
        regDate or "", maxRegDate or ""
    ]))