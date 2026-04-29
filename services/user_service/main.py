from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session

from app.core.database import Base, engine, get_db
from app.models.user import User
from services.common import CorrelationIdMiddleware, decode_token, get_token_from_header, register_error_handlers


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


app = FastAPI(title="user-service", version="1.0.0")
app.add_middleware(CorrelationIdMiddleware)
Instrumentator().instrument(app).expose(app)
register_error_handlers(app)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "user-service"}


def current_user(token: str = Depends(get_token_from_header), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@app.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return UserOut.model_validate(user)


@app.get("/", response_model=list[UserOut])
def list_users(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[UserOut]:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    users = db.query(User).all()
    return [UserOut.model_validate(item) for item in users]
