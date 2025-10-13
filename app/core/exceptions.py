"""
Пользовательские исключения приложения.

Содержит все исключения, используемые в приложении.
"""


class BaseException(Exception):
    """Базовое исключение приложения."""
    
    def __init__(self, message: str = "Произошла ошибка"):
        self.message = message
        super().__init__(self.message)


class UserException(BaseException):
    """Исключение для ошибок, связанных с пользователями."""
    pass


class PaymentException(BaseException):
    """Исключение для ошибок, связанных с платежами."""
    pass


class FreeKassaException(BaseException):
    """Исключение для ошибок, связанных с FreeKassa."""
    pass


class TelegramException(BaseException):
    """Исключение для ошибок, связанных с Telegram API."""
    pass


class DatabaseException(BaseException):
    """Исключение для ошибок базы данных."""
    pass


class ValidationException(BaseException):
    """Исключение для ошибок валидации."""
    pass


class ConfigurationException(BaseException):
    """Исключение для ошибок конфигурации."""
    pass


class WarmupException(BaseException):
    """Исключение для ошибок системы прогрева."""
    pass


class RitualException(BaseException):
    """Исключение для ошибок системы ритуалов."""
    pass
