from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    cargo_description = Column(String, nullable=False)  # Из Figma: "Medical Supplies"
    destination = Column(String, nullable=False)  # "Chicago, IL"
    weight = Column(Float)  # 500 kg
    distance = Column(Float)  # 800 km
    cargo_type = Column(Integer)  # 0, 1, 2 (как в ML модели)
    delivery_date = Column(String)  # Дата доставки

    # Результаты работы твоей ML модели:
    risk_score = Column(Integer)  # 0, 1 или 2
    risk_level = Column(String)  # "Low", "Medium", "High" (для фронта)

    status = Column(String, default="New")  # New, In Transit, Delivered

    owner_id = Column(Integer, ForeignKey("users.id"))
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())