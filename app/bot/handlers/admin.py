"""
Исправленные обработчики для административных команд.

Обрабатывает команды доступные только администраторам.
"""

from datetime import datetime
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from loguru import logger

from app.core.database import get_database
from app.services import UserService, ProductService, LeadMagnetService, WarmupService, PaymentService


async def _restore_uuid(short_id: str, product_service: ProductService) -> Optional[str]:
    """Восстановить полный UUID из короткого ID через поиск в базе."""
    try:
        # Ищем продукты с UUID начинающимся на short_id  
        products = await product_service.get_all_products()
        for product in products:
            if str(product.id).replace('-', '').startswith(short_id):
                return str(product.id)
        
        # Ищем офферы с UUID начинающимся на short_id
        offers = await product_service.get_all_offers()
        for offer in offers:
            if str(offer.id).replace('-', '').startswith(short_id):
                return str(offer.id)
                
        return None
    except Exception as e:
        logger.error(f"Ошибка восстановления UUID для {short_id}: {e}")
        return None


async def _restore_warmup_scenario_uuid(short_id: str, warmup_service: "WarmupService") -> Optional[str]:
    """Восстановить полный UUID сценария прогрева из короткого ID."""
    try:
        # Ищем сценарии с UUID начинающимся на short_id
        scenarios = await warmup_service.get_all_scenarios()
        for scenario in scenarios:
            if str(scenario.id).replace('-', '').startswith(short_id):
                return str(scenario.id)
                
        return None
    except Exception as e:
        logger.error(f"Ошибка восстановления UUID сценария прогрева для {short_id}: {e}")
        return None


async def _safe_edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None) -> None:
    """Безопасное редактирование сообщения через контекст бота."""
    try:
        # Определяем chat_id заранее
        chat_id = None
        message_id = None
        
        if update.callback_query and update.callback_query.message:
            chat_id = update.callback_query.message.chat.id
            message_id = update.callback_query.message.message_id
        elif update.effective_chat:
            chat_id = update.effective_chat.id
        elif update.message and update.message.chat:
            chat_id = update.message.chat.id
            
        if not chat_id:
            logger.error(f"Не удалось определить chat_id для отправки сообщения. Update: {update}")
            logger.error(f"Callback query: {update.callback_query}")
            logger.error(f"Effective chat: {update.effective_chat}")
            logger.error(f"Message: {update.message}")
            return
            
        # Пытаемся отредактировать существующее сообщение если есть message_id
        if message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                return
            except Exception as edit_error:
                logger.debug(f"Не удалось отредактировать сообщение: {edit_error}")
                # Fallback к отправке нового сообщения
        
        # Отправляем новое сообщение
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Критическая ошибка в _safe_edit_message: {e}")
        # Последняя попытка через effective_user если есть
        try:
            if update.effective_user:
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text=f"⚠️ Ошибка админки: {text[:100]}..."
                )
        except:
            logger.error("Не удалось отправить даже fallback сообщение")


async def admin_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик административных команд.
    
    Args:
        update: Обновление от Telegram
        context: Контекст бота
    """
    try:
        # Получаем данные пользователя
        user = update.effective_user
        message_text = update.message.text
        
        if not user:
            logger.error("Не удалось получить данные пользователя")
            return
        
        # Проверяем, является ли пользователь администратором
        admin_ids = [1670311707]  # Ваш Telegram ID для тестирования
        
        if user.id not in admin_ids:
            await update.message.reply_text(
                "❌ У вас нет прав для выполнения административных команд."
            )
            return
        
        # Разбираем команду
        parts = message_text.split()
        if len(parts) < 2:
            # Показываем админ-панель с кнопками
            await _show_admin_panel(update, context)
            return
        
        command = parts[1]
        args = parts[2:] if len(parts) > 2 else []
        
        # Получаем сессию базы данных
        async for session in get_database():
            user_service = UserService(session)
            payment_service = PaymentService(session)
            reminder_service = ReminderService(session)
            analytics_service = AnalyticsService(session)
            product_service = ProductService(session)
            
            if command == "stats":
                await _handle_stats_command(update, context, user_service, payment_service)
            
            elif command == "users":
                await _handle_users_command(update, context, user_service, args)
            
            elif command == "payments":
                await _handle_payments_command(update, context, payment_service, args)
            
            elif command == "reminders":
                await _handle_reminders_command(update, context, reminder_service)
            
            elif command == "activity":
                await _handle_activity_command(update, context, user_service)
            
            elif command == "settings":
                await _handle_settings_command(update, context)
            
            else:
                await update.message.reply_text(
                    f"❌ Неизвестная команда: {command}\n"
                    "Доступные команды: stats, users, payments, reminders, activity, settings"
                )
            
            break  # Выходим после первой сессии
            
    except Exception as e:
        logger.error(f"Ошибка в админ обработчике: {e}")
        await update.message.reply_text("❌ Произошла ошибка при выполнении команды")


async def _show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    """Показ админ-панели с кнопками."""
    try:
        message_text = (
            "🔧 <b>Полная Админ-панель</b>\n\n"
            "💼 <b>Управление всеми функциями бота:</b>\n"
            "👥 Пользователи • 💳 Платежи • 📊 Аналитика\n"
            "🕘 Ритуалы • 📝 Контент (+ Трипвайеры)\n"
            "📢 Рассылки • ⚙️ Настройки • 🚀 Система"
        )
        
        keyboard = [
            # Основное управление
            [InlineKeyboardButton("👥 Управление пользователями", callback_data="admin_users_manage")],
            [InlineKeyboardButton("💳 Управление платежами", callback_data="admin_payments_manage")],
            
            # Контент и функции
            [InlineKeyboardButton("📝 Управление контентом", callback_data="admin_content_manage")],
            [InlineKeyboardButton("🕘 Управление ритуалами", callback_data="admin_rituals_manage")],
            
            # Аналитика и отчеты
            [InlineKeyboardButton("📊 Подробная аналитика", callback_data="admin_analytics")],
            [InlineKeyboardButton("📈 Активность в чатах", callback_data="admin_activity")],
            
            # Системные функции
            [InlineKeyboardButton("📢 Массовые рассылки", callback_data="admin_broadcast")],
            [InlineKeyboardButton("⚙️ Системные настройки", callback_data="admin_system_settings")],
            
            # Быстрые действия
            [InlineKeyboardButton("🔄 Перезапуск задач", callback_data="admin_restart_tasks"),
             InlineKeyboardButton("📋 Логи", callback_data="admin_logs")],
            
            # Старые функции (совместимость)
            [InlineKeyboardButton("📊 Базовая статистика", callback_data="admin_stats")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка показа админ-панели: {e}")
        error_text = "❌ Ошибка загрузки админ-панели"
        await _safe_edit_message(update, context, error_text)


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик callback'ов админ-панели."""
    try:
        query = update.callback_query
        user = query.from_user
        
        logger.info(f"🔍 Получен admin callback: {query.data}")
        
        # Проверяем права администратора
        admin_ids = [1670311707]  # Ваш Telegram ID для тестирования
        
        if user.id not in admin_ids:
            await context.bot.answer_callback_query(query.id, "❌ У вас нет прав администратора")
            return
        
        # Пытаемся ответить на callback, но игнорируем ошибки истечения времени
        try:
            await context.bot.answer_callback_query(query.id)
        except Exception as callback_error:
            # Игнорируем ошибки истечения времени callback'а
            if "too old" in str(callback_error) or "timeout" in str(callback_error):
                logger.debug(f"Callback запрос истек: {callback_error}")
            else:
                logger.warning(f"Ошибка ответа на callback: {callback_error}")
        
        # Получаем сессию базы данных
        async for session in get_database():
            user_service = UserService(session)
            payment_service = PaymentService(session)
            reminder_service = ReminderService(session)
            product_service = ProductService(session)
            
            # Основные функции (совместимость)
            if query.data == "admin_stats":
                await _handle_stats_command(update, context, user_service, payment_service, is_callback=True)
            elif query.data == "admin_activity":
                await _handle_activity_command(update, context, user_service, is_callback=True)
            elif query.data == "admin_back":
                await _show_admin_panel(update, context, is_callback=True)
            
            # Новое управление пользователями
            elif query.data == "admin_users_manage":
                await _handle_users_management(update, context, user_service, is_callback=True)
            elif query.data.startswith("admin_user_list_page_"):
                page = int(query.data.replace("admin_user_list_page_", ""))
                await _handle_list_all_users(update, context, user_service, is_callback=True, page=page)
            elif query.data.startswith("admin_user_"):
                await _handle_user_action(update, context, user_service, query.data, is_callback=True)
            
            # Новое управление платежами
            elif query.data == "admin_payments_manage":
                await _handle_payments_management(update, context, payment_service, is_callback=True)
            elif query.data.startswith("admin_payment_"):
                await _handle_payment_action(update, context, payment_service, query.data, is_callback=True)
            
            # Управление контентом
            elif query.data == "admin_content_manage":
                await _handle_content_management(update, context, is_callback=True)
            elif query.data.startswith("admin_content_"):
                if query.data == "admin_content_tripwires":
                    await _handle_tripwire_management(update, context, product_service, is_callback=True)
                elif query.data == "admin_content_leadmagnets":
                    await _handle_lead_magnets_management(update, context, is_callback=True)
                elif query.data == "admin_content_warmup":
                    await _handle_warmup_management(update, context, is_callback=True)
                elif query.data == "admin_content_messages":
                    await _handle_messages_management(update, context, is_callback=True)
                else:
                    await _handle_content_action(update, context, query.data, is_callback=True)
            
            # Управление текстовыми шаблонами
            elif query.data.startswith("admin_messages_"):
                await _handle_messages_action(update, context, query.data, is_callback=True)
            
            # Управление трипвайерами
            elif query.data == "admin_tripwire_manage":
                await _handle_tripwire_management(update, context, product_service, is_callback=True)
            elif (query.data.startswith("admin_tripwire_") or 
                  query.data.startswith("admin_tp_") or 
                  query.data.startswith("admin_to_") or 
                  query.data.startswith("admin_create_")):
                logger.info(f"🎯 Направляем в _handle_tripwire_action: {query.data}")
                await _handle_tripwire_action(update, context, product_service, query.data, is_callback=True)
            
            # Управление лид магнитами
            elif query.data.startswith("admin_lead_magnet_"):
                await _handle_lead_magnet_action(update, context, query.data, is_callback=True)
            
            # Управление сценариями прогрева
            elif query.data.startswith("admin_warmup_"):
                await _handle_warmup_action(update, context, query.data, is_callback=True)
            
            # Управление ритуалами
            elif query.data == "admin_rituals_manage":
                await _handle_rituals_management(update, context, is_callback=True)
            elif query.data.startswith("admin_ritual_"):
                await _handle_ritual_action(update, context, query.data, is_callback=True)
            
            # Аналитика
            elif query.data == "admin_analytics":
                await _handle_analytics_dashboard(update, context, user_service, payment_service, is_callback=True)
            
            # Системные функции
            elif query.data == "admin_broadcast":
                await _handle_broadcast_system(update, context, is_callback=True)
            elif query.data == "admin_system_settings":
                await _handle_system_settings(update, context, is_callback=True)
            elif query.data == "admin_restart_tasks":
                await _handle_restart_tasks(update, context, is_callback=True)
            elif query.data == "admin_logs":
                await _handle_logs_view(update, context, is_callback=True)
            
            else:
                await _safe_edit_message(update, context, "❌ Неизвестная команда")
            
            break  # Выходим после первой сессии
        
    except Exception as e:
        logger.error(f"Ошибка обработки админского callback: {e}")
        try:
            # Пытаемся ответить на callback только если ошибка не связана с истечением времени
            if "too old" not in str(e) and "timeout" not in str(e):
                await context.bot.answer_callback_query(query.id, "❌ Произошла ошибка")
        except Exception as callback_error:
            # Полностью игнорируем ошибки callback'ов в обработчике ошибок
            logger.debug(f"Не удалось ответить на callback в обработчике ошибок: {callback_error}")


async def _handle_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               user_service: UserService, payment_service: PaymentService, 
                               is_callback: bool = False) -> None:
    """Обработка команды статистики."""
    try:
        # Получаем статистику пользователей
        total_users = await user_service.get_users_count()
        active_users = await user_service.get_active_users_count()
        
        # Получаем статистику платежей
        total_payments = await payment_service.get_payments_count()
        total_revenue = await payment_service.get_total_revenue()
        
        stats_text = (
            f"📊 <b>Статистика бота</b>\n\n"
            f"👥 <b>Пользователи:</b>\n"
            f"• Всего: {total_users}\n"
            f"• Активных: {active_users}\n\n"
            f"💳 <b>Платежи:</b>\n"
            f"• Всего транзакций: {total_payments}\n"
            f"• Общий доход: {total_revenue} ₽\n\n"
            f"📈 <b>Конверсия:</b> {(active_users/max(total_users, 1)*100):.1f}%"
        )
        
        # Кнопка "Назад"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await _safe_edit_message(update, context, stats_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        error_text = "❌ Ошибка получения статистики"
        await _safe_edit_message(update, context, error_text)


async def _handle_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               user_service: UserService, args: list, is_callback: bool = False) -> None:
    """Обработка команды управления пользователями."""
    try:
        users = await user_service.get_recent_users(limit=10)
        
        if not users:
            users_text = "👥 <b>Пользователи</b>\n\n❌ Пользователи не найдены"
        else:
            users_text = "👥 <b>Последние пользователи:</b>\n\n"
            for i, user in enumerate(users, 1):
                status_emoji = "✅" if user.status == "active" else "⏸️"
                users_text += (
                    f"{i}. {status_emoji} {user.display_name}\n"
                    f"   ID: {user.telegram_id}\n"
                    f"   Статус: {user.status}\n\n"
                )
        
        # Кнопка "Назад"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await _safe_edit_message(update, context, users_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка получения пользователей: {e}")
        error_text = "❌ Ошибка получения списка пользователей"
        await _safe_edit_message(update, context, error_text)


async def _handle_payments_command(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                  payment_service: PaymentService, args: list, is_callback: bool = False) -> None:
    """Обработка команды управления платежами."""
    try:
        payments = await payment_service.get_recent_payments(limit=5)
        
        if not payments:
            payments_text = "💳 <b>Платежи</b>\n\n❌ Платежи не найдены"
        else:
            payments_text = "💳 <b>Последние платежи:</b>\n\n"
            for i, payment in enumerate(payments, 1):
                status_emoji = "✅" if payment.status == "completed" else "⏳"
                payments_text += (
                    f"{i}. {status_emoji} {payment.amount} {payment.currency}\n"
                    f"   От: {payment.user.display_name if payment.user else 'N/A'}\n"
                    f"   Дата: {payment.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                )
        
        # Кнопка "Назад"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await _safe_edit_message(update, context, payments_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка получения платежей: {e}")
        error_text = "❌ Ошибка получения списка платежей"
        await _safe_edit_message(update, context, error_text)


async def _handle_reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   reminder_service: ReminderService, is_callback: bool = False) -> None:
    """Обработка команды управления напоминаниями."""
    try:
        # Получаем статистику напоминаний
        enabled_count = await reminder_service.get_enabled_reminders_count()
        
        reminders_text = (
            f"⏰ <b>Напоминания</b>\n\n"
            f"• Активных напоминаний: {enabled_count}\n"
            f"• Следующая отправка: в течение часа\n\n"
            f"Напоминания отправляются автоматически\n"
            f"в зависимости от настроек пользователей."
        )
        
        # Кнопка "Назад"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await _safe_edit_message(update, context, reminders_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка получения напоминаний: {e}")
        error_text = "❌ Ошибка получения информации о напоминаниях"
        await _safe_edit_message(update, context, error_text)


async def _handle_activity_command(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                  user_service: UserService, is_callback: bool = False) -> None:
    """Обработка команды анализа активности."""
    try:
        # Получаем базовую статистику активности
        total_users = await user_service.get_users_count()
        active_users = await user_service.get_active_users_count()
        
        activity_text = (
            f"📈 <b>Анализ активности</b>\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"✅ Активных: {active_users}\n"
            f"📊 Процент активности: {(active_users/max(total_users, 1)*100):.1f}%\n\n"
            f"📋 <b>Система отслеживания:</b>\n"
            f"• Активность в чатах\n"
            f"• Еженедельные отчеты\n"
            f"• Топ пользователей\n\n"
            f"Полная статистика доступна в базе данных."
        )
        
        # Кнопка "Назад"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await _safe_edit_message(update, context, activity_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка анализа активности: {e}")
        error_text = "❌ Ошибка получения данных активности"
        await _safe_edit_message(update, context, error_text)


async def _handle_settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    """Обработка команды настроек."""
    try:
        from config.settings import settings
        
        settings_text = (
            f"⚙️ <b>Настройки бота</b>\n\n"
            f"🤖 <b>Основные:</b>\n"
            f"• Режим отладки: {'Включен' if settings.debug else 'Выключен'}\n"
            f"• Группа: {settings.telegram_group_id}\n\n"
            f"💳 <b>Платежи:</b>\n"
            f"• Валюта: {settings.payment_currency}\n"
            f"• Стандартная сумма: {settings.payment_amount}\n\n"
            f"📊 <b>Функции:</b>\n"
            f"• ✅ Система ритуалов ЯДРА\n"
            f"• ✅ Отслеживание активности\n"
            f"• ✅ Система прогрева\n"
            f"• ✅ Трипвайеры и продажи\n"
            f"• ✅ Еженедельные отчеты"
        )
        
        # Кнопка "Назад"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await _safe_edit_message(update, context, settings_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка получения настроек: {e}")
        error_text = "❌ Ошибка получения настроек"
        await _safe_edit_message(update, context, error_text)


