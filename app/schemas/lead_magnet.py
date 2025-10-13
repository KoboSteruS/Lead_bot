"""
Схемы для работы с лид-магнитами.

Содержит Pydantic модели для валидации данных лид-магнитов.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.lead_magnet import LeadMagnetType


class LeadMagnetBase(BaseModel):
    """Базовая схема лид-магнита."""
    
    name: str = Field(..., max_length=255, description="Название лид-магнита")
    description: Optional[str] = Field(None, description="Описание лид-магнита")
    type: LeadMagnetType = Field(..., description="Тип лид-магнита")
    file_url: Optional[str] = Field(None, description="Ссылка на файл или ресурс")
    message_text: Optional[str] = Field(None, description="Текст сообщения при выдаче")
    is_active: bool = Field(default=True, description="Активен ли лид-магнит")
    sort_order: int = Field(default=0, description="Порядок сортировки")
    
    class Config:
        use_enum_values = True


class LeadMagnetCreate(LeadMagnetBase):
    """Схема для создания лид-магнита."""
    pass


class LeadMagnetUpdate(BaseModel):
    """Схема для обновления лид-магнита."""
    
    name: Optional[str] = Field(None, max_length=255, description="Название лид-магнита")
    description: Optional[str] = Field(None, description="Описание лид-магнита")
    type: Optional[LeadMagnetType] = Field(None, description="Тип лид-магнита")
    file_url: Optional[str] = Field(None, description="Ссылка на файл или ресурс")
    message_text: Optional[str] = Field(None, description="Текст сообщения при выдаче")
    is_active: Optional[bool] = Field(None, description="Активен ли лид-магнит")
    sort_order: Optional[int] = Field(None, description="Порядок сортировки")
    
    class Config:
        use_enum_values = True


class LeadMagnetResponse(LeadMagnetBase):
    """Схема ответа с данными лид-магнита."""
    
    id: str = Field(..., description="ID лид-магнита")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    
    class Config:
        from_attributes = True
        use_enum_values = True


class UserLeadMagnetResponse(BaseModel):
    """Схема ответа с данными выданного лид-магнита."""
    
    id: str = Field(..., description="ID записи")
    user_id: str = Field(..., description="ID пользователя")
    lead_magnet_id: str = Field(..., description="ID лид-магнита")
    issued_at: datetime = Field(..., description="Дата выдачи")
    
    # Данные лид-магнита
    lead_magnet: LeadMagnetResponse = Field(..., description="Данные лид-магнита")
    
    class Config:
        from_attributes = True
