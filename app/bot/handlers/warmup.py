"""
Обработчики для системы прогрева пользователей.

Содержит логику для обработки кнопок и взаимодействий в системе прогрева.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from loguru import logger

from app.services.user_service import UserService
from app.services.warmup_service import WarmupService
from app.services.product_service import ProductService
from app.services.followup_service import FollowUpService
from app.models import ProductType
from app.core.database import get_db_session


async def warmup_offer_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик кнопки "Войти в программу" в сообщениях прогрева.
    """
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    try:
        async with get_db_session() as session:
            user_service = UserService(session)
            product_service = ProductService(session)
            
            # Получаем пользователя
            db_user = await user_service.get_user_by_telegram_id(user.id)
            if not db_user:
                await query.edit_message_text(
                    "❌ Пользователь не найден. Попробуйте команду /start",
                    parse_mode="HTML"
                )
                return
            
            # Получаем активный трипвайер
            tripwire = await product_service.get_active_product_by_type(ProductType.TRIPWIRE)
            if not tripwire:
                await query.edit_message_text(
                    "❌ Трипвайер временно недоступен. Обратитесь к администратору.",
                    parse_mode="HTML"
                )
                return
            
            # Получаем активный оффер для трипвайера
            offer = await product_service.get_active_offer_for_product(tripwire.id.hex)
            if not offer:
                await query.edit_message_text(
                    "❌ Оффер временно недоступен. Обратитесь к администратору.",
                    parse_mode="HTML"
                )
                return
            
            # Отмечаем показ оффера
            await product_service.show_offer_to_user(str(db_user.id), offer.id.hex)
            
            # Формируем сообщение с офером
            price = offer.price if offer.price else tripwire.price
            price_rub = price / 100
            
            keyboard = [
                [InlineKeyboardButton("💳 Оплатить картой", callback_data=f"payment_card_{tripwire.id.hex}")],
                [InlineKeyboardButton("📱 СПБ (Faster Payments)", callback_data=f"payment_spb_{tripwire.id.hex}")],
                [InlineKeyboardButton("🔗 Перейти на сайт оплаты", url=tripwire.payment_url)] if tripwire.payment_url else [],
                [InlineKeyboardButton("🔙 Назад", callback_data="warmup_info")]
            ]
            # Убираем пустые списки
            keyboard = [row for row in keyboard if row]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                offer.text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            logger.info(f"Показан оффер трипвайера '{tripwire.name}' пользователю {user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка показа оффера пользователю {user.id}: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка. Попробуйте позже.",
            parse_mode="HTML"
        )


