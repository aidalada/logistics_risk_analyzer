from pydantic import BaseModel, EmailStr
from typing import Optional

# Что мы просим у пользователя при регистрации
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str  # Добавляем имя при регистрации

# Что мы отдаем пользователю (нельзя отдавать пароль!)
class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    role: str
    is_verified: bool
    delay_count: int
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
