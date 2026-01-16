import csv
import random
from io import StringIO
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt

# Импорты проекта
from app.core.database import engine, Base, get_db
from app.models import user as user_model
from app.models import order as order_model
from app.schemas import user as user_schema
from app.schemas import order as order_schema
from app.core import security
from app.core.security import verify_password, create_access_token
from app.services import ml_service
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

app = FastAPI(title="Logistics CRM API")

# Автоматическое создание таблиц
Base.metadata.create_all(bind=engine)

# Настройка CORS
origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация почты
conf = ConnectionConfig(
    MAIL_USERNAME="hanagooru@gmail.com",
    MAIL_PASSWORD="xjlr oyzw pfks nwqv",  # Твой App Password
    MAIL_FROM="hanagooru@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
)


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

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


# --- ЭНДПОИНТЫ ПОЛЬЗОВАТЕЛЕЙ ---

@app.post("/register", response_model=user_schema.UserOut)
async def register_user(
        user: user_schema.UserCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    # 1. Проверка на дубликаты
    if db.query(user_model.User).filter(user_model.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Генерируем ОДИН код для базы и письма
    generated_code = str(random.randint(100000, 999999))

    # 3. Создаем пользователя
    hashed_pwd = security.get_password_hash(user.password)
    new_user = user_model.User(
        email=user.email,
        hashed_password=hashed_pwd,
        full_name=user.full_name,
        role="client",
        is_verified=False,
        verification_code=generated_code  # Код сохраняется здесь
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 4. Отправляем письмо с ЭТИМ ЖЕ кодом
    message = MessageSchema(
        subject="Logistics App - Verification Code",
        recipients=[user.email],
        body=f"Your verification code is: {generated_code}",  # Тот же код в письме
        subtype="html"
    )
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)

    return new_user


@app.post("/verify-email")
def verify_email(email: str, code: str, db: Session = Depends(get_db)):
    # 1. Ищем пользователя
    user = db.query(user_model.User).filter(user_model.User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Проверяем код (сравнение того, что пришло, с тем, что в базе)
    if user.verification_code == code:
        user.is_verified = True
        user.verification_code = None  # Очищаем код после успеха
        db.commit()
        return {"status": "success", "message": "Account activated!"}
    else:
        raise HTTPException(status_code=400, detail="Wrong verification code")


@app.post("/login", response_model=user_schema.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(user_model.User).filter(user_model.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверный email или пароль")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Ваш аккаунт деактивирован. Обратитесь к админу.")
    # Проверка верификации при логине (важно для ТЗ)
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Пожалуйста, подтвердите email")

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=user_schema.UserOut)
def read_users_me(current_user: user_model.User = Depends(get_current_user)):
    return current_user


# --- АДМИН-ФУНКЦИИ ---

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: user_model.User = Depends(get_current_user)):
    # Только админ может деактивировать
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user = db.query(user_model.User).filter(user_model.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Вместо db.delete(user) делаем:
    user.is_active = False
    db.commit()

    return {"message": f"User {user_id} has been deactivated"}


@app.patch("/users/drivers/{user_id}/verify")
def verify_driver(user_id: int, verify: bool, db: Session = Depends(get_db),
                  current_user: user_model.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")

    driver = db.query(user_model.User).filter(user_model.User.id == user_id, user_model.User.role == "driver").first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    driver.is_verified = verify
    db.commit()
    return {"message": f"Driver verification set to {verify}"}


# --- ЗАКАЗЫ И АНАЛИТИКА ---

@app.post("/orders", response_model=order_schema.OrderOut)
def create_order(order: order_schema.OrderCreate, db: Session = Depends(get_db),
                 current_user: user_model.User = Depends(get_current_user)):
    risk_score, risk_level = ml_service.predict_risk(  #
        distance=order.distance, cargo_type=order.cargo_type, driver_exp=3, hour=12, weather=0
    )
    new_order = order_model.Order(
        **order.model_dump(), risk_score=risk_score, risk_level=risk_level, owner_id=current_user.id, status="New"
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order


@app.get("/orders", response_model=List[order_schema.OrderOut])
def get_orders(search: Optional[str] = None, status: Optional[str] = None, db: Session = Depends(get_db),
               current_user: user_model.User = Depends(get_current_user)):
    query = db.query(order_model.Order)
    if current_user.role != "admin":
        query = query.filter(order_model.Order.owner_id == current_user.id)
    if search:
        query = query.filter((order_model.Order.cargo_description.ilike(f"%{search}%")) | (
            order_model.Order.destination.ilike(f"%{search}%")))
    if status:
        query = query.filter(order_model.Order.status == status)
    return query.all()


@app.get("/analytics/summary", response_model=order_schema.AnalyticsSummary)
def get_analytics_summary(db: Session = Depends(get_db), current_user: user_model.User = Depends(get_current_user)):
    query = db.query(order_model.Order)
    if current_user.role != "admin":
        query = query.filter(order_model.Order.owner_id == current_user.id)
    return {
        "total_orders": query.count(),
        "high_risk_count": query.filter(order_model.Order.risk_level == "High").count(),
        "in_transit_count": query.filter(order_model.Order.status == "In Transit").count(),
        "delivered_count": query.filter(order_model.Order.status == "Delivered").count()
    }