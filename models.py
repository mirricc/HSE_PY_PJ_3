from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import hashlib

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_authenticated = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    links = relationship("ShortLink", back_populates="user", cascade="all, delete-orphan")


class ShortLink(Base):
    __tablename__ = "short_links"
    
    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String, unique=True, index=True, nullable=False)
    original_url = Column(Text, nullable=False)
    custom_alias = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_accessed_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0)
    
    # Владелец ссылки
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="links")
    
    # Проект (группировка)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    project = relationship("Project", back_populates="links")
    
    # Флаг активности
    is_active = Column(Boolean, default=True)


class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    user = relationship("User", backref="projects")
    links = relationship("ShortLink", back_populates="project")


class ExpiredLinkHistory(Base):
    """История истекших ссылок"""
    __tablename__ = "expired_link_history"
    
    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String, index=True, nullable=False)
    original_url = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
    expired_at = Column(DateTime, default=datetime.utcnow)
    access_count = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


def get_engine(database_url: str):
    """Создание движка SQLAlchemy"""
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args, echo=False)


def get_session_local(engine):
    """Создание сессии"""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(engine):
    """Инициализация БД"""
    Base.metadata.create_all(bind=engine)


def generate_short_code(url: str, length: int = 6) -> str:
    """Генерация короткого кода из URL"""
    hash_object = hashlib.md5(f"{url}{datetime.utcnow().timestamp()}".encode())
    return hash_object.hexdigest()[:length]
