"""
Схемы для пользователей.

Содержит Pydantic модели для валидации данных пользователей.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator

from app.models.user import UserStatus


class UserBase(BaseModel):
    """Базовая схема пользователя."""
    
    telegram_id: int = Field(..., description="ID пользователя в Telegram")
    username: Optional[str] = Field(None, description="Имя пользователя в Telegram")
    first_name: Optional[str] = Field(None, description="Имя пользователя")
    last_name: Optional[str] = Field(None, description="Фамилия пользователя")
    
    @validator("telegram_id")
    def validate_telegram_id(cls, v: int) -> int:
        """Валидация Telegram ID."""
        if v <= 0:
            raise ValueError("Telegram ID должен быть положительным числом")
        return v
    
    @validator("username")
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Валидация имени пользователя."""
        if v is not None and len(v) > 255:
            raise ValueError("Имя пользователя не может быть длиннее 255 символов")
        return v
    
    @validator("first_name", "last_name")
    def validate_names(cls, v: Optional[str]) -> Optional[str]:
        """Валидация имени и фамилии."""
        if v is not None and len(v) > 255:
            raise ValueError("Имя и фамилия не могут быть длиннее 255 символов")
        return v


class UserCreate(UserBase):
    """Схема для создания пользователя."""
    pass


class UserUpdate(BaseModel):
    """Схема для обновления пользователя."""
    
    username: Optional[str] = Field(None, description="Имя пользователя в Telegram")
    first_name: Optional[str] = Field(None, description="Имя пользователя")
    last_name: Optional[str] = Field(None, description="Фамилия пользователя")
    status: Optional[UserStatus] = Field(None, description="Статус пользователя")
    is_in_group: Optional[bool] = Field(None, description="Добавлен ли в группу")
    additional_info: Optional[str] = Field(None, description="Дополнительная информация")
    
    @validator("username")
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Валидация имени пользователя."""
        if v is not None and len(v) > 255:
            raise ValueError("Имя пользователя не может быть длиннее 255 символов")
        return v
    
    @validator("first_name", "last_name")
    def validate_names(cls, v: Optional[str]) -> Optional[str]:
        """Валидация имени и фамилии."""
        if v is not None and len(v) > 255:
            raise ValueError("Имя и фамилия не могут быть длиннее 255 символов")
        return v


class UserResponse(UserBase):
    """Схема для ответа с данными пользователя."""
    
    id: str = Field(..., description="Уникальный идентификатор пользователя")
    status: UserStatus = Field(..., description="Статус пользователя")
    is_in_group: bool = Field(..., description="Добавлен ли в группу")
    joined_group_at: Optional[datetime] = Field(None, description="Дата добавления в группу")
    additional_info: Optional[str] = Field(None, description="Дополнительная информация")
    created_at: datetime = Field(..., description="Дата создания записи")
    updated_at: datetime = Field(..., description="Дата последнего обновления")
    
    class Config:
        from_attributes = True


class UserList(BaseModel):
    """Схема для списка пользователей."""
    
    users: list[UserResponse] = Field(..., description="Список пользователей")
    total: int = Field(..., description="Общее количество пользователей")
    page: int = Field(..., description="Номер страницы")
    per_page: int = Field(..., description="Количество записей на странице")
