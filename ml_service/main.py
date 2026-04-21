import math
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Literal

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_fastapi_instrumentator import Instrumentator


BASE_DIR = os.path.dirname(__file__)
DELAY_MODEL_PATH = os.path.join(BASE_DIR, "logistics_delay_model.pkl")
DELAY_MODEL_COLUMNS_PATH = os.path.join(BASE_DIR, "model_columns.pkl")
DAMAGE_MODEL_PATH = os.path.join(BASE_DIR, "logistics_damage_model.pkl")
DAMAGE_MODEL_COLUMNS_PATH = os.path.join(BASE_DIR, "damage_model_columns.pkl")
CANCEL_MODEL_PATH = os.path.join(BASE_DIR, "logistics_cancel_model.pkl")
CANCEL_MODEL_COLUMNS_PATH = os.path.join(BASE_DIR, "cancel_model_columns.pkl")

DEFAULT_CATEGORY_RISK = 0.146
CATEGORY_RISK_MAP = {
    "moveis_escritorio": 0.252,
    "fashion_roupa_masculina": 0.248,
    "telefonia_fixa": 0.227,
    "audio": 0.213,
    "casa_conforto": 0.193,
}


class PredictRequest(BaseModel):
    price: float = Field(..., ge=0)
    freight_value: float = Field(..., ge=0)
    product_weight_g: float = Field(..., ge=0)
    customer_lat: float = Field(..., ge=-90, le=90)
    customer_lng: float = Field(..., ge=-180, le=180)
    seller_lat: float = Field(..., ge=-90, le=90)
    seller_lng: float = Field(..., ge=-180, le=180)
    purchase_timestamp: datetime
    estimated_delivery_date: datetime
    customer_state: str = Field(..., min_length=2, max_length=2)
    product_length_cm: float = Field(..., gt=0)
    product_height_cm: float = Field(..., gt=0)
    product_width_cm: float = Field(..., gt=0)
    product_category_name: str = Field(..., min_length=1)
    payment_type: Literal["credit_card", "boleto", "voucher", "debit_card"]
    payment_installments: int = Field(default=1, ge=1, le=24)
    order_purchase_timestamp: datetime
    order_approved_at: datetime | None = None


class PredictResponse(BaseModel):
    delay_risk_percent: float
    damage_risk_percent: float
    cancel_risk_percent: float


def haversine_distance_km(
    customer_lat: float,
    customer_lng: float,
    seller_lat: float,
    seller_lng: float,
) -> float:
    earth_radius_km = 6371.0
    lat1_rad = math.radians(customer_lat)
    lng1_rad = math.radians(customer_lng)
    lat2_rad = math.radians(seller_lat)
    lng2_rad = math.radians(seller_lng)

    delta_lat = lat2_rad - lat1_rad
    delta_lng = lng2_rad - lng1_rad
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c


def build_feature_row(payload: PredictRequest, model_columns: list[str]) -> pd.DataFrame:
    distance_km = haversine_distance_km(
        customer_lat=payload.customer_lat,
        customer_lng=payload.customer_lng,
        seller_lat=payload.seller_lat,
        seller_lng=payload.seller_lng,
    )
    transport_effort = distance_km * (payload.product_weight_g / 1000.0)
    purchase_dayofweek = payload.purchase_timestamp.weekday()
    expected_wait_days = (
        payload.estimated_delivery_date.date() - payload.purchase_timestamp.date()
    ).days

    row = {column: 0 for column in model_columns}
    raw_features = {
        "price": payload.price,
        "freight_value": payload.freight_value,
        "product_weight_g": payload.product_weight_g,
        "distance_km": distance_km,
        "transport_effort": transport_effort,
        "purchase_dayofweek": purchase_dayofweek,
        "expected_wait_days": expected_wait_days,
    }
    for feature_name, value in raw_features.items():
        if feature_name in row:
            row[feature_name] = value

    state_column = f"customer_state_{payload.customer_state.upper()}"
    if state_column in row:
        row[state_column] = 1

    return pd.DataFrame([[row[column] for column in model_columns]], columns=model_columns)


