from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt

from config import settings
from models.user import User as UserModel
from schemas.auth import UserCreate, UserRead

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_username(db: Session, username: str) -> Optional[UserModel]:
    return db.query(UserModel).filter(UserModel.username == username).first()

def register_user(db: Session, user: UserCreate) -> UserRead:
    if get_user_by_username(db, user.username):
        raise ValueError("Username already exists")
    hashed = pwd_context.hash(user.password)
    db_user = UserModel(username=user.username, hashed_password=hashed)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return UserRead(username=db_user.username)

def authenticate_user(db: Session, username: str, password: str) -> Optional[UserRead]:
    db_user = get_user_by_username(db, username)
    if not db_user or not pwd_context.verify(password, db_user.hashed_password):
        return None
    return UserRead(username=db_user.username)

def create_access_token(sub: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": sub, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
