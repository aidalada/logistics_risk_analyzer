from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field
from prometheus_fastapi_instrumentator import Instrumentator

from services.common import CorrelationIdMiddleware, decode_token, get_token_from_header, register_error_handlers


class ChatMessageIn(BaseModel):
    to_user: str
    text: str = Field(..., min_length=1, max_length=1000)


class ChatMessage(BaseModel):
    id: int
    from_user: str
    to_user: str
    text: str
    sent_at: datetime


MESSAGES: list[ChatMessage] = []


app = FastAPI(title="chat-service", version="1.0.0")
app.add_middleware(CorrelationIdMiddleware)
Instrumentator().instrument(app).expose(app)
register_error_handlers(app)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "chat-service"}


def current_email(token: str = Depends(get_token_from_header)) -> str:
    payload = decode_token(token)
    return str(payload.get("sub", "unknown"))


@app.post("/messages", response_model=ChatMessage)
def send_message(payload: ChatMessageIn, sender: str = Depends(current_email)) -> ChatMessage:
    item = ChatMessage(
        id=len(MESSAGES) + 1,
        from_user=sender,
        to_user=payload.to_user,
        text=payload.text,
        sent_at=datetime.now(timezone.utc),
    )
    MESSAGES.append(item)
    return item


@app.get("/messages", response_model=list[ChatMessage])
def get_messages(user: str = Depends(current_email), since_id: int = 0) -> list[ChatMessage]:
    return [
        message
        for message in MESSAGES
        if message.id > since_id and (message.from_user == user or message.to_user == user)
    ]
