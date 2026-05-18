import os
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, EmailStr
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Notification Service", port=8004)
Instrumentator().instrument(app).expose(app)

# Пароль берем из .env!
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", "hanagooru@gmail.com"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""), 
    MAIL_FROM=os.getenv("MAIL_USERNAME", "hanagooru@gmail.com"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
)

class EmailRequest(BaseModel):
    email: EmailStr
    subject: str
    body: str

@app.post("/send-email")
async def send_email(req: EmailRequest, background_tasks: BackgroundTasks):
    message = MessageSchema(
        subject=req.subject,
        recipients=[req.email],
        body=req.body,
        subtype="html"
    )
    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)
    return {"status": "Email queued for sending"}