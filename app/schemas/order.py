from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# Базовая схема с общими полями и валидацией
class OrderBase(BaseModel):
    cargo_description: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Детальное описание груза (минимум 5 символов)"
    )
    destination: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Адрес назначения"
    )
    weight: float = Field(
        ...,
        gt=0,
        lt=50000,
        description="Вес груза в кг (должен быть больше 0 и меньше 50 тонн)"
    )
    distance: float = Field(
        ...,
        gt=0,
        lt=10000,
        description="Расстояние в км (от 0.1 до 10 000)"
    )
    # Используем str для типа груза, так как в UI пользователю легче выбрать название
    cargo_type: str = Field(
        ...,
        min_length=2,
        description="Категория груза (например: Хрупкое, Опасное)"
    )
    delivery_date: datetime = Field(
        ...,
        description="Дата и время доставки в формате ISO (например: 2026-01-20T12:00:00)"
    )

# Схема для создания заказа (то, что присылает фронтенд)
class OrderCreate(OrderBase):
    pass

# Схема для ответа (то, что возвращает бэкенд)
class OrderOut(OrderBase):
    id: int
    owner_id: int
    risk_score: float
    risk_level: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True # Позволяет Pydantic работать с моделями SQLAlchemy

# Схема для сводной аналитики
class AnalyticsSummary(BaseModel):
    total_orders: int
    high_risk_count: int
    in_transit_count: int
    delivered_count: int