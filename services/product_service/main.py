from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

from services.common import CorrelationIdMiddleware, register_error_handlers


class Product(BaseModel):
    id: int
    name: str
    category: str
    price: float


CATALOG: list[Product] = [
    Product(id=1, name="Office Chair", category="moveis_escritorio", price=120.0),
    Product(id=2, name="Headphones", category="audio", price=85.0),
    Product(id=3, name="Phone Accessory", category="telefonia_fixa", price=15.0),
]


app = FastAPI(title="product-service", version="1.0.0")
app.add_middleware(CorrelationIdMiddleware)
Instrumentator().instrument(app).expose(app)
register_error_handlers(app)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "product-service"}


@app.get("/", response_model=list[Product])
def list_products() -> list[Product]:
    return CATALOG


@app.get("/categories", response_model=list[str])
def categories() -> list[str]:
    return sorted({product.category for product in CATALOG})
