"""
Модель лид-магнитов.

Содержит информацию о подарках, которые выдаются пользователям.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class LeadMagnetType(str, Enum):
    """Типы лид-магнитов."""
    
    PDF = "pdf"
    GOOGLE_SHEET = "google_sheet"
    LINK = "link"
    TEXT = "text"


class LeadMagnet(BaseModel):
    """Модель лид-магнита."""
    
    __tablename__ = "lead_magnets"
    
    # Название лид-магнита
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Название лид-магнита"
    )
    
    # Описание
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Описание лид-магнита"
    )
    
    # Тип лид-магнита
    type: Mapped[LeadMagnetType] = mapped_column(
        String(20),
        nullable=False,
        doc="Тип лид-магнита"
    )
    
    # Ссылка на файл/ресурс
    file_url: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Ссылка на файл или ресурс"
    )
    
    # Текст для отправки
    message_text: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Текст сообщения при выдаче"
    )
    
    # Активен ли лид-магнит
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Активен ли лид-магнит"
    )
    
    # Порядок выдачи (если несколько)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Порядок сортировки"
    )
    
    def __repr__(self) -> str:
        """Строковое представление лид-магнита."""
        return f"<LeadMagnet(name='{self.name}', type={self.type})>"


class UserLeadMagnet(BaseModel):
    """Модель выданных лид-магнитов пользователям."""
    
    __tablename__ = "user_lead_magnets"
    
    # ID пользователя
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        doc="ID пользователя"
    )
    
    # ID лид-магнита
    lead_magnet_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("lead_magnets.id"),
        nullable=False,
        index=True,
        doc="ID лид-магнита"
    )
    
    # Дата выдачи
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="Дата выдачи лид-магнита"
    )
    
    # Связи
    user = relationship("User", back_populates="lead_magnets")
    lead_magnet = relationship("LeadMagnet")
    
    def __repr__(self) -> str:
        """Строковое представление выданного лид-магнита."""
        return f"<UserLeadMagnet(user_id={self.user_id}, lead_magnet_id={self.lead_magnet_id})>"
