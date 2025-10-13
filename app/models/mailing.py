"""
Модель для рассылок.

Содержит информацию о массовых рассылках.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import String, Text, DateTime, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class MailingStatus(str, Enum):
    """Статусы рассылки."""
    
    DRAFT = "draft"  # Черновик
    SCHEDULED = "scheduled"  # Запланирована
    SENDING = "sending"  # Отправляется
    COMPLETED = "completed"  # Завершена
    FAILED = "failed"  # Неудачная


class Mailing(BaseModel):
    """Модель рассылки."""
    
    __tablename__ = "mailings"
    
    # Название рассылки
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Название рассылки"
    )
    
    # Текст сообщения
    message_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Текст сообщения"
    )
    
    # Статус рассылки
    status: Mapped[MailingStatus] = mapped_column(
        String(20),
        default=MailingStatus.DRAFT,
        nullable=False,
        doc="Статус рассылки"
    )
    
    # Количество получателей
    total_recipients: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Общее количество получателей"
    )
    
    # Количество отправленных
    sent_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Количество отправленных сообщений"
    )
    
    # Количество успешно доставленных
    delivered_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Количество успешно доставленных сообщений"
    )
    
    # Количество ошибок
    failed_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Количество ошибок при отправке"
    )
    
    # Время начала отправки
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Время начала отправки"
    )
    
    # Время завершения отправки
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Время завершения отправки"
    )
    
    # Создатель рассылки (ID администратора)
    created_by: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="ID администратора, создавшего рассылку"
    )
    
    def __repr__(self) -> str:
        """Строковое представление рассылки."""
        return f"<Mailing(name='{self.name}', status={self.status})>"


class MailingRecipient(BaseModel):
    """Модель получателя рассылки."""
    
    __tablename__ = "mailing_recipients"
    
    # ID рассылки
    mailing_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        doc="ID рассылки"
    )
    
    # ID пользователя
    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        doc="ID пользователя"
    )
    
    # Статус доставки
    delivery_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        doc="Статус доставки (pending, sent, delivered, failed)"
    )
    
    # Время отправки
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Время отправки сообщения"
    )
    
    # Сообщение об ошибке
    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Сообщение об ошибке при отправке"
    )
    
    def __repr__(self) -> str:
        """Строковое представление получателя рассылки."""
        return f"<MailingRecipient(mailing_id={self.mailing_id}, user_id={self.user_id}, status={self.delivery_status})>"


