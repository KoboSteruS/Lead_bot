"""
ReplyKeyboard клавиатуры для быстрого доступа к функциям бота.
"""

from telegram import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Получение основной клавиатуры с быстрыми командами.
    
    Returns:
        ReplyKeyboardMarkup: Основная клавиатура
    """
    keyboard = [
        [
            KeyboardButton("📝 Главное меню"),
            KeyboardButton("✅ Проверить подписку")
        ],
        [
            KeyboardButton("💳 Выбрать тариф"),
            KeyboardButton("📘 О клубе")
        ],
        [
            KeyboardButton("📊 Мой прогресс"),
            KeyboardButton("🎯 Моя цель")
        ]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие..."
    )


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """
    Получение админской клавиатуры.
    
    Returns:
        ReplyKeyboardMarkup: Админская клавиатура
    """
    keyboard = [
        [
            KeyboardButton("📝 Главное меню"),
            KeyboardButton("📊 Статистика")
        ],
        [
            KeyboardButton("👥 Пользователи"),
            KeyboardButton("⚙️ Настройки")
        ],
        [
            KeyboardButton("📋 Отчеты"),
            KeyboardButton("🔄 Обновить")
        ]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Админские команды..."
    )


def remove_keyboard() -> ReplyKeyboardMarkup:
    """
    Удаление клавиатуры.
    
    Returns:
        ReplyKeyboardMarkup: Пустая клавиатура для удаления
    """
    from telegram import ReplyKeyboardRemove
    return ReplyKeyboardRemove()
