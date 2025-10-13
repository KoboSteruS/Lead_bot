"""
Обработчик команды /start.

Обрабатывает команду /start и создает нового пользователя.
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from loguru import logger

from app.core.database import get_database
from app.services import UserService, TelegramService
from app.schemas.user import UserCreate
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


async def start_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /start.
    
    Args:
        update: Обновление от Telegram
        context: Контекст бота
    """
    try:
        # Получаем данные пользователя
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        if not user:
            logger.error("Не удалось получить данные пользователя")
            return
        
        # Получаем сессию базы данных
        async for session in get_database():
            user_service = UserService(session)
            telegram_service = TelegramService(context.bot)
            
            # Проверяем, существует ли пользователь
            existing_user = await user_service.get_user_by_telegram_id(user.id)
            
            if existing_user:
                logger.info(f"Пользователь {user.id} уже существует")
                
                # Создаем клавиатуру с кнопкой "Забрать подарок"
                keyboard = [
                    [InlineKeyboardButton("🎁 Забрать подарок", callback_data="get_gift")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Отправляем приветственное сообщение с reply keyboard
                await telegram_service.send_welcome_message(
                    chat_id=chat_id,
                    user_name=user.first_name or user.username or str(user.id),
                    reply_markup=reply_markup
                )
            else:
                # Создаем нового пользователя
                user_data = UserCreate(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
                
                new_user = await user_service.create_user(user_data)
                logger.info(f"Создан новый пользователь: {new_user.id}")
                
                # Создаем клавиатуру с кнопкой "Забрать подарок"
                keyboard = [
                    [InlineKeyboardButton("🎁 Забрать подарок", callback_data="get_gift")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Отправляем приветственное сообщение с reply keyboard
                await telegram_service.send_welcome_message(
                    chat_id=chat_id,
                    user_name=user.first_name or user.username or str(user.id),
                    reply_markup=reply_markup
                )
        
    except Exception as e:
        logger.error(f"Ошибка обработки команды /start: {e}")
        
        # Отправляем сообщение об ошибке пользователю
        try:
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке команды. Попробуйте позже или обратитесь к администратору."
            )
        except Exception as reply_error:
            logger.error(f"Ошибка отправки сообщения об ошибке: {reply_error}")


# Создаем обработчик команды
start_handler = CommandHandler("start", start_command_handler)
