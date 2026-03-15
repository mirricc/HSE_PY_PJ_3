from pydantic import BaseModel, EmailStr, HttpUrl
from datetime import datetime
from typing import Optional, List


# === User Schemas ===
class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: int
    is_authenticated: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# === Link Schemas ===
class LinkCreate(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None
    project_id: Optional[int] = None


class LinkUpdate(BaseModel):
    original_url: Optional[HttpUrl] = None
    expires_at: Optional[datetime] = None
    project_id: Optional[int] = None


class LinkResponse(BaseModel):
    short_code: str
    original_url: str
    custom_alias: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    user_id: Optional[int]
    project_id: Optional[int]
    
    class Config:
        from_attributes = True


class LinkStats(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    access_count: int
    last_accessed_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool


class LinkSearchResult(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    access_count: int
    is_active: bool


# === Project Schemas ===
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    user_id: int
    
    class Config:
        from_attributes = True


# === Token Schema ===
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


# === History Schema ===
class ExpiredLinkHistoryResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    expired_at: datetime
    access_count: int
    
    class Config:
        from_attributes = True
