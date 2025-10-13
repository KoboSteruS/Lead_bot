"""
Обработчики для трипвайеров и платежей.

Содержит логику для обработки покупки трипвайеров.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from loguru import logger

from app.services.user_service import UserService
from app.services.product_service import ProductService
from app.models import ProductType
from app.core.database import get_db_session


async def payment_card_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик кнопки "Оплатить картой".
    """
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    try:
        # Извлекаем ID продукта из callback_data
        callback_data = query.data
        if "_" in callback_data:
            product_id = callback_data.split("_", 2)[-1] if len(callback_data.split("_")) > 2 else None
        else:
            product_id = None
        
        async with get_db_session() as session:
            user_service = UserService(session)
            product_service = ProductService(session)
            
            # Получаем пользователя
            db_user = await user_service.get_user_by_telegram_id(user.id)
            if not db_user:
                await query.edit_message_text(
                    "❌ Пользователь не найден.",
                    parse_mode="HTML"
                )
                return
            
            # Получаем продукт
            if product_id:
                # Если указан конкретный продукт
                stmt = f"SELECT * FROM products WHERE id = '{product_id}'"
                # TODO: Заменить на ORM запрос
                tripwire = await product_service.get_active_product_by_type(ProductType.TRIPWIRE)
            else:
                # Получаем активный трипвайер
                tripwire = await product_service.get_active_product_by_type(ProductType.TRIPWIRE)
            
            if not tripwire:
                await query.edit_message_text(
                    "❌ Продукт не найден.",
                    parse_mode="HTML"
                )
                return
            
            # Отмечаем клик по офферу (если есть активный оффер)
            offer = await product_service.get_active_offer_for_product(tripwire.id.hex)
            if offer:
                await product_service.mark_offer_clicked(str(db_user.id), offer.id.hex)
            
            # Формируем сообщение с инструкцией по оплате
            payment_text = (
                f"💳 <b>Оплата: {tripwire.name}</b>\n\n"
                f"💰 <b>Сумма: {tripwire.price_rub} ₽</b>\n\n"
                f"📱 <b>Инструкция по оплате:</b>\n"
                f"1. Нажмите кнопку «Перейти к оплате»\n"
                f"2. Введите данные карты на защищенной странице\n"
                f"3. Подтвердите платеж\n"
                f"4. После оплаты вы автоматически получите доступ\n\n"
                f"🔒 <b>Безопасность:</b> Ваши данные защищены SSL-шифрованием"
            )
            
            keyboard = [
                [InlineKeyboardButton("💳 Перейти к оплате", url=tripwire.payment_url)] if tripwire.payment_url else [],
                [InlineKeyboardButton("📞 Помощь", callback_data="payment_help")],
                [InlineKeyboardButton("🔙 Назад", callback_data="warmup_offer")]
            ]
            # Убираем пустые списки
            keyboard = [row for row in keyboard if row]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                payment_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            logger.info(f"Показана страница оплаты картой пользователю {user.id} для продукта {tripwire.name}")
        
    except Exception as e:
        logger.error(f"Ошибка обработки оплаты картой для пользователя {user.id}: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка. Попробуйте позже или обратитесь в поддержку.",
            parse_mode="HTML"
        )


async def payment_spb_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик кнопки "СПБ (Faster Payments)".
    """
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    try:
        # Извлекаем ID продукта из callback_data
        callback_data = query.data
        if "_" in callback_data:
            product_id = callback_data.split("_", 2)[-1] if len(callback_data.split("_")) > 2 else None
        else:
            product_id = None
        
        async with get_db_session() as session:
            user_service = UserService(session)
            product_service = ProductService(session)
            
            # Получаем пользователя
            db_user = await user_service.get_user_by_telegram_id(user.id)
            if not db_user:
                await query.edit_message_text(
                    "❌ Пользователь не найден.",
                    parse_mode="HTML"
                )
                return
            
            # Получаем активный трипвайер
            tripwire = await product_service.get_active_product_by_type(ProductType.TRIPWIRE)
            if not tripwire:
                await query.edit_message_text(
                    "❌ Продукт не найден.",
                    parse_mode="HTML"
                )
                return
            
            # Отмечаем клик по офферу (если есть активный оффер)
            offer = await product_service.get_active_offer_for_product(tripwire.id.hex)
            if offer:
                await product_service.mark_offer_clicked(str(db_user.id), offer.id.hex)
            
            # Формируем сообщение с инструкцией по СБП
            payment_text = (
                f"📱 <b>Оплата через СБП: {tripwire.name}</b>\n\n"
                f"💰 <b>Сумма: {tripwire.price_rub} ₽</b>\n\n"
                f"📱 <b>Инструкция по оплате:</b>\n"
                f"1. Нажмите кнопку «Оплатить через СБП»\n"
                f"2. Выберите ваш банк из списка\n"
                f"3. Подтвердите платеж в приложении банка\n"
                f"4. После оплаты вы автоматически получите доступ\n\n"
                f"⚡ <b>Быстро и безопасно!</b> Платеж происходит мгновенно"
            )
            
            keyboard = [
                [InlineKeyboardButton("📱 Оплатить через СБП", url=tripwire.payment_url)] if tripwire.payment_url else [],
                [InlineKeyboardButton("📞 Помощь", callback_data="payment_help")],
                [InlineKeyboardButton("🔙 Назад", callback_data="warmup_offer")]
            ]
            # Убираем пустые списки
            keyboard = [row for row in keyboard if row]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                payment_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            logger.info(f"Показана страница оплаты СБП пользователю {user.id} для продукта {tripwire.name}")
        
    except Exception as e:
        logger.error(f"Ошибка обработки оплаты СБП для пользователя {user.id}: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка. Попробуйте позже или обратитесь в поддержку.",
            parse_mode="HTML"
        )


async def payment_help_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик кнопки "Помощь" в процессе оплаты.
    """
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    try:
        help_text = (
            "🆘 <b>Помощь с оплатой</b>\n\n"
            "❓ <b>Частые вопросы:</b>\n\n"
            "• <b>Не работает оплата?</b>\n"
            "  Попробуйте другой способ оплаты или обновите страницу\n\n"
            "• <b>Деньги списались, но доступа нет?</b>\n"
            "  Обратитесь в поддержку с номером транзакции\n\n"
            "• <b>Хочу вернуть деньги?</b>\n"
            "  Возврат возможен в течение 14 дней\n\n"
            "📞 <b>Контакты поддержки:</b>\n"
            "Telegram: @osnovaputi_support\n"
            "Email: support@osnovaputi.ru\n\n"
            "⏰ <b>Время работы:</b> Пн-Пт 9:00-18:00 (МСК)"
        )
        
        keyboard = [
            [InlineKeyboardButton("📞 Написать в поддержку", url="https://t.me/osnovaputi_support")],
            [InlineKeyboardButton("🔙 Назад к оплате", callback_data="warmup_offer")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            help_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
        logger.info(f"Показана помощь по оплате пользователю {user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка показа помощи по оплате для пользователя {user.id}: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка. Попробуйте позже.",
            parse_mode="HTML"
        )


# Создание обработчиков для регистрации
payment_card_callback = CallbackQueryHandler(payment_card_callback_handler, pattern="^payment_card")
payment_spb_callback = CallbackQueryHandler(payment_spb_callback_handler, pattern="^payment_spb")
payment_help_callback = CallbackQueryHandler(payment_help_callback_handler, pattern="^payment_help$")
