import csv
import os
import random
from io import StringIO
from typing import List, Optional, Union
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
import httpx
from sqlalchemy.orm import Session
from jose import JWTError, jwt

# Импорты проекта
from app.core.database import engine, Base, get_db
from app.models import user as user_model
from app.models import order as order_model
from app.models.user import UserRole
from app.schemas import user as user_schema
from app.schemas import order as order_schema
from app.core import security
from app.core.security import verify_password, create_access_token
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from prometheus_fastapi_instrumentator import Instrumentator
from app.services.ml_risk import predict_risks

tags_metadata = [
    {"name": "Authentication", "description": "Registration, login and access resending."},
    {"name": "Orders", "description": "Order managing and risk counting with ML."},
    {"name": "User Profile", "description": "Profile operations of current user."},
    {"name": "Admin Operations", "description": "Analytics and users management (only for admins)."},
]

app = FastAPI(
    title="Logistics Risk Management API",
    description="""
    API for managing logistics risks and automation of orders.

    ### Main features:
    * **Security**: JWT authorization and verification via email.
    * **Intellect**: Risk assessment of orders with Machine Learning.
    * **Control**: Full cycle of managing orders and analytic panel.
    """,
    version="1.0.0",
    contact={
        "name": "Yerulan Arman",
        "email": "aidala.damyn@gmail.com",
    },
    openapi_tags=tags_metadata
)

def _parse_csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# Comma-separated list of exact origins, e.g.
# CORS_ORIGINS="http://localhost:3000,https://your-app.vercel.app"
origins = _parse_csv_env(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3002",
)

# Optional regex for preview deployments (Vercel), e.g.
# CORS_ORIGIN_REGEX="https://.*\\.vercel\\.app"
cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://ml_service:8001")


@app.get("/health", tags=["Admin Operations"], summary="Health check")
def healthcheck():
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    """
    Create tables on startup with retry.
    In docker-compose, Postgres may not be ready when the app process starts.
    """
    last_error: Exception | None = None
    for attempt in range(1, 11):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            import time

            time.sleep(min(2 * attempt, 10))
    # If DB is still not reachable, fail fast with a clear error.
    raise RuntimeError("Database is not reachable on startup") from last_error

conf = ConnectionConfig(
    MAIL_USERNAME="hanagooru@gmail.com",
    MAIL_PASSWORD="xjlr oyzw pfks nwqv", 
    MAIL_FROM="hanagooru@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
)


