"""
Основные клавиатуры бота.

Содержит функции для создания inline клавиатур с улучшенным UX.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Создание основного меню.
    
    Returns:
        InlineKeyboardMarkup: Основное меню
    """
    keyboard = [
        [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")],
        [InlineKeyboardButton("💳 Выбрать тариф", callback_data="choose_tariff")],
        [InlineKeyboardButton("📝 Написать отчёт", callback_data="write_report")],
        [InlineKeyboardButton("📊 Отчёты за неделю", callback_data="reports_week"), InlineKeyboardButton("🎯 Мои цели", callback_data="my_goals")],
        [InlineKeyboardButton("📘 О клубе", callback_data="about_club")],
        [
            InlineKeyboardButton("📊 Мой прогресс", callback_data="my_progress"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """
    Создание клавиатуры для проверки подписки.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура проверки подписки
    """
    keyboard = [
        [InlineKeyboardButton("🔄 Проверить снова", callback_data="check_subscription")],
        [InlineKeyboardButton("← Главное меню", callback_data="main_menu")]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def get_tariff_keyboard() -> InlineKeyboardMarkup:
    """
    Создание клавиатуры выбора тарифа.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура тарифов
    """
    keyboard = [
        [InlineKeyboardButton("📅 1 месяц — 1000 руб.", callback_data="pay_1_month")],
        [InlineKeyboardButton("📅 3 месяца — 2700 руб.", callback_data="pay_3_months")],
        [InlineKeyboardButton("📅 Год — 9000 руб.", callback_data="pay_subscription")],
        [InlineKeyboardButton("← Главное меню", callback_data="main_menu")]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def get_report_keyboard() -> InlineKeyboardMarkup:
    """
    Создание клавиатуры для отчетов.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура отчетов
    """
    keyboard = [
        [InlineKeyboardButton("📝 Отчёт отправлен", callback_data="report_sent")],
        [InlineKeyboardButton("🧩 Не готов делиться", callback_data="report_skipped")]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def get_progress_keyboard() -> InlineKeyboardMarkup:
    """
    Создание клавиатуры прогресса.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура прогресса
    """
    keyboard = [
        [InlineKeyboardButton("📈 Отчеты за неделю", callback_data="reports_week")],
        [InlineKeyboardButton("🎯 Мои цели", callback_data="my_goals")],
        [InlineKeyboardButton("📊 Общая статистика", callback_data="my_stats")],
        [InlineKeyboardButton("← Главное меню", callback_data="main_menu")]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def get_club_info_keyboard() -> InlineKeyboardMarkup:
    """
    Создание клавиатуры информации о клубе.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура информации о клубе
    """
    keyboard = [
        [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")],
        [InlineKeyboardButton("💳 Выбрать тариф", callback_data="choose_tariff")],
        [InlineKeyboardButton("← Главное меню", callback_data="main_menu")]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """
    Создание админской клавиатуры.
    
    Returns:
        InlineKeyboardMarkup: Админская клавиатура
    """
    keyboard = [
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("💰 Платежи", callback_data="admin_payments")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")],
        [InlineKeyboardButton("← Главное меню", callback_data="main_menu")]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(confirm_data: str, cancel_data: str = "main_menu") -> InlineKeyboardMarkup:
    """
    Создание клавиатуры подтверждения.
    
    Args:
        confirm_data: Callback data для подтверждения
        cancel_data: Callback data для отмены
        
    Returns:
        InlineKeyboardMarkup: Клавиатура подтверждения
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=confirm_data),
            InlineKeyboardButton("❌ Отменить", callback_data=cancel_data)
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard(back_data: str = "main_menu") -> InlineKeyboardMarkup:
    """
    Создание клавиатуры с кнопкой "Назад".
    
    Args:
        back_data: Callback data для кнопки "Назад"
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой "Назад"
    """
    keyboard = [
        [InlineKeyboardButton("← Главное меню", callback_data=back_data)]
    ]
    
    return InlineKeyboardMarkup(keyboard)


# Для обратной совместимости
get_main_keyboard = get_main_menu_keyboard


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """
    Создание клавиатуры настроек.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура настроек
    """
    keyboard = [
        [InlineKeyboardButton("🕐 Время напоминаний", callback_data="settings_reminder_time")],
        [InlineKeyboardButton("🔔 Вкл/выкл напоминания", callback_data="settings_toggle_reminders")],
        [InlineKeyboardButton("🌍 Часовой пояс", callback_data="settings_timezone")],
        [InlineKeyboardButton("← Назад в меню", callback_data="back_to_main")]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def get_reminder_time_keyboard() -> InlineKeyboardMarkup:
    """
    Создание клавиатуры выбора времени напоминаний.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура времени
    """
    keyboard = []
    
    # Популярные варианты времени
    times = [
        ("🌅 08:00", "set_time_8_0"),
        ("☀️ 12:00", "set_time_12_0"),
        ("🌆 18:00", "set_time_18_0"),
        ("🌙 21:00", "set_time_21_0"),
        ("🌃 22:00", "set_time_22_0"),
        ("🌌 23:00", "set_time_23_0"),
    ]
    
    # Добавляем кнопки времени парами
    for i in range(0, len(times), 2):
        row = []
        row.append(InlineKeyboardButton(times[i][0], callback_data=times[i][1]))
        if i + 1 < len(times):
            row.append(InlineKeyboardButton(times[i + 1][0], callback_data=times[i + 1][1]))
        keyboard.append(row)
    
    # Кнопки управления
    keyboard.append([InlineKeyboardButton("⏰ Настроить свое время", callback_data="custom_time")])
    keyboard.append([InlineKeyboardButton("← Назад к настройкам", callback_data="settings")])
    
    return InlineKeyboardMarkup(keyboard)


def get_timezone_keyboard() -> InlineKeyboardMarkup:
    """
    Создание клавиатуры выбора часового пояса.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура часовых поясов
    """
    keyboard = [
        [InlineKeyboardButton("🇷🇺 МСК UTC+3", callback_data="tz_3")],
        [InlineKeyboardButton("🇷🇺 ЕКБ UTC+5", callback_data="tz_5")],
        [InlineKeyboardButton("🇷🇺 НСК UTC+7", callback_data="tz_7")],
        [InlineKeyboardButton("🇷🇺 ВЛД UTC+10", callback_data="tz_10")],
        [InlineKeyboardButton("🇺🇦 КИВ UTC+2", callback_data="tz_2")],
        [InlineKeyboardButton("🇰🇿 АСТ UTC+6", callback_data="tz_6")],
        [InlineKeyboardButton("← Назад к настройкам", callback_data="settings")]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def get_toggle_reminders_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    """
    Создание клавиатуры включения/выключения напоминаний.
    
    Args:
        enabled: Включены ли напоминания
        
    Returns:
        InlineKeyboardMarkup: Клавиатура переключения
    """
    status_text = "🔔 Включить" if not enabled else "🔕 Выключить"
    callback = "toggle_reminders_on" if not enabled else "toggle_reminders_off"
    
    keyboard = [
        [InlineKeyboardButton(status_text, callback_data=callback)],
        [InlineKeyboardButton("← Назад к настройкам", callback_data="settings")]
    ]
    
    return InlineKeyboardMarkup(keyboard)
get_payment_keyboard = get_tariff_keyboard
get_success_keyboard = get_back_keyboard
get_error_keyboard = get_back_keyboard