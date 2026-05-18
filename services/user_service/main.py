from fastapi import FastAPI, Depends
from prometheus_fastapi_instrumentator import Instrumentator

from app.schemas import user as user_schema
from app.models import user as user_model
from app.core.database import get_db
# Предполагается, что get_current_user вынесен в общий app/core/security.py или dependencies.py
from app.core.security import get_current_user 

app = FastAPI(title="User Profile Service", port=8003)
Instrumentator().instrument(app).expose(app)

@app.get("/users/me", response_model=user_schema.UserOut)
def read_users_me(current_user: user_model.User = Depends(get_current_user)):
    return current_user