from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import hashlib
import os
import redis

import models
import schemas
import crud
import auth
from config import get_settings
from database import get_db

settings = get_settings()

app = FastAPI(
    title="URL Shortener API",
    description="Сервис для сокращения ссылок с аналитикой и управлением",
    version="1.0.0"
)

# Монтирование статики
static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")


# === Инициализация кэша ===
@app.on_event("startup")
async def startup():
    """Инициализация Redis кэша при старте"""
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
        print("✅ Redis кэш подключён")
    except redis.ConnectionError:
        print("⚠️  Redis не доступен. Кэширование отключено.")
        # Работаем без кэша


# === Вспомогательные функции ===
def generate_short_code(length: int = 6) -> str:
    """Генерация уникального короткого кода"""
    import random
    import string
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


def check_link_expired(link: models.ShortLink) -> bool:
    """Проверка, истекла ли ссылка"""
    if link.expires_at and link.expires_at < datetime.utcnow():
        return True
    return False


# ============================================
# === Auth Endpoints ===
# ============================================

@app.post("/auth/register", response_model=schemas.UserResponse, tags=["Auth"])
async def register(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """Регистрация нового пользователя"""
    # Проверка существующего пользователя
    if crud.get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    if crud.get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Создание пользователя
    hashed_password = auth.get_password_hash(user_data.password)
    user = crud.create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    return user


@app.post("/auth/login", response_model=schemas.Token, tags=["Auth"])
async def login(
    form_data: schemas.UserLogin,
    db: Session = Depends(get_db)
):
    """Вход пользователя (получение токена)"""
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(
        data={"sub": user.username}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=schemas.UserResponse, tags=["Auth"])
async def get_current_user_info(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Получение информации о текущем пользователе"""
    return current_user


# ============================================
# === Link Endpoints ===
# ============================================

@app.post("/links/shorten", response_model=schemas.LinkResponse, tags=["Links"])
async def shorten_link(
    link_data: schemas.LinkCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_optional_user)
):
    """
    Создание короткой ссылки.

    - **original_url**: Длинная ссылка (обязательно)
    - **custom_alias**: Пользовательский алиас (опционально)
    - **expires_at**: Дата истечения срока действия (опционально)
    - **project_id**: ID проекта для группировки (опционально)
    """
    # Проверка custom_alias на уникальность
    if link_data.custom_alias:
        existing = crud.get_link_by_custom_alias(db, link_data.custom_alias)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom alias already exists"
            )
        short_code = link_data.custom_alias
    else:
        # Генерация уникального short_code
        short_code = generate_short_code(settings.SHORT_CODE_LENGTH)
        # Проверка на уникальность
        while crud.get_link_by_short_code(db, short_code):
            short_code = generate_short_code(settings.SHORT_CODE_LENGTH)
    
    # Проверка проекта (если указан)
    if link_data.project_id:
        project = crud.get_project_by_id(db, link_data.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project not found"
            )
        # Проверка, что проект принадлежит пользователю
        if current_user and project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
    
    # Создание ссылки
    link = crud.create_short_link(
        db=db,
        short_code=short_code,
        original_url=str(link_data.original_url),
        custom_alias=link_data.custom_alias,
        expires_at=link_data.expires_at,
        user_id=current_user.id if current_user else None,
        project_id=link_data.project_id
    )

    return link


# === Важно: /links/my должен быть перед /links/{short_code} ===
@app.get("/links/my", response_model=List[schemas.LinkResponse], tags=["Links"])
async def get_my_links(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Получение всех ссылок текущего пользователя"""
    return crud.get_user_links(db, current_user.id)


# ============================================
# === Project Endpoints (перед /{short_code}) ===
# ============================================

@app.post("/projects", response_model=schemas.ProjectResponse, tags=["Projects"])
async def create_project(
    project_data: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Создание нового проекта для группировки ссылок"""
    return crud.create_project(
        db=db,
        name=project_data.name,
        user_id=current_user.id,
        description=project_data.description
    )


@app.get("/projects", response_model=List[schemas.ProjectResponse], tags=["Projects"])
async def get_my_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Получение всех проектов пользователя со ссылками"""
    projects = crud.get_user_projects(db, current_user.id)
    
    # Добавляем ссылки к каждому проекту
    for project in projects:
        project.links = crud.get_project_links(db, project.id)
    
    return projects


# ============================================
# === Admin / Maintenance Endpoints ===
# ============================================

@app.post("/admin/cleanup/expired", tags=["Admin"])
async def cleanup_expired(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Удаление истекших ссылок.

    Доступно только авторизованным пользователям.
    """
    count = crud.cleanup_expired_links(db)
    return {"message": f"Deleted {count} expired links"}


@app.post("/admin/cleanup/unused", tags=["Admin"])
async def cleanup_unused(
    days_inactive: int = 30,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Удаление неиспользуемых ссылок.

    - **days_inactive**: Количество дней без активности (по умолчанию 30)
    """
    count = crud.cleanup_unused_links(db, days_inactive)
    return {"message": f"Deleted {count} unused links"}


@app.get("/admin/history/expired", response_model=List[schemas.ExpiredLinkHistoryResponse], tags=["Admin"])
async def get_expired_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Получение истории истекших ссылок"""
    return crud.get_expired_history(db, current_user.id)


@app.get("/admin/popular", tags=["Admin"])
async def get_popular_links(
    limit: int = 10
):
    """Получение популярных ссылок (заглушка)"""
    return {"message": "Popular links endpoint", "limit": limit}


# === Короткие ссылки в корне (для редиректа) - ПОСЛЕ всех специфичных маршрутов ===
@app.get("/{short_code}", tags=["Redirect"])
async def redirect_short(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Перенаправление на оригинальный URL по короткой ссылке"""
    # Исключаем служебные пути
    if short_code in ['static', 'docs', 'redoc', 'openapi.json', 'auth', 'links', 'projects', 'admin']:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Получение из БД
    link = crud.get_link_by_short_code(db, short_code)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short link not found"
        )

    # Проверка истечения срока
    if check_link_expired(link):
        crud.cleanup_expired_links(db)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Link has expired"
        )

    # Увеличение счетчика переходов
    crud.increment_access_count(db, short_code)

    return RedirectResponse(url=link.original_url)


@app.get("/links/{short_code}", tags=["Links"])
async def redirect_to_original(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Перенаправление на оригинальный URL.

    Открывается короткая ссылка и происходит редирект.
    """
    # Получение из БД
    link = crud.get_link_by_short_code(db, short_code)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short link not found"
        )

    # Проверка истечения срока
    if check_link_expired(link):
        # Перемещение в историю и удаление
        crud.cleanup_expired_links(db)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Link has expired"
        )

    # Увеличение счетчика переходов
    crud.increment_access_count(db, short_code)

    return RedirectResponse(url=link.original_url)


@app.delete("/links/{short_code}", tags=["Links"])
async def delete_link(
    short_code: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Удаление короткой ссылки.

    Доступно только авторизованным пользователям.
    Можно удалять только свои ссылки.
    """
    link = crud.get_link_by_short_code(db, short_code)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short link not found"
        )

    # Проверка прав доступа
    if link.user_id and link.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own links"
        )

    # Удаление
    crud.delete_short_link(db, short_code)

    return {"message": "Link deleted successfully"}


@app.put("/links/{short_code}", response_model=schemas.LinkResponse, tags=["Links"])
async def update_link(
    short_code: str,
    link_data: schemas.LinkUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Обновление короткой ссылки.

    Можно обновить original_url, expires_at, project_id.
    Доступно только авторизованным пользователям.
    """
    link = crud.get_link_by_short_code(db, short_code)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short link not found"
        )

    # Проверка прав доступа
    if link.user_id and link.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own links"
        )

    # Обновление
    updated_link = crud.update_short_link(
        db=db,
        short_code=short_code,
        original_url=str(link_data.original_url) if link_data.original_url else None,
        expires_at=link_data.expires_at,
        project_id=link_data.project_id
    )

    return updated_link


@app.get("/links/{short_code}/stats", response_model=schemas.LinkStats, tags=["Links"])
@cache(expire=60)  # Кэширование на 1 минуту
async def get_link_statistics(
    short_code: str,
    db: Session = Depends(get_db)
):
    """
    Получение статистики по ссылке.

    Возвращает:
    - original_url
    - created_at
    - access_count
    - last_accessed_at
    - expires_at
    """
    # Получение из БД
    link = crud.get_link_by_short_code(db, short_code)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short link not found"
        )

    return {
        "short_code": link.short_code,
        "original_url": link.original_url,
        "created_at": link.created_at,
        "access_count": link.access_count,
        "last_accessed_at": link.last_accessed_at,
        "expires_at": link.expires_at,
        "is_active": link.is_active
    }


@app.get("/links/search", response_model=List[schemas.LinkSearchResult], tags=["Links"])
async def search_links(
    original_url: str,
    db: Session = Depends(get_db)
):
    """
    Поиск ссылок по оригинальному URL.

    Поддерживает частичное совпадение.
    """
    links = crud.search_links_by_original_url(db, original_url)
    return links


# ============================================
# === Health Check ===
# ============================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Проверка работоспособности сервиса"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ============================================
# === Frontend Routes ===
# ============================================

@app.get("/")
async def root():
    """Главная страница UI"""
    return FileResponse(os.path.join(static_path, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