async def _handle_users_management(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   user_service: UserService, is_callback: bool = False) -> None:
    """Управление пользователями."""
    try:
        users = await user_service.get_recent_users(limit=5)
        total_users = await user_service.get_users_count()
        active_users = await user_service.get_active_users_count()
        
        users_text = (
            f"👥 <b>Управление пользователями</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Всего: {total_users}\n"
            f"• Активных: {active_users}\n"
            f"• Неактивных: {total_users - active_users}\n\n"
            f"👤 <b>Последние пользователи:</b>\n"
        )
        
        keyboard = []
        
        for i, user in enumerate(users, 1):
            status_emoji = "✅" if user.status == "active" else "⏸️"
            users_text += f"{i}. {status_emoji} {user.display_name} (ID: {user.telegram_id})\n"
            
            # Добавляем кнопки управления для каждого пользователя
            keyboard.append([
                InlineKeyboardButton(f"👤 {user.display_name[:15]}...", 
                                   callback_data=f"admin_user_view_{user.id}"),
                InlineKeyboardButton("✏️", callback_data=f"admin_user_edit_{user.id}"),
                InlineKeyboardButton("🗑️", callback_data=f"admin_user_delete_{user.id}")
            ])
        
        # Добавляем функциональные кнопки
        keyboard.extend([
            [InlineKeyboardButton("➕ Добавить пользователя", callback_data="admin_user_add")],
            [InlineKeyboardButton("📋 Все пользователи", callback_data="admin_user_list_all"),
             InlineKeyboardButton("🔍 Поиск", callback_data="admin_user_search")],
            [InlineKeyboardButton("📊 Детальная статистика", callback_data="admin_user_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, users_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка управления пользователями: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки управления пользователями")


async def _handle_payments_management(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     payment_service: PaymentService, is_callback: bool = False) -> None:
    """Управление платежами."""
    try:
        payments = await payment_service.get_recent_payments(limit=5)
        total_payments = await payment_service.get_payments_count()
        total_revenue = await payment_service.get_total_revenue()
        
        payments_text = (
            f"💳 <b>Управление платежами</b>\n\n"
            f"💰 <b>Финансовая сводка:</b>\n"
            f"• Всего платежей: {total_payments}\n"
            f"• Общий доход: {total_revenue:.2f} ₽\n"
            f"• Средний чек: {(total_revenue/max(total_payments, 1)):.2f} ₽\n\n"
            f"💳 <b>Последние платежи:</b>\n"
        )
        
        keyboard = []
        
        for i, payment in enumerate(payments, 1):
            status_emoji = "✅" if payment.status == "paid" else "⏳"
            payments_text += (
                f"{i}. {status_emoji} {payment.amount} {payment.currency} "
                f"({payment.created_at.strftime('%d.%m %H:%M')})\n"
            )
            
            keyboard.append([
                InlineKeyboardButton(f"💳 {payment.amount} {payment.currency}", 
                                   callback_data=f"admin_payment_view_{payment.id}"),
                InlineKeyboardButton("✏️", callback_data=f"admin_payment_edit_{payment.id}"),
                InlineKeyboardButton("❌", callback_data=f"admin_payment_cancel_{payment.id}")
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("➕ Создать платеж", callback_data="admin_payment_create")],
            [InlineKeyboardButton("📊 Аналитика платежей", callback_data="admin_payment_analytics")],
            [InlineKeyboardButton("💰 Финансовый отчет", callback_data="admin_payment_report")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, payments_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка управления платежами: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки управления платежами")


async def _handle_content_management(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    """Управление контентом."""
    try:
        content_text = (
            f"📝 <b>Управление контентом</b>\n\n"
            f"🎁 <b>Лид-магниты:</b>\n"
            f"• Активных: 1 (7-дневный трекер)\n"
            f"• Скачиваний: 245\n\n"
            f"🔥 <b>Сценарии прогрева:</b>\n"
            f"• Активных: 1 (основной сценарий)\n"
            f"• Сообщений: 5\n"
            f"• Конверсия: 23.4%\n\n"
            f"🎯 <b>Трипвайеры:</b>\n"
            f"• Активных: 1 (30 дней по Хиллу)\n"
            f"• Цена: 990 ₽\n"
            f"• Продаж: 12\n\n"
            f"📋 <b>Выберите категорию для управления:</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎁 Лид-магниты", callback_data="admin_content_leadmagnets")],
            [InlineKeyboardButton("🔥 Сценарии прогрева", callback_data="admin_content_warmup")],
            [InlineKeyboardButton("🎯 Трипвайеры", callback_data="admin_content_tripwires")],
            [InlineKeyboardButton("📝 Тексты сообщений", callback_data="admin_content_messages")],
            [InlineKeyboardButton("🎨 Медиа файлы", callback_data="admin_content_media")],
            [InlineKeyboardButton("📊 Статистика контента", callback_data="admin_content_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, content_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка управления контентом: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки управления контентом")


async def _handle_lead_magnets_management(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    """Управление лид магнитами."""
    try:
        async for session in get_database():
            lead_magnet_service = LeadMagnetService(session)
            
            # Получаем статистику лид магнитов
            stats = await lead_magnet_service.get_lead_magnet_stats()
            
            message_text = (
                f"📚 <b>Управление лид магнитами</b>\n\n"
                f"📊 <b>Статистика:</b>\n"
                f"• Всего выдано: {stats.get('total_issued', 0)}\n"
                f"• Уникальных пользователей: {stats.get('unique_users', 0)}\n"
                f"• Активных лид магнитов: {stats.get('active_lead_magnets', 0)}\n\n"
                f"🎁 <b>Доступные подарки:</b>\n"
            )
            
            # Получаем активные лид магниты
            active_magnets = await lead_magnet_service.get_active_lead_magnets()
            
            if active_magnets:
                for magnet in active_magnets[:3]:  # Показываем первые 3
                    status = "🟢" if magnet.is_active else "🔴"
                    type_icon = {
                        "pdf": "📄",
                        "google_sheet": "📊", 
                        "link": "🔗",
                        "text": "📝"
                    }.get(magnet.type, "📁")
                    
                    message_text += f"{status} {type_icon} {magnet.name}\n"
                    message_text += f"   📝 {magnet.description[:50]}...\n\n"
            else:
                message_text += "📭 Активных лид магнитов не найдено\n\n"
            
            message_text += "💡 <b>Команда для пользователей:</b> /gift"
            
            keyboard = [
                # Управление лид магнитами
                [InlineKeyboardButton("➕ Создать лид магнит", callback_data="admin_lead_magnet_create")],
                [InlineKeyboardButton("📋 Список всех", callback_data="admin_lead_magnet_list")],
                [InlineKeyboardButton("📊 Детальная статистика", callback_data="admin_lead_magnet_stats")],
                [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_lead_magnet_settings")],
                
                # Общие функции
                [InlineKeyboardButton("🔄 Обновить", callback_data="admin_content_leadmagnets")],
                [InlineKeyboardButton("🔙 К управлению контентом", callback_data="admin_content_manage")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await _safe_edit_message(update, context, message_text, reply_markup)
            
    except Exception as e:
        logger.error(f"Ошибка управления лид магнитами: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки управления лид магнитами")


async def _handle_lead_magnet_action(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   action: str, is_callback: bool = False) -> None:
    """Обработка действий с лид магнитами."""
    try:
        async for session in get_database():
            lead_magnet_service = LeadMagnetService(session)
            
            if action == "admin_lead_magnet_create":
                await _handle_lead_magnet_create_form(update, context, lead_magnet_service, is_callback=True)
            elif action == "admin_lead_magnet_list":
                await _handle_lead_magnet_list(update, context, lead_magnet_service, is_callback=True)
            elif action == "admin_lead_magnet_stats":
                await _handle_lead_magnet_detailed_stats(update, context, lead_magnet_service, is_callback=True)
            elif action == "admin_lead_magnet_settings":
                await _handle_lead_magnet_settings(update, context, lead_magnet_service, is_callback=True)
            elif action.startswith("admin_lead_magnet_create_type_"):
                await _handle_lead_magnet_create_type_selection(update, context, action, lead_magnet_service, is_callback=True)
            elif action == "admin_lead_magnet_create_name":
                await _handle_lead_magnet_create_name_step(update, context, lead_magnet_service, is_callback=True)
            elif action == "admin_lead_magnet_create_description":
                await _handle_lead_magnet_create_description_step(update, context, lead_magnet_service, is_callback=True)
            elif action == "admin_lead_magnet_create_file_url":
                await _handle_lead_magnet_create_file_url_step(update, context, lead_magnet_service, is_callback=True)
            elif action == "admin_lead_magnet_create_message":
                await _handle_lead_magnet_create_message_step(update, context, lead_magnet_service, is_callback=True)
            elif action == "admin_lead_magnet_create_confirm":
                await _handle_lead_magnet_create_confirm(update, context, lead_magnet_service, is_callback=True)
            elif action == "admin_lead_magnet_create_final":
                await _handle_lead_magnet_create_final(update, context, lead_magnet_service, is_callback=True)
            else:
                await _safe_edit_message(update, context, f"🔧 Функция '{action}' в разработке...")
                
    except Exception as e:
        logger.error(f"Ошибка обработки действий с лид магнитами {action}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка выполнения действия с лид магнитами")


async def _handle_warmup_management(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    """Управление сценариями прогрева."""
    try:
        async for session in get_database():
            warmup_service = WarmupService(session)
            
            # Получаем активный сценарий
            active_scenario = await warmup_service.get_active_scenario()
            
            # Получаем статистику
            total_scenarios = await warmup_service.get_all_scenarios()
            active_users = await warmup_service.get_active_warmup_users()
            
            message_text = (
                f"🔥 <b>Управление сценариями прогрева</b>\n\n"
                f"📊 <b>Статистика:</b>\n"
                f"• Всего сценариев: {len(total_scenarios)}\n"
                f"• Активных пользователей: {len(active_users)}\n"
                f"• Активный сценарий: {active_scenario.name if active_scenario else 'Не установлен'}\n\n"
            )
            
            if active_scenario:
                message_text += (
                    f"🎯 <b>Текущий активный сценарий:</b>\n"
                    f"• Название: {active_scenario.name}\n"
                    f"• Описание: {active_scenario.description[:100] if active_scenario.description else 'Не указано'}...\n"
                    f"• Сообщений: {len(active_scenario.messages)}\n\n"
                )
            else:
                message_text += "⚠️ <b>Активный сценарий не установлен!</b>\n\n"
            
            message_text += "💡 <b>Система прогрева автоматически отправляет последовательность сообщений новым пользователям</b>"
            
            keyboard = [
                # Управление сценариями
                [InlineKeyboardButton("➕ Создать сценарий", callback_data="admin_warmup_create_scenario")],
                [InlineKeyboardButton("📋 Список сценариев", callback_data="admin_warmup_list_scenarios")],
                [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_warmup_settings")],
                
                # Управление сообщениями
                [InlineKeyboardButton("💬 Управление сообщениями", callback_data="admin_warmup_messages")],
                [InlineKeyboardButton("👥 Пользователи в прогреве", callback_data="admin_warmup_users")],
                
                # Статистика и мониторинг
                [InlineKeyboardButton("📊 Статистика", callback_data="admin_warmup_stats")],
                [InlineKeyboardButton("🔄 Обновить", callback_data="admin_content_warmup")],
                [InlineKeyboardButton("🔙 К управлению контентом", callback_data="admin_content_manage")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await _safe_edit_message(update, context, message_text, reply_markup)
            
    except Exception as e:
        logger.error(f"Ошибка управления сценариями прогрева: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки управления сценариями прогрева")


async def _handle_warmup_action(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               action: str, is_callback: bool = False) -> None:
    """Обработка действий с сценариями прогрева."""
    try:
        async for session in get_database():
            warmup_service = WarmupService(session)
            
            if action == "admin_warmup_create_scenario":
                await _handle_warmup_create_scenario_form(update, context, warmup_service, is_callback=True)
            elif action == "admin_warmup_create_scenario_final":
                await _handle_warmup_create_scenario_final(update, context, warmup_service, is_callback=True)
            elif action == "admin_warmup_list_scenarios":
                await _handle_warmup_list_scenarios(update, context, warmup_service, is_callback=True)
            elif action == "admin_warmup_settings":
                await _handle_warmup_settings(update, context, warmup_service, is_callback=True)
            elif action == "admin_warmup_messages":
                await _handle_warmup_messages_management(update, context, warmup_service, is_callback=True)
            elif action == "admin_warmup_users":
                await _handle_warmup_users_list(update, context, warmup_service, is_callback=True)
            elif action == "admin_warmup_stats":
                await _handle_warmup_stats(update, context, warmup_service, is_callback=True)
            elif action.startswith("admin_warmup_scenario_"):
                await _handle_warmup_scenario_edit(update, context, warmup_service, action, is_callback=True)
            elif action.startswith("admin_warmup_edit_"):
                await _handle_warmup_edit_action(update, context, warmup_service, action, is_callback=True)
            elif action.startswith("admin_warmup_toggle_status_"):
                await _handle_warmup_toggle_status(update, context, warmup_service, action, is_callback=True)
            elif action.startswith("admin_warmup_delete_confirm_"):
                await _handle_warmup_delete_confirm(update, context, warmup_service, action, is_callback=True)
            elif action.startswith("admin_warmup_edit_name_confirm_"):
                await _handle_warmup_edit_name_confirm(update, context, warmup_service, action, is_callback=True)
            elif action.startswith("admin_warmup_edit_desc_confirm_"):
                await _handle_warmup_edit_desc_confirm(update, context, warmup_service, action, is_callback=True)
            else:
                await _safe_edit_message(update, context, f"🔧 Функция '{action}' в разработке...")
                
    except Exception as e:
        logger.error(f"Ошибка обработки действий с сценариями прогрева {action}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка выполнения действия с сценариями прогрева")


async def _handle_warmup_create_scenario_form(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                            warmup_service: "WarmupService", is_callback: bool = False) -> None:
    """Форма создания сценария прогрева."""
    try:
        message_text = (
            "🔥 <b>Создание нового сценария прогрева</b>\n\n"
            "📝 <b>Введите название сценария:</b>\n\n"
            "💡 <b>Советы:</b>\n"
            "• Название должно быть понятным и описательным\n"
            "• Например: 'Базовый прогрев', 'Прогрев для новичков'\n"
            "• После создания сценария вы сможете добавить сообщения"
        )
        
        # Сохраняем состояние создания
        context.user_data['creating_warmup_scenario'] = {
            'step': 'name'
        }
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_warmup")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка создания формы сценария: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка создания формы сценария")


async def _handle_warmup_list_scenarios(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                      warmup_service: "WarmupService", is_callback: bool = False) -> None:
    """Список всех сценариев прогрева."""
    try:
        # Получаем все сценарии
        all_scenarios = await warmup_service.get_all_scenarios()
        
        if not all_scenarios:
            message_text = "📭 Сценарии прогрева не найдены\n\nНажмите 'Создать сценарий' для добавления первого."
            keyboard = [
                [InlineKeyboardButton("➕ Создать сценарий", callback_data="admin_warmup_create_scenario")],
                [InlineKeyboardButton("🔙 К управлению прогрева", callback_data="admin_content_warmup")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await _safe_edit_message(update, context, message_text, reply_markup)
            return
        
        message_text = "📋 <b>Все сценарии прогрева</b>\n\n"
        
        for i, scenario in enumerate(all_scenarios, 1):
            status = "🟢" if scenario.is_active else "🔴"
            message_text += f"{i}. {status} <b>{scenario.name}</b>\n"
            if scenario.description:
                message_text += f"   📝 {scenario.description[:60]}...\n"
            message_text += f"   💬 Сообщений: {len(scenario.messages)}\n"
            message_text += f"   📅 Создан: {scenario.created_at.strftime('%d.%m.%Y')}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Создать новый", callback_data="admin_warmup_create_scenario")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_warmup_list_scenarios")],
            [InlineKeyboardButton("🔙 К управлению прогрева", callback_data="admin_content_warmup")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки списка сценариев: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки списка сценариев")


async def _handle_warmup_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                warmup_service: "WarmupService", is_callback: bool = False) -> None:
    """Настройки сценариев прогрева."""
    try:
        # Получаем все сценарии
        all_scenarios = await warmup_service.get_all_scenarios()
        active_count = sum(1 for s in all_scenarios if s.is_active)
        inactive_count = len(all_scenarios) - active_count
        
        message_text = (
            f"⚙️ <b>Настройки сценариев прогрева</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Всего сценариев: {len(all_scenarios)}\n"
            f"• Активных: {active_count}\n"
            f"• Неактивных: {inactive_count}\n\n"
            f"💡 <b>Важно:</b> Только один сценарий может быть активным одновременно\n\n"
            f"🔧 <b>Доступные действия:</b>"
        )
        
        keyboard = [
            # Управление активностью
            [InlineKeyboardButton("🔄 Активировать другой сценарий", callback_data="admin_warmup_activate")],
            [InlineKeyboardButton("⏸️ Остановить все прогревы", callback_data="admin_warmup_stop_all")],
            [InlineKeyboardButton("▶️ Возобновить прогревы", callback_data="admin_warmup_resume")],
            
            # Настройки
            [InlineKeyboardButton("⏰ Настройка времени", callback_data="admin_warmup_time_settings")],
            [InlineKeyboardButton("📧 Шаблоны сообщений", callback_data="admin_warmup_templates")],
            
            # Общие функции
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_warmup_settings")],
            [InlineKeyboardButton("🔙 К управлению прогрева", callback_data="admin_content_warmup")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки настроек прогрева: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки настроек прогрева")


async def _handle_warmup_messages_management(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                           warmup_service: "WarmupService", is_callback: bool = False) -> None:
    """Управление сообщениями прогрева."""
    try:
        # Получаем все сценарии
        all_scenarios = await warmup_service.get_all_scenarios()
        
        if not all_scenarios:
            message_text = "📭 Сценарии прогрева не найдены\n\nСначала создайте сценарий."
            keyboard = [
                [InlineKeyboardButton("➕ Создать сценарий", callback_data="admin_warmup_create_scenario")],
                [InlineKeyboardButton("🔙 К управлению прогрева", callback_data="admin_content_warmup")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await _safe_edit_message(update, context, message_text, reply_markup)
            return
        
        message_text = "💬 <b>Управление сообщениями прогрева</b>\n\n"
        message_text += "📋 <b>Выберите сценарий для управления сообщениями:</b>\n\n"
        
        for i, scenario in enumerate(all_scenarios, 1):
            status = "🟢" if scenario.is_active else "🔴"
            message_text += f"{i}. {status} <b>{scenario.name}</b>\n"
            message_text += f"   💬 Сообщений: {len(scenario.messages)}\n\n"
        
        keyboard = []
        
        # Кнопки для каждого сценария
        for i, scenario in enumerate(all_scenarios, 1):
            short_id = str(scenario.id).replace('-', '')[:16]
            keyboard.append([
                InlineKeyboardButton(
                    f"📝 {scenario.name}", 
                    callback_data=f"admin_warmup_scenario_{short_id}"
                )
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("➕ Создать сценарий", callback_data="admin_warmup_create_scenario")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_warmup_messages")],
            [InlineKeyboardButton("🔙 К управлению прогрева", callback_data="admin_content_warmup")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка управления сообщениями прогрева: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка управления сообщениями прогрева")


async def _handle_warmup_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  warmup_service: "WarmupService", is_callback: bool = False) -> None:
    """Список пользователей в прогреве."""
    try:
        # Получаем активных пользователей
        active_users = await warmup_service.get_active_warmup_users()
        
        if not active_users:
            message_text = "👥 <b>Пользователи в прогреве</b>\n\n📭 Активных прогрева не найдено"
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="admin_warmup_users")],
                [InlineKeyboardButton("🔙 К управлению прогрева", callback_data="admin_content_warmup")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await _safe_edit_message(update, context, message_text, reply_markup)
            return
        
        message_text = f"👥 <b>Пользователи в прогреве</b>\n\n📊 <b>Всего активных: {len(active_users)}</b>\n\n"
        
        # Показываем первые 10 пользователей
        for i, user_warmup in enumerate(active_users[:10], 1):
            user = user_warmup.user
            scenario = user_warmup.scenario
            
            # Проверяем, что user и scenario существуют
            if not user:
                message_text += f"{i}. 👤 <b>Пользователь не найден (ID: {user_warmup.user_id})</b>\n"
                message_text += f"   🎯 Сценарий: {scenario.name if scenario else 'Не найден'}\n"
                message_text += f"   📍 Шаг: {user_warmup.current_step + 1}\n"
                message_text += f"   🕐 Начат: {user_warmup.started_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                continue
                
            if not scenario:
                message_text += f"{i}. 👤 <b>{user.first_name or 'Пользователь'}</b>\n"
                message_text += f"   📱 @{user.username or 'без username'}\n"
                message_text += f"   🎯 Сценарий: <i>Сценарий не найден</i>\n"
                message_text += f"   📍 Шаг: {user_warmup.current_step + 1}\n"
                message_text += f"   🕐 Начат: {user_warmup.started_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                continue
            
            message_text += f"{i}. 👤 <b>{user.first_name or 'Пользователь'}</b>\n"
            message_text += f"   📱 @{user.username or 'без username'}\n"
            message_text += f"   🎯 Сценарий: {scenario.name}\n"
            message_text += f"   📍 Шаг: {user_warmup.current_step + 1}\n"
            message_text += f"   🕐 Начат: {user_warmup.started_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        if len(active_users) > 10:
            message_text += f"... и еще {len(active_users) - 10} пользователей\n\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Экспорт данных", callback_data="admin_warmup_export_users")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_warmup_users")],
            [InlineKeyboardButton("🔙 К управлению прогрева", callback_data="admin_content_warmup")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки пользователей прогрева: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки пользователей прогрева")


async def _handle_warmup_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                             warmup_service: "WarmupService", is_callback: bool = False) -> None:
    """Статистика прогрева."""
    try:
        # Получаем статистику
        stats = await warmup_service.get_warmup_stats()
        
        message_text = "📊 <b>Статистика прогрева</b>\n\n"
        
        message_text += f"📈 <b>Общие показатели:</b>\n"
        message_text += f"• Всего сценариев: {stats.get('total_scenarios', 0)}\n"
        message_text += f"• Активных сценариев: {stats.get('active_scenarios', 0)}\n"
        message_text += f"• Всего сообщений: {stats.get('total_messages', 0)}\n"
        message_text += f"• Активных пользователей: {stats.get('active_users', 0)}\n\n"
        
        # Статистика по типам сообщений
        message_types = stats.get('message_types', {})
        if message_types:
            message_text += f"📊 <b>Типы сообщений:</b>\n"
            for msg_type, count in message_types.items():
                type_names = {
                    'welcome': '👋 Приветствие',
                    'pain_point': '💔 Болевая точка',
                    'solution': '💡 Решение',
                    'social_proof': '🌟 Социальное доказательство',
                    'offer': '🎯 Предложение',
                    'follow_up': '📧 Дополнительно'
                }
                display_name = type_names.get(msg_type, msg_type)
                message_text += f"• {display_name}: {count}\n"
            message_text += "\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Детальная статистика", callback_data="admin_warmup_detailed_stats")],
            [InlineKeyboardButton("📈 Графики", callback_data="admin_warmup_charts")],
            [InlineKeyboardButton("📋 Экспорт", callback_data="admin_warmup_export_stats")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_warmup_stats")],
            [InlineKeyboardButton("🔙 К управлению прогрева", callback_data="admin_content_warmup")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки статистики прогрева: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки статистики прогрева")


async def _handle_warmup_create_scenario_final(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                             warmup_service: "WarmupService", is_callback: bool = False) -> None:
    """Финальное создание сценария прогрева."""
    try:
        # Получаем данные создания
        creating_data = context.user_data.get('creating_warmup_scenario', {})
        
        if not creating_data:
            await _safe_edit_message(update, context, "❌ Ошибка: данные создания не найдены")
            return
        
        # Проверяем обязательные поля
        if not creating_data.get('name'):
            await _safe_edit_message(update, context, "❌ Ошибка: название обязательно для заполнения")
            return
        
        # Создаем сценарий
        new_scenario = await warmup_service.create_scenario(
            name=creating_data['name'],
            description=creating_data.get('description')
        )
        
        # Очищаем данные создания
        context.user_data.pop('creating_warmup_scenario', None)
        
        message_text = (
            "✅ <b>Сценарий прогрева успешно создан!</b>\n\n"
            f"📝 <b>Название:</b> {new_scenario.name}\n"
            f"📄 <b>Описание:</b> {new_scenario.description or 'Не указано'}\n"
            f"🆔 <b>ID:</b> {new_scenario.id}\n"
            f"🟢 <b>Статус:</b> Активен\n\n"
            "🎯 <b>Что дальше:</b>\n"
            "• Сценарий автоматически активирован\n"
            "• Теперь вы можете добавить сообщения\n"
            "• Пользователи будут автоматически подключаться к прогреву"
        )
        
        keyboard = [
            [InlineKeyboardButton("💬 Добавить сообщения", callback_data="admin_warmup_messages")],
            [InlineKeyboardButton("📋 К списку сценариев", callback_data="admin_warmup_list_scenarios")],
            [InlineKeyboardButton("➕ Создать еще один", callback_data="admin_warmup_create_scenario")],
            [InlineKeyboardButton("🔙 К управлению прогрева", callback_data="admin_content_warmup")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка создания сценария прогрева: {e}")
        await _safe_edit_message(update, context, f"❌ Ошибка создания сценария прогрева: {str(e)}")


async def _handle_rituals_management(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    """Управление ритуалами."""
    try:
        rituals_text = (
            f"🎯 <b>Управление ритуалами ЯДРА</b>\n\n"
            f"🌅 <b>Утренние ритуалы (6:30):</b>\n"
            f"• Статус: ✅ Активен\n"
            f"• Участников: 15\n"
            f"• Ответов сегодня: 8\n\n"
            f"🌙 <b>Вечерние ритуалы (21:00):</b>\n"
            f"• Статус: ✅ Активен\n"
            f"• Участников: 18\n"
            f"• Отчетов сегодня: 12\n\n"
            f"📅 <b>Еженедельные цели (воскресенье):</b>\n"
            f"• Статус: ✅ Активен\n"
            f"• Целей на этой неделе: 23\n\n"
            f"💪 <b>Личные вызовы (понедельник):</b>\n"
            f"• Статус: ✅ Активен\n"
            f"• Принято вызовов: 16\n\n"
            f"🔄 <b>Циклические ритуалы (пятница):</b>\n"
            f"• Статус: ✅ Активен\n"
            f"• Участников: 14"
        )
        
        keyboard = [
            # Управление конкретными ритуалами
            [InlineKeyboardButton("🌅 Утренние ритуалы", callback_data="admin_ritual_morning")],
            [InlineKeyboardButton("🌙 Вечерние ритуалы", callback_data="admin_ritual_evening")],
            [InlineKeyboardButton("📅 Еженедельные цели", callback_data="admin_ritual_weekly_goals")],
            [InlineKeyboardButton("💪 Личные вызовы", callback_data="admin_ritual_challenges")],
            [InlineKeyboardButton("🔄 Циклические ритуалы", callback_data="admin_ritual_cycles")],
            
            # Общие функции
            [InlineKeyboardButton("⏰ Настройка времени", callback_data="admin_ritual_schedule")],
            [InlineKeyboardButton("📊 Статистика ритуалов", callback_data="admin_ritual_stats")],
            [InlineKeyboardButton("🔧 Глобальные настройки", callback_data="admin_ritual_global")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, rituals_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка управления ритуалами: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки управления ритуалами")


async def _handle_analytics_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     user_service: UserService, payment_service: PaymentService, 
                                     is_callback: bool = False) -> None:
    """Расширенная аналитика."""
    try:
        # Получаем данные
        total_users = await user_service.get_users_count()
        active_users = await user_service.get_active_users_count()
        total_payments = await payment_service.get_payments_count()
        total_revenue = await payment_service.get_total_revenue()
        
        analytics_text = (
            f"📊 <b>Расширенная аналитика</b>\n\n"
            f"👥 <b>Пользователи:</b>\n"
            f"• Всего: {total_users}\n"
            f"• Активных: {active_users} ({(active_users/max(total_users,1)*100):.1f}%)\n"
            f"• Конверсия в активных: {(active_users/max(total_users,1)*100):.1f}%\n\n"
            f"💰 <b>Финансы:</b>\n"
            f"• Платежей: {total_payments}\n"
            f"• Доход: {total_revenue:.2f} ₽\n"
            f"• ARPU: {(total_revenue/max(total_users,1)):.2f} ₽\n\n"
            f"📈 <b>Активность:</b>\n"
            f"• Сообщений в чатах: 1,247\n"
            f"• Отчетов сегодня: 23\n"
            f"• Целей на неделю: 45\n\n"
            f"🎯 <b>Воронка продаж:</b>\n"
            f"• Лиды: 523\n"
            f"• Прогрев завершен: 127 (24.3%)\n"
            f"• Купили трипвайер: 31 (24.4%)\n"
            f"• Подписались: 18 (58.1%)"
        )
        
        keyboard = [
            [InlineKeyboardButton("📊 Детальные метрики", callback_data="admin_analytics_detailed")],
            [InlineKeyboardButton("📈 Графики и тренды", callback_data="admin_analytics_trends")],
            [InlineKeyboardButton("🎯 Воронка продаж", callback_data="admin_analytics_funnel")],
            [InlineKeyboardButton("💰 Финансовый отчет", callback_data="admin_analytics_finance")],
            [InlineKeyboardButton("👥 Сегментация", callback_data="admin_analytics_segments")],
            [InlineKeyboardButton("📋 Экспорт данных", callback_data="admin_analytics_export")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, analytics_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка аналитики: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки аналитики")


async def _handle_broadcast_system(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    """Система массовых рассылок."""
    try:
        broadcast_text = (
            f"📢 <b>Система массовых рассылок</b>\n\n"
            f"📊 <b>Статистика рассылок:</b>\n"
            f"• Всего отправлено: 2,847 сообщений\n"
            f"• Доставлено: 2,731 (95.9%)\n"
            f"• Прочитано: 2,156 (78.9%)\n"
            f"• Нажали на кнопки: 687 (31.9%)\n\n"
            f"📝 <b>Последние рассылки:</b>\n"
            f"• Вечерние напоминания (сегодня)\n"
            f"• Еженедельные цели (вчера)\n"
            f"• Новый трипвайер (3 дня назад)\n\n"
            f"🎯 <b>Выберите тип рассылки:</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("📨 Обычная рассылка", callback_data="admin_broadcast_regular")],
            [InlineKeyboardButton("🎯 Сегментированная", callback_data="admin_broadcast_segment")],
            [InlineKeyboardButton("⏰ Отложенная", callback_data="admin_broadcast_scheduled")],
            [InlineKeyboardButton("🔥 Срочная", callback_data="admin_broadcast_urgent")],
            [InlineKeyboardButton("📊 Статистика рассылок", callback_data="admin_broadcast_stats")],
            [InlineKeyboardButton("📋 История", callback_data="admin_broadcast_history")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, broadcast_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка системы рассылок: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки системы рассылок")


async def _handle_system_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    """Системные настройки."""
    try:
        from config.settings import settings
        
        settings_text = (
            f"⚙️ <b>Системные настройки</b>\n\n"
            f"🤖 <b>Основные настройки:</b>\n"
            f"• Режим отладки: {'✅ Включен' if settings.debug else '❌ Выключен'}\n"
            f"• Группа: {settings.telegram_group_id}\n"
            f"• Канал: {settings.telegram_channel_id}\n\n"
            f"💳 <b>Платежи:</b>\n"
            f"• Валюта: {settings.payment_currency}\n"
            f"• Базовая сумма: {settings.payment_amount} ₽\n\n"
            f"⏰ <b>Расписание:</b>\n"
            f"• Утренние ритуалы: 06:30\n"
            f"• Вечерние ритуалы: 21:00\n"
            f"• Еженедельные цели: Воскресенье\n\n"
            f"🔧 <b>Система:</b>\n"
            f"• Планировщик: ✅ Активен\n"
            f"• База данных: ✅ Подключена\n"
            f"• Логирование: ✅ Включено"
        )
        
        keyboard = [
            [InlineKeyboardButton("🤖 Основные настройки", callback_data="admin_system_main")],
            [InlineKeyboardButton("💳 Настройки платежей", callback_data="admin_system_payments")],
            [InlineKeyboardButton("⏰ Расписание задач", callback_data="admin_system_schedule")],
            [InlineKeyboardButton("🔧 Системные параметры", callback_data="admin_system_params")],
            [InlineKeyboardButton("🛡️ Безопасность", callback_data="admin_system_security")],
            [InlineKeyboardButton("📊 Мониторинг", callback_data="admin_system_monitoring")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, settings_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка системных настроек: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки системных настроек")


# Заглушки для остальных функций
async def _handle_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                             user_service: UserService, action: str, is_callback: bool = False) -> None:
    """Обработка действий с пользователями."""
    try:
        if action == "admin_user_add":
            await _handle_add_user_form(update, context, is_callback=True)
            
        elif action == "admin_user_list_all":
            await _handle_list_all_users(update, context, user_service, is_callback=True)
            
        elif action == "admin_user_search":
            await _handle_search_users_form(update, context, is_callback=True)
            
        elif action == "admin_user_stats":
            await _handle_user_detailed_stats(update, context, user_service, is_callback=True)
            
        elif action.startswith("admin_user_view_"):
            user_id = action.replace("admin_user_view_", "")
            await _handle_view_user(update, context, user_service, user_id, is_callback=True)
            
        elif action.startswith("admin_user_edit_"):
            user_id = action.replace("admin_user_edit_", "")
            await _handle_edit_user(update, context, user_service, user_id, is_callback=True)
            
        elif action.startswith("admin_user_delete_confirm_"):
            user_id = action.replace("admin_user_delete_confirm_", "")
            logger.info(f"🗑️ Удаление пользователя с ID: '{user_id}'")
            await _handle_delete_user_final(update, context, user_service, user_id, is_callback=True)
            
        elif action.startswith("admin_user_delete_"):
            user_id = action.replace("admin_user_delete_", "")
            await _handle_delete_user_confirm(update, context, user_service, user_id, is_callback=True)
            
        elif action.startswith("admin_user_status_"):
            # admin_user_status_{user_id}_{status}
            parts = action.split("_")
            if len(parts) >= 5:
                user_id = parts[3]
                status = parts[4]
                await _handle_change_user_status(update, context, user_service, user_id, status, is_callback=True)
            
        else:
            await _safe_edit_message(update, context, f"🔧 Функция '{action}' в разработке...")
            
    except Exception as e:
        logger.error(f"Ошибка обработки действия пользователей {action}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка выполнения действия")


async def _handle_add_user_form(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    """Форма добавления пользователя."""
    try:
        form_text = (
            f"➕ <b>Добавление пользователя</b>\n\n"
            f"📝 <b>Инструкция:</b>\n"
            f"1. Получите Telegram ID пользователя\n"
            f"2. Укажите имя пользователя\n"
            f"3. Выберите статус\n\n"
            f"💡 <b>Способы получения Telegram ID:</b>\n"
            f"• Попросите пользователя написать @userinfobot\n"
            f"• Используйте @getidsbot\n"
            f"• ID появится в логах при первом сообщении\n\n"
            f"⚠️ <b>Пока доступно только через команды бота</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 Инструкция по ID", callback_data="admin_user_id_help")],
            [InlineKeyboardButton("🔙 Назад к пользователям", callback_data="admin_users_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, form_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка формы добавления пользователя: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки формы")


async def _handle_list_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                user_service: UserService, is_callback: bool = False, 
                                page: int = 0) -> None:
    """Список всех пользователей с пагинацией."""
    try:
        limit = 10
        offset = page * limit
        users = await user_service.get_all_users(offset=offset, limit=limit)
        total_users = await user_service.get_users_count()
        
        if not users:
            await _safe_edit_message(update, context, "👥 Пользователи не найдены")
            return
        
        list_text = (
            f"📋 <b>Все пользователи</b> (стр. {page + 1})\n"
            f"📊 Всего: {total_users} пользователей\n\n"
        )
        
        keyboard = []
        
        for i, user in enumerate(users, 1):
            status_emoji = {
                "active": "✅",
                "inactive": "⏸️", 
                "banned": "🚫"
            }.get(user.status, "❓")
            
            group_emoji = "👥" if user.is_in_group else "👤"
            subscription_emoji = "💎" if user.subscription_until and user.subscription_until > datetime.utcnow() else "🆓"
            
            list_text += (
                f"{offset + i}. {status_emoji}{group_emoji}{subscription_emoji} "
                f"<b>{user.display_name}</b>\n"
                f"   ID: {user.telegram_id} | "
                f"Создан: {user.created_at.strftime('%d.%m.%y')}\n"
            )
            
            keyboard.append([
                InlineKeyboardButton(f"👁️ {user.display_name[:15]}...", 
                                   callback_data=f"admin_user_view_{user.id}"),
                InlineKeyboardButton("✏️", callback_data=f"admin_user_edit_{user.id}"),
                InlineKeyboardButton("🗑️", callback_data=f"admin_user_delete_{user.id}")
            ])
        
        # Пагинация
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(
                InlineKeyboardButton("⬅️ Предыдущие", callback_data=f"admin_user_list_page_{page-1}")
            )
        if len(users) == limit:  # Есть еще страницы
            pagination_buttons.append(
                InlineKeyboardButton("Следующие ➡️", callback_data=f"admin_user_list_page_{page+1}")
            )
        
        if pagination_buttons:
            keyboard.append(pagination_buttons)
        
        keyboard.extend([
            [InlineKeyboardButton("🔍 Поиск", callback_data="admin_user_search")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_users_manage")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, list_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка списка пользователей: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки списка пользователей")


async def _handle_search_users_form(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    """Форма поиска пользователей."""
    try:
        search_text = (
            f"🔍 <b>Поиск пользователей</b>\n\n"
            f"📝 <b>Что можно искать:</b>\n"
            f"• Имя пользователя\n"
            f"• Username (@username)\n"
            f"• Telegram ID\n\n"
            f"💡 <b>Примеры запросов:</b>\n"
            f"• <code>Иван</code> - поиск по имени\n"
            f"• <code>@ivan_petrov</code> - поиск по username\n"
            f"• <code>123456789</code> - поиск по ID\n\n"
            f"⚠️ <b>Пока доступно только через команды бота</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к списку", callback_data="admin_user_list_all")],
            [InlineKeyboardButton("🔙 К управлению", callback_data="admin_users_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, search_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка формы поиска: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки формы поиска")


async def _handle_user_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     user_service: UserService, is_callback: bool = False) -> None:
    """Детальная статистика пользователей."""
    try:
        stats = await user_service.get_user_statistics()
        
        stats_text = (
            f"📊 <b>Детальная статистика пользователей</b>\n\n"
            f"👥 <b>Общая статистика:</b>\n"
            f"• Всего пользователей: {stats['total']}\n"
            f"• Активных: {stats['active']} ({stats['activity_rate']}%)\n"
            f"• Неактивных: {stats['inactive']}\n"
            f"• Заблокированных: {stats['banned']}\n\n"
            f"📈 <b>Новые пользователи:</b>\n"
            f"• Сегодня: {stats['new_today']}\n"
            f"• За неделю: {stats['new_week']}\n"
            f"• За месяц: {stats['new_month']}\n\n"
            f"🎯 <b>Активность:</b>\n"
            f"• Коэффициент активности: {stats['activity_rate']}%\n"
            f"• Удержание: {100 - stats['activity_rate']:.1f}% неактивных\n\n"
            f"📋 <b>Сегментация по статусам:</b>\n"
            f"✅ Активные: {stats['active']}\n"
            f"⏸️ Неактивные: {stats['inactive']}\n"
            f"🚫 Заблокированные: {stats['banned']}"
        )
        
        keyboard = [
            [InlineKeyboardButton("📊 Экспорт статистики", callback_data="admin_user_stats_export")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_user_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_users_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, stats_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка детальной статистики: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки статистики")


async def _handle_view_user(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           user_service: UserService, user_id: str, is_callback: bool = False) -> None:
    """Просмотр детальной информации о пользователе."""
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            await _safe_edit_message(update, context, "❌ Пользователь не найден")
            return
        
        status_emoji = {
            "active": "✅ Активен",
            "inactive": "⏸️ Неактивен", 
            "banned": "🚫 Заблокирован"
        }.get(user.status, "❓ Неизвестно")
        
        subscription_status = "💎 Активна" if (
            user.subscription_until and user.subscription_until > datetime.utcnow()
        ) else "🆓 Истекла/Отсутствует"
        
        user_text = (
            f"👤 <b>Информация о пользователе</b>\n\n"
            f"📋 <b>Основные данные:</b>\n"
            f"• Имя: <b>{user.display_name}</b>\n"
            f"• Username: @{user.username or 'не указан'}\n"
            f"• Telegram ID: <code>{user.telegram_id}</code>\n"
            f"• Статус: {status_emoji}\n\n"
            f"👥 <b>Участие:</b>\n"
            f"• В группе: {'✅ Да' if user.is_in_group else '❌ Нет'}\n"
            f"• Подписка: {subscription_status}\n"
        )
        
        if user.subscription_until:
            user_text += f"• До: {user.subscription_until.strftime('%d.%m.%Y %H:%M')}\n"
        
        user_text += (
            f"\n📅 <b>Временные метки:</b>\n"
            f"• Создан: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"• Обновлен: {user.updated_at.strftime('%d.%m.%Y %H:%M')}\n"
        )
        
        if user.last_activity_at:
            user_text += f"• Последняя активность: {user.last_activity_at.strftime('%d.%m.%Y %H:%M')}\n"
        
        keyboard = [
            [InlineKeyboardButton("✏️ Редактировать", callback_data=f"admin_user_edit_{user_id}")],
            [
                InlineKeyboardButton("✅ Активировать", callback_data=f"admin_user_status_{user_id}_active"),
                InlineKeyboardButton("⏸️ Деактивировать", callback_data=f"admin_user_status_{user_id}_inactive")
            ],
            [InlineKeyboardButton("🚫 Заблокировать", callback_data=f"admin_user_status_{user_id}_banned")],
            [InlineKeyboardButton("🗑️ Удалить", callback_data=f"admin_user_delete_{user_id}")],
            [InlineKeyboardButton("🔙 Назад к списку", callback_data="admin_user_list_all")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, user_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка просмотра пользователя {user_id}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки информации о пользователе")


async def _handle_edit_user(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           user_service: UserService, user_id: str, is_callback: bool = False) -> None:
    """Редактирование пользователя."""
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            await _safe_edit_message(update, context, "❌ Пользователь не найден")
            return
        
        edit_text = (
            f"✏️ <b>Редактирование пользователя</b>\n\n"
            f"👤 <b>{user.display_name}</b>\n"
            f"ID: {user.telegram_id}\n\n"
            f"📝 <b>Доступные действия:</b>\n"
            f"• Изменить статус\n"
            f"• Управление группой\n"
            f"• Управление подпиской\n\n"
            f"⚠️ <b>Выберите действие:</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Изменить статус", callback_data=f"admin_user_change_status_{user_id}")],
            [
                InlineKeyboardButton("➕ Добавить в группу", callback_data=f"admin_user_add_group_{user_id}"),
                InlineKeyboardButton("➖ Убрать из группы", callback_data=f"admin_user_remove_group_{user_id}")
            ],
            [InlineKeyboardButton("💎 Управление подпиской", callback_data=f"admin_user_subscription_{user_id}")],
            [InlineKeyboardButton("👁️ Просмотр", callback_data=f"admin_user_view_{user_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_users_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, edit_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка редактирования пользователя {user_id}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки редактирования")


async def _handle_change_user_status(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    user_service: UserService, user_id: str, status: str, 
                                    is_callback: bool = False) -> None:
    """Изменение статуса пользователя."""
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            await _safe_edit_message(update, context, "❌ Пользователь не найден")
            return
        
        success = await user_service.update_user_status(user_id, status)
        
        status_names = {
            "active": "активирован",
            "inactive": "деактивирован",
            "banned": "заблокирован"
        }
        
        if success:
            result_text = (
                f"✅ <b>Статус изменен</b>\n\n"
                f"👤 Пользователь <b>{user.display_name}</b>\n"
                f"🔄 Статус: {status_names.get(status, status)}\n"
                f"📅 Время: {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}"
            )
        else:
            result_text = (
                f"❌ <b>Ошибка изменения статуса</b>\n\n"
                f"Не удалось изменить статус пользователя {user.display_name}"
            )
        
        keyboard = [
            [InlineKeyboardButton("👁️ Просмотр пользователя", callback_data=f"admin_user_view_{user_id}")],
            [InlineKeyboardButton("🔙 К управлению", callback_data="admin_users_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, result_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка изменения статуса пользователя {user_id}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка изменения статуса")


async def _handle_delete_user_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     user_service: UserService, user_id: str, is_callback: bool = False) -> None:
    """Подтверждение удаления пользователя."""
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            await _safe_edit_message(update, context, "❌ Пользователь не найден")
            return
        
        confirm_text = (
            f"⚠️ <b>ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ</b>\n\n"
            f"Вы действительно хотите удалить пользователя?\n\n"
            f"👤 <b>{user.display_name}</b>\n"
            f"ID: {user.telegram_id}\n"
            f"Статус: {user.status}\n"
            f"Создан: {user.created_at.strftime('%d.%m.%Y')}\n\n"
            f"🚨 <b>ВНИМАНИЕ!</b>\n"
            f"• Пользователь будет удален навсегда\n"
            f"• Все связанные данные будут потеряны\n"
            f"• Действие необратимо\n\n"
            f"❓ Продолжить удаление?"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🗑️ ДА, УДАЛИТЬ", callback_data=f"admin_user_delete_confirm_{user_id}"),
                InlineKeyboardButton("❌ Отмена", callback_data=f"admin_user_view_{user_id}")
            ],
            [InlineKeyboardButton("🔙 Назад к списку", callback_data="admin_users_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, confirm_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка подтверждения удаления {user_id}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка подтверждения удаления")


async def _handle_delete_user_final(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   user_service: UserService, user_id: str, is_callback: bool = False) -> None:
    """Финальное удаление пользователя."""
    try:
        logger.info(f"🔍 _handle_delete_user_final получил user_id: '{user_id}'")
        user = await user_service.get_user_by_id(user_id)
        if not user:
            await _safe_edit_message(update, context, "❌ Пользователь не найден")
            return
        
        user_name = user.display_name
        success = await user_service.delete_user(user_id)
        
        if success:
            result_text = (
                f"✅ <b>Пользователь удален</b>\n\n"
                f"👤 <b>{user_name}</b> был успешно удален из системы\n"
                f"📅 Время удаления: {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"🗂️ Все связанные данные очищены"
            )
        else:
            result_text = (
                f"❌ <b>Ошибка удаления</b>\n\n"
                f"Не удалось удалить пользователя {user_name}\n"
                f"Попробуйте позже или обратитесь к разработчику"
            )
        
        keyboard = [
            [InlineKeyboardButton("📋 К списку пользователей", callback_data="admin_user_list_all")],
            [InlineKeyboardButton("🔙 К управлению", callback_data="admin_users_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, result_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка финального удаления {user_id}: {e}")
        await _safe_edit_message(update, context, "❌ Критическая ошибка удаления")


async def _handle_payment_action(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                payment_service: PaymentService, action: str, is_callback: bool = False) -> None:
    """Обработка действий с платежами."""
    await _safe_edit_message(update, context, f"🔧 Функция '{action}' в разработке...")


async def _handle_content_action(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                action: str, is_callback: bool = False) -> None:
    """Обработка действий с контентом."""
    await _safe_edit_message(update, context, f"🔧 Функция '{action}' в разработке...")


# === УПРАВЛЕНИЕ ТРИПВАЙЕРАМИ ===

async def _handle_tripwire_management(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     product_service: ProductService, is_callback: bool = False) -> None:
    """Главная панель управления трипвайерами."""
    try:
        # Получаем статистику
        stats = await product_service.get_tripwire_statistics()
        
        management_text = (
            f"🎯 <b>Управление трипвайерами</b>\n\n"
            f"📊 <b>Быстрая статистика:</b>\n"
            f"• 📦 Продуктов: {stats['products']['total']} ({stats['products']['active']} активных)\n"
            f"• 📋 Офферов: {stats['offers']['total']} ({stats['offers']['active']} активных)\n"
            f"• 📈 Конверсия: {stats['user_offers']['conversion_rate']}%\n\n"
            f"🎯 <b>Трипвайеры:</b> {stats['products']['tripwire']} продуктов\n\n"
            f"📋 <b>Доступные функции:</b>\n"
            f"• Управление продуктами\n"
            f"• Управление офферами\n"
            f"• Детальная статистика\n"
            f"• Анализ конверсий"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("📦 Продукты", callback_data="admin_tripwire_products"),
                InlineKeyboardButton("📋 Офферы", callback_data="admin_tripwire_offers")
            ],
            [InlineKeyboardButton("📊 Детальная статистика", callback_data="admin_tripwire_stats")],
            [InlineKeyboardButton("➕ Добавить продукт", callback_data="admin_tripwire_add_product")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, management_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка управления трипвайерами: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки управления трипвайерами")


async def _handle_tripwire_action(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  product_service: ProductService, action: str, is_callback: bool = False) -> None:
    """Обработка действий с трипвайерами."""
    try:
        logger.info(f"🚀 _handle_tripwire_action получил действие: {action}")
        if action == "admin_tripwire_products":
            await _handle_tripwire_products_list(update, context, product_service, is_callback=True)
            
        elif action == "admin_tripwire_offers":
            await _handle_tripwire_offers_list(update, context, product_service, is_callback=True)
            
        elif action == "admin_tripwire_stats":
            await _handle_tripwire_detailed_stats(update, context, product_service, is_callback=True)
            
        elif action == "admin_tripwire_add_product":
            await _handle_add_product_form(update, context, is_callback=True)
            
        elif action == "admin_create_tripwire":
            logger.info(f"✅ Найдено действие создания трипвайера")
            await _handle_create_product_dialog(update, context, "tripwire", is_callback=True)
            
        elif action == "admin_create_course":
            logger.info(f"✅ Найдено действие создания курса")
            await _handle_create_product_dialog(update, context, "course", is_callback=True)
            
        elif action == "admin_create_consultation":
            logger.info(f"✅ Найдено действие создания консультации")
            await _handle_create_product_dialog(update, context, "consultation", is_callback=True)
            
        # Новые короткие callback'и для продуктов
        elif action.startswith("admin_tp_view_"):
            short_id = action.replace("admin_tp_view_", "")
            product_id = await _restore_uuid(short_id, product_service)
            if product_id:
                await _handle_view_product(update, context, product_service, product_id, is_callback=True)
            else:
                await _safe_edit_message(update, context, "❌ Продукт не найден")
            
        elif action.startswith("admin_tp_toggle_"):
            short_id = action.replace("admin_tp_toggle_", "")
            product_id = await _restore_uuid(short_id, product_service)
            if product_id:
                await _handle_toggle_product_status(update, context, product_service, product_id, is_callback=True)
            else:
                await _safe_edit_message(update, context, "❌ Продукт не найден")
            
        elif action.startswith("admin_tp_delete_"):
            short_id = action.replace("admin_tp_delete_", "")
            product_id = await _restore_uuid(short_id, product_service)
            if product_id:
                await _handle_delete_product_confirm(update, context, product_service, product_id, is_callback=True)
            else:
                await _safe_edit_message(update, context, "❌ Продукт не найден")
            
        elif action.startswith("admin_tp_confirm_"):
            short_id = action.replace("admin_tp_confirm_", "")
            product_id = await _restore_uuid(short_id, product_service)
            if product_id:
                await _handle_delete_product_final(update, context, product_service, product_id, is_callback=True)
            else:
                await _safe_edit_message(update, context, "❌ Продукт не найден")
            
        # Новые короткие callback'и для офферов
        elif action.startswith("admin_to_view_"):
            short_id = action.replace("admin_to_view_", "")
            offer_id = await _restore_uuid(short_id, product_service)
            if offer_id:
                await _handle_view_offer(update, context, product_service, offer_id, is_callback=True)
            else:
                await _safe_edit_message(update, context, "❌ Оффер не найден")
            
        elif action.startswith("admin_to_toggle_"):
            short_id = action.replace("admin_to_toggle_", "")
            offer_id = await _restore_uuid(short_id, product_service)
            if offer_id:
                await _handle_toggle_offer_status(update, context, product_service, offer_id, is_callback=True)
            else:
                await _safe_edit_message(update, context, "❌ Оффер не найден")
            
        elif action.startswith("admin_to_delete_"):
            short_id = action.replace("admin_to_delete_", "")
            offer_id = await _restore_uuid(short_id, product_service)
            if offer_id:
                await _handle_delete_offer_confirm(update, context, product_service, offer_id, is_callback=True)
            else:
                await _safe_edit_message(update, context, "❌ Оффер не найден")
            
        elif action.startswith("admin_to_confirm_"):
            short_id = action.replace("admin_to_confirm_", "")
            offer_id = await _restore_uuid(short_id, product_service)
            if offer_id:
                await _handle_delete_offer_final(update, context, product_service, offer_id, is_callback=True)
            else:
                await _safe_edit_message(update, context, "❌ Оффер не найден")
            
        # Старые длинные callback'и (совместимость)
        elif action.startswith("admin_tripwire_product_view_"):
            product_id = action.replace("admin_tripwire_product_view_", "")
            await _handle_view_product(update, context, product_service, product_id, is_callback=True)
            
        elif action.startswith("admin_tripwire_product_toggle_"):
            product_id = action.replace("admin_tripwire_product_toggle_", "")
            await _handle_toggle_product_status(update, context, product_service, product_id, is_callback=True)
            
        elif action.startswith("admin_tripwire_product_delete_"):
            product_id = action.replace("admin_tripwire_product_delete_", "")
            await _handle_delete_product_confirm(update, context, product_service, product_id, is_callback=True)
            
        elif action.startswith("admin_tripwire_product_delete_confirm_"):
            product_id = action.replace("admin_tripwire_product_delete_confirm_", "")
            await _handle_delete_product_final(update, context, product_service, product_id, is_callback=True)
            
        elif action.startswith("admin_tripwire_offer_view_"):
            offer_id = action.replace("admin_tripwire_offer_view_", "")
            await _handle_view_offer(update, context, product_service, offer_id, is_callback=True)
            
        elif action.startswith("admin_tripwire_offer_toggle_"):
            offer_id = action.replace("admin_tripwire_offer_toggle_", "")
            await _handle_toggle_offer_status(update, context, product_service, offer_id, is_callback=True)
            
        elif action.startswith("admin_tripwire_offer_delete_"):
            offer_id = action.replace("admin_tripwire_offer_delete_", "")
            await _handle_delete_offer_confirm(update, context, product_service, offer_id, is_callback=True)
            
        elif action.startswith("admin_tripwire_offer_delete_confirm_"):
            offer_id = action.replace("admin_tripwire_offer_delete_confirm_", "")
            await _handle_delete_offer_final(update, context, product_service, offer_id, is_callback=True)
            
        else:
            logger.warning(f"Неизвестное действие трипвайера: {action}")
            await _safe_edit_message(update, context, f"🔧 Функция '{action}' в разработке...")
            
    except Exception as e:
        logger.error(f"Ошибка обработки действия трипвайеров {action}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка выполнения действия")


async def _handle_tripwire_products_list(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                        product_service: ProductService, is_callback: bool = False) -> None:
    """Список всех продуктов-трипвайеров."""
    try:
        products = await product_service.get_all_products()
        
        if not products:
            empty_text = (
                f"📦 <b>Продукты не найдены</b>\n\n"
                f"У вас пока нет созданных продуктов.\n\n"
                f"💡 <b>Чтобы создать продукт:</b>\n"
                f"• Нажмите '➕ Добавить продукт'\n"
                f"• Выберите тип (трипвайер/курс/консультация)\n"
                f"• Заполните 5 простых шагов\n\n"
                f"🚀 Создайте свой первый продукт!"
            )
            
            keyboard = [
                [InlineKeyboardButton("➕ Добавить продукт", callback_data="admin_tripwire_add_product")],
                [InlineKeyboardButton("🔙 К управлению", callback_data="admin_tripwire_manage")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await _safe_edit_message(update, context, empty_text, reply_markup)
            return
        
        list_text = (
            f"📦 <b>Все продукты</b>\n"
            f"📊 Всего: {len(products)} продуктов\n\n"
        )
        
        keyboard = []
        
        for i, product in enumerate(products, 1):
            status_emoji = "✅" if product.is_active else "⏸️"
            type_emoji = {
                "tripwire": "🎯",
                "course": "📚",
                "consultation": "💬"
            }.get(product.type, "📦")
            
            price_text = f"{product.price}₽" if product.price else "Бесплатно"
            offers_count = len(product.offers) if product.offers else 0
            
            list_text += (
                f"{i}. {status_emoji}{type_emoji} <b>{product.name}</b>\n"
                f"   💰 {price_text} | 📋 {offers_count} офферов\n"
                f"   📅 {product.created_at.strftime('%d.%m.%y')}\n"
            )
            
            # Сокращаем UUID для callback_data
            short_id = str(product.id).replace('-', '')[:16]
            keyboard.append([
                InlineKeyboardButton(f"👁️ {product.name[:20]}...", 
                                   callback_data=f"admin_tp_view_{short_id}"),
                InlineKeyboardButton("🔄", callback_data=f"admin_tp_toggle_{short_id}"),
                InlineKeyboardButton("🗑️", callback_data=f"admin_tp_delete_{short_id}")
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("➕ Добавить продукт", callback_data="admin_tripwire_add_product")],
            [InlineKeyboardButton("📋 Офферы", callback_data="admin_tripwire_offers")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_tripwire_manage")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, list_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка списка продуктов: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки списка продуктов")


async def _handle_tripwire_offers_list(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                      product_service: ProductService, is_callback: bool = False) -> None:
    """Список всех офферов."""
    try:
        offers = await product_service.get_all_offers()
        
        if not offers:
            empty_text = (
                f"📋 <b>Офферы не найдены</b>\n\n"
                f"У вас пока нет созданных офферов.\n\n"
                f"💡 <b>Офферы создаются автоматически</b> при создании продуктов.\n\n"
                f"🚀 Создайте продукт, чтобы получить офферы!"
            )
            
            keyboard = [
                [InlineKeyboardButton("➕ Добавить продукт", callback_data="admin_tripwire_add_product")],
                [InlineKeyboardButton("📦 Продукты", callback_data="admin_tripwire_products")],
                [InlineKeyboardButton("🔙 К управлению", callback_data="admin_tripwire_manage")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await _safe_edit_message(update, context, empty_text, reply_markup)
            return
        
        list_text = (
            f"📋 <b>Все офферы</b>\n"
            f"📊 Всего: {len(offers)} офферов\n\n"
        )
        
        keyboard = []
        
        for i, offer in enumerate(offers, 1):
            status_emoji = "✅" if offer.is_active else "⏸️"
            product_name = offer.product.name if offer.product else "Неизвестный продукт"
            
            list_text += (
                f"{i}. {status_emoji} <b>Оффер #{i}</b>\n"
                f"   📦 Продукт: {product_name}\n"
                f"   📅 Создан: {offer.created_at.strftime('%d.%m.%y')}\n"
            )
            
            # Сокращаем UUID для callback_data
            short_id = str(offer.id).replace('-', '')[:16]
            keyboard.append([
                InlineKeyboardButton(f"👁️ Оффер #{i}", 
                                   callback_data=f"admin_to_view_{short_id}"),
                InlineKeyboardButton("🔄", callback_data=f"admin_to_toggle_{short_id}"),
                InlineKeyboardButton("🗑️", callback_data=f"admin_to_delete_{short_id}")
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("📦 Продукты", callback_data="admin_tripwire_products")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_tripwire_manage")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, list_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка списка офферов: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки списка офферов")


async def _handle_tripwire_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                         product_service: ProductService, is_callback: bool = False) -> None:
    """Детальная статистика трипвайеров."""
    try:
        stats = await product_service.get_tripwire_statistics()
        top_offers = await product_service.get_top_performing_offers()
        
        stats_text = (
            f"📊 <b>Статистика трипвайеров</b>\n\n"
            f"📦 <b>Продукты:</b>\n"
            f"• Всего: {stats['products']['total']}\n"
            f"• Активных: {stats['products']['active']}\n"
            f"• Трипвайеров: {stats['products']['tripwire']}\n\n"
            f"📋 <b>Офферы:</b>\n"
            f"• Всего: {stats['offers']['total']}\n"
            f"• Активных: {stats['offers']['active']}\n\n"
            f"👥 <b>Пользовательские офферы:</b>\n"
            f"• Всего созданных: {stats['user_offers']['total']}\n"
            f"• Показано: {stats['user_offers']['shown']}\n"
            f"• Кликнуто: {stats['user_offers']['clicked']}\n"
            f"• Конверсия: {stats['user_offers']['conversion_rate']}%\n"
        )
        
        if top_offers:
            stats_text += f"\n🏆 <b>Топ-офферы:</b>\n"
            for i, offer in enumerate(top_offers, 1):
                stats_text += (
                    f"{i}. {offer['product_name']}\n"
                    f"   👁️ {offer['shows']} показов | "
                    f"👆 {offer['clicks']} кликов | "
                    f"📈 {offer['conversion']}%\n"
                )
        
        keyboard = [
            [InlineKeyboardButton("📦 Продукты", callback_data="admin_tripwire_products")],
            [InlineKeyboardButton("📋 Офферы", callback_data="admin_tripwire_offers")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_tripwire_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_tripwire_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, stats_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка детальной статистики трипвайеров: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки статистики")


async def _handle_add_product_form(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    """Интерактивная форма добавления продукта."""
    try:
        form_text = (
            f"➕ <b>Создание нового продукта</b>\n\n"
            f"🎯 <b>Выберите тип продукта для создания:</b>\n\n"
            f"📈 <b>Трипвайер</b> - Недорогой продукт для первого знакомства\n"
            f"💰 Цена: 300-2000 рублей\n"
            f"🎯 Цель: Привлечь новых клиентов\n\n"
            f"📚 <b>Курс</b> - Полноценный обучающий курс\n"
            f"💰 Цена: 5000-50000 рублей\n"
            f"🎯 Цель: Основной продукт\n\n"
            f"👥 <b>Консультация</b> - Персональная работа\n"
            f"💰 Цена: 3000-30000 рублей\n"
            f"🎯 Цель: Премиум услуги"
        )
        
        keyboard = [
            [InlineKeyboardButton("📈 Создать трипвайер", callback_data="admin_create_tripwire")],
            [InlineKeyboardButton("📚 Создать курс", callback_data="admin_create_course")],
            [InlineKeyboardButton("👥 Создать консультацию", callback_data="admin_create_consultation")],
            [InlineKeyboardButton("🔙 К продуктам", callback_data="admin_tripwire_products")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, form_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка формы добавления продукта: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки формы")


async def _handle_create_product_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                       product_type: str, is_callback: bool = False) -> None:
    """Диалог создания продукта конкретного типа."""
    try:
        logger.info(f"🎯 Начинаем создание продукта типа: {product_type}")
        # Сохраняем тип продукта в context.user_data
        if not hasattr(context, 'user_data') or context.user_data is None:
            context.user_data = {}
        context.user_data['product_creation'] = {'type': product_type, 'step': 'name'}
        
        type_names = {
            'tripwire': '📈 Трипвайер',
            'course': '📚 Курс', 
            'consultation': '👥 Консультация'
        }
        
        examples = {
            'tripwire': '30 дней по книге Хилла',
            'course': 'Полный курс по созданию бизнеса',
            'consultation': 'Индивидуальная консультация по стратегии'
        }
        
        dialog_text = (
            f"✍️ <b>Создание: {type_names.get(product_type, product_type.title())}</b>\n\n"
            f"📝 <b>Шаг 1/5: Название продукта</b>\n\n"
            f"Введите название вашего продукта:\n\n"
            f"💡 <b>Пример:</b> <i>{examples.get(product_type, 'Название продукта')}</i>\n\n"
            f"⚠️ <b>Требования:</b>\n"
            f"• Длина: 3-100 символов\n"
            f"• Понятное и привлекательное название\n"
            f"• Без специальных символов\n\n"
            f"📨 <b>Напишите название и отправьте сообщение</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_tripwire_add_product")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, dialog_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка диалога создания продукта {product_type}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка создания продукта")


async def handle_product_creation_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений для создания продукта."""
    try:
        # Проверяем что пользователь в процессе создания продукта
        if (not hasattr(context, 'user_data') or 
            context.user_data is None or 
            'product_creation' not in context.user_data):
            return
            
        creation_data = context.user_data['product_creation']
        text = update.message.text.strip()
        
        if creation_data['step'] == 'name':
            await _handle_product_name_step(update, context, text)
        elif creation_data['step'] == 'description':
            await _handle_product_description_step(update, context, text)
        elif creation_data['step'] == 'price':
            await _handle_product_price_step(update, context, text)
        elif creation_data['step'] == 'payment_url':
            await _handle_product_payment_url_step(update, context, text)
            
    except Exception as e:
        logger.error(f"Ошибка обработки создания продукта: {e}")
        await update.message.reply_text("❌ Ошибка обработки данных")


async def _handle_product_name_step(update: Update, context: ContextTypes.DEFAULT_TYPE, name: str) -> None:
    """Обработка шага ввода названия продукта."""
    try:
        if len(name) < 3 or len(name) > 100:
            await update.message.reply_text(
                "❌ Название должно быть от 3 до 100 символов. Попробуйте ещё раз:"
            )
            return
            
        # Сохраняем название и переходим к описанию
        context.user_data['product_creation']['name'] = name
        context.user_data['product_creation']['step'] = 'description'
        
        product_type = context.user_data['product_creation']['type']
        type_names = {
            'tripwire': '📈 Трипвайер',
            'course': '📚 Курс', 
            'consultation': '👥 Консультация'
        }
        
        examples = {
            'tripwire': 'Мини-курс из 5 уроков по основам инвестирования. Поможет начать инвестировать уже через неделю.',
            'course': 'Полный курс из 20 модулей по созданию бизнеса с нуля до первой прибыли за 3 месяца.',
            'consultation': 'Персональная 2-часовая консультация по стратегии развития бизнеса с планом на 6 месяцев.'
        }
        
        dialog_text = (
            f"✅ <b>Название сохранено:</b> {name}\n\n"
            f"✍️ <b>Создание: {type_names.get(product_type, product_type.title())}</b>\n\n"
            f"📝 <b>Шаг 2/5: Описание продукта</b>\n\n"
            f"Напишите подробное описание продукта:\n\n"
            f"💡 <b>Пример:</b>\n<i>{examples.get(product_type, 'Описание продукта')}</i>\n\n"
            f"⚠️ <b>Требования:</b>\n"
            f"• Длина: 10-500 символов\n"
            f"• Подробно опишите что получит клиент\n"
            f"• Укажите результат и время\n\n"
            f"📨 <b>Напишите описание и отправьте сообщение</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_tripwire_add_product")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(dialog_text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Ошибка шага названия продукта: {e}")
        await update.message.reply_text("❌ Ошибка сохранения названия")


async def _handle_product_description_step(update: Update, context: ContextTypes.DEFAULT_TYPE, description: str) -> None:
    """Обработка шага ввода описания продукта."""
    try:
        if len(description) < 10 or len(description) > 500:
            await update.message.reply_text(
                "❌ Описание должно быть от 10 до 500 символов. Попробуйте ещё раз:"
            )
            return
            
        # Сохраняем описание и переходим к цене
        context.user_data['product_creation']['description'] = description
        context.user_data['product_creation']['step'] = 'price'
        
        product_type = context.user_data['product_creation']['type']
        type_names = {
            'tripwire': '📈 Трипвайер',
            'course': '📚 Курс', 
            'consultation': '👥 Консультация'
        }
        
        price_ranges = {
            'tripwire': '300-2000 рублей',
            'course': '5000-50000 рублей',
            'consultation': '3000-30000 рублей'
        }
        
        dialog_text = (
            f"✅ <b>Описание сохранено</b>\n\n"
            f"✍️ <b>Создание: {type_names.get(product_type, product_type.title())}</b>\n\n"
            f"📝 <b>Шаг 3/5: Цена продукта</b>\n\n"
            f"Введите цену продукта в рублях (только число):\n\n"
            f"💰 <b>Рекомендуемый диапазон:</b> {price_ranges.get(product_type, '1000-10000 рублей')}\n\n"
            f"⚠️ <b>Требования:</b>\n"
            f"• Только число (без слов и символов)\n"
            f"• От 100 до 500000 рублей\n"
            f"• Например: 990 или 5000\n\n"
            f"📨 <b>Введите цену и отправьте сообщение</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_tripwire_add_product")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(dialog_text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Ошибка шага описания продукта: {e}")
        await update.message.reply_text("❌ Ошибка сохранения описания")


async def _handle_product_price_step(update: Update, context: ContextTypes.DEFAULT_TYPE, price_text: str) -> None:
    """Обработка шага ввода цены продукта."""
    try:
        try:
            price = int(price_text)
        except ValueError:
            await update.message.reply_text(
                "❌ Цена должна быть числом. Например: 990\nПопробуйте ещё раз:"
            )
            return
            
        if price < 100 or price > 500000:
            await update.message.reply_text(
                "❌ Цена должна быть от 100 до 500000 рублей. Попробуйте ещё раз:"
            )
            return
            
        # Сохраняем цену и переходим к ссылке на оплату
        context.user_data['product_creation']['price'] = price
        context.user_data['product_creation']['step'] = 'payment_url'
        
        product_type = context.user_data['product_creation']['type']
        type_names = {
            'tripwire': '📈 Трипвайер',
            'course': '📚 Курс', 
            'consultation': '👥 Консультация'
        }
        
        dialog_text = (
            f"✅ <b>Цена сохранена:</b> {price:,} ₽\n\n"
            f"✍️ <b>Создание: {type_names.get(product_type, product_type.title())}</b>\n\n"
            f"📝 <b>Шаг 4/5: Ссылка на оплату</b>\n\n"
            f"Введите ссылку на страницу оплаты:\n\n"
            f"💡 <b>Примеры:</b>\n"
            f"• https://pay.cloudpayments.ru/...\n"
            f"• https://yookassa.ru/...\n"
            f"• https://t.me/CryptoBot?start=...\n\n"
            f"⚠️ <b>Требования:</b>\n"
            f"• Должна начинаться с https://\n"
            f"• Рабочая ссылка на платёжную систему\n\n"
            f"📨 <b>Введите ссылку и отправьте сообщение</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_tripwire_add_product")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(dialog_text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Ошибка шага цены продукта: {e}")
        await update.message.reply_text("❌ Ошибка сохранения цены")


async def _handle_product_payment_url_step(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_url: str) -> None:
    """Обработка шага ввода ссылки на оплату и финальное создание продукта."""
    try:
        if not payment_url.startswith('https://'):
            await update.message.reply_text(
                "❌ Ссылка должна начинаться с https://\nПопробуйте ещё раз:"
            )
            return
            
        if len(payment_url) < 10 or len(payment_url) > 500:
            await update.message.reply_text(
                "❌ Ссылка слишком короткая или длинная. Попробуйте ещё раз:"
            )
            return
            
        # Сохраняем ссылку и создаём продукт
        creation_data = context.user_data['product_creation']
        
        # Создаём продукт через ProductService
        async for session in get_database():
            product_service = ProductService(session)
            
            from app.schemas.product import ProductCreate
            from app.models.product import ProductType, Currency
            
            # Конвертируем тип продукта в enum
            product_type_enum = ProductType.TRIPWIRE
            if creation_data['type'] == 'course':
                product_type_enum = ProductType.COURSE
            elif creation_data['type'] == 'consultation':
                product_type_enum = ProductType.CONSULTATION
                
            product_data = ProductCreate(
                name=creation_data['name'],
                description=creation_data['description'],
                type=product_type_enum,
                price=creation_data['price'],
                currency=Currency.RUB,
                payment_url=payment_url,
                offer_text=f"🎯 {creation_data['name']}\n\n{creation_data['description']}\n\n💰 Цена: {creation_data['price']:,} ₽",
                is_active=True
            )
            
            product = await product_service.create_product(product_data)
            
            if product:
                type_names = {
                    'tripwire': '📈 Трипвайер',
                    'course': '📚 Курс', 
                    'consultation': '👥 Консультация'
                }
                
                success_text = (
                    f"🎉 <b>Продукт успешно создан!</b>\n\n"
                    f"📦 <b>Тип:</b> {type_names.get(creation_data['type'], creation_data['type'].title())}\n"
                    f"🏷️ <b>Название:</b> {creation_data['name']}\n"
                    f"💰 <b>Цена:</b> {creation_data['price']:,} ₽\n"
                    f"🔗 <b>Ссылка:</b> {payment_url[:50]}...\n\n"
                    f"✅ <b>Статус:</b> Активен\n"
                    f"🆔 <b>ID:</b> <code>{product.id}</code>\n\n"
                    f"🚀 <b>Продукт готов к использованию!</b>"
                )
                
                keyboard = [
                    [InlineKeyboardButton("👁️ Просмотр продукта", callback_data=f"admin_tp_view_{str(product.id).replace('-', '')[:16]}")],
                    [InlineKeyboardButton("📦 Все продукты", callback_data="admin_tripwire_products")],
                    [InlineKeyboardButton("➕ Создать ещё", callback_data="admin_tripwire_add_product")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(success_text, reply_markup=reply_markup, parse_mode='HTML')
                
                # Очищаем данные создания
                del context.user_data['product_creation']
                
            else:
                await update.message.reply_text("❌ Ошибка создания продукта. Попробуйте позже.")
                
    except Exception as e:
        logger.error(f"Ошибка создания продукта: {e}")
        await update.message.reply_text("❌ Ошибка создания продукта")


async def _handle_view_product(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                              product_service: ProductService, product_id: str, is_callback: bool = False) -> None:
    """Просмотр детальной информации о продукте."""
    try:
        product = await product_service.get_product_by_id(product_id)
        if not product:
            await _safe_edit_message(update, context, "❌ Продукт не найден")
            return
        
        status_emoji = "✅ Активен" if product.is_active else "⏸️ Неактивен"
        type_emoji = {
            "tripwire": "🎯 Трипвайер",
            "course": "📚 Курс", 
            "consultation": "💬 Консультация"
        }.get(product.type, "📦 Неизвестно")
        
        offers_count = len(product.offers) if product.offers else 0
        active_offers = sum(1 for offer in (product.offers or []) if offer.is_active)
        
        product_text = (
            f"📦 <b>Информация о продукте</b>\n\n"
            f"📋 <b>Основные данные:</b>\n"
            f"• Название: <b>{product.name}</b>\n"
            f"• Тип: {type_emoji}\n"
            f"• Статус: {status_emoji}\n"
            f"• Цена: <b>{product.price}₽</b>\n\n"
            f"📝 <b>Описание:</b>\n"
            f"{product.description or 'Описание отсутствует'}\n\n"
            f"📋 <b>Офферы:</b>\n"
            f"• Всего: {offers_count}\n"
            f"• Активных: {active_offers}\n\n"
            f"🔗 <b>Ссылки:</b>\n"
            f"• Оплата: {product.payment_url or 'Не указана'}\n\n"
            f"📅 <b>Временные метки:</b>\n"
            f"• Создан: {product.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"• Обновлен: {product.updated_at.strftime('%d.%m.%Y %H:%M')}\n"
        )
        
        # Используем короткие callback'и
        short_id = str(product_id).replace('-', '')[:16]
        keyboard = [
            [
                InlineKeyboardButton("✅ Активировать" if not product.is_active else "⏸️ Деактивировать", 
                                   callback_data=f"admin_tp_toggle_{short_id}"),
                InlineKeyboardButton("🗑️ Удалить", callback_data=f"admin_tp_delete_{short_id}")
            ],
            [InlineKeyboardButton("📋 Офферы продукта", callback_data="admin_tripwire_offers")],
            [InlineKeyboardButton("🔙 К списку", callback_data="admin_tripwire_products")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, product_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка просмотра продукта {product_id}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки информации о продукте")


async def _handle_toggle_product_status(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                       product_service: ProductService, product_id: str, is_callback: bool = False) -> None:
    """Переключение статуса продукта."""
    try:
        product = await product_service.get_product_by_id(product_id)
        if not product:
            await _safe_edit_message(update, context, "❌ Продукт не найден")
            return
        
        success = await product_service.toggle_product_status(product_id)
        
        if success:
            new_status = "активирован" if not product.is_active else "деактивирован"
            result_text = (
                f"✅ <b>Статус изменен</b>\n\n"
                f"📦 Продукт <b>{product.name}</b>\n"
                f"🔄 Статус: {new_status}\n"
                f"📅 Время: {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}"
            )
        else:
            result_text = (
                f"❌ <b>Ошибка изменения статуса</b>\n\n"
                f"Не удалось изменить статус продукта {product.name}"
            )
        
        # Используем короткие callback'и
        short_id = str(product_id).replace('-', '')[:16]
        keyboard = [
            [InlineKeyboardButton("👁️ Просмотр продукта", callback_data=f"admin_tp_view_{short_id}")],
            [InlineKeyboardButton("🔙 К управлению", callback_data="admin_tripwire_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, result_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка переключения статуса продукта {product_id}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка изменения статуса")


async def _handle_delete_product_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                        product_service: ProductService, product_id: str, is_callback: bool = False) -> None:
    """Подтверждение удаления продукта."""
    try:
        product = await product_service.get_product_by_id(product_id)
        if not product:
            await _safe_edit_message(update, context, "❌ Продукт не найден")
            return
        
        offers_count = len(product.offers) if product.offers else 0
        
        confirm_text = (
            f"⚠️ <b>ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ</b>\n\n"
            f"Вы действительно хотите удалить продукт?\n\n"
            f"📦 <b>{product.name}</b>\n"
            f"💰 Цена: {product.price}₽\n"
            f"📋 Офферов: {offers_count}\n"
            f"📅 Создан: {product.created_at.strftime('%d.%m.%Y')}\n\n"
            f"🚨 <b>ВНИМАНИЕ!</b>\n"
            f"• Продукт будет удален навсегда\n"
            f"• Все связанные офферы будут потеряны\n"
            f"• Статистика будет очищена\n"
            f"• Действие необратимо\n\n"
            f"❓ Продолжить удаление?"
        )
        
        # Используем короткие callback'и
        short_id = str(product_id).replace('-', '')[:16]
        keyboard = [
            [
                InlineKeyboardButton("🗑️ ДА, УДАЛИТЬ", callback_data=f"admin_tp_confirm_{short_id}"),
                InlineKeyboardButton("❌ Отмена", callback_data=f"admin_tp_view_{short_id}")
            ],
            [InlineKeyboardButton("🔙 К списку", callback_data="admin_tripwire_products")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, confirm_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка подтверждения удаления продукта {product_id}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка подтверждения удаления")


async def _handle_delete_product_final(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                      product_service: ProductService, product_id: str, is_callback: bool = False) -> None:
    """Финальное удаление продукта."""
    try:
        product = await product_service.get_product_by_id(product_id)
        if not product:
            await _safe_edit_message(update, context, "❌ Продукт не найден")
            return
        
        product_name = product.name
        success = await product_service.delete_product(product_id)
        
        if success:
            result_text = (
                f"✅ <b>Продукт удален</b>\n\n"
                f"📦 <b>{product_name}</b> был успешно удален из системы\n"
                f"📅 Время удаления: {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"🗂️ Все связанные данные очищены"
            )
        else:
            result_text = (
                f"❌ <b>Ошибка удаления</b>\n\n"
                f"Не удалось удалить продукт {product_name}\n"
                f"Попробуйте позже или обратитесь к разработчику"
            )
        
        keyboard = [
            [InlineKeyboardButton("📦 К списку продуктов", callback_data="admin_tripwire_products")],
            [InlineKeyboardButton("🔙 К управлению", callback_data="admin_tripwire_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, result_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка финального удаления продукта {product_id}: {e}")
        await _safe_edit_message(update, context, "❌ Критическая ошибка удаления")


async def _handle_view_offer(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                            product_service: ProductService, offer_id: str, is_callback: bool = False) -> None:
    """Просмотр детальной информации об оффере."""
    try:
        offer = await product_service.get_offer_by_id(offer_id)
        if not offer:
            await _safe_edit_message(update, context, "❌ Оффер не найден")
            return
        
        status_emoji = "✅ Активен" if offer.is_active else "⏸️ Неактивен"
        product_name = offer.product.name if offer.product else "Неизвестный продукт"
        
        offer_text = (
            f"📋 <b>Информация об оффере</b>\n\n"
            f"📦 <b>Продукт:</b> {product_name}\n"
            f"🔄 <b>Статус:</b> {status_emoji}\n\n"
            f"📅 <b>Временные метки:</b>\n"
            f"• Создан: {offer.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"• Обновлен: {offer.updated_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🔧 <b>Техническая информация:</b>\n"
            f"• ID оффера: <code>{offer.id}</code>\n"
            f"• ID продукта: <code>{offer.product_id}</code>"
        )
        
        # Используем короткие callback'и
        short_offer_id = str(offer_id).replace('-', '')[:16]
        short_product_id = str(offer.product_id).replace('-', '')[:16]
        keyboard = [
            [
                InlineKeyboardButton("✅ Активировать" if not offer.is_active else "⏸️ Деактивировать", 
                                   callback_data=f"admin_to_toggle_{short_offer_id}"),
                InlineKeyboardButton("🗑️ Удалить", callback_data=f"admin_to_delete_{short_offer_id}")
            ],
            [InlineKeyboardButton("📦 Просмотр продукта", callback_data=f"admin_tp_view_{short_product_id}")],
            [InlineKeyboardButton("🔙 К офферам", callback_data="admin_tripwire_offers")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, offer_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка просмотра оффера {offer_id}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки информации об оффере")


async def _handle_toggle_offer_status(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     product_service: ProductService, offer_id: str, is_callback: bool = False) -> None:
    """Переключение статуса оффера."""
    try:
        offer = await product_service.get_offer_by_id(offer_id)
        if not offer:
            await _safe_edit_message(update, context, "❌ Оффер не найден")
            return
        
        success = await product_service.toggle_offer_status(offer_id)
        
        if success:
            new_status = "активирован" if not offer.is_active else "деактивирован"
            product_name = offer.product.name if offer.product else "Неизвестный продукт"
            result_text = (
                f"✅ <b>Статус изменен</b>\n\n"
                f"📋 Оффер для продукта <b>{product_name}</b>\n"
                f"🔄 Статус: {new_status}\n"
                f"📅 Время: {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}"
            )
        else:
            result_text = (
                f"❌ <b>Ошибка изменения статуса</b>\n\n"
                f"Не удалось изменить статус оффера"
            )
        
        # Используем короткие callback'и
        short_id = str(offer_id).replace('-', '')[:16]
        keyboard = [
            [InlineKeyboardButton("👁️ Просмотр оффера", callback_data=f"admin_to_view_{short_id}")],
            [InlineKeyboardButton("🔙 К управлению", callback_data="admin_tripwire_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, result_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка переключения статуса оффера {offer_id}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка изменения статуса")


async def _handle_delete_offer_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                      product_service: ProductService, offer_id: str, is_callback: bool = False) -> None:
    """Подтверждение удаления оффера."""
    try:
        offer = await product_service.get_offer_by_id(offer_id)
        if not offer:
            await _safe_edit_message(update, context, "❌ Оффер не найден")
            return
        
        product_name = offer.product.name if offer.product else "Неизвестный продукт"
        
        confirm_text = (
            f"⚠️ <b>ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ</b>\n\n"
            f"Вы действительно хотите удалить оффер?\n\n"
            f"📋 <b>Оффер</b>\n"
            f"📦 Продукт: {product_name}\n"
            f"📅 Создан: {offer.created_at.strftime('%d.%m.%Y')}\n\n"
            f"🚨 <b>ВНИМАНИЕ!</b>\n"
            f"• Оффер будет удален навсегда\n"
            f"• Статистика по офферу будет потеряна\n"
            f"• Пользователи не смогут получить этот оффер\n"
            f"• Действие необратимо\n\n"
            f"❓ Продолжить удаление?"
        )
        
        # Используем короткие callback'и  
        short_id = str(offer_id).replace('-', '')[:16]
        keyboard = [
            [
                InlineKeyboardButton("🗑️ ДА, УДАЛИТЬ", callback_data=f"admin_to_confirm_{short_id}"),
                InlineKeyboardButton("❌ Отмена", callback_data=f"admin_to_view_{short_id}")
            ],
            [InlineKeyboardButton("🔙 К офферам", callback_data="admin_tripwire_offers")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, confirm_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка подтверждения удаления оффера {offer_id}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка подтверждения удаления")


async def _handle_delete_offer_final(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    product_service: ProductService, offer_id: str, is_callback: bool = False) -> None:
    """Финальное удаление оффера."""
    try:
        offer = await product_service.get_offer_by_id(offer_id)
        if not offer:
            await _safe_edit_message(update, context, "❌ Оффер не найден")
            return
        
        product_name = offer.product.name if offer.product else "Неизвестный продукт"
        success = await product_service.delete_offer(offer_id)
        
        if success:
            result_text = (
                f"✅ <b>Оффер удален</b>\n\n"
                f"📋 Оффер для продукта <b>{product_name}</b> был успешно удален\n"
                f"📅 Время удаления: {datetime.utcnow().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"🗂️ Все связанные данные очищены"
            )
        else:
            result_text = (
                f"❌ <b>Ошибка удаления</b>\n\n"
                f"Не удалось удалить оффер\n"
                f"Попробуйте позже или обратитесь к разработчику"
            )
        
        keyboard = [
            [InlineKeyboardButton("📋 К списку офферов", callback_data="admin_tripwire_offers")],
            [InlineKeyboardButton("🔙 К управлению", callback_data="admin_tripwire_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, result_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка финального удаления оффера {offer_id}: {e}")
        await _safe_edit_message(update, context, "❌ Критическая ошибка удаления")


async def _handle_ritual_action(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               action: str, is_callback: bool = False) -> None:
    """Обработка действий с ритуалами."""
    try:
        async for session in get_database():
            ritual_service = RitualService(session)
            user_service = UserService(session)
            
            if action == "admin_ritual_morning":
                await _handle_ritual_type_management(update, context, ritual_service, "morning", is_callback=True)
            elif action == "admin_ritual_evening":
                await _handle_ritual_type_management(update, context, ritual_service, "evening", is_callback=True)
            elif action == "admin_ritual_weekly_goals":
                await _handle_ritual_type_management(update, context, ritual_service, "weekly_goals", is_callback=True)
            elif action == "admin_ritual_challenges":
                await _handle_ritual_type_management(update, context, ritual_service, "weekly_challenge", is_callback=True)
            elif action == "admin_ritual_cycles":
                await _handle_ritual_type_management(update, context, ritual_service, "friday_cycle", is_callback=True)
            elif action == "admin_ritual_schedule":
                await _handle_ritual_schedule(update, context, ritual_service, is_callback=True)
            elif action == "admin_ritual_stats":
                await _handle_ritual_statistics(update, context, ritual_service, is_callback=True)
            elif action == "admin_ritual_global":
                await _handle_ritual_global_settings(update, context, ritual_service, is_callback=True)
            else:
                await _safe_edit_message(update, context, f"🔧 Функция '{action}' в разработке...")
                
    except Exception as e:
        logger.error(f"Ошибка обработки действий с ритуалами {action}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка выполнения действия с ритуалами")


async def _handle_ritual_type_management(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                      ritual_service: "RitualService", ritual_type: str, is_callback: bool = False) -> None:
    """Управление конкретным типом ритуалов."""
    try:
        from app.models.ritual import RitualType
        
        # Конвертируем строку в enum
        type_mapping = {
            "morning": RitualType.MORNING,
            "evening": RitualType.EVENING,
            "weekly_goals": RitualType.WEEKLY_GOALS,
            "weekly_challenge": RitualType.WEEKLY_CHALLENGE,
            "friday_cycle": RitualType.FRIDAY_CYCLE
        }
        
        ritual_type_enum = type_mapping.get(ritual_type)
        if not ritual_type_enum:
            await _safe_edit_message(update, context, "❌ Неизвестный тип ритуала")
            return
        
        # Получаем ритуалы этого типа
        rituals = await ritual_service.get_active_rituals(ritual_type_enum)
        
        type_names = {
            "morning": "🌅 Утренние ритуалы",
            "evening": "🌙 Вечерние ритуалы", 
            "weekly_goals": "🎯 Цели на неделю",
            "weekly_challenge": "💪 Еженедельные вызовы",
            "friday_cycle": "🔄 Пятничные циклы"
        }
        
        message_text = f"{type_names[ritual_type]}\n\n"
        
        if rituals:
            for ritual in rituals[:5]:  # Показываем первые 5
                status = "🟢" if ritual.is_active else "🔴"
                time_str = f"{ritual.send_hour:02d}:{ritual.send_minute:02d}"
                weekday_str = ""
                if ritual.weekday is not None:
                    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                    weekday_str = f" ({days[ritual.weekday]})"
                
                message_text += f"{status} {ritual.name}\n"
                message_text += f"   ⏰ {time_str}{weekday_str}\n"
                message_text += f"   📝 {ritual.description or 'Без описания'}\n\n"
        else:
            message_text += "📭 Ритуалы этого типа не найдены\n\n"
        
        message_text += f"📊 Всего ритуалов: {len(rituals)}"
        
        keyboard = [
            [InlineKeyboardButton("🟢 Включить все", callback_data=f"admin_ritual_enable_{ritual_type}")],
            [InlineKeyboardButton("🔴 Выключить все", callback_data=f"admin_ritual_disable_{ritual_type}")],
            [InlineKeyboardButton("⚙️ Настроить время", callback_data=f"admin_ritual_time_{ritual_type}")],
            [InlineKeyboardButton("📊 Статистика", callback_data=f"admin_ritual_stats_{ritual_type}")],
            [InlineKeyboardButton("🔙 К управлению ритуалами", callback_data="admin_rituals_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка управления ритуалами типа {ritual_type}: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки ритуалов")


async def _handle_ritual_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  ritual_service: "RitualService", is_callback: bool = False) -> None:
    """Статистика ритуалов."""
    try:
        # Получаем все активные ритуалы
        rituals = await ritual_service.get_active_rituals()
        
        total_rituals = len(rituals)
        total_participants = 0
        total_sent = 0
        total_responses = 0
        
        message_text = "📊 СТАТИСТИКА РИТУАЛОВ\n\n"
        
        for ritual in rituals:
            try:
                # Упрощенная статистика без get_ritual_stats
                message_text += f"📌 {ritual.name}\n"
                message_text += f"   📅 {ritual.type.value}\n"
                message_text += f"   ⏰ {ritual.send_hour:02d}:{ritual.send_minute:02d}\n"
                if ritual.weekday is not None:
                    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                    message_text += f"   📆 {days[ritual.weekday]}\n"
                message_text += f"   🟢 Активен: {'Да' if ritual.is_active else 'Нет'}\n\n"
            except Exception as e:
                logger.error(f"Ошибка получения статистики ритуала {ritual.name}: {e}")
        
        message_text += f"📈 ОБЩАЯ СТАТИСТИКА:\n"
        message_text += f"🔮 Всего ритуалов: {total_rituals}\n"
        message_text += f"🟢 Активных: {sum(1 for r in rituals if r.is_active)}\n"
        message_text += f"🔴 Неактивных: {sum(1 for r in rituals if not r.is_active)}\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_ritual_stats")],
            [InlineKeyboardButton("📋 Экспорт данных", callback_data="admin_ritual_export")],
            [InlineKeyboardButton("🔙 К управлению ритуалами", callback_data="admin_rituals_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики ритуалов: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки статистики")


async def _handle_ritual_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                ritual_service: "RitualService", is_callback: bool = False) -> None:
    """Настройка расписания ритуалов."""
    try:
        rituals = await ritual_service.get_active_rituals()
        
        message_text = "⏰ РАСПИСАНИЕ РИТУАЛОВ\n\n"
        
        # Группируем по времени
        schedule_map = {}
        for ritual in rituals:
            time_key = f"{ritual.send_hour:02d}:{ritual.send_minute:02d}"
            if time_key not in schedule_map:
                schedule_map[time_key] = []
            schedule_map[time_key].append(ritual)
        
        # Сортируем по времени
        for time_str in sorted(schedule_map.keys()):
            message_text += f"🕐 {time_str}\n"
            for ritual in schedule_map[time_str]:
                weekday_str = ""
                if ritual.weekday is not None:
                    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                    weekday_str = f" ({days[ritual.weekday]})"
                message_text += f"   • {ritual.name}{weekday_str}\n"
            message_text += "\n"
        
        keyboard = [
            [InlineKeyboardButton("⏰ Изменить время", callback_data="admin_ritual_change_time")],
            [InlineKeyboardButton("🔄 Синхронизация", callback_data="admin_ritual_sync")],
            [InlineKeyboardButton("📅 Календарь", callback_data="admin_ritual_calendar")],
            [InlineKeyboardButton("🔙 К управлению ритуалами", callback_data="admin_rituals_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки расписания ритуалов: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки расписания")


async def _handle_ritual_global_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                       ritual_service: "RitualService", is_callback: bool = False) -> None:
    """Глобальные настройки ритуалов."""
    try:
        rituals = await ritual_service.get_active_rituals()
        active_count = sum(1 for r in rituals if r.is_active)
        inactive_count = len(rituals) - active_count
        
        message_text = "🔧 ГЛОБАЛЬНЫЕ НАСТРОЙКИ РИТУАЛОВ\n\n"
        message_text += f"📊 Состояние системы:\n"
        message_text += f"🟢 Активных ритуалов: {active_count}\n"
        message_text += f"🔴 Неактивных ритуалов: {inactive_count}\n"
        message_text += f"🔮 Всего ритуалов: {len(rituals)}\n\n"
        
        message_text += "⚙️ Доступные действия:\n"
        message_text += "• Массовое включение/выключение\n"
        message_text += "• Сброс статистики\n"
        message_text += "• Пересоздание ритуалов\n"
        message_text += "• Управление планировщиком\n"
        
        keyboard = [
            [InlineKeyboardButton("🟢 Включить все ритуалы", callback_data="admin_ritual_enable_all")],
            [InlineKeyboardButton("🔴 Выключить все ритуалы", callback_data="admin_ritual_disable_all")],
            [InlineKeyboardButton("📊 Сброс статистики", callback_data="admin_ritual_reset_stats")],
            [InlineKeyboardButton("🔄 Перезапуск планировщика", callback_data="admin_ritual_restart_scheduler")],
            [InlineKeyboardButton("🆕 Пересоздать базовые ритуалы", callback_data="admin_ritual_recreate")],
            [InlineKeyboardButton("🔙 К управлению ритуалами", callback_data="admin_rituals_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки глобальных настроек ритуалов: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки настроек")


async def _handle_restart_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    """Перезапуск задач планировщика."""
    await _safe_edit_message(update, context, "🔄 Перезапуск задач планировщика...")


async def _handle_lead_magnet_create_form(update: Update, context: ContextTypes.DEFAULT_TYPE, lead_magnet_service: "LeadMagnetService", is_callback: bool = False) -> None:
    """Форма создания лид магнита."""
    # Очищаем предыдущие данные создания
    context.user_data.pop('creating_lead_magnet', None)
    
    message_text = (
        "➕ <b>Создание нового лид магнита</b>\n\n"
        "📝 <b>Что нужно указать:</b>\n"
        "• Название лид магнита\n"
        "• Описание\n"
        "• Тип (PDF, Google Sheet, ссылка, текст)\n"
        "• Ссылку на файл (если есть)\n"
        "• Текст сообщения при выдаче\n\n"
        "💡 <b>Примеры успешных лид магнитов:</b>\n"
        "• Чек-листы и трекеры\n"
        "• Гайды и инструкции\n"
        "• Шаблоны и инструменты\n"
        "• Мотивирующие материалы\n\n"
        "🎯 <b>Начнем создание!</b>\n"
        "Выберите тип лид магнита:"
    )
    
    keyboard = [
        [InlineKeyboardButton("📄 PDF документ", callback_data="admin_lead_magnet_create_type_pdf")],
        [InlineKeyboardButton("📊 Google Sheet", callback_data="admin_lead_magnet_create_type_google_sheet")],
        [InlineKeyboardButton("🔗 Ссылка", callback_data="admin_lead_magnet_create_type_link")],
        [InlineKeyboardButton("📝 Текст", callback_data="admin_lead_magnet_create_type_text")],
        [InlineKeyboardButton("🔙 К управлению лид магнитами", callback_data="admin_content_leadmagnets")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await _safe_edit_message(update, context, message_text, reply_markup)


async def _handle_lead_magnet_list(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  lead_magnet_service: "LeadMagnetService", is_callback: bool = False) -> None:
    """Список всех лид магнитов."""
    try:
        # Получаем все лид магниты
        all_magnets = await lead_magnet_service.get_all_lead_magnets()
        
        if not all_magnets:
            message_text = "📭 Лид магниты не найдены\n\nНажмите 'Создать лид магнит' для добавления первого."
            keyboard = [
                [InlineKeyboardButton("➕ Создать лид магнит", callback_data="admin_lead_magnet_create")],
                [InlineKeyboardButton("🔙 К управлению лид магнитами", callback_data="admin_content_leadmagnets")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await _safe_edit_message(update, context, message_text, reply_markup)
            return
        
        message_text = "📋 <b>Все лид магниты</b>\n\n"
        
        for i, magnet in enumerate(all_magnets, 1):
            status = "🟢" if magnet.is_active else "🔴"
            
            # Безопасно получаем тип для отображения
            if hasattr(magnet.type, 'value'):
                type_value = magnet.type.value
            else:
                type_value = str(magnet.type)
            
            type_icon = {
                "pdf": "📄",
                "google_sheet": "📊", 
                "link": "🔗",
                "text": "📝"
            }.get(type_value, "📁")
            
            message_text += f"{i}. {status} {type_icon} <b>{magnet.name}</b>\n"
            message_text += f"   📝 {magnet.description[:60]}...\n"
            message_text += f"   📊 Тип: {type_value}\n"
            message_text += f"   🎯 Порядок: {magnet.sort_order}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Создать новый", callback_data="admin_lead_magnet_create")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_lead_magnet_list")],
            [InlineKeyboardButton("🔙 К управлению лид магнитами", callback_data="admin_content_leadmagnets")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки списка лид магнитов: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки списка лид магнитов")


async def _handle_lead_magnet_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                           lead_magnet_service: "LeadMagnetService", is_callback: bool = False) -> None:
    """Детальная статистика лид магнитов."""
    try:
        # Получаем статистику
        stats = await lead_magnet_service.get_lead_magnet_stats()
        
        message_text = "📊 <b>Детальная статистика лид магнитов</b>\n\n"
        
        message_text += f"📈 <b>Общие показатели:</b>\n"
        message_text += f"• Всего выдано: {stats.get('total_issued', 0)}\n"
        message_text += f"• Уникальных пользователей: {stats.get('unique_users', 0)}\n"
        message_text += f"• Активных лид магнитов: {stats.get('active_lead_magnets', 0)}\n\n"
        
        # Статистика по типам
        type_stats = stats.get('type_stats', {})
        if type_stats:
            message_text += f"📊 <b>Статистика по лид магнитам:</b>\n"
            for magnet_name, issued_count in type_stats.items():
                message_text += f"• {magnet_name}: {issued_count} выдач\n"
            message_text += "\n"
        
        # Получаем активные лид магниты для дополнительной информации
        active_magnets = await lead_magnet_service.get_active_lead_magnets()
        if active_magnets:
            message_text += f"🎁 <b>Активные лид магниты:</b>\n"
            for magnet in active_magnets:
                # Безопасно получаем тип для отображения
                if hasattr(magnet.type, 'value'):
                    type_display = magnet.type.value
                else:
                    type_display = str(magnet.type)
                message_text += f"• {magnet.name} ({type_display})\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_lead_magnet_stats")],
            [InlineKeyboardButton("📋 Экспорт данных", callback_data="admin_lead_magnet_export")],
            [InlineKeyboardButton("🔙 К управлению лид магнитами", callback_data="admin_content_leadmagnets")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки детальной статистики лид магнитов: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки статистики")


async def _handle_lead_magnet_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     lead_magnet_service: "LeadMagnetService", is_callback: bool = False) -> None:
    """Настройки лид магнитов."""
    try:
        # Получаем все лид магниты
        all_magnets = await lead_magnet_service.get_all_lead_magnets()
        active_count = sum(1 for m in all_magnets if m.is_active)
        inactive_count = len(all_magnets) - active_count
        
        message_text = "⚙️ <b>Настройки лид магнитов</b>\n\n"
        message_text += f"📊 <b>Состояние системы:</b>\n"
        message_text += f"• Всего лид магнитов: {len(all_magnets)}\n"
        message_text += f"• Активных: {active_count}\n"
        message_text += f"• Неактивных: {inactive_count}\n\n"
        
        message_text += "🔧 <b>Доступные действия:</b>\n"
        message_text += "• Массовое включение/выключение\n"
        message_text += "• Изменение порядка сортировки\n"
        message_text += "• Сброс статистики\n"
        message_text += "• Управление типами\n"
        
        keyboard = [
            [InlineKeyboardButton("🟢 Включить все", callback_data="admin_lead_magnet_enable_all")],
            [InlineKeyboardButton("🔴 Выключить все", callback_data="admin_lead_magnet_disable_all")],
            [InlineKeyboardButton("📊 Сброс статистики", callback_data="admin_lead_magnet_reset_stats")],
            [InlineKeyboardButton("🔄 Пересоздать базовые", callback_data="admin_lead_magnet_recreate")],
            [InlineKeyboardButton("🔙 К управлению лид магнитами", callback_data="admin_content_leadmagnets")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки настроек лид магнитов: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки настроек")


async def _handle_logs_view(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    """Просмотр логов."""
    try:
        import os
        log_file = "logs/bot.log"
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_lines = ''.join(lines[-10:])  # Последние 10 строк
                
            logs_text = f"📋 <b>Последние логи:</b>\n\n<code>{last_lines}</code>"
        else:
            logs_text = "📋 <b>Логи не найдены</b>"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, logs_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка просмотра логов: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки логов")


# Функции для многошагового создания лид магнитов

async def _handle_lead_magnet_create_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                                  action: str, lead_magnet_service: "LeadMagnetService", 
                                                  is_callback: bool = False) -> None:
    """Выбор типа лид магнита."""
    try:
        # Извлекаем тип из callback data
        magnet_type = action.replace("admin_lead_magnet_create_type_", "")
        
        # Инициализируем данные создания
        context.user_data['creating_lead_magnet'] = {
            'type': magnet_type,
            'step': 'name'
        }
        
        type_names = {
            'pdf': '📄 PDF документ',
            'google_sheet': '📊 Google Sheet',
            'link': '🔗 Ссылка',
            'text': '📝 Текст'
        }
        
        message_text = (
            f"✅ <b>Выбран тип: {type_names.get(magnet_type, magnet_type)}</b>\n\n"
            "📝 <b>Шаг 1: Название лид магнита</b>\n\n"
            "Введите название лид магнита (например: '7-дневный трекер дисциплины')\n\n"
            "💡 <b>Советы:</b>\n"
            "• Используйте четкие, понятные названия\n"
            "• Указывайте ценность для пользователя\n"
            "• Держите название в пределах 50 символов"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к выбору типа", callback_data="admin_lead_magnet_create")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_leadmagnets")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка выбора типа лид магнита: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка выбора типа лид магнита")


async def _handle_lead_magnet_create_name_step(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                             lead_magnet_service: "LeadMagnetService", 
                                             is_callback: bool = False) -> None:
    """Шаг ввода названия лид магнита."""
    try:
        # Проверяем, что у нас есть данные создания
        if 'creating_lead_magnet' not in context.user_data:
            await _safe_edit_message(update, context, "❌ Ошибка: данные создания не найдены")
            return
        
        message_text = (
            "📝 <b>Введите название лид магнита</b>\n\n"
            "Отправьте сообщение с названием лид магнита.\n\n"
            "💡 <b>Примеры хороших названий:</b>\n"
            "• 7-дневный трекер дисциплины\n"
            "• Утренняя рутина чемпиона\n"
            "• Как ставить и достигать цели\n"
            "• Еженедельный план действий\n"
            "• 50 мотивирующих цитат"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к выбору типа", callback_data="admin_lead_magnet_create")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_leadmagnets")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка шага ввода названия: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка ввода названия")


async def _handle_lead_magnet_create_description_step(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                                    lead_magnet_service: "LeadMagnetService", 
                                                    is_callback: bool = False) -> None:
    """Шаг ввода описания лид магнита."""
    try:
        message_text = (
            "📝 <b>Введите описание лид магнита</b>\n\n"
            "Отправьте сообщение с описанием.\n\n"
            "💡 <b>Что включить в описание:</b>\n"
            "• Что получит пользователь\n"
            "• Как это поможет в развитии\n"
            "• Формат и объем материала\n"
            "• Время на изучение\n\n"
            "💡 <b>Пример описания:</b>\n"
            "Чек-лист из 21 пункта для формирования утренней рутины. "
            "Поможет структурировать утро и повысить продуктивность дня."
        )
        
        keyboard = [
            [InlineKeyboardButton("⏭️ Пропустить описание", callback_data="admin_lead_magnet_create_file_url")],
            [InlineKeyboardButton("🔙 Назад к названию", callback_data="admin_lead_magnet_create_name")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_leadmagnets")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка шага ввода описания: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка ввода описания")


async def _handle_lead_magnet_create_file_url_step(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                                 lead_magnet_service: "LeadMagnetService", 
                                                 is_callback: bool = False) -> None:
    """Шаг ввода ссылки на файл."""
    try:
        magnet_type = context.user_data.get('creating_lead_magnet', {}).get('type', 'text')
        
        if magnet_type == 'text':
            # Для текстовых лид магнитов пропускаем этот шаг
            await _handle_lead_magnet_create_message_step(update, context, lead_magnet_service, is_callback=True)
            return
        
        type_info = {
            'pdf': 'PDF документ (Google Drive, Dropbox, прямая ссылка)',
            'google_sheet': 'Google Sheet (ссылка на таблицу)',
            'link': 'Веб-страница или ресурс'
        }
        
        message_text = (
            f"🔗 <b>Введите ссылку на {type_info.get(magnet_type, 'файл')}</b>\n\n"
            "Отправьте сообщение со ссылкой.\n\n"
            "💡 <b>Требования к ссылкам:</b>\n"
            "• Должна быть публично доступной\n"
            "• Для Google Drive: настройте доступ 'Кто угодно с ссылкой'\n"
            "• Для PDF: убедитесь, что файл не требует авторизации\n\n"
            "💡 <b>Примеры ссылок:</b>\n"
            "• https://drive.google.com/file/d/...\n"
            "• https://docs.google.com/spreadsheets/d/...\n"
            "• https://example.com/guide.pdf"
        )
        
        keyboard = [
            [InlineKeyboardButton("⏭️ Пропустить ссылку", callback_data="admin_lead_magnet_create_message")],
            [InlineKeyboardButton("🔙 Назад к описанию", callback_data="admin_lead_magnet_create_description")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_leadmagnets")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка шага ввода ссылки: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка ввода ссылки")


async def _handle_lead_magnet_create_message_step(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                                lead_magnet_service: "LeadMagnetService", 
                                                is_callback: bool = False) -> None:
    """Шаг ввода текста сообщения при выдаче."""
    try:
        message_text = (
            "💬 <b>Введите текст сообщения при выдаче</b>\n\n"
            "Отправьте сообщение, которое будет показано пользователю при выдаче лид магнита.\n\n"
            "💡 <b>Что включить в сообщение:</b>\n"
            "• Благодарность за интерес\n"
            "• Краткое описание ценности\n"
            "• Инструкции по использованию\n"
            "• Призыв к действию\n\n"
            "💡 <b>Пример сообщения:</b>\n"
            "🎁 Спасибо! Вот ваш трекер дисциплины.\n\n"
            "📋 Распечатайте и заполняйте каждый день. "
            "Это поможет отслеживать прогресс и формировать полезные привычки.\n\n"
            "💪 Удачи в развитии дисциплины!"
        )
        
        keyboard = [
            [InlineKeyboardButton("⏭️ Использовать шаблон", callback_data="admin_lead_magnet_create_confirm")],
            [InlineKeyboardButton("🔙 Назад к ссылке", callback_data="admin_lead_magnet_create_file_url")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_leadmagnets")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка шага ввода сообщения: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка ввода сообщения")


async def _handle_lead_magnet_create_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                           lead_magnet_service: "LeadMagnetService", 
                                           is_callback: bool = False) -> None:
    """Подтверждение создания лид магнита."""
    try:
        # Получаем данные создания
        creating_data = context.user_data.get('creating_lead_magnet', {})
        
        if not creating_data:
            await _safe_edit_message(update, context, "❌ Ошибка: данные создания не найдены")
            return
        
        # Формируем предварительный просмотр
        type_names = {
            'pdf': '📄 PDF',
            'google_sheet': '📊 Google Sheet',
            'link': '🔗 Ссылка',
            'text': '📝 Текст'
        }
        
        message_text = (
            "✅ <b>Предварительный просмотр лид магнита</b>\n\n"
            f"📝 <b>Название:</b> {creating_data.get('name', 'Не указано')}\n"
            f"📄 <b>Тип:</b> {type_names.get(creating_data.get('type'), creating_data.get('type'))}\n"
            f"📋 <b>Описание:</b> {creating_data.get('description', 'Не указано')[:100]}...\n"
            f"🔗 <b>Ссылка:</b> {'Указана' if creating_data.get('file_url') else 'Не указана'}\n"
            f"💬 <b>Сообщение:</b> {creating_data.get('message_text', 'Не указано')[:100]}...\n\n"
            "🎯 <b>Создать лид магнит?</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Создать лид магнит", callback_data="admin_lead_magnet_create_final")],
            [InlineKeyboardButton("🔙 Назад к редактированию", callback_data="admin_lead_magnet_create_message")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_leadmagnets")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка подтверждения создания: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка подтверждения создания")


async def _handle_lead_magnet_create_final(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                         lead_magnet_service: "LeadMagnetService", 
                                         is_callback: bool = False) -> None:
    """Финальное создание лид магнита."""
    try:
        # Получаем данные создания
        creating_data = context.user_data.get('creating_lead_magnet', {})
        
        if not creating_data:
            await _safe_edit_message(update, context, "❌ Ошибка: данные создания не найдены")
            return
        
        # Проверяем обязательные поля
        if not creating_data.get('name'):
            await _safe_edit_message(update, context, "❌ Ошибка: название обязательно для заполнения")
            return
        
        # Создаем схему для создания лид магнита
        from app.schemas.lead_magnet import LeadMagnetCreate
        
        lead_magnet_data = LeadMagnetCreate(
            name=creating_data['name'],
            description=creating_data.get('description'),
            type=creating_data['type'],
            file_url=creating_data.get('file_url'),
            message_text=creating_data.get('message_text') or f"🎁 Вот ваш {creating_data['name']}!",
            is_active=True,
            sort_order=0
        )
        
        # Создаем лид магнит
        new_lead_magnet = await lead_magnet_service.create_lead_magnet(lead_magnet_data)
        
        # Очищаем данные создания
        context.user_data.pop('creating_lead_magnet', None)
        
        # Получаем читаемое название типа
        type_names = {
            'pdf': '📄 PDF',
            'google_sheet': '📊 Google Sheet',
            'link': '🔗 Ссылка',
            'text': '📝 Текст'
        }
        
        # Проверяем, является ли type enum объектом или строкой
        if hasattr(new_lead_magnet.type, 'value'):
            type_display = type_names.get(new_lead_magnet.type.value, new_lead_magnet.type.value)
        else:
            type_display = type_names.get(str(new_lead_magnet.type), str(new_lead_magnet.type))
        
        message_text = (
            "✅ <b>Лид магнит успешно создан!</b>\n\n"
            f"📝 <b>Название:</b> {new_lead_magnet.name}\n"
            f"📄 <b>Тип:</b> {type_display}\n"
            f"🆔 <b>ID:</b> {new_lead_magnet.id}\n\n"
            "🎯 <b>Что дальше:</b>\n"
            "• Лид магнит автоматически активен\n"
            "• Пользователи могут получить его командой /gift\n"
            "• Вы можете управлять им в админ панели"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 К списку лид магнитов", callback_data="admin_lead_magnet_list")],
            [InlineKeyboardButton("➕ Создать еще один", callback_data="admin_lead_magnet_create")],
            [InlineKeyboardButton("🔙 К управлению лид магнитами", callback_data="admin_content_leadmagnets")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка создания лид магнита: {e}")
        await _safe_edit_message(update, context, f"❌ Ошибка создания лид магнита: {str(e)}")


async def _handle_messages_management(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    is_callback: bool = False) -> None:
    """Управление текстовыми шаблонами сообщений."""
    try:
        message_text = (
            "📝 <b>Управление текстовыми шаблонами</b>\n\n"
            "🎯 <b>Что можно настроить:</b>\n"
            "• Приветственные сообщения\n"
            "• Сообщения об ошибках\n"
            "• Уведомления и напоминания\n"
            "• Шаблоны для лид магнитов\n"
            "• Тексты для прогрева\n"
            "• Системные сообщения\n\n"
            "📊 <b>Статистика:</b>\n"
            "• Всего шаблонов: 0\n"
            "• Активных шаблонов: 0\n"
            "• Последнее обновление: Сегодня\n\n"
            "🔧 <b>Выберите действие:</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 Все шаблоны", callback_data="admin_messages_list")],
            [InlineKeyboardButton("➕ Создать шаблон", callback_data="admin_messages_create")],
            [InlineKeyboardButton("🔍 Поиск шаблона", callback_data="admin_messages_search")],
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_messages_stats")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_messages_settings")],
            [InlineKeyboardButton("🔙 К управлению контентом", callback_data="admin_content_manage")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if is_callback:
            await _safe_edit_message(update, context, message_text, reply_markup)
        else:
            await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='HTML')
            
    except Exception as e:
        logger.error(f"Ошибка управления текстовыми шаблонами: {e}")
        error_message = "❌ Ошибка управления текстовыми шаблонами"
        if is_callback:
            await _safe_edit_message(update, context, error_message)
        else:
            await update.message.reply_text(error_message)


async def _handle_messages_action(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                action: str, is_callback: bool = False) -> None:
    """Обработка действий с текстовыми шаблонами."""
    try:
        query = update.callback_query
        
        if action == "admin_messages_list":
            await _handle_messages_list(update, context, is_callback=True)
        elif action == "admin_messages_create":
            await _handle_messages_create_form(update, context, is_callback=True)
        elif action == "admin_messages_search":
            await _handle_messages_search_form(update, context, is_callback=True)
        elif action == "admin_messages_stats":
            await _handle_messages_stats(update, context, is_callback=True)
        elif action == "admin_messages_settings":
            await _handle_messages_settings(update, context, is_callback=True)
        elif action.startswith("admin_messages_category_"):
            await _handle_messages_category_selection(update, context, action, is_callback=True)
        elif action == "admin_messages_create_final":
            await _handle_messages_create_final(update, context, is_callback=True)
        elif action == "admin_messages_create_confirm":
            await _handle_messages_create_confirm(update, context, is_callback=True)
        elif action == "admin_messages_html_examples":
            await _handle_messages_html_examples(update, context, is_callback=True)
        else:
            await _safe_edit_message(update, context, "❌ Неизвестное действие")
            
    except Exception as e:
        logger.error(f"Ошибка обработки действия с шаблонами: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка обработки действия")


async def _handle_messages_list(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               is_callback: bool = False) -> None:
    """Список всех текстовых шаблонов."""
    try:
        message_text = (
            "📋 <b>Все текстовые шаблоны</b>\n\n"
            "📭 Шаблоны не найдены\n\n"
            "💡 <b>Создайте первый шаблон:</b>\n"
            "• Приветственное сообщение\n"
            "• Сообщение об ошибке\n"
            "• Уведомление пользователя"
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Создать шаблон", callback_data="admin_messages_create")],
            [InlineKeyboardButton("🔙 К управлению шаблонами", callback_data="admin_content_messages")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки списка шаблонов: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки списка шаблонов")


async def _handle_messages_create_form(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     is_callback: bool = False) -> None:
    """Форма создания текстового шаблона."""
    try:
        message_text = (
            "➕ <b>Создание текстового шаблона</b>\n\n"
            "📝 <b>Введите название шаблона:</b>\n"
            "Например: 'Приветствие', 'Ошибка 404', 'Уведомление'"
        )
        
        # Устанавливаем состояние создания шаблона
        context.user_data['creating_message_template'] = {
            'step': 'name',
            'name': '',
            'category': '',
            'content': ''
        }
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_messages")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка создания формы шаблона: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка создания формы")


async def _handle_messages_search_form(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     is_callback: bool = False) -> None:
    """Форма поиска текстового шаблона."""
    try:
        message_text = (
            "🔍 <b>Поиск текстового шаблона</b>\n\n"
            "📝 <b>Введите название или часть текста для поиска:</b>\n"
            "Поиск будет выполнен по названию и содержимому шаблона"
        )
        
        # Устанавливаем состояние поиска
        context.user_data['searching_message_template'] = {
            'step': 'search'
        }
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить поиск", callback_data="admin_content_messages")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка создания формы поиска: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка создания формы поиска")


async def _handle_messages_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                is_callback: bool = False) -> None:
    """Статистика текстовых шаблонов."""
    try:
        message_text = (
            "📊 <b>Статистика текстовых шаблонов</b>\n\n"
            "📈 <b>Общие показатели:</b>\n"
            "• Всего шаблонов: 0\n"
            "• Активных шаблонов: 0\n"
            "• Неактивных шаблонов: 0\n\n"
            "📊 <b>По категориям:</b>\n"
            "• Приветствия: 0\n"
            "• Ошибки: 0\n"
            "• Уведомления: 0\n"
            "• Системные: 0\n\n"
            "📅 <b>Последние изменения:</b>\n"
            "• Создано: 0\n"
            "• Обновлено: 0\n"
            "• Удалено: 0"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 К списку шаблонов", callback_data="admin_messages_list")],
            [InlineKeyboardButton("🔙 К управлению шаблонами", callback_data="admin_content_messages")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки статистики: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки статистики")


async def _handle_messages_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  is_callback: bool = False) -> None:
    """Настройки текстовых шаблонов."""
    try:
        message_text = (
            "⚙️ <b>Настройки текстовых шаблонов</b>\n\n"
            "🔧 <b>Доступные настройки:</b>\n"
            "• Автоматическое создание резервных копий\n"
            "• Экспорт/импорт шаблонов\n"
            "• Настройка уведомлений об изменениях\n"
            "• Управление правами доступа\n\n"
            "📝 <b>Выберите действие:</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("💾 Создать резервную копию", callback_data="admin_messages_backup")],
            [InlineKeyboardButton("📤 Экспорт шаблонов", callback_data="admin_messages_export")],
            [InlineKeyboardButton("📥 Импорт шаблонов", callback_data="admin_messages_import")],
            [InlineKeyboardButton("🔔 Настройки уведомлений", callback_data="admin_messages_notifications")],
            [InlineKeyboardButton("🔐 Права доступа", callback_data="admin_messages_permissions")],
            [InlineKeyboardButton("🔙 К управлению шаблонами", callback_data="admin_content_messages")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки настроек: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка загрузки настроек")


async def _handle_messages_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                            action: str, is_callback: bool = False) -> None:
    """Обработка выбора категории текстового шаблона."""
    try:
        # Извлекаем категорию из action
        category = action.replace("admin_messages_category_", "")
        
        # Определяем читаемые названия категорий
        category_names = {
            'welcome': 'Приветствие',
            'error': 'Ошибка',
            'notification': 'Уведомление',
            'system': 'Системное'
        }
        
        category_name = category_names.get(category, category)
        
        # Сохраняем выбранную категорию
        if 'creating_message_template' in context.user_data:
            context.user_data['creating_message_template']['category'] = category
            context.user_data['creating_message_template']['step'] = 'content'
        
        message_text = (
            f"✅ <b>Категория выбрана:</b> {category_name}\n\n"
            "📝 <b>Следующий шаг: Содержимое шаблона</b>\n\n"
            "Введите текст шаблона. Можно использовать HTML-разметку для форматирования."
        )
        
        keyboard = [
            [InlineKeyboardButton("💡 Примеры HTML", callback_data="admin_messages_html_examples")],
            [InlineKeyboardButton("🔙 Назад к категории", callback_data="admin_messages_create")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_messages")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка выбора категории: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка выбора категории")


async def _handle_messages_html_examples(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                       is_callback: bool = False) -> None:
    """Показ примеров HTML-разметки для текстовых шаблонов."""
    try:
        message_text = (
            "💡 <b>Примеры HTML-разметки</b>\n\n"
            "📝 <b>Основные теги:</b>\n"
            "• <b>Жирный текст</b> - <code>&lt;b&gt;текст&lt;/b&gt;</code>\n"
            "• <i>Курсив</i> - <code>&lt;i&gt;текст&lt;/i&gt;</code>\n"
            "• <code>Моноширинный</code> - <code>&lt;code&gt;текст&lt;/code&gt;</code>\n"
            "• <pre>Блок кода</pre> - <code>&lt;pre&gt;текст&lt;/pre&gt;</code>\n"
            "• <a href='https://example.com'>Ссылка</a> - <code>&lt;a href='URL'&gt;текст&lt;/a&gt;</code>\n\n"
            "🎨 <b>Примеры использования:</b>\n"
            "• <b>Важно!</b> Это важное сообщение\n"
            "• <i>Подсказка:</i> Это подсказка для пользователя\n"
            "• <code>Команда:</code> /start для начала работы\n\n"
            "⚠️ <b>Внимание:</b> Не все HTML-теги поддерживаются Telegram"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к созданию", callback_data="admin_messages_create")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_messages")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Ошибка показа HTML-примеров: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка показа HTML-примеров")


async def _handle_messages_create_final(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                      is_callback: bool = False) -> None:
    """Финальное создание текстового шаблона."""
    try:
        # Получаем данные создания
        creating_data = context.user_data.get('creating_message_template', {})
        
        if not creating_data:
            await _safe_edit_message(update, context, "❌ Ошибка: данные создания не найдены")
            return
        
        # Проверяем обязательные поля
        if not creating_data.get('name') or not creating_data.get('content'):
            await _safe_edit_message(update, context, "❌ Ошибка: название и содержимое обязательны")
            return
        
        # Показываем предварительный просмотр
        message_text = (
            "📋 <b>Предварительный просмотр шаблона</b>\n\n"
            f"📝 <b>Название:</b> {creating_data.get('name', 'Не указано')}\n"
            f"🏷️ <b>Категория:</b> {creating_data.get('category', 'Не указана')}\n"
            f"📄 <b>Содержимое:</b>\n{creating_data.get('content', 'Не указано')}\n\n"
            "🎯 <b>Создать текстовый шаблон?</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Создать шаблон", callback_data="admin_messages_create_confirm")],
            [InlineKeyboardButton("🔙 Назад к редактированию", callback_data="admin_messages_create")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_messages")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Ошибка финального создания: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка финального создания")


async def _handle_messages_create_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                        is_callback: bool = False) -> None:
    """Подтверждение создания текстового шаблона."""
    try:
        # Получаем данные создания
        creating_data = context.user_data.get('creating_message_template', {})
        
        if not creating_data:
            await _safe_edit_message(update, context, "❌ Ошибка: данные создания не найдены")
            return
        
        # Здесь будет логика создания шаблона в базе данных
        # Пока что просто показываем сообщение об успехе
        
        message_text = (
            "✅ <b>Текстовый шаблон успешно создан!</b>\n\n"
            f"📝 <b>Название:</b> {creating_data.get('name', 'Не указано')}\n"
            f"🏷️ <b>Категория:</b> {creating_data.get('category', 'Не указана')}\n"
            f"📄 <b>Содержимое:</b> {creating_data.get('content', 'Не указано')[:100]}...\n\n"
            "🎯 <b>Что дальше:</b>\n"
            "• Шаблон готов к использованию\n"
            "• Вы можете управлять им в админ панели\n"
            "• Создайте еще один шаблон или вернитесь к управлению"
        )
        
        # Очищаем данные создания
        context.user_data.pop('creating_message_template', None)
        
        keyboard = [
            [InlineKeyboardButton("📋 К списку шаблонов", callback_data="admin_messages_list")],
            [InlineKeyboardButton("➕ Создать еще один", callback_data="admin_messages_create")],
            [InlineKeyboardButton("🔙 К управлению шаблонами", callback_data="admin_content_messages")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Ошибка создания шаблона: {e}")
        await _safe_edit_message(update, context, f"❌ Ошибка создания шаблона: {str(e)}")


async def _handle_warmup_edit_action(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    warmup_service: "WarmupService", action: str, 
                                    is_callback: bool = False) -> None:
    """Обработка действий редактирования сценария прогрева."""
    try:
        # Извлекаем тип редактирования и ID
        parts = action.split("_")
        if len(parts) < 4:
            await _safe_edit_message(update, context, "❌ Ошибка: неверный формат действия")
            return
        
        edit_type = parts[3]  # name, desc, messages
        short_id = parts[4] if len(parts) > 4 else ""
        
        if edit_type == "name":
            await _handle_warmup_edit_name_form(update, context, warmup_service, short_id, is_callback=True)
        elif edit_type == "desc":
            await _handle_warmup_edit_desc_form(update, context, warmup_service, short_id, is_callback=True)
        elif edit_type == "messages":
            await _handle_warmup_edit_messages(update, context, warmup_service, short_id, is_callback=True)
        else:
            await _safe_edit_message(update, context, f"❌ Неизвестный тип редактирования: {edit_type}")
            
    except Exception as e:
        logger.error(f"Ошибка обработки действия редактирования: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка обработки действия редактирования")


async def _handle_warmup_edit_name_form(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                       warmup_service: "WarmupService", short_id: str, 
                                       is_callback: bool = False) -> None:
    """Форма редактирования названия сценария."""
    try:
        # Сохраняем состояние редактирования
        context.user_data['editing_warmup_scenario'] = {
            'type': 'name',
            'short_id': short_id,
            'step': 'input'
        }
        
        message_text = (
            "✏️ <b>Изменение названия сценария</b>\n\n"
            "📝 <b>Введите новое название:</b>\n\n"
            "💡 <b>Советы:</b>\n"
            "• Название должно быть понятным и описательным\n"
            "• Например: 'Базовый прогрев', 'Прогрев для новичков'\n"
            "• После изменения название будет обновлено"
        )
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить изменение", callback_data=f"admin_warmup_scenario_{short_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка создания формы редактирования названия: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка создания формы редактирования")


async def _handle_warmup_edit_desc_form(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                       warmup_service: "WarmupService", short_id: str, 
                                       is_callback: bool = False) -> None:
    """Форма редактирования описания сценария."""
    try:
        # Сохраняем состояние редактирования
        context.user_data['editing_warmup_scenario'] = {
            'type': 'description',
            'short_id': short_id,
            'step': 'input'
        }
        
        message_text = (
            "📝 <b>Изменение описания сценария</b>\n\n"
            "📝 <b>Введите новое описание:</b>\n\n"
            "💡 <b>Советы:</b>\n"
            "• Опишите цель и задачи сценария\n"
            "• Укажите целевую аудиторию\n"
            "• Опишите ожидаемые результаты\n"
            "• После изменения описание будет обновлено"
        )
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить изменение", callback_data=f"admin_warmup_scenario_{short_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка создания формы редактирования описания: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка создания формы редактирования")


async def _handle_warmup_edit_messages(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                      warmup_service: "WarmupService", short_id: str, 
                                      is_callback: bool = False) -> None:
    """Управление сообщениями сценария."""
    try:
        # Восстанавливаем полный UUID
        scenario_id = await _restore_warmup_scenario_uuid(short_id, warmup_service)
        
        if not scenario_id:
            await _safe_edit_message(update, context, "❌ Ошибка: неверный ID сценария")
            return
        
        # Получаем сценарий
        scenario = await warmup_service.get_scenario_by_id(scenario_id)
        
        if not scenario:
            await _safe_edit_message(update, context, "❌ Сценарий не найден")
            return
        
        # Показываем сообщения сценария
        message_text = (
            f"💬 <b>Сообщения сценария: {scenario.name}</b>\n\n"
            f"📊 <b>Всего сообщений: {len(scenario.messages)}</b>\n\n"
        )
        
        if scenario.messages:
            for i, msg in enumerate(scenario.messages, 1):
                message_text += f"{i}. <b>{msg.type.value}</b>\n"
                message_text += f"   📝 {msg.content[:50]}...\n"
                message_text += f"   ⏱️ Задержка: {msg.delay_hours}ч\n\n"
        else:
            message_text += "📭 Сообщения не найдены\n\n"
        
        message_text += "🔧 <b>Выберите действие:</b>"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить сообщение", callback_data=f"admin_warmup_add_message_{short_id}")],
            [InlineKeyboardButton("✏️ Редактировать сообщение", callback_data=f"admin_warmup_edit_message_{short_id}")],
            [InlineKeyboardButton("🗑️ Удалить сообщение", callback_data=f"admin_warmup_delete_message_{short_id}")],
            [InlineKeyboardButton("🔄 Изменить порядок", callback_data=f"admin_warmup_reorder_messages_{short_id}")],
            [InlineKeyboardButton("🔙 К редактированию сценария", callback_data=f"admin_warmup_scenario_{short_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Ошибка управления сообщениями: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка управления сообщениями")


async def _handle_warmup_toggle_status(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     warmup_service: "WarmupService", action: str, 
                                     is_callback: bool = False) -> None:
    """Переключение статуса сценария прогрева."""
    try:
        # Извлекаем ID сценария
        short_id = action.replace("admin_warmup_toggle_status_", "")
        
        # Восстанавливаем полный UUID
        scenario_id = await _restore_warmup_scenario_uuid(short_id, warmup_service)
        
        if not scenario_id:
            await _safe_edit_message(update, context, "❌ Ошибка: неверный ID сценария")
            return
        
        # Получаем сценарий
        scenario = await warmup_service.get_scenario_by_id(scenario_id)
        
        if not scenario:
            await _safe_edit_message(update, context, "❌ Сценарий не найден")
            return
        
        # Переключаем статус
        new_status = not scenario.is_active
        scenario.is_active = new_status
        
        # Сохраняем изменения
        await warmup_service.session.commit()
        
        status_text = "🟢 активирован" if new_status else "🔴 деактивирован"
        message_text = (
            f"✅ <b>Статус сценария изменен!</b>\n\n"
            f"🎯 <b>Сценарий:</b> {scenario.name}\n"
            f"📊 <b>Новый статус:</b> {status_text}\n\n"
            f"🎯 <b>Что дальше:</b>\n"
            "• Сценарий готов к использованию" if new_status else "• Сценарий временно отключен"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 К редактированию сценария", callback_data=f"admin_warmup_scenario_{short_id}")],
            [InlineKeyboardButton("📋 К списку сценариев", callback_data="admin_warmup_list_scenarios")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Ошибка переключения статуса: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка переключения статуса")


async def _handle_warmup_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                      warmup_service: "WarmupService", action: str, 
                                      is_callback: bool = False) -> None:
    """Подтверждение удаления сценария прогрева."""
    try:
        # Извлекаем ID сценария
        short_id = action.replace("admin_warmup_delete_confirm_", "")
        
        # Восстанавливаем полный UUID
        scenario_id = await _restore_warmup_scenario_uuid(short_id, warmup_service)
        
        if not scenario_id:
            await _safe_edit_message(update, context, "❌ Ошибка: неверный ID сценария")
            return
        
        # Получаем сценарий
        scenario = await warmup_service.get_scenario_by_id(scenario_id)
        
        if not scenario:
            await _safe_edit_message(update, context, "❌ Сценарий не найден")
            return
        
        message_text = (
            "⚠️ <b>Подтверждение удаления</b>\n\n"
            f"🎯 <b>Сценарий:</b> {scenario.name}\n"
            f"💬 <b>Сообщений:</b> {len(scenario.messages)}\n"
            f"📅 <b>Создан:</b> {scenario.created_at.strftime('%d.%m.%Y')}\n\n"
            "🚨 <b>Внимание!</b> Это действие нельзя отменить!\n"
            "Все сообщения и настройки сценария будут удалены.\n\n"
            "❓ <b>Вы уверены, что хотите удалить этот сценарий?</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Да, удалить", callback_data=f"admin_warmup_delete_final_{short_id}")],
            [InlineKeyboardButton("❌ Отменить", callback_data=f"admin_warmup_scenario_{short_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Ошибка подтверждения удаления: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка подтверждения удаления")


async def _handle_warmup_edit_name_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                         warmup_service: "WarmupService", action: str, 
                                         is_callback: bool = False) -> None:
    """Подтверждение изменения названия сценария."""
    try:
        # Извлекаем ID сценария
        short_id = action.replace("admin_warmup_edit_name_confirm_", "")
        
        # Получаем данные редактирования
        editing_data = context.user_data.get('editing_warmup_scenario', {})
        new_name = editing_data.get('new_name', '')
        
        if not new_name:
            await _safe_edit_message(update, context, "❌ Ошибка: новое название не найдено")
            return
        
        # Восстанавливаем полный UUID
        scenario_id = await _restore_warmup_scenario_uuid(short_id, warmup_service)
        
        if not scenario_id:
            await _safe_edit_message(update, context, "❌ Ошибка: неверный ID сценария")
            return
        
        # Получаем сценарий
        scenario = await warmup_service.get_scenario_by_id(scenario_id)
        
        if not scenario:
            await _safe_edit_message(update, context, "❌ Сценарий не найден")
            return
        
        # Сохраняем старое название для отображения
        old_name = scenario.name
        
        # Обновляем название
        scenario.name = new_name
        
        # Сохраняем изменения
        await warmup_service.session.commit()
        
        # Очищаем данные редактирования
        context.user_data.pop('editing_warmup_scenario', None)
        
        message_text = (
            "✅ <b>Название сценария изменено!</b>\n\n"
            f"🎯 <b>Старое название:</b> {old_name}\n"
            f"🎯 <b>Новое название:</b> {new_name}\n\n"
            f"🎯 <b>Что дальше:</b>\n"
            "• Название сценария обновлено\n"
            "• Все изменения сохранены\n"
            "• Сценарий готов к использованию"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 К редактированию сценария", callback_data=f"admin_warmup_scenario_{short_id}")],
            [InlineKeyboardButton("📋 К списку сценариев", callback_data="admin_warmup_list_scenarios")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Ошибка изменения названия: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка изменения названия")


async def _handle_warmup_edit_desc_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                         warmup_service: "WarmupService", action: str, 
                                         is_callback: bool = False) -> None:
    """Подтверждение изменения описания сценария."""
    try:
        # Извлекаем ID сценария
        short_id = action.replace("admin_warmup_edit_desc_confirm_", "")
        
        # Получаем данные редактирования
        editing_data = context.user_data.get('editing_warmup_scenario', {})
        new_description = editing_data.get('new_description', '')
        
        if not new_description:
            await _safe_edit_message(update, context, "❌ Ошибка: новое описание не найдено")
            return
        
        # Восстанавливаем полный UUID
        scenario_id = await _restore_warmup_scenario_uuid(short_id, warmup_service)
        
        if not scenario_id:
            await _safe_edit_message(update, context, "❌ Ошибка: неверный ID сценария")
            return
        
        # Получаем сценарий
        scenario = await warmup_service.get_scenario_by_id(scenario_id)
        
        if not scenario:
            await _safe_edit_message(update, context, "❌ Сценарий не найден")
            return
        
        # Сохраняем старое описание для отображения
        old_description = scenario.description or "Не указано"
        
        # Обновляем описание
        scenario.description = new_description
        
        # Сохраняем изменения
        await warmup_service.session.commit()
        
        # Очищаем данные редактирования
        context.user_data.pop('editing_warmup_scenario', None)
        
        message_text = (
            "✅ <b>Описание сценария изменено!</b>\n\n"
            f"🎯 <b>Сценарий:</b> {scenario.name}\n"
            f"📝 <b>Старое описание:</b> {old_description}\n"
            f"📝 <b>Новое описание:</b> {new_description}\n\n"
            f"🎯 <b>Что дальше:</b>\n"
            "• Описание сценария обновлено\n"
            "• Все изменения сохранены\n"
            "• Сценарий готов к использованию"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 К редактированию сценария", callback_data=f"admin_warmup_scenario_{short_id}")],
            [InlineKeyboardButton("📋 К списку сценариев", callback_data="admin_warmup_list_scenarios")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Ошибка изменения описания: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка изменения описания")


async def _handle_warmup_scenario_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                      warmup_service: "WarmupService", action: str, 
                                      is_callback: bool = False) -> None:
    """Редактирование сценария прогрева."""
    try:
        # Извлекаем ID сценария из action
        short_id = action.replace("admin_warmup_scenario_", "")
        
        # Восстанавливаем полный UUID
        scenario_id = await _restore_warmup_scenario_uuid(short_id, warmup_service)
        
        if not scenario_id:
            await _safe_edit_message(update, context, "❌ Ошибка: неверный ID сценария")
            return
        
        # Получаем сценарий
        scenario = await warmup_service.get_scenario_by_id(scenario_id)
        
        if not scenario:
            await _safe_edit_message(update, context, "❌ Сценарий не найден")
            return
        
        # Показываем информацию о сценарии и кнопки управления
        status = "🟢 Активен" if scenario.is_active else "🔴 Неактивен"
        message_text = (
            f"📝 <b>Редактирование сценария прогрева</b>\n\n"
            f"🎯 <b>Название:</b> {scenario.name}\n"
            f"📝 <b>Описание:</b> {scenario.description or 'Не указано'}\n"
            f"💬 <b>Сообщений:</b> {len(scenario.messages)}\n"
            f"📊 <b>Статус:</b> {status}\n"
            f"📅 <b>Создан:</b> {scenario.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"🔄 <b>Обновлен:</b> {scenario.updated_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🔧 <b>Выберите действие:</b>"
        )
        
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить название", callback_data=f"admin_warmup_edit_name_{short_id}")],
            [InlineKeyboardButton("📝 Изменить описание", callback_data=f"admin_warmup_edit_desc_{short_id}")],
            [InlineKeyboardButton("💬 Управление сообщениями", callback_data=f"admin_warmup_edit_messages_{short_id}")],
            [InlineKeyboardButton("🔄 Изменить статус", callback_data=f"admin_warmup_toggle_status_{short_id}")],
            [InlineKeyboardButton("🗑️ Удалить сценарий", callback_data=f"admin_warmup_delete_confirm_{short_id}")],
            [InlineKeyboardButton("🔙 К списку сценариев", callback_data="admin_warmup_list_scenarios")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await _safe_edit_message(update, context, message_text, reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Ошибка редактирования сценария: {e}")
        await _safe_edit_message(update, context, "❌ Ошибка редактирования сценария")


# Создание обработчика callback'ов для регистрации
admin_callback = CallbackQueryHandler(admin_callback_handler, pattern="^admin_")
