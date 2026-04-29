from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.database import Base, engine, get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User, UserRole
from services.common import CorrelationIdMiddleware, register_error_handlers


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = UserRole.CLIENT.value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


app = FastAPI(title="auth-service", version="1.0.0")
app.add_middleware(CorrelationIdMiddleware)
Instrumentator().instrument(app).expose(app)
register_error_handlers(app)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "auth-service"}


@app.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        full_name=payload.email.split("@")[0],
        is_verified=True,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.email, "role": user.role})
    return TokenResponse(access_token=token)


@app.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")
    token = create_access_token({"sub": user.email, "role": user.role})
    return TokenResponse(access_token=token)
