import uuid

from fastapi import FastAPI, Header, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core import security


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = correlation_id
        return response


def get_token_from_header(authorization: str = Header(default="")) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.split(" ", 1)[1]


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(OperationalError)
    async def _handle_db_operational_error(request: Request, exc: OperationalError):
        return JSONResponse(
            status_code=503,
            content={"detail": "Database temporarily unavailable"},
        )

    @app.exception_handler(SQLAlchemyError)
    async def _handle_sqlalchemy_error(request: Request, exc: SQLAlchemyError):
        return JSONResponse(
            status_code=500,
            content={"detail": "Database query failed"},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
