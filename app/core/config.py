"""
Конфигурация приложения.

Содержит все настройки приложения, загружаемые из переменных окружения.
"""

from typing import Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Telegram Bot
    telegram_bot_token: str = Field(default="", description="Токен Telegram бота")
    telegram_group_id: int = Field(default=-1001234567890, description="ID группы Telegram")
    telegram_channel_id: int = Field(default=-1001234567891, description="ID канала для проверки подписки")
    
    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./osnovaputi_bot.db", description="URL подключения к базе данных")
    
    # Payment system (disabled for now)
    # freekassa_shop_id: str = Field(default="", description="ID магазина в FreeKassa")
    # freekassa_secret_key: str = Field(default="", description="Секретный ключ FreeKassa")
    # freekassa_api_key: str = Field(default="", description="API ключ FreeKassa")
    # freekassa_webhook_url: Optional[str] = Field(None, description="URL для webhook FreeKassa")
    
    # Security
    secret_key: str = Field(default="default_secret_key", description="Секретный ключ для JWT")
    
    # Application
    debug: bool = Field(default=False, description="Режим отладки")
    log_level: str = Field(default="INFO", description="Уровень логирования")
    
    # Payment settings
    payment_amount: float = Field(default=1000.0, description="Сумма платежа по умолчанию")
    payment_currency: str = Field(default="RUB", description="Валюта платежа по умолчанию")
    
    # Subscription settings
    one_month_price: float = Field(default=1000.0, description="Цена подписки на 1 месяц")
    three_months_price: float = Field(default=2700.0, description="Цена подписки на 3 месяца")
    subscription_price: float = Field(default=9000.0, description="Цена годовой подписки")
    
    # Schedule settings
    report_time_hour: int = Field(default=21, description="Час отправки напоминания об отчете")
    report_time_minute: int = Field(default=0, description="Минута отправки напоминания об отчете")
    goal_day_of_week: int = Field(default=6, description="День недели для постановки целей (0-понедельник, 6-воскресенье)")
    analytics_day_of_week: int = Field(default=6, description="День недели для анализа активности")
    
    @validator("telegram_bot_token")
    def validate_telegram_bot_token(cls, v: str) -> str:
        """Валидация токена Telegram бота."""
        if not v or v == "":
            raise ValueError("Токен Telegram бота обязателен для запуска")
        return v
    
    @validator("telegram_group_id")
    def validate_telegram_group_id(cls, v: int) -> int:
        """Валидация ID группы Telegram."""
        if v >= 0:
            raise ValueError("ID группы должен быть отрицательным числом")
        return v
    
    @validator("payment_amount")
    def validate_payment_amount(cls, v: float) -> float:
        """Валидация суммы платежа."""
        if v <= 0:
            raise ValueError("Сумма платежа должна быть больше нуля")
        return v
    
    @validator("payment_currency")
    def validate_payment_currency(cls, v: str) -> str:
        """Валидация валюты платежа."""
        if len(v) != 3:
            raise ValueError("Код валюты должен состоять из 3 символов")
        return v.upper()
    
    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Валидация уровня логирования."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Уровень логирования должен быть одним из: {valid_levels}")
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Игнорируем лишние поля из .env


# Создаем экземпляр настроек
settings = Settings()
