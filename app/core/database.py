from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Читаем адрес базы из .env
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Engine — это механизм связи с БД.
# pool_pre_ping helps recover stale/broken DB connections (e.g., cloud SSL drops).
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)

# SessionLocal — это "фабрика" сессий (каждый запрос к БД — новая сессия)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base — от него будут наследоваться все наши таблицы
Base = declarative_base()

# Зависимость (Dependency) для FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()