def get_current_user(db: Session = Depends(get_db), token: str = Depends(security.oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(user_model.User).filter(user_model.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def require_operator(current_user: user_model.User = Depends(get_current_user)):
    if current_user.role not in {UserRole.OPERATOR.value, UserRole.ADMIN.value}:
        raise HTTPException(status_code=403, detail="Operator or admin role required")
    return current_user


def require_admin(current_user: user_model.User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user



@app.post("/register", response_model=user_schema.UserOut, tags=["Authentication"], summary="Регистрация нового пользователя")
async def register_user(user: user_schema.UserCreateLegacy, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if db.query(user_model.User).filter(user_model.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    generated_code = str(random.randint(100000, 999999))
    hashed_pwd = security.get_password_hash(user.password)
    new_user = user_model.User(
        email=user.email,
        hashed_password=hashed_pwd,
        full_name=user.full_name,
        role=UserRole.CLIENT.value,
        is_verified=False,
        verification_code=generated_code
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    message = MessageSchema(
        subject="Logistics App - Verification Code",
        recipients=[user.email],
        body=f"Your verification code is: {generated_code}",
        subtype="html"
    )
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)
    return new_user


@app.post("/auth/register", response_model=user_schema.Token, tags=["Authentication"], summary="quick registration with selected role")
def register_user_with_role(user: user_schema.UserCreate, db: Session = Depends(get_db)):
    if db.query(user_model.User).filter(user_model.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = security.get_password_hash(user.password)
    new_user = user_model.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.email.split("@")[0],
        role=user.role,
        is_verified=True,
        is_active=True,
        verification_code=None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.email, "role": new_user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/verify-email", tags=["Authentication"], summary="email verification")
def verify_email(email: str, code: str, db: Session = Depends(get_db)):
    user = db.query(user_model.User).filter(user_model.User.email == email).first()
    if not user or user.verification_code != code:
        raise HTTPException(status_code=400, detail="Wrong verification code")
    user.is_verified = True
    user.verification_code = None
    db.commit()
    return {"status": "success", "message": "Account activated!"}

@app.post("/resend-code", tags=["Authentication"], summary="verification code resent")
async def resend_code(email: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(user_model.User).filter(user_model.User.email == email).first()
    if not user or user.is_verified:
        raise HTTPException(status_code=400, detail="User not found or already verified")

    new_code = str(random.randint(100000, 999999))
    user.verification_code = new_code
    db.commit()

    message = MessageSchema(
        subject="Logistics App - NEW Code",
        recipients=[user.email],
        body=f"New code: {new_code}",
        subtype="html"
    )
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)
    return {"message": "New code sent"}

@app.post("/forgot-password", tags=["Authentication"], summary="password recovery request")
async def forgot_password(email: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(user_model.User).filter(user_model.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")

    reset_code = str(random.randint(100000, 999999))
    user.verification_code = reset_code
    db.commit()

    message = MessageSchema(
        subject="Password Reset",
        recipients=[user.email],
        body=f"Reset code: {reset_code}",
        subtype="html"
    )
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)
    return {"message": "Reset code sent"}

@app.post("/reset-password", tags=["Authentication"], summary="set new password")
def reset_password(email: str, code: str, new_password: str, db: Session = Depends(get_db)):
    user = db.query(user_model.User).filter(user_model.User.email == email).first()
    if not user or user.verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid code")
    user.hashed_password = security.get_password_hash(new_password)
    user.verification_code = None
    db.commit()
    return {"message": "Password updated"}

@app.post("/login", response_model=user_schema.Token, tags=["Authentication"], summary="login into the system (getting JWT)")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(user_model.User).filter(user_model.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not user.is_active or not user.is_verified:
        raise HTTPException(status_code=403, detail="Account not active or not verified")

    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}



@app.get("/users/me", response_model=user_schema.UserOut, tags=["User Profile"], summary="current user data")
def read_users_me(current_user: user_model.User = Depends(get_current_user)):
    return current_user



@app.post("/orders", response_model=order_schema.OrderOut, tags=["Orders"], summary="Создать новый заказ и сохранить 3 ML-риска")
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


@app.post("/ml/predict", tags=["Orders"], summary="Predict 3 ML risks (no save)")
def predict_only(order: order_schema.OrderCreate, current_user: user_model.User = Depends(require_operator)):
    risk = predict_risks(order.model_dump())
    return {
        "delay_probability": risk.delay_probability,
        "damage_probability": risk.damage_probability,
        "cancel_probability": risk.cancel_probability,
        "risk_level": risk.risk_level,
    }

@app.get("/orders", response_model=List[Union[order_schema.OrderOut, order_schema.OrderOutClient]], tags=["Orders"], summary="list of all orders")
def get_orders(search: Optional[str] = None, status: Optional[str] = None, db: Session = Depends(get_db), current_user: user_model.User = Depends(get_current_user)):
    query = db.query(order_model.Order)
    if current_user.role == UserRole.CLIENT.value:
        query = query.filter(order_model.Order.owner_id == current_user.id)
    # search/status filters can be reintroduced for new product later
    if status:
        query = query.filter(order_model.Order.status == status)
    orders = query.all()
    if current_user.role == UserRole.CLIENT.value:
        return [order_schema.OrderOutClient.model_validate(order) for order in orders]
    return orders


@app.patch(
    "/orders/{order_id}/status",
    response_model=order_schema.OrderOut,
    tags=["Orders"],
    summary="Update order status (freeze ML results)",
)
def update_order_status(
    order_id: int,
    payload: order_schema.OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: user_model.User = Depends(require_operator),
):
    order = db.query(order_model.Order).filter(order_model.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    # IMPORTANT: ML probabilities are frozen at creation time.
    # Status updates must not trigger any re-prediction.
    order.status = payload.status.value
    db.commit()
    db.refresh(order)
    return order



@app.get("/analytics/summary", response_model=order_schema.AnalyticsSummary, tags=["Admin Operations"], summary="Сводная статистика (Админ)")
def get_analytics_summary(db: Session = Depends(get_db), current_user: user_model.User = Depends(require_operator)):
    query = db.query(order_model.Order)
    return {
        "total_orders": query.count(),
        "high_risk_count": query.filter(order_model.Order.risk_level == "High").count(),
        "in_transit_count": query.filter(order_model.Order.status == "In Transit").count(),
        "delivered_count": query.filter(order_model.Order.status == "Delivered").count()
    }

@app.delete("/users/{user_id}", tags=["Admin Operations"], summary="Деактивация пользователя (Soft Delete)")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: user_model.User = Depends(require_admin)):
    user = db.query(user_model.User).filter(user_model.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    return {"message": "User deactivated"}