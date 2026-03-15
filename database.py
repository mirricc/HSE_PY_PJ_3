from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator
import redis

from config import get_settings
import models

settings = get_settings()

# Создание движка для SQLite
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, echo=False)

# Создание сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency для получения сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Инициализация базы данных (создание таблиц)"""
    models.Base.metadata.create_all(bind=engine)


# Redis подключение
def get_redis(redis_url: str = None) -> redis.Redis:
    """Получение Redis клиента"""
    if redis_url is None:
        redis_url = settings.REDIS_URL
    
    return redis.from_url(redis_url, decode_responses=True)
