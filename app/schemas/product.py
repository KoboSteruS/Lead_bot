"""
Схемы для работы с продуктами (трипвайерами).

Содержит Pydantic модели для валидации данных продуктов.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.product import ProductType


class ProductBase(BaseModel):
    """Базовая схема продукта."""
    
    name: str = Field(..., max_length=255, description="Название продукта")
    description: Optional[str] = Field(None, description="Описание продукта")
    type: ProductType = Field(..., description="Тип продукта")
    price: int = Field(..., gt=0, description="Цена продукта в копейках")
    currency: str = Field(default="RUB", max_length=3, description="Валюта продукта")
    payment_url: Optional[str] = Field(None, description="Ссылка на страницу оплаты")
    offer_text: Optional[str] = Field(None, description="Текст оффера для продажи")
    is_active: bool = Field(default=True, description="Активен ли продукт")
    sort_order: int = Field(default=0, description="Порядок сортировки")
    
    class Config:
        use_enum_values = True


class ProductCreate(ProductBase):
    """Схема для создания продукта."""
    pass


class ProductUpdate(BaseModel):
    """Схема для обновления продукта."""
    
    name: Optional[str] = Field(None, max_length=255, description="Название продукта")
    description: Optional[str] = Field(None, description="Описание продукта")
    type: Optional[ProductType] = Field(None, description="Тип продукта")
    price: Optional[int] = Field(None, gt=0, description="Цена продукта в копейках")
    currency: Optional[str] = Field(None, max_length=3, description="Валюта продукта")
    payment_url: Optional[str] = Field(None, description="Ссылка на страницу оплаты")
    offer_text: Optional[str] = Field(None, description="Текст оффера для продажи")
    is_active: Optional[bool] = Field(None, description="Активен ли продукт")
    sort_order: Optional[int] = Field(None, description="Порядок сортировки")
    
    class Config:
        use_enum_values = True


class ProductResponse(ProductBase):
    """Схема ответа с данными продукта."""
    
    id: str = Field(..., description="ID продукта")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    
    # Вычисляемые поля
    price_rub: float = Field(..., description="Цена в рублях")
    
    class Config:
        from_attributes = True
        use_enum_values = True


class ProductOfferBase(BaseModel):
    """Базовая схема оффера продукта."""
    
    name: str = Field(..., max_length=255, description="Название оффера")
    text: str = Field(..., description="Текст оффера")
    price: Optional[int] = Field(None, gt=0, description="Цена оффера в копейках")
    is_active: bool = Field(default=True, description="Активен ли оффер")


class ProductOfferCreate(ProductOfferBase):
    """Схема для создания оффера продукта."""
    
    product_id: str = Field(..., description="ID продукта")


class ProductOfferUpdate(BaseModel):
    """Схема для обновления оффера продукта."""
    
    name: Optional[str] = Field(None, max_length=255, description="Название оффера")
    text: Optional[str] = Field(None, description="Текст оффера")
    price: Optional[int] = Field(None, gt=0, description="Цена оффера в копейках")
    is_active: Optional[bool] = Field(None, description="Активен ли оффер")


class ProductOfferResponse(ProductOfferBase):
    """Схема ответа с данными оффера продукта."""
    
    id: str = Field(..., description="ID оффера")
    product_id: str = Field(..., description="ID продукта")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    
    class Config:
        from_attributes = True


class UserProductOfferResponse(BaseModel):
    """Схема ответа с данными показанного оффера пользователю."""
    
    id: str = Field(..., description="ID записи")
    user_id: str = Field(..., description="ID пользователя")
    offer_id: str = Field(..., description="ID оффера")
    shown_at: datetime = Field(..., description="Дата показа оффера")
    clicked: bool = Field(..., description="Кликнул ли пользователь на оффер")
    clicked_at: Optional[datetime] = Field(None, description="Дата клика на оффер")
    
    # Данные оффера
    offer: ProductOfferResponse = Field(..., description="Данные оффера")
    
    class Config:
        from_attributes = True
