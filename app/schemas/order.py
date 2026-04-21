from enum import Enum
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


class OrderStatus(str, Enum):
    NEW = "New"
    PROCESSING = "Processing"
    IN_TRANSIT = "In Transit"
    DELIVERED = "Delivered"
    CANCELED = "Canceled"

class OrderBase(BaseModel):
    price: float = Field(..., ge=0)
    freight_value: float = Field(..., ge=0)
    weight_g: float = Field(..., gt=0)
    length_cm: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    width_cm: float = Field(..., gt=0)
    category: str = Field(..., min_length=2, max_length=200)
    payment_type: Literal["credit_card", "boleto", "voucher", "debit_card", "not_defined", "unknown"] = "unknown"
    installments: int = Field(..., ge=1, le=24)
    customer_lat: float = Field(..., ge=-90, le=90)
    customer_lng: float = Field(..., ge=-180, le=180)
    seller_lat: float = Field(..., ge=-90, le=90)
    seller_lng: float = Field(..., ge=-180, le=180)
    purchase_timestamp: datetime
    estimated_delivery_date: datetime
    order_approved_at: Optional[datetime] = None
    customer_state: str = Field(..., min_length=2, max_length=2)

class OrderCreate(OrderBase):
    pass

class OrderOut(OrderBase):
    id: int
    owner_id: int
    delay_probability: float
    damage_probability: float
    cancel_probability: float
    risk_level: str
    status: OrderStatus
    created_at: datetime

    class Config:
        from_attributes = True


class OrderOutClient(BaseModel):
    id: int
    owner_id: int
    status: OrderStatus
    created_at: datetime

    class Config:
        from_attributes = True


class AnalyticsSummary(BaseModel):
    total_orders: int
    high_risk_count: int
    in_transit_count: int
    delivered_count: int


class OrderStatusUpdate(BaseModel):
    status: OrderStatus