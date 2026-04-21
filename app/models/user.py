from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base


class UserRole(str, Enum):
    CLIENT = "client"
    OPERATOR = "operator"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default=UserRole.CLIENT.value)

    full_name = Column(String)  # Для имен типа "John Smith"
    is_verified = Column(Boolean, default=False)  # Для экрана "Manage Drivers"
    delay_count = Column(Integer, default=0)  # Для статистики задержек

    is_active = Column(Boolean, default=True)
    verification_code = Column(String, nullable=True)