import os
import random
import httpx
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.database import get_db, engine, Base
from app.models import user as user_model
from app.models.user import UserRole
from app.schemas import user as user_schema
from app.core import security

app = FastAPI(title="Auth Service", port=8002)
Instrumentator().instrument(app).expose(app)

NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification_service:8004")

async def send_notification(email: str, subject: str, body: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{NOTIFICATION_SERVICE_URL}/send-email",
                json={"email": email, "subject": subject, "body": body}
            )
        except httpx.RequestError as e:
            print(f"Failed to send notification: {e}")

@app.post("/register", response_model=user_schema.UserOut)
async def register_user(user: user_schema.UserCreateLegacy, db: Session = Depends(get_db)):
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

    await send_notification(user.email, "Logistics App - Verification Code", f"Your verification code is: {generated_code}")
    return new_user

@app.post("/auth/register", response_model=user_schema.Token)
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

    access_token = security.create_access_token(data={"sub": new_user.email, "role": new_user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/verify-email")
def verify_email(email: str, code: str, db: Session = Depends(get_db)):
    user = db.query(user_model.User).filter(user_model.User.email == email).first()
    if not user or user.verification_code != code:
        raise HTTPException(status_code=400, detail="Wrong verification code")
    user.is_verified = True
    user.verification_code = None
    db.commit()
    return {"status": "success", "message": "Account activated!"}

@app.post("/resend-code")
async def resend_code(email: str, db: Session = Depends(get_db)):
    user = db.query(user_model.User).filter(user_model.User.email == email).first()
    if not user or user.is_verified:
        raise HTTPException(status_code=400, detail="User not found or already verified")

    new_code = str(random.randint(100000, 999999))
    user.verification_code = new_code
    db.commit()

    await send_notification(user.email, "Logistics App - NEW Code", f"New code: {new_code}")
    return {"message": "New code sent"}

@app.post("/forgot-password")
async def forgot_password(email: str, db: Session = Depends(get_db)):
    user = db.query(user_model.User).filter(user_model.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")

    reset_code = str(random.randint(100000, 999999))
    user.verification_code = reset_code
    db.commit()

    await send_notification(user.email, "Password Reset", f"Reset code: {reset_code}")
    return {"message": "Reset code sent"}

@app.post("/reset-password")
def reset_password(email: str, code: str, new_password: str, db: Session = Depends(get_db)):
    user = db.query(user_model.User).filter(user_model.User.email == email).first()
    if not user or user.verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid code")
    user.hashed_password = security.get_password_hash(new_password)
    user.verification_code = None
    db.commit()
    return {"message": "Password updated"}

@app.post("/login", response_model=user_schema.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(user_model.User).filter(user_model.User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not user.is_active or not user.is_verified:
        raise HTTPException(status_code=403, detail="Account not active or not verified")

    access_token = security.create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}