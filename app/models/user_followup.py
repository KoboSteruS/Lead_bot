"""
Модель для отслеживания отправленных дожимов пользователям.
"""

from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class UserFollowUp(BaseModel):
    """Модель для отслеживания отправленных дожимов."""

    __tablename__ = "user_followups"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        doc="ID пользователя"
    )

    offer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("product_offers.id"),
        nullable=False,
        doc="ID оффера"
    )

    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="Время отправки дожима"
    )

    # Связи
    user = relationship("User", back_populates="followups")
    offer = relationship("ProductOffer", back_populates="followups")

    def __repr__(self) -> str:
        return f"<UserFollowUp(user_id='{self.user_id}', offer_id='{self.offer_id}')>"


