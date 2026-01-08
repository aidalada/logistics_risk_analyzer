from pydantic import BaseModel, EmailStr
from typing import Optional

# Что мы просим у пользователя при регистрации
class UserCreate(BaseModel):
    email: EmailStr
    password: str

# Что мы отдаем пользователю (нельзя отдавать пароль!)
class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool

    class Config:
        from_attributes = True # Позволяет Pydantic работать с моделями SQLAlchemy