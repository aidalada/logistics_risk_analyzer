from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import engine, Base, get_db
from app.models import user as user_model
from app.schemas import user as user_schema
from app.core import security
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import verify_password, create_access_token
from jose import JWTError, jwt
from typing import List
from app.models import order as order_model
from app.schemas import order as order_schema
from app.services import ml_service

app = FastAPI(title="Logistics CRM API")

# Создаем таблицы при запуске (на всякий случай, хотя у нас есть Alembic)
Base.metadata.create_all(bind=engine)


@app.post("/register", response_model=user_schema.UserOut)
def register_user(user: user_schema.UserCreate, db: Session = Depends(get_db)):
    # 1. Проверяем, нет ли уже такого пользователя
    db_user = db.query(user_model.User).filter_by(email=user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Хэшируем пароль
    hashed_pwd = security.get_password_hash(user.password)

    # 3. Создаем запись в базе
    new_user = user_model.User(
        email=user.email,
        hashed_password=hashed_pwd,
        full_name=user.full_name,
        role="client"  # По умолчанию роль - клиент
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

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

@app.get("/")
def read_root():
    return {"status": "API is working"}

@app.get("/users/me", response_model=user_schema.UserOut)
def read_users_me(current_user: user_model.User = Depends(get_current_user)):
    return current_user


@app.post("/login", response_model=user_schema.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Ищем пользователя
    user = db.query(user_model.User).filter(user_model.User.email == form_data.username).first()

    # 2. Проверяем пароль
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверный email или пароль")

    # 3. Создаем токен
    access_token = create_access_token(data={"sub": user.email})

    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/orders", response_model=order_schema.OrderOut)
def create_order(
    order: order_schema.OrderCreate,
    db: Session = Depends(get_db),
    current_user: user_model.User = Depends(get_current_user)
):
    # 1. Предикт риска (подставляем данные из заказа + заглушки для опыта и погоды)
    risk_score, risk_level = ml_service.predict_risk(
        distance=order.distance,
        cargo_type=order.cargo_type,
        driver_exp=3, # В будущем можно брать из профиля выбранного водителя
        hour=12,
        weather=0
    )

    # 2. Сохранение
    new_order = order_model.Order(
        **order.model_dump(),
        risk_score=risk_score,
        risk_level=risk_level,
        owner_id=current_user.id,
        status="New"
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order

@app.get("/orders", response_model=List[order_schema.OrderOut])
def get_orders(db: Session = Depends(get_db), current_user: user_model.User = Depends(get_current_user)):
    # Возвращаем все заказы (для админа) или только свои (для клиента/водителя)
    if current_user.role == "admin":
        return db.query(order_model.Order).all()
    return db.query(order_model.Order).filter(order_model.Order.owner_id == current_user.id).all()

@app.get("/orders/{order_id}", response_model=order_schema.OrderOut)
def get_order_details(order_id: int, db: Session = Depends(get_db)):
    order = db.query(order_model.Order).filter(order_model.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/analytics/summary", response_model=order_schema.AnalyticsSummary)
def get_analytics_summary(
    db: Session = Depends(get_db),
    current_user: user_model.User = Depends(get_current_user)
):
    # Если ты админ — видишь всё. Если клиент — только свою статистику.
    query = db.query(order_model.Order)
    if current_user.role != "admin":
        query = query.filter(order_model.Order.owner_id == current_user.id)

    total = query.count()
    high_risk = query.filter(order_model.Order.risk_level == "High").count()
    in_transit = query.filter(order_model.Order.status == "In Transit").count()
    delivered = query.filter(order_model.Order.status == "Delivered").count()

    return {
        "total_orders": total,
        "high_risk_count": high_risk,
        "in_transit_count": in_transit,
        "delivered_count": delivered
    }


@app.patch("/orders/{order_id}/status", response_model=order_schema.OrderOut)
def update_order_status(
        order_id: int,
        new_status: str,
        db: Session = Depends(get_db),
        current_user: user_model.User = Depends(get_current_user)
):
    order = db.query(order_model.Order).filter(order_model.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Допустимые статусы: New, In Transit, Delivered, Cancelled
    order.status = new_status
    db.commit()
    db.refresh(order)
    return order


@app.patch("/orders/{order_id}/status", response_model=order_schema.OrderOut)
def update_order_status(
        order_id: int,
        new_status: str,
        db: Session = Depends(get_db),
        current_user: user_model.User = Depends(get_current_user)
):
    # Ищем заказ в базе
    order = db.query(order_model.Order).filter(order_model.Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Список разрешенных статусов из твоего ТЗ/Figma
    allowed_statuses = ["New", "In Transit", "Delivered", "Cancelled"]

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Choose from: {', '.join(allowed_statuses)}"
        )

    # Обновляем и сохраняем
    order.status = new_status
    db.commit()
    db.refresh(order)
    return order