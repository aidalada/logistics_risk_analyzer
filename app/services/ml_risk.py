from __future__ import annotations

import math
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RiskResult:
    delay_probability: float
    damage_probability: float
    cancel_probability: float
    risk_level: str


def _load_pickle(path: Path) -> Any:
    with path.open("rb") as f:
        return pickle.load(f)


_DELAY_MODEL = _load_pickle(REPO_ROOT / "logistics_delay_model.pkl")
_DAMAGE_MODEL = _load_pickle(REPO_ROOT / "logistics_damage_model.pkl")
_CANCEL_MODEL = _load_pickle(REPO_ROOT / "logistics_cancel_model.pkl")

_DELAY_COLS: List[str] = list(_load_pickle(REPO_ROOT / "model_columns.pkl"))
_DAMAGE_COLS: List[str] = list(_load_pickle(REPO_ROOT / "damage_model_columns.pkl"))
_CANCEL_COLS: List[str] = list(_load_pickle(REPO_ROOT / "cancel_model_columns.pkl"))


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _category_risk_score(category: str) -> float:
    # Minimal mapping; tune later with real business knowledge.
    high = {"hazardous", "medicine", "electronics", "fragile"}
    low = {"other"}
    c = (category or "").strip().lower()
    if c in low:
        return 0.2
    if c in high:
        return 0.8
    return 0.5


def _payment_one_hot(payment_type: str) -> Dict[str, float]:
    normalized = (payment_type or "unknown").strip().lower()
    mapping = {
        "boleto": "pay_boleto",
        "credit_card": "pay_credit_card",
        "debit_card": "pay_debit_card",
        "voucher": "pay_voucher",
        "not_defined": "pay_not_defined",
        "unknown": "pay_unknown",
    }
    out = {k: 0.0 for k in mapping.values()}
    out[mapping.get(normalized, "pay_unknown")] = 1.0
    return out


def _risk_level(*probs: float) -> str:
    m = max(probs)
    if m > 0.50:
        return "High"
    if m >= 0.25:
        return "Medium"
    return "Low"


def build_features(payload: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns (delay_df, damage_df, cancel_df) with exactly the columns required by each model.
    """
    purchase_ts = _to_utc(payload["purchase_timestamp"])
    est_delivery = _to_utc(payload["estimated_delivery_date"])
    approved_at: Optional[datetime] = payload.get("order_approved_at")
    approved_at = _to_utc(approved_at) if approved_at else None

    distance_km = _haversine_km(
        payload["customer_lat"], payload["customer_lng"], payload["seller_lat"], payload["seller_lng"]
    )
    product_volume_cm3 = float(payload["length_cm"]) * float(payload["height_cm"]) * float(payload["width_cm"])
    product_density = float(payload["weight_g"]) / product_volume_cm3 if product_volume_cm3 > 0 else 0.0
    expected_wait_days = (est_delivery - purchase_ts).total_seconds() / 86400.0
    purchase_dayofweek = float(purchase_ts.weekday())
    transport_effort = distance_km * (float(payload["weight_g"]) / 1000.0)
    approval_delay_hours = 0.0 if not approved_at else (approved_at - purchase_ts).total_seconds() / 3600.0

    base_numeric = {
        "price": float(payload["price"]),
        "freight_value": float(payload["freight_value"]),
        "product_weight_g": float(payload["weight_g"]),
        "distance_km": float(distance_km),
        "transport_effort": float(transport_effort),
        "product_volume_cm3": float(product_volume_cm3),
        "product_density": float(product_density),
        "category_risk_score": float(_category_risk_score(payload["category"])),
        "expected_wait_days": float(expected_wait_days),
        "purchase_dayofweek": float(purchase_dayofweek),
        "payment_installments": float(payload["installments"]),
        "approval_delay_hours": float(max(0.0, approval_delay_hours)),
    }

    # Delay model expects customer_state one-hots
    delay_row = {c: 0.0 for c in _DELAY_COLS}
    for k, v in base_numeric.items():
        if k in delay_row:
            delay_row[k] = v
    state = (payload.get("customer_state") or "").strip().upper()
    state_col = f"customer_state_{state}"
    if state_col in delay_row:
        delay_row[state_col] = 1.0
    delay_df = pd.DataFrame([delay_row], columns=_DELAY_COLS)

    damage_row = {c: 0.0 for c in _DAMAGE_COLS}
    for k, v in base_numeric.items():
        if k in damage_row:
            damage_row[k] = v
    damage_df = pd.DataFrame([damage_row], columns=_DAMAGE_COLS)

    cancel_row = {c: 0.0 for c in _CANCEL_COLS}
    for k, v in base_numeric.items():
        if k in cancel_row:
            cancel_row[k] = v
    cancel_row.update(_payment_one_hot(payload.get("payment_type")))
    cancel_df = pd.DataFrame([cancel_row], columns=_CANCEL_COLS)

    return delay_df, damage_df, cancel_df


def predict_risks(payload: Dict[str, Any]) -> RiskResult:
    delay_df, damage_df, cancel_df = build_features(payload)

    delay_prob = float(_DELAY_MODEL.predict_proba(delay_df)[0][1])
    damage_prob = float(_DAMAGE_MODEL.predict_proba(damage_df)[0][1])
    cancel_prob = float(_CANCEL_MODEL.predict_proba(cancel_df)[0][1])

    return RiskResult(
        delay_probability=delay_prob,
        damage_probability=damage_prob,
        cancel_probability=cancel_prob,
        risk_level=_risk_level(delay_prob, damage_prob, cancel_prob),
    )

