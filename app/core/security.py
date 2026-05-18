import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import user as user_model
from app.models.user import UserRole

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-render")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

_expire_raw = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(_expire_raw)
except ValueError:
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    if "role" not in to_encode:
        to_encode["role"] = "client"
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(user_model.User).filter(user_model.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def require_operator(current_user: user_model.User = Depends(get_current_user)):
    if current_user.role not in {UserRole.OPERATOR.value, UserRole.ADMIN.value}:
        raise HTTPException(status_code=403, detail="Operator or admin role required")
    return current_user

def require_admin(current_user: user_model.User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user