def build_damage_feature_row(
    payload: PredictRequest, damage_model_columns: list[str]
) -> pd.DataFrame:
    distance_km = haversine_distance_km(
        customer_lat=payload.customer_lat,
        customer_lng=payload.customer_lng,
        seller_lat=payload.seller_lat,
        seller_lng=payload.seller_lng,
    )
    product_volume_cm3 = (
        payload.product_length_cm * payload.product_height_cm * payload.product_width_cm
    )
    product_density = payload.product_weight_g / (product_volume_cm3 + 1.0)
    transport_effort = distance_km * (payload.product_weight_g / 1000.0)
    category_risk_score = CATEGORY_RISK_MAP.get(
        payload.product_category_name.strip().lower(), DEFAULT_CATEGORY_RISK
    )

    row = {column: 0 for column in damage_model_columns}
    raw_features = {
        "distance_km": distance_km,
        "freight_value": payload.freight_value,
        "product_weight_g": payload.product_weight_g,
        "product_volume_cm3": product_volume_cm3,
        "product_density": product_density,
        "category_risk_score": category_risk_score,
        "transport_effort": transport_effort,
    }
    for feature_name, value in raw_features.items():
        if feature_name in row:
            row[feature_name] = value

    return pd.DataFrame(
        [[row[column] for column in damage_model_columns]],
        columns=damage_model_columns,
    )


def build_cancel_feature_row(
    payload: PredictRequest, cancel_model_columns: list[str]
) -> pd.DataFrame:
    row = {column: 0 for column in cancel_model_columns}

    if payload.order_approved_at is None:
        approval_delay_hours = -1.0
    else:
        approval_delta = payload.order_approved_at - payload.order_purchase_timestamp
        approval_delay_hours = approval_delta.total_seconds() / 3600.0

    raw_features = {
        "price": payload.price,
        "payment_installments": payload.payment_installments,
        "approval_delay_hours": approval_delay_hours,
    }
    for feature_name, value in raw_features.items():
        if feature_name in row:
            row[feature_name] = value

    payment_column = f"pay_{payload.payment_type.strip().lower()}"
    if payment_column in row:
        row[payment_column] = 1

    return pd.DataFrame(
        [[row[column] for column in cancel_model_columns]],
        columns=cancel_model_columns,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    required_files = [
        DELAY_MODEL_PATH,
        DELAY_MODEL_COLUMNS_PATH,
        DAMAGE_MODEL_PATH,
        DAMAGE_MODEL_COLUMNS_PATH,
        CANCEL_MODEL_PATH,
        CANCEL_MODEL_COLUMNS_PATH,
    ]
    for file_path in required_files:
        if not os.path.exists(file_path):
            raise RuntimeError(f"Required artifact file not found at {file_path}")

    app.state.delay_model = joblib.load(DELAY_MODEL_PATH)
    app.state.delay_model_columns = list(joblib.load(DELAY_MODEL_COLUMNS_PATH))
    app.state.damage_model = joblib.load(DAMAGE_MODEL_PATH)
    app.state.damage_model_columns = list(joblib.load(DAMAGE_MODEL_COLUMNS_PATH))
    app.state.cancel_model = joblib.load(CANCEL_MODEL_PATH)
    app.state.cancel_model_columns = list(joblib.load(CANCEL_MODEL_COLUMNS_PATH))
    yield


app = FastAPI(title="Logistics ML Service", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Instrumentator().instrument(app).expose(app)


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    delay_model: Any = getattr(app.state, "delay_model", None)
    delay_model_columns: Any = getattr(app.state, "delay_model_columns", None)
    damage_model: Any = getattr(app.state, "damage_model", None)
    damage_model_columns: Any = getattr(app.state, "damage_model_columns", None)
    cancel_model: Any = getattr(app.state, "cancel_model", None)
    cancel_model_columns: Any = getattr(app.state, "cancel_model_columns", None)
    if (
        delay_model is None
        or delay_model_columns is None
        or damage_model is None
        or damage_model_columns is None
        or cancel_model is None
        or cancel_model_columns is None
    ):
        raise HTTPException(status_code=503, detail="Model artifacts are not loaded")

    if payload.estimated_delivery_date < payload.purchase_timestamp:
        raise HTTPException(
            status_code=422,
            detail="estimated_delivery_date must be after purchase_timestamp",
        )
    if payload.order_approved_at and payload.order_approved_at < payload.order_purchase_timestamp:
        raise HTTPException(
            status_code=422,
            detail="order_approved_at must be after order_purchase_timestamp",
        )

    delay_features = build_feature_row(payload=payload, model_columns=delay_model_columns)
    damage_features = build_damage_feature_row(
        payload=payload,
        damage_model_columns=damage_model_columns,
    )
    cancel_features = build_cancel_feature_row(
        payload=payload,
        cancel_model_columns=cancel_model_columns,
    )

    delay_probability = float(delay_model.predict_proba(delay_features)[0][1])
    damage_probability = float(damage_model.predict_proba(damage_features)[0][1])
    cancel_probability = float(cancel_model.predict_proba(cancel_features)[0][1])

    return PredictResponse(
        delay_risk_percent=round(delay_probability * 100, 2),
        damage_risk_percent=round(damage_probability * 100, 2),
        cancel_risk_percent=round(cancel_probability * 100, 2),
    )
