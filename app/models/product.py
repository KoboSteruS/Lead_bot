"""
Модель продуктов (трипвайеров).

Содержит информацию о продаваемых продуктах.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class ProductType(str, Enum):
    """Типы продуктов."""
    
    TRIPWIRE = "tripwire"
    COURSE = "course"
    CONSULTATION = "consultation"
    MAIN_PRODUCT = "main_product"
    UPSELL = "upsell"
    DOWNSELL = "downsell"


class Currency(str, Enum):
    """Валюты."""
    
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class Product(BaseModel):
    """Модель продукта."""
    
    __tablename__ = "products"
    
    # Название продукта
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Название продукта"
    )
    
    # Описание продукта
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Описание продукта"
    )
    
    # Тип продукта
    type: Mapped[ProductType] = mapped_column(
        String(20),
        nullable=False,
        doc="Тип продукта"
    )
    
    # Цена в копейках
    price: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Цена продукта в копейках"
    )
    
    # Валюта
    currency: Mapped[str] = mapped_column(
        String(3),
        default="RUB",
        nullable=False,
        doc="Валюта продукта"
    )
    
    # Ссылка на страницу оплаты
    payment_url: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Ссылка на страницу оплаты"
    )
    
    # Текст оффера
    offer_text: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Текст оффера для продажи"
    )
    
    # Активен ли продукт
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Активен ли продукт"
    )
    
    # Порядок сортировки
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Порядок сортировки"
    )
    
    def __repr__(self) -> str:
        """Строковое представление продукта."""
        return f"<Product(name='{self.name}', price={self.price})>"
    
    @property
    def price_rub(self) -> float:
        """Цена в рублях."""
        return self.price / 100
    
    # Relationships
    offers = relationship("ProductOffer", back_populates="product")


class ProductOffer(BaseModel):
    """Модель оффера продукта."""
    
    __tablename__ = "product_offers"
    
    # ID продукта
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id"),
        nullable=False,
        index=True,
        doc="ID продукта"
    )
    
    # Название оффера
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Название оффера"
    )
    
    # Текст оффера
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Текст оффера"
    )
    
    # Цена в копейках (может отличаться от основной цены продукта)
    price: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        doc="Цена оффера в копейках (если отличается от продукта)"
    )
    
    # Активен ли оффер
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Активен ли оффер"
    )
    
    # Связи
    product = relationship("Product", back_populates="offers")
    followups = relationship("UserFollowUp", back_populates="offer")
    
    def __repr__(self) -> str:
        """Строковое представление оффера."""
        return f"<ProductOffer(name='{self.name}', product_id={self.product_id})>"


class UserProductOffer(BaseModel):
    """Модель показанных офферов пользователям."""
    
    __tablename__ = "user_product_offers"
    
    # ID пользователя
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        doc="ID пользователя"
    )
    
    # ID оффера
    offer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("product_offers.id"),
        nullable=False,
        doc="ID оффера"
    )
    
    # Дата показа оффера
    shown_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="Дата показа оффера"
    )
    
    # Кликнул ли пользователь на оффер
    clicked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Кликнул ли пользователь на оффер"
    )
    
    # Дата клика
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Дата клика на оффер"
    )
    
    # Связи
    user = relationship("User", back_populates="product_offers")
    offer = relationship("ProductOffer")
    
    def __repr__(self) -> str:
        """Строковое представление показанного оффера."""
        return f"<UserProductOffer(user_id={self.user_id}, offer_id={self.offer_id})>"
