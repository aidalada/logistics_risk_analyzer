from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.database import get_db
from app.models import order as order_model, user as user_model
from app.schemas import order as order_schema
from app.core.security import require_operator, require_admin

app = FastAPI(title="Analytics Service", port=8006)
Instrumentator().instrument(app).expose(app)

@app.get("/analytics/summary", response_model=order_schema.AnalyticsSummary)
def get_analytics_summary(db: Session = Depends(get_db), current_user: user_model.User = Depends(require_operator)):
    query = db.query(order_model.Order)
    return {
        "total_orders": query.count(),
        "high_risk_count": query.filter(order_model.Order.risk_level == "High").count(),
        "in_transit_count": query.filter(order_model.Order.status == "In Transit").count(),
        "delivered_count": query.filter(order_model.Order.status == "Delivered").count()
    }

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: user_model.User = Depends(require_admin)):
    user = db.query(user_model.User).filter(user_model.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    return {"message": "User deactivated"}