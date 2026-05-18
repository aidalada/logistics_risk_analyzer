from typing import List, Union, Optional
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.database import get_db
from app.models import order as order_model, user as user_model
from app.models.user import UserRole
from app.schemas import order as order_schema
from app.core.security import get_current_user, require_operator
from app.services.ml_risk import predict_risks

app = FastAPI(title="Order Service", port=8005)
Instrumentator().instrument(app).expose(app)

@app.post("/orders", response_model=order_schema.OrderOut)
def create_order(order: order_schema.OrderCreate, db: Session = Depends(get_db), current_user: user_model.User = Depends(require_operator)):
    risk = predict_risks(order.model_dump())
    new_order = order_model.Order(
        **order.model_dump(),
        owner_id=current_user.id,
        status="New",
        delay_probability=risk.delay_probability,
        damage_probability=risk.damage_probability,
        cancel_probability=risk.cancel_probability,
        risk_level=risk.risk_level,
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order

@app.post("/ml/predict")
def predict_only(order: order_schema.OrderCreate, current_user: user_model.User = Depends(require_operator)):
    risk = predict_risks(order.model_dump())
    return {
        "delay_probability": risk.delay_probability,
        "damage_probability": risk.damage_probability,
        "cancel_probability": risk.cancel_probability,
        "risk_level": risk.risk_level,
    }

@app.get("/orders", response_model=List[Union[order_schema.OrderOut, order_schema.OrderOutClient]])
def get_orders(search: Optional[str] = None, status: Optional[str] = None, db: Session = Depends(get_db), current_user: user_model.User = Depends(get_current_user)):
    query = db.query(order_model.Order)
    if current_user.role == UserRole.CLIENT.value:
        query = query.filter(order_model.Order.owner_id == current_user.id)
    if status:
        query = query.filter(order_model.Order.status == status)
    
    orders = query.all()
    if current_user.role == UserRole.CLIENT.value:
        return [order_schema.OrderOutClient.model_validate(order) for order in orders]
    return orders

@app.patch("/orders/{order_id}/status", response_model=order_schema.OrderOut)
def update_order_status(
    order_id: int,
    payload: order_schema.OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: user_model.User = Depends(require_operator),
):
    order = db.query(order_model.Order).filter(order_model.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = payload.status.value
    db.commit()
    db.refresh(order)
    return order