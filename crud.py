from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import models
import config as cfg


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Получение пользователя по username"""
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Получение пользователя по email"""
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, username: str, email: str, hashed_password: str) -> models.User:
    """Создание нового пользователя"""
    user = models.User(
        username=username,
        email=email,
        hashed_password=hashed_password
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_link_by_short_code(db: Session, short_code: str) -> Optional[models.ShortLink]:
    """Получение ссылки по короткому коду"""
    return db.query(models.ShortLink).filter(
        models.ShortLink.short_code == short_code
    ).first()


def get_link_by_custom_alias(db: Session, custom_alias: str) -> Optional[models.ShortLink]:
    """Получение ссылки по custom alias"""
    return db.query(models.ShortLink).filter(
        models.ShortLink.custom_alias == custom_alias
    ).first()


def get_link_by_original_url(db: Session, original_url: str) -> Optional[models.ShortLink]:
    """Поиск ссылки по оригинальному URL"""
    return db.query(models.ShortLink).filter(
        models.ShortLink.original_url == original_url
    ).first()


def create_short_link(
    db: Session,
    short_code: str,
    original_url: str,
    custom_alias: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    user_id: Optional[int] = None,
    project_id: Optional[int] = None
) -> models.ShortLink:
    """Создание короткой ссылки"""
    link = models.ShortLink(
        short_code=short_code,
        original_url=original_url,
        custom_alias=custom_alias,
        expires_at=expires_at,
        user_id=user_id,
        project_id=project_id
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def update_short_link(
    db: Session,
    short_code: str,
    original_url: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    project_id: Optional[int] = None
) -> Optional[models.ShortLink]:
    """Обновление короткой ссылки"""
    link = get_link_by_short_code(db, short_code)
    if not link:
        return None
    
    if original_url is not None:
        link.original_url = original_url
    if expires_at is not None:
        link.expires_at = expires_at
    if project_id is not None:
        link.project_id = project_id
    
    db.commit()
    db.refresh(link)
    return link


def delete_short_link(db: Session, short_code: str) -> bool:
    """Удаление короткой ссылки"""
    link = get_link_by_short_code(db, short_code)
    if not link:
        return False
    
    # Сохраняем в историю перед удалением
    history = models.ExpiredLinkHistory(
        short_code=link.short_code,
        original_url=link.original_url,
        created_at=link.created_at,
        access_count=link.access_count,
        user_id=link.user_id
    )
    db.add(history)
    
    db.delete(link)
    db.commit()
    return True


def increment_access_count(
    db: Session,
    short_code: str
) -> Optional[models.ShortLink]:
    """Увеличение счетчика переходов"""
    link = get_link_by_short_code(db, short_code)
    if not link:
        return None

    link.access_count += 1
    link.last_accessed_at = datetime.utcnow()
    db.commit()
    db.refresh(link)

    return link


def get_link_stats(db: Session, short_code: str) -> Optional[dict]:
    """Получение статистики по ссылке"""
    link = get_link_by_short_code(db, short_code)
    if not link:
        return None
    
    return {
        "short_code": link.short_code,
        "original_url": link.original_url,
        "created_at": link.created_at,
        "access_count": link.access_count,
        "last_accessed_at": link.last_accessed_at,
        "expires_at": link.expires_at,
        "is_active": link.is_active
    }


def search_links_by_original_url(
    db: Session,
    original_url: str
) -> List[models.ShortLink]:
    """Поиск ссылок по оригинальному URL (частичное совпадение)"""
    return db.query(models.ShortLink).filter(
        models.ShortLink.original_url.like(f"%{original_url}%")
    ).all()


def get_user_links(db: Session, user_id: int) -> List[models.ShortLink]:
    """Получение всех ссылок пользователя"""
    return db.query(models.ShortLink).filter(
        models.ShortLink.user_id == user_id
    ).all()


def get_expired_links(db: Session) -> List[models.ShortLink]:
    """Получение истекших ссылок"""
    return db.query(models.ShortLink).filter(
        models.ShortLink.expires_at < datetime.utcnow(),
        models.ShortLink.is_active == True
    ).all()


def cleanup_expired_links(db: Session) -> int:
    """Удаление истекших ссылок"""
    expired = get_expired_links(db)
    count = 0

    for link in expired:
        # Сохраняем в историю
        history = models.ExpiredLinkHistory(
            short_code=link.short_code,
            original_url=link.original_url,
            created_at=link.created_at,
            access_count=link.access_count,
            user_id=link.user_id
        )
        db.add(history)
        db.delete(link)
        count += 1

    db.commit()
    return count


def cleanup_unused_links(
    db: Session,
    days_inactive: int = 30
) -> int:
    """Удаление неиспользуемых ссылок"""
    threshold = datetime.utcnow() - timedelta(days=days_inactive)

    unused = db.query(models.ShortLink).filter(
        models.ShortLink.is_active == True,
        models.ShortLink.last_accessed_at < threshold
    ).all()

    count = 0
    for link in unused:
        # Сохраняем в историю
        history = models.ExpiredLinkHistory(
            short_code=link.short_code,
            original_url=link.original_url,
            created_at=link.created_at,
            access_count=link.access_count,
            user_id=link.user_id
        )
        db.add(history)
        db.delete(link)
        count += 1

    db.commit()
    return count


def get_expired_history(db: Session, user_id: Optional[int] = None) -> List[models.ExpiredLinkHistory]:
    """Получение истории истекших ссылок"""
    query = db.query(models.ExpiredLinkHistory)
    if user_id:
        query = query.filter(models.ExpiredLinkHistory.user_id == user_id)
    return query.order_by(models.ExpiredLinkHistory.expired_at.desc()).all()


# === Project CRUD ===
def create_project(
    db: Session,
    name: str,
    user_id: int,
    description: Optional[str] = None
) -> models.Project:
    """Создание проекта"""
    project = models.Project(
        name=name,
        description=description,
        user_id=user_id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_user_projects(db: Session, user_id: int) -> List[models.Project]:
    """Получение проектов пользователя"""
    return db.query(models.Project).filter(
        models.Project.user_id == user_id
    ).all()


def get_project_by_id(db: Session, project_id: int) -> Optional[models.Project]:
    """Получение проекта по ID"""
    return db.query(models.Project).filter(
        models.Project.id == project_id
    ).first()


def get_project_links(db: Session, project_id: int) -> List[models.ShortLink]:
    """Получение всех ссылок проекта"""
    return db.query(models.ShortLink).filter(
        models.ShortLink.project_id == project_id
    ).all()
