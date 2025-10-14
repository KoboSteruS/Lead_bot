"""
Модель администраторов бота.
"""

from sqlalchemy import String, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class Admin(BaseModel):
    """Модель администратора бота."""
    
    __tablename__ = "admins"
    
    # Telegram ID администратора
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        doc="Telegram ID администратора"
    )
    
    # Имя пользователя в Telegram
    username: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        doc="Username в Telegram"
    )
    
    # Полное имя
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        doc="Полное имя администратора"
    )
    
    # Активен ли админ
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Активен ли администратор"
    )
    
    # Уровень доступа (для будущего расширения)
    access_level: Mapped[int] = mapped_column(
        BigInteger,
        default=1,
        nullable=False,
        doc="Уровень доступа (1 - обычный админ, 100 - суперадмин)"
    )
    
    # Кто добавил этого админа
    added_by_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=True,
        doc="ID администратора, который добавил этого админа"
    )
    
    def __repr__(self) -> str:
        """Строковое представление админа."""
        return f"<Admin(telegram_id={self.telegram_id}, username='{self.username}')>"

