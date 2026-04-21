from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Пароль минимум 8 символов")
    role: Literal["client", "operator", "admin"] = "client"


class UserCreateLegacy(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Пароль минимум 8 символов")
    full_name: str = Field(..., min_length=2)
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
    role: Optional[str] = None
