from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, default="New", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Input data
    price = Column(Float, nullable=False)
    freight_value = Column(Float, nullable=False)
    weight_g = Column(Float, nullable=False)
    length_cm = Column(Float, nullable=False)
    height_cm = Column(Float, nullable=False)
    width_cm = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    payment_type = Column(String, nullable=False)
    installments = Column(Integer, nullable=False)
    customer_lat = Column(Float, nullable=False)
    customer_lng = Column(Float, nullable=False)
    seller_lat = Column(Float, nullable=False)
    seller_lng = Column(Float, nullable=False)
    purchase_timestamp = Column(DateTime(timezone=True), nullable=False)
    estimated_delivery_date = Column(DateTime(timezone=True), nullable=False)
    order_approved_at = Column(DateTime(timezone=True), nullable=True)
    customer_state = Column(String, nullable=False)

    # ML results
    delay_probability = Column(Float, nullable=False)
    damage_probability = Column(Float, nullable=False)
    cancel_probability = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)