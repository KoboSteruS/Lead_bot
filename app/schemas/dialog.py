"""
Схемы для системы диалогов.

Содержит Pydantic схемы для валидации данных диалогов.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.models.dialog import DialogStatus


class DialogAnswerBase(BaseModel):
    """Базовая схема ответа."""
    
    answer_text: str = Field(..., description="Текст ответа")
    answer_type: str = Field(default="text", description="Тип ответа (text, image, document)")
    additional_data: Optional[str] = Field(None, description="Дополнительные данные")
    is_active: bool = Field(default=True, description="Активен ли ответ")
    sort_order: int = Field(default=0, description="Порядок сортировки")


class DialogAnswerCreate(DialogAnswerBase):
    """Схема создания ответа."""
    pass


class DialogAnswerResponse(DialogAnswerBase):
    """Схема ответа ответа."""
    
    id: str = Field(..., description="ID ответа")
    question_id: str = Field(..., description="ID вопроса")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата обновления")
    
    class Config:
        from_attributes = True


class DialogQuestionBase(BaseModel):
    """Базовая схема вопроса."""
    
    question_text: str = Field(..., description="Текст вопроса")
    keywords: Optional[str] = Field(None, description="Ключевые слова через запятую")
    is_active: bool = Field(default=True, description="Активен ли вопрос")
    sort_order: int = Field(default=0, description="Порядок сортировки")


class DialogQuestionCreate(DialogQuestionBase):
    """Схема создания вопроса."""
    
    answers: List[DialogAnswerCreate] = Field(default=[], description="Ответы на вопрос")


class DialogQuestionResponse(DialogQuestionBase):
    """Схема ответа вопроса."""
    
    id: str = Field(..., description="ID вопроса")
    dialog_id: str = Field(..., description="ID диалога")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата обновления")
    answers: List[DialogAnswerResponse] = Field(default=[], description="Ответы на вопрос")
    
    class Config:
        from_attributes = True


class DialogBase(BaseModel):
    """Базовая схема диалога."""
    
    name: str = Field(..., description="Название диалога")
    description: Optional[str] = Field(None, description="Описание диалога")
    status: DialogStatus = Field(default=DialogStatus.ACTIVE, description="Статус диалога")
    sort_order: int = Field(default=0, description="Порядок сортировки")


class DialogCreate(DialogBase):
    """Схема создания диалога."""
    
    questions: List[DialogQuestionCreate] = Field(default=[], description="Вопросы диалога")


class DialogUpdate(BaseModel):
    """Схема обновления диалога."""
    
    name: Optional[str] = Field(None, description="Название диалога")
    description: Optional[str] = Field(None, description="Описание диалога")
    status: Optional[DialogStatus] = Field(None, description="Статус диалога")
    sort_order: Optional[int] = Field(None, description="Порядок сортировки")


class DialogResponse(DialogBase):
    """Схема ответа диалога."""
    
    id: str = Field(..., description="ID диалога")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата обновления")
    questions: List[DialogQuestionResponse] = Field(default=[], description="Вопросы диалога")
    
    class Config:
        from_attributes = True


class DialogSearchRequest(BaseModel):
    """Схема запроса поиска диалога."""
    
    query: str = Field(..., description="Поисковый запрос")
    limit: int = Field(default=5, description="Максимальное количество результатов")


class DialogSearchResult(BaseModel):
    """Схема результата поиска диалога."""
    
    question: DialogQuestionResponse = Field(..., description="Найденный вопрос")
    dialog: DialogResponse = Field(..., description="Диалог вопроса")
    answers: List[DialogAnswerResponse] = Field(..., description="Ответы на вопрос")
    relevance_score: float = Field(..., description="Оценка релевантности (0-1)")
