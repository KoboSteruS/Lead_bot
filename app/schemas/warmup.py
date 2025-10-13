"""
Схемы для работы с системой прогрева.

Содержит Pydantic модели для валидации данных прогрева.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.warmup import WarmupMessageType


class WarmupScenarioBase(BaseModel):
    """Базовая схема сценария прогрева."""
    
    name: str = Field(..., max_length=255, description="Название сценария прогрева")
    description: Optional[str] = Field(None, description="Описание сценария")
    is_active: bool = Field(default=True, description="Активен ли сценарий")


class WarmupScenarioCreate(WarmupScenarioBase):
    """Схема для создания сценария прогрева."""
    pass


class WarmupScenarioUpdate(BaseModel):
    """Схема для обновления сценария прогрева."""
    
    name: Optional[str] = Field(None, max_length=255, description="Название сценария прогрева")
    description: Optional[str] = Field(None, description="Описание сценария")
    is_active: Optional[bool] = Field(None, description="Активен ли сценарий")


class WarmupMessageBase(BaseModel):
    """Базовая схема сообщения прогрева."""
    
    message_type: WarmupMessageType = Field(..., description="Тип сообщения")
    title: Optional[str] = Field(None, max_length=255, description="Заголовок сообщения")
    text: str = Field(..., description="Текст сообщения")
    delay_hours: int = Field(default=24, description="Задержка в часах от предыдущего сообщения")
    order: int = Field(..., description="Порядок сообщения в сценарии")
    is_active: bool = Field(default=True, description="Активно ли сообщение")
    
    class Config:
        use_enum_values = True


class WarmupMessageCreate(WarmupMessageBase):
    """Схема для создания сообщения прогрева."""
    
    scenario_id: str = Field(..., description="ID сценария прогрева")


class WarmupMessageUpdate(BaseModel):
    """Схема для обновления сообщения прогрева."""
    
    message_type: Optional[WarmupMessageType] = Field(None, description="Тип сообщения")
    title: Optional[str] = Field(None, max_length=255, description="Заголовок сообщения")
    text: Optional[str] = Field(None, description="Текст сообщения")
    delay_hours: Optional[int] = Field(None, description="Задержка в часах от предыдущего сообщения")
    order: Optional[int] = Field(None, description="Порядок сообщения в сценарии")
    is_active: Optional[bool] = Field(None, description="Активно ли сообщение")
    
    class Config:
        use_enum_values = True


class WarmupMessageResponse(WarmupMessageBase):
    """Схема ответа с данными сообщения прогрева."""
    
    id: str = Field(..., description="ID сообщения")
    scenario_id: str = Field(..., description="ID сценария прогрева")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    
    class Config:
        from_attributes = True
        use_enum_values = True


class WarmupScenarioResponse(WarmupScenarioBase):
    """Схема ответа с данными сценария прогрева."""
    
    id: str = Field(..., description="ID сценария")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    
    # Сообщения сценария
    messages: List[WarmupMessageResponse] = Field(default_factory=list, description="Сообщения сценария")
    
    class Config:
        from_attributes = True


class UserWarmupBase(BaseModel):
    """Базовая схема прогрева пользователя."""
    
    current_step: int = Field(default=0, description="Текущий шаг прогрева")
    is_completed: bool = Field(default=False, description="Завершен ли прогрев")
    is_stopped: bool = Field(default=False, description="Остановлен ли прогрев")


class UserWarmupCreate(UserWarmupBase):
    """Схема для создания прогрева пользователя."""
    
    user_id: str = Field(..., description="ID пользователя")
    scenario_id: str = Field(..., description="ID сценария прогрева")


class UserWarmupUpdate(BaseModel):
    """Схема для обновления прогрева пользователя."""
    
    current_step: Optional[int] = Field(None, description="Текущий шаг прогрева")
    is_completed: Optional[bool] = Field(None, description="Завершен ли прогрев")
    is_stopped: Optional[bool] = Field(None, description="Остановлен ли прогрев")
    last_message_at: Optional[datetime] = Field(None, description="Дата последнего сообщения")


class UserWarmupResponse(UserWarmupBase):
    """Схема ответа с данными прогрева пользователя."""
    
    id: str = Field(..., description="ID записи прогрева")
    user_id: str = Field(..., description="ID пользователя")
    scenario_id: str = Field(..., description="ID сценария прогрева")
    started_at: datetime = Field(..., description="Дата начала прогрева")
    last_message_at: Optional[datetime] = Field(None, description="Дата последнего сообщения")
    
    # Данные сценария
    scenario: WarmupScenarioResponse = Field(..., description="Данные сценария")
    
    class Config:
        from_attributes = True


class UserWarmupMessageResponse(BaseModel):
    """Схема ответа с данными отправленного сообщения прогрева."""
    
    id: str = Field(..., description="ID записи")
    user_id: str = Field(..., description="ID пользователя")
    warmup_message_id: str = Field(..., description="ID сообщения прогрева")
    sent_at: datetime = Field(..., description="Дата отправки")
    is_sent: bool = Field(..., description="Успешно ли отправлено")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    
    # Данные сообщения
    warmup_message: WarmupMessageResponse = Field(..., description="Данные сообщения")
    
    class Config:
        from_attributes = True
