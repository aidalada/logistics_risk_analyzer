from pydantic import BaseModel
from typing import Optional


class OrderCreate(BaseModel):
    cargo_description: str
    destination: str
    weight: float
    distance: float
    cargo_type: int
    delivery_date: str


class OrderOut(OrderCreate):
    id: int
    risk_level: str
    status: str

    class Config:
        from_attributes = True


class AnalyticsSummary(BaseModel):
    total_orders: int
    high_risk_count: int
    in_transit_count: int
    delivered_count: int