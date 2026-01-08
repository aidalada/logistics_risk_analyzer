from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import engine, Base, get_db
from app.models import user as user_model
from app.schemas import user as user_schema
from app.core import security

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
        role="client"  # По умолчанию роль - клиент
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.get("/")
def read_root():
    return {"status": "API is working"}