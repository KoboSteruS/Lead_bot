"""
Модель пользователя.

Содержит информацию о пользователях Telegram.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class UserStatus(str, Enum):
    """Статусы пользователя."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    PENDING = "pending"


class User(BaseModel):
    """Модель пользователя Telegram."""
    
    __tablename__ = "users"
    
    # Telegram ID пользователя
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        doc="ID пользователя в Telegram"
    )
    
    # Имя пользователя в Telegram
    username: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Имя пользователя в Telegram"
    )
    
    # Имя пользователя
    first_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        doc="Имя пользователя"
    )
    
    # Фамилия пользователя
    last_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        doc="Фамилия пользователя"
    )
    
    # Статус пользователя
    status: Mapped[UserStatus] = mapped_column(
        String(20),
        default=UserStatus.PENDING,
        nullable=False,
        doc="Статус пользователя"
    )
    
    # Добавлен ли в группу
    is_in_group: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Добавлен ли пользователь в группу"
    )
    
    # Дата добавления в группу
    joined_group_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Дата добавления в группу"
    )
    
    # Дополнительная информация
    additional_info: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Дополнительная информация о пользователе"
    )
    
    # Дата окончания подписки
    subscription_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Дата окончания подписки"
    )
    
    # Подписан ли на канал
    is_subscribed_to_channel: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Подписан ли пользователь на основной канал"
    )
    
    # Дата последней проверки подписки
    last_subscription_check: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Дата последней проверки подписки на канал"
    )
    
    # Настройки напоминаний
    reminder_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Включены ли напоминания об отчетах"
    )
    
    reminder_time_hour: Mapped[int] = mapped_column(
        Integer,
        default=21,
        nullable=False,
        doc="Час для напоминания об отчете (0-23)"
    )
    
    reminder_time_minute: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Минута для напоминания об отчете (0-59)"
    )
    
    timezone_offset: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        doc="Часовой пояс относительно UTC (+3 для Москвы)"
    )
    
    # Связи с другими таблицами (старые, отключены для LeadBot)
    # payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    # reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    # goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    
    # Новые связи для лид-магнитов и прогрева (только для LeadBot)
    lead_magnets = relationship("UserLeadMagnet", back_populates="user", cascade="all, delete-orphan")
    warmups = relationship("UserWarmup", back_populates="user", cascade="all, delete-orphan")
    warmup_messages = relationship("UserWarmupMessage", back_populates="user", cascade="all, delete-orphan")
    product_offers = relationship("UserProductOffer", back_populates="user", cascade="all, delete-orphan")
    
    # Старые связи (отключены для LeadBot)
    # user_rituals = relationship("UserRitual", back_populates="user", cascade="all, delete-orphan")
    # chat_activities = relationship("ChatActivity", back_populates="user", cascade="all, delete-orphan")
    # user_activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        """Строковое представление пользователя."""
        return f"<User(telegram_id={self.telegram_id}, username={self.username}, status={self.status})>"
    
    @property
    def full_name(self) -> str:
        """Полное имя пользователя."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else str(self.telegram_id)
    
    @property
    def display_name(self) -> str:
        """Отображаемое имя пользователя."""
        if self.username:
            return f"@{self.username}"
        return self.full_name
    
    @property
    def is_subscription_active(self) -> bool:
        """Проверка, активна ли подписка пользователя."""
        if not self.subscription_until:
            return False
        return self.subscription_until > datetime.now()
    
    @property
    def subscription_days_left(self) -> int:
        """Количество дней до окончания подписки."""
        if not self.subscription_until:
            return 0
        delta = self.subscription_until - datetime.now()
        return max(0, delta.days)
    
    # Связи для LeadBot
    followups = relationship("UserFollowUp", back_populates="user")