async def warmup_info_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик кнопки "Узнать больше" в сообщениях прогрева.
    """
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    try:
        async with get_db_session() as session:
            user_service = UserService(session)
            warmup_service = WarmupService(session)
            
            # Получаем пользователя
            db_user = await user_service.get_user_by_telegram_id(user.id)
            if not db_user:
                await query.edit_message_text(
                    "❌ Пользователь не найден. Попробуйте команду /start",
                    parse_mode="HTML"
                )
                return
            
            # Получаем информацию о прогреве пользователя
            user_warmup = await warmup_service.get_user_active_warmup(str(db_user.id))
            
            if user_warmup:
                # Показываем прогресс прогрева
                info_text = (
                    "📊 <b>ВАШ ПРОГРЕСС В СИСТЕМЕ</b>\n\n"
                    f"🎯 Текущий шаг: {user_warmup.current_step + 1}\n"
                    f"📅 Начат: {user_warmup.started_at.strftime('%d.%m.%Y')}\n\n"
                    "🔥 <b>Что дальше:</b>\n"
                    "• Продолжайте получать полезные материалы\n"
                    "• Применяйте знания на практике\n"
                    "• Готовьтесь к основной программе\n\n"
                    "💡 <b>Совет:</b> Не пропускайте сообщения - каждое содержит важную информацию для вашего развития!"
                )
            else:
                # Общая информация о проекте
                info_text = (
                    "🌟 <b>ПРОЕКТ «ОСНОВА ПУТИ»</b>\n\n"
                    "🎯 <b>Наша миссия:</b>\n"
                    "Помочь людям создать систему личного развития и достичь своих целей\n\n"
                    "📚 <b>Что мы предлагаем:</b>\n"
                    "• Практические инструменты развития\n"
                    "• Проверенные методики успеха\n"
                    "• Сообщество единомышленников\n"
                    "• Персональную поддержку\n\n"
                    "✨ Начните свой путь к изменениям уже сегодня!"
                )
            
            keyboard = [
                [InlineKeyboardButton("📺 Подписаться на канал", url="https://t.me/osnovaputi")],
                [InlineKeyboardButton("💬 Связаться с нами", url="https://t.me/osnovaputi_support")],
                [InlineKeyboardButton("🔙 Вернуться", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                info_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            logger.info(f"Показана информация о проекте пользователю {user.id}")
            
    except Exception as e:
        logger.error(f"Ошибка показа информации пользователю {user.id}: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка. Попробуйте позже.",
            parse_mode="HTML"
        )


async def warmup_stop_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик для остановки прогрева пользователем.
    """
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    try:
        async with get_db_session() as session:
            user_service = UserService(session)
            warmup_service = WarmupService(session)
            
            # Получаем пользователя
            db_user = await user_service.get_user_by_telegram_id(user.id)
            if not db_user:
                await query.edit_message_text(
                    "❌ Пользователь не найден.",
                    parse_mode="HTML"
                )
                return
            
            # Останавливаем прогрев
            success = await warmup_service.stop_warmup_for_user(str(db_user.id))
            
            if success:
                stop_text = (
                    "⏹️ <b>Прогрев остановлен</b>\n\n"
                    "Вы больше не будете получать автоматические сообщения.\n\n"
                    "Если захотите возобновить получение материалов, "
                    "обратитесь к администратору или используйте команду /start."
                )
            else:
                stop_text = (
                    "ℹ️ У вас нет активного прогрева или он уже был остановлен ранее."
                )
            
            keyboard = [
                [InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                stop_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            logger.info(f"Остановлен прогрев для пользователя {user.id}")
            
    except Exception as e:
        logger.error(f"Ошибка остановки прогрева для пользователя {user.id}: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка. Попробуйте позже.",
            parse_mode="HTML"
        )


async def stop_followup_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик кнопки "Остановить напоминания" в дожимах.
    """
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    try:
        async with get_db_session() as session:
            user_service = UserService(session)
            followup_service = FollowUpService(session)
            
            # Получаем пользователя
            db_user = await user_service.get_user_by_telegram_id(user.id)
            if not db_user:
                await query.edit_message_text(
                    "❌ Пользователь не найден.",
                    parse_mode="HTML"
                )
                return
            
            # Останавливаем дожим
            success = await followup_service.stop_followup_for_user(str(db_user.id))
            
            if success:
                stop_text = (
                    "⏹️ <b>Напоминания остановлены</b>\n\n"
                    "Вы больше не будете получать напоминания о программе.\n\n"
                    "Если захотите возобновить получение информации, "
                    "обратитесь к администратору или используйте команду /start."
                )
            else:
                stop_text = (
                    "ℹ️ Напоминания уже были остановлены ранее."
                )
            
            keyboard = [
                [InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                stop_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            logger.info(f"Остановлены напоминания для пользователя {user.id}")
            
    except Exception as e:
        logger.error(f"Ошибка остановки напоминаний для пользователя {user.id}: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка. Попробуйте позже.",
            parse_mode="HTML"
        )


# Создание обработчиков для регистрации
warmup_offer_callback = CallbackQueryHandler(warmup_offer_callback_handler, pattern="^warmup_offer$")
warmup_info_callback = CallbackQueryHandler(warmup_info_callback_handler, pattern="^warmup_info$")
warmup_stop_callback = CallbackQueryHandler(warmup_stop_callback_handler, pattern="^warmup_stop$")
stop_followup_callback = CallbackQueryHandler(stop_followup_callback_handler, pattern="^stop_followup$")
