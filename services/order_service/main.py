import os
from datetime import datetime
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session

from app.core.database import Base, engine, get_db
from app.models.order import Order
from app.models.user import User
from services.common import CorrelationIdMiddleware, decode_token, get_token_from_header, register_error_handlers


PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8003")
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml_service:8001")


class OrderCreate(BaseModel):
    price: float = Field(..., ge=0)
    freight_value: float = Field(..., ge=0)
    weight_g: float = Field(..., gt=0)
    length_cm: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    width_cm: float = Field(..., gt=0)
    category: str = Field(..., min_length=2)
    payment_type: str
    installments: int = Field(..., ge=1, le=24)
    customer_lat: float = Field(..., ge=-90, le=90)
    customer_lng: float = Field(..., ge=-180, le=180)
    seller_lat: float = Field(..., ge=-90, le=90)
    seller_lng: float = Field(..., ge=-180, le=180)
    purchase_timestamp: datetime
    estimated_delivery_date: datetime
    order_approved_at: Optional[datetime] = None
    customer_state: str = Field(..., min_length=2, max_length=2)


class OrderStatusUpdate(BaseModel):
    status: str


app = FastAPI(title="order-service", version="1.0.0")
app.add_middleware(CorrelationIdMiddleware)
Instrumentator().instrument(app).expose(app)
register_error_handlers(app)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "order-service"}


def current_user(token: str = Depends(get_token_from_header), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def ensure_category_exists(category: str, request_id: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{PRODUCT_SERVICE_URL}/categories",
            headers={"X-Request-ID": request_id},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Product service unavailable")
    categories = set(response.json())
    if category not in categories:
        raise HTTPException(status_code=400, detail=f"Unknown product category: {category}")


async def fetch_ml_probabilities(payload: OrderCreate, request_id: str) -> dict:
    ml_payload = {
        "price": payload.price,
        "freight_value": payload.freight_value,
        "product_weight_g": payload.weight_g,
        "product_length_cm": payload.length_cm,
        "product_height_cm": payload.height_cm,
        "product_width_cm": payload.width_cm,
        "product_category_name": payload.category,
        "payment_type": payload.payment_type,
        "payment_installments": payload.installments,
        "customer_lat": payload.customer_lat,
        "customer_lng": payload.customer_lng,
        "seller_lat": payload.seller_lat,
        "seller_lng": payload.seller_lng,
        "purchase_timestamp": payload.purchase_timestamp.isoformat(),
        "estimated_delivery_date": payload.estimated_delivery_date.isoformat(),
        "order_purchase_timestamp": payload.purchase_timestamp.isoformat(),
        "order_approved_at": payload.order_approved_at.isoformat() if payload.order_approved_at else None,
        "customer_state": payload.customer_state.upper(),
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{ML_SERVICE_URL}/predict",
            headers={"X-Request-ID": request_id},
            json=ml_payload,
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="ML service unavailable")
    data = response.json()
    delay = float(data["delay_risk_percent"]) / 100
    damage = float(data["damage_risk_percent"]) / 100
    cancel = float(data["cancel_risk_percent"]) / 100
    max_prob = max(delay, damage, cancel)
    risk_level = "High" if max_prob > 0.5 else "Medium" if max_prob >= 0.25 else "Low"
    return {
        "delay_probability": delay,
        "damage_probability": damage,
        "cancel_probability": cancel,
        "risk_level": risk_level,
    }


@app.post("/ml/predict")
async def predict_only(payload: OrderCreate, request_id: str = Header(default="")):
    xid = request_id or "order-predict"
    await ensure_category_exists(payload.category, xid)
    return await fetch_ml_probabilities(payload, xid)


@app.post("/")
async def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    request_id: str = Header(default=""),
):
    xid = request_id or "order-create"
    await ensure_category_exists(payload.category, xid)
    risks = await fetch_ml_probabilities(payload, xid)
    order = Order(
        owner_id=user.id,
        status="New",
        **payload.model_dump(),
        **risks,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return {
        "id": order.id,
        "status": order.status,
        "risk_level": order.risk_level,
        "delay_probability": order.delay_probability,
        "damage_probability": order.damage_probability,
        "cancel_probability": order.cancel_probability,
    }


@app.get("/")
def list_orders(db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = db.query(Order)
    if user.role == "client":
        query = query.filter(Order.owner_id == user.id)
    return query.order_by(Order.id.desc()).all()


@app.get("/analytics/summary")
def analytics_summary(db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role not in {"operator", "admin"}:
        raise HTTPException(status_code=403, detail="Operator or admin role required")
    query = db.query(Order)
    return {
        "total_orders": query.count(),
        "high_risk_count": query.filter(Order.risk_level == "High").count(),
        "in_transit_count": query.filter(Order.status == "In Transit").count(),
        "delivered_count": query.filter(Order.status == "Delivered").count(),
    }


@app.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if user.role not in {"operator", "admin"}:
        raise HTTPException(status_code=403, detail="Operator or admin role required")
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = payload.status
    db.commit()
    db.refresh(order)
    return {"id": order.id, "status": order.status}
