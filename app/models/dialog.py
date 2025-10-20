"""
Модели для системы диалогов.

Содержит модели для настраиваемых вопросов и ответов.
"""

from sqlalchemy import String, Text, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum

from app.models.base import BaseModel


class DialogStatus(str, Enum):
    """Статусы диалога."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"


class Dialog(BaseModel):
    """Модель диалога."""
    
    __tablename__ = "dialogs"
    
    # Название диалога
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Название диалога"
    )
    
    # Описание диалога
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Описание диалога"
    )
    
    # Статус диалога
    status: Mapped[DialogStatus] = mapped_column(
        String(20),
        default=DialogStatus.ACTIVE,
        nullable=False,
        doc="Статус диалога"
    )
    
    # Порядок сортировки
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Порядок сортировки"
    )
    
    # Связи
    questions = relationship("DialogQuestion", back_populates="dialog", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        """Строковое представление диалога."""
        return f"<Dialog(name='{self.name}', status='{self.status}')>"


class DialogQuestion(BaseModel):
    """Модель вопроса в диалоге."""
    
    __tablename__ = "dialog_questions"
    
    # ID диалога
    dialog_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("dialogs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID диалога"
    )
    
    # Текст вопроса
    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Текст вопроса"
    )
    
    # Ключевые слова для поиска (через запятую)
    keywords: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Ключевые слова для поиска через запятую"
    )
    
    # Активен ли вопрос
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Активен ли вопрос"
    )
    
    # Порядок сортировки
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Порядок сортировки"
    )
    
    # Связи
    dialog = relationship("Dialog", back_populates="questions")
    answers = relationship("DialogAnswer", back_populates="question", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        """Строковое представление вопроса."""
        return f"<DialogQuestion(question='{self.question_text[:50]}...', dialog_id='{self.dialog_id[:8]}...')>"


class DialogAnswer(BaseModel):
    """Модель ответа на вопрос."""
    
    __tablename__ = "dialog_answers"
    
    # ID вопроса
    question_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("dialog_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID вопроса"
    )
    
    # Текст ответа
    answer_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Текст ответа"
    )
    
    # Тип ответа (text, image, document, etc.)
    answer_type: Mapped[str] = mapped_column(
        String(20),
        default="text",
        nullable=False,
        doc="Тип ответа"
    )
    
    # Дополнительные данные (file_id, url, etc.)
    additional_data: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Дополнительные данные (file_id, url, etc.)"
    )
    
    # Активен ли ответ
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Активен ли ответ"
    )
    
    # Порядок сортировки
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Порядок сортировки"
    )
    
    # Связи
    question = relationship("DialogQuestion", back_populates="answers")
    
    def __repr__(self) -> str:
        """Строковое представление ответа."""
        return f"<DialogAnswer(answer='{self.answer_text[:50]}...', type='{self.answer_type}')>"
