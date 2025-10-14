"""
Обработчики для лид-магнитов.

Содержит логику выдачи подарков пользователям.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger

from app.services.user_service import UserService
from app.services.lead_magnet_service import LeadMagnetService
from app.services.warmup_service import WarmupService
from app.services.telegram_service import TelegramService
from app.core.database import get_db_session
from config.settings import settings


from telegram.ext import CommandHandler, CallbackQueryHandler

async def get_gift_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /gift - выдача лид-магнита.
    """
    user = update.effective_user
    chat = update.effective_chat
    
    if not user or not chat:
        return
    
    try:
        async with get_db_session() as session:
            user_service = UserService(session)
            lead_magnet_service = LeadMagnetService(session)
            warmup_service = WarmupService(session)
            telegram_service = TelegramService(context.bot)
            
            # Получаем или создаем пользователя
            db_user = await user_service.get_user_by_telegram_id(user.id)
            if not db_user:
                db_user = await user_service.create_user({
                    "telegram_id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                })
                logger.info(f"Создан новый пользователь: {user.id}")
            
            # Проверяем подписку на канал
            is_subscribed = await telegram_service.check_channel_subscription(user.id)
            if not is_subscribed:
                # Пользователь не подписан на канал
                keyboard = [
                    [InlineKeyboardButton("📺 Подписаться на канал", url=f"https://t.me/{settings.CHANNEL_USERNAME}")],
                    [InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await telegram_service.send_subscription_required_message(
                    chat_id=chat.id,
                    channel_username=settings.CHANNEL_USERNAME,
                    reply_markup=reply_markup
                )
                return
            
            # Проверяем, получал ли пользователь уже лид-магнит
            has_lead_magnet = await lead_magnet_service.user_has_lead_magnet(str(db_user.id))
            
            if has_lead_magnet:
                # Пользователь уже получал лид-магнит
                await update.message.reply_text(
                    "🎁 Вы уже получили подарок!\n\n"
                    "📋 Если вам нужен еще один экземпляр трекера, "
                    "обратитесь к администратору.",
                    parse_mode="HTML"
                )
                return
            
            # Выдаем лид-магнит
            lead_magnet = await lead_magnet_service.give_lead_magnet_to_user(str(db_user.id))
            
            if not lead_magnet:
                await update.message.reply_text(
                    "❌ К сожалению, подарок временно недоступен.\n"
                    "Попробуйте позже или обратитесь к администратору.",
                    parse_mode="HTML"
                )
                return
            
            # Формируем сообщение с лид-магнитом
            message_text = (
                f"🎁 <b>Ваш подарок готов!</b>\n\n"
                f"📋 <b>{lead_magnet.name}</b>\n\n"
            )
            
            if lead_magnet.message_text:
                message_text += f"{lead_magnet.message_text}\n\n"
            
            # Если есть telegram_file_id, отправляем файл напрямую
            if lead_magnet.telegram_file_id:
                # Сначала отправляем текст
                await update.message.reply_text(
                    message_text,
                    parse_mode="HTML"
                )
                # Затем отправляем файл
                try:
                    await update.message.reply_document(
                        document=lead_magnet.telegram_file_id,
                        caption=f"📄 {lead_magnet.name}"
                    )
                except Exception as file_error:
                    logger.error(f"Ошибка отправки файла: {file_error}")
                    # Если файл не отправился, отправляем ссылку (если есть)
                    if lead_magnet.file_url:
                        keyboard = [[InlineKeyboardButton("📄 Скачать файл", url=lead_magnet.file_url)]]
                        await update.message.reply_text(
                            "Или скачайте по ссылке:",
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
            else:
                # Создаем клавиатуру для ссылок
                keyboard = []
                
                if lead_magnet.type == "pdf" and lead_magnet.file_url:
                    keyboard.append([
                        InlineKeyboardButton("📄 Скачать PDF", url=lead_magnet.file_url)
                    ])
                elif lead_magnet.type == "google_sheet" and lead_magnet.file_url:
                    keyboard.append([
                        InlineKeyboardButton("📊 Открыть таблицу", url=lead_magnet.file_url)
                    ])
                elif lead_magnet.type == "link" and lead_magnet.file_url:
                    keyboard.append([
                        InlineKeyboardButton("🔗 Перейти по ссылке", url=lead_magnet.file_url)
                    ])
                
                reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
                
                await update.message.reply_text(
                    message_text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            
            logger.info(f"Выдан лид-магнит пользователю {user.id}: {lead_magnet.name}")
            
            # Запускаем прогрев для пользователя
            try:
                await warmup_service.start_warmup_for_user(str(db_user.id))
                logger.info(f"Запущен прогрев для пользователя {user.id}")
            except Exception as warmup_error:
                logger.error(f"Ошибка запуска прогрева для пользователя {user.id}: {warmup_error}")
                # Прогрев не критичен, продолжаем
            
    except Exception as e:
        logger.error(f"Ошибка выдачи лид-магнита пользователю {user.id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при выдаче подарка. Попробуйте позже.",
            parse_mode="HTML"
        )


async def gift_button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик кнопки "Забрать подарок".
    """
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    try:
        async with get_db_session() as session:
            user_service = UserService(session)
            lead_magnet_service = LeadMagnetService(session)
            warmup_service = WarmupService(session)
            
            # Получаем пользователя
            db_user = await user_service.get_user_by_telegram_id(user.id)
            if not db_user:
                await query.edit_message_text(
                    "❌ Пользователь не найден. Попробуйте команду /start",
                    parse_mode="HTML"
                )
                return
            
            # Проверяем, получал ли пользователь уже лид-магнит
            has_lead_magnet = await lead_magnet_service.user_has_lead_magnet(str(db_user.id))
            
            if has_lead_magnet:
                # Пользователь уже получал лид-магнит
                await query.edit_message_text(
                    "🎁 Вы уже получили подарок!\n\n"
                    "📋 Если вам нужен еще один экземпляр трекера, "
                    "обратитесь к администратору.",
                    parse_mode="HTML"
                )
                return
            
            # Сначала проверяем подписку на канал
            telegram_service = TelegramService(context.bot)
            is_subscribed = await telegram_service.check_channel_subscription(user.id)
            
            if not is_subscribed:
                # Пользователь не подписан - показываем сообщение с требованием подписки
                await query.edit_message_text(
                    "🎁 <b>Для получения подарка необходимо подписаться на наш канал!</b>\n\n"
                    f"📺 <b>Канал:</b> @{settings.CHANNEL_USERNAME}\n\n"
                    "После подписки нажмите кнопку «Я подписался» ниже:",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📺 Подписаться на канал", url=f"https://t.me/{settings.CHANNEL_USERNAME}")],
                        [InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")]
                    ])
                )
                return
            
            # Пользователь подписан - выдаем лид-магнит
            lead_magnet = await lead_magnet_service.give_lead_magnet_to_user(str(db_user.id))
            
            if not lead_magnet:
                await query.edit_message_text(
                    "❌ К сожалению, подарок временно недоступен.\n"
                    "Попробуйте позже или обратитесь к администратору.",
                    parse_mode="HTML"
                )
                return
            
            # Формируем сообщение с лид-магнитом
            message_text = (
                f"🎁 <b>Ваш подарок готов!</b>\n\n"
                f"📋 <b>{lead_magnet.name}</b>\n\n"
            )
            
            if lead_magnet.message_text:
                message_text += f"{lead_magnet.message_text}\n\n"
            
            # Если есть telegram_file_id, отправляем файл напрямую
            if lead_magnet.telegram_file_id:
                # Сначала редактируем сообщение
                await query.edit_message_text(
                    message_text,
                    parse_mode="HTML"
                )
                # Затем отправляем файл
                try:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=lead_magnet.telegram_file_id,
                        caption=f"📄 {lead_magnet.name}"
                    )
                except Exception as file_error:
                    logger.error(f"Ошибка отправки файла: {file_error}")
                    # Если файл не отправился, отправляем ссылку (если есть)
                    if lead_magnet.file_url:
                        keyboard = [[InlineKeyboardButton("📄 Скачать файл", url=lead_magnet.file_url)]]
                        await context.bot.send_message(
                            chat_id=query.message.chat_id,
                            text="Или скачайте по ссылке:",
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
            else:
                # Создаем клавиатуру для ссылок
                keyboard = []
                
                if lead_magnet.type == "pdf" and lead_magnet.file_url:
                    keyboard.append([
                        InlineKeyboardButton("📄 Скачать PDF", url=lead_magnet.file_url)
                    ])
                elif lead_magnet.type == "google_sheet" and lead_magnet.file_url:
                    keyboard.append([
                        InlineKeyboardButton("📊 Открыть таблицу", url=lead_magnet.file_url)
                    ])
                elif lead_magnet.type == "link" and lead_magnet.file_url:
                    keyboard.append([
                        InlineKeyboardButton("🔗 Перейти по ссылке", url=lead_magnet.file_url)
                    ])
                
                reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
                
                await query.edit_message_text(
                    message_text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            
            logger.info(f"Выдан лид-магнит пользователю {user.id}: {lead_magnet.name}")
            
            # Запускаем прогрев для пользователя
            try:
                await warmup_service.start_warmup_for_user(str(db_user.id))
                logger.info(f"Запущен прогрев для пользователя {user.id}")
            except Exception as warmup_error:
                logger.error(f"Ошибка запуска прогрева для пользователя {user.id}: {warmup_error}")
                # Прогрев не критичен, продолжаем
            
    except Exception as e:
        logger.error(f"Ошибка выдачи лид-магнита пользователю {user.id}: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при выдаче подарка. Попробуйте позже.",
            parse_mode="HTML"
        )





async def subscribe_channel_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик кнопки "Подписаться на канал".
    """
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    # Ссылка на основной канал
    channel_link = "https://t.me/osnovaputi"
    
    message_text = (
        "📺 <b>Подпишитесь на основной канал проекта!</b>\n\n"
        "🔥 Здесь вы найдете:\n"
        "• Полезные материалы по развитию\n"
        "• Мотивационные посты\n"
        "• Анонсы новых продуктов\n"
        "• Общение с единомышленниками\n\n"
        "👇 Нажмите кнопку ниже для подписки:"
    )
    
    keyboard = [
        [InlineKeyboardButton("📺 Подписаться на канал", url=channel_link)],
        [InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )


async def check_subscription_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик кнопки "Я подписался" - проверка подписки.
    """
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    try:
        async with get_db_session() as session:
            user_service = UserService(session)
            lead_magnet_service = LeadMagnetService(session)
            warmup_service = WarmupService(session)
            telegram_service = TelegramService(context.bot)
            
            # Получаем пользователя
            db_user = await user_service.get_user_by_telegram_id(user.id)
            if not db_user:
                await query.edit_message_text(
                    "❌ Пользователь не найден. Попробуйте команду /start",
                    parse_mode="HTML"
                )
                return
            
            # Проверяем подписку на канал
            is_subscribed = await telegram_service.check_channel_subscription(user.id)
            if not is_subscribed:
                # Пользователь все еще не подписан
                keyboard = [
                    [InlineKeyboardButton("📺 Подписаться на канал", url=f"https://t.me/{settings.CHANNEL_USERNAME}")],
                    [InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    await query.edit_message_text(
                        "❌ Подписка не найдена. Пожалуйста, подпишитесь на канал и попробуйте снова.",
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                except Exception as edit_error:
                    # Если сообщение не изменилось, просто отвечаем
                    if "Message is not modified" in str(edit_error):
                        await query.answer("❌ Подписка не найдена. Пожалуйста, подпишитесь на канал.")
                    else:
                        raise edit_error
                return
            
            # Пользователь подписан, выдаем лид-магнит
            # Проверяем, получал ли пользователь уже лид-магнит
            has_lead_magnet = await lead_magnet_service.user_has_lead_magnet(str(db_user.id))
            
            if has_lead_magnet:
                # Пользователь уже получал лид-магнит
                await query.edit_message_text(
                    "🎁 Вы уже получили подарок!\n\n"
                    "📋 Если вам нужен еще один экземпляр трекера, "
                    "обратитесь к администратору.",
                    parse_mode="HTML"
                )
                return
            
            # Выдаем лид-магнит
            lead_magnet = await lead_magnet_service.give_lead_magnet_to_user(str(db_user.id))
            
            if not lead_magnet:
                await query.edit_message_text(
                    "❌ К сожалению, подарок временно недоступен.\n"
                    "Попробуйте позже или обратитесь к администратору.",
                    parse_mode="HTML"
                )
                return
            
            # Формируем сообщение с лид-магнитом
            message_text = (
                f"🎁 <b>Ваш подарок готов!</b>\n\n"
                f"📋 <b>{lead_magnet.name}</b>\n\n"
            )
            
            if lead_magnet.message_text:
                message_text += f"{lead_magnet.message_text}\n\n"
            
            # Создаем клавиатуру в зависимости от типа лид-магнита
            keyboard = []
            
            if lead_magnet.type == "pdf":
                keyboard.append([
                    InlineKeyboardButton("📄 Скачать PDF", url=lead_magnet.file_url)
                ])
            elif lead_magnet.type == "google_sheet":
                keyboard.append([
                    InlineKeyboardButton("📊 Открыть таблицу", url=lead_magnet.file_url)
                ])
            elif lead_magnet.type == "link":
                keyboard.append([
                    InlineKeyboardButton("🔗 Перейти по ссылке", url=lead_magnet.file_url)
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            logger.info(f"Выдан лид-магнит пользователю {user.id}: {lead_magnet.name}")
            
            # Запускаем прогрев для пользователя
            try:
                await warmup_service.start_warmup_for_user(str(db_user.id))
                logger.info(f"Запущен прогрев для пользователя {user.id}")
            except Exception as warmup_error:
                logger.error(f"Ошибка запуска прогрева для пользователя {user.id}: {warmup_error}")
                # Прогрев не критичен, продолжаем
            
    except Exception as e:
        logger.error(f"Ошибка проверки подписки пользователя {user.id}: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при проверке подписки. Попробуйте позже.",
            parse_mode="HTML"
        )


# Создание обработчиков для регистрации
get_gift_command = CommandHandler("gift", get_gift_command_handler)
gift_button_callback = CallbackQueryHandler(gift_button_callback_handler, pattern="^get_gift$")
subscribe_channel_callback = CallbackQueryHandler(subscribe_channel_callback_handler, pattern="^subscribe_channel$")
check_subscription_callback = CallbackQueryHandler(check_subscription_callback_handler, pattern="^check_subscription$")
