from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="client") # admin, manager, driver, client

    full_name = Column(String)  # Для имен типа "John Smith"
    is_verified = Column(Boolean, default=False)  # Для экрана "Manage Drivers"
    delay_count = Column(Integer, default=0)  # Для статистики задержек

    is_active = Column(Boolean, default=True)