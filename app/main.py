from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import engine, Base, get_db
from app.models import user as user_model
from app.schemas import user as user_schema
from app.core import security
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import verify_password, create_access_token
from jose import JWTError, jwt

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