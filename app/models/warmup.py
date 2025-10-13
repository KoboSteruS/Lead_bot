"""
Модель системы прогрева пользователей.

Содержит информацию о последовательности сообщений для прогрева.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class WarmupMessageType(str, Enum):
    """Типы сообщений прогрева."""
    
    WELCOME = "welcome"
    PAIN_POINT = "pain_point"
    SOLUTION = "solution"
    SOCIAL_PROOF = "social_proof"
    OFFER = "offer"
    FOLLOW_UP = "follow_up"


class WarmupScenario(BaseModel):
    """Модель сценария прогрева."""
    
    __tablename__ = "warmup_scenarios"
    
    # Название сценария
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Название сценария прогрева"
    )
    
    # Описание сценария
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Описание сценария"
    )
    
    # Активен ли сценарий
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Активен ли сценарий"
    )
    
    # Связи
    messages = relationship("WarmupMessage", back_populates="scenario", order_by="WarmupMessage.delay_hours")
    
    def __repr__(self) -> str:
        """Строковое представление сценария."""
        return f"<WarmupScenario(name='{self.name}')>"


class WarmupMessage(BaseModel):
    """Модель сообщения прогрева."""
    
    __tablename__ = "warmup_messages"
    
    # ID сценария
    scenario_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("warmup_scenarios.id"),
        nullable=False,
        index=True,
        doc="ID сценария прогрева"
    )
    
    # Тип сообщения
    message_type: Mapped[WarmupMessageType] = mapped_column(
        String(20),
        nullable=False,
        doc="Тип сообщения"
    )
    
    # Заголовок сообщения
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        doc="Заголовок сообщения"
    )
    
    # Текст сообщения
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Текст сообщения"
    )
    
    # Задержка в часах от предыдущего сообщения
    delay_hours: Mapped[int] = mapped_column(
        Integer,
        default=24,
        nullable=False,
        doc="Задержка в часах от предыдущего сообщения"
    )
    
    # Порядок в сценарии
    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Порядок сообщения в сценарии"
    )
    
    # Активно ли сообщение
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Активно ли сообщение"
    )
    
    # Связи
    scenario = relationship("WarmupScenario", back_populates="messages")
    
    def __repr__(self) -> str:
        """Строковое представление сообщения."""
        return f"<WarmupMessage(type={self.message_type}, order={self.order})>"


class UserWarmup(BaseModel):
    """Модель прогрева пользователя."""
    
    __tablename__ = "user_warmups"
    
    # ID пользователя
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        doc="ID пользователя"
    )
    
    # ID сценария
    scenario_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("warmup_scenarios.id"),
        nullable=False,
        doc="ID сценария прогрева"
    )
    
    # Текущий шаг прогрева
    current_step: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Текущий шаг прогрева"
    )
    
    # Дата начала прогрева
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="Дата начала прогрева"
    )
    
    # Дата последнего сообщения
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Дата последнего отправленного сообщения"
    )
    
    # Завершен ли прогрев
    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Завершен ли прогрев"
    )
    
    # Остановлен ли прогрев
    is_stopped: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Остановлен ли прогрев"
    )
    
    # Связи
    user = relationship("User", back_populates="warmups")
    scenario = relationship("WarmupScenario")
    
    def __repr__(self) -> str:
        """Строковое представление прогрева пользователя."""
        return f"<UserWarmup(user_id={self.user_id}, step={self.current_step})>"


class UserWarmupMessage(BaseModel):
    """Модель отправленных сообщений прогрева пользователю."""
    
    __tablename__ = "user_warmup_messages"
    
    # ID пользователя
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        doc="ID пользователя"
    )
    
    # ID сообщения прогрева
    warmup_message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("warmup_messages.id"),
        nullable=False,
        doc="ID сообщения прогрева"
    )
    
    # Дата отправки
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="Дата отправки сообщения"
    )
    
    # Успешно ли отправлено
    is_sent: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Успешно ли отправлено"
    )
    
    # Ошибка отправки
    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Сообщение об ошибке"
    )
    
    # Связи
    user = relationship("User", back_populates="warmup_messages")
    warmup_message = relationship("WarmupMessage")
    
    def __repr__(self) -> str:
        """Строковое представление отправленного сообщения."""
        return f"<UserWarmupMessage(user_id={self.user_id}, sent_at={self.sent_at})>"
