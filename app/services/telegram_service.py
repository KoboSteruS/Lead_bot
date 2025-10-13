"""
Сервис для работы с Telegram API.

Содержит методы для отправки сообщений, работы с клавиатурами и проверки подписок.
"""

from typing import Optional, List, Dict, Any
from telegram import Bot, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.error import TelegramError, BadRequest, Forbidden
from loguru import logger

from config.settings import settings


class TelegramService:
    """Сервис для работы с Telegram API."""
    
    def __init__(self, bot: Bot):
        """
        Инициализация сервиса.
        
        Args:
            bot: Экземпляр Telegram бота
        """
        self.bot = bot
    
    async def send_welcome_message(
        self, 
        chat_id: int, 
        user_name: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """
        Отправка приветственного сообщения.
        
        Args:
            chat_id: ID чата
            user_name: Имя пользователя
            reply_markup: Клавиатура для ответа
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        try:
            welcome_text = (
                f"🎯 <b>Добро пожаловать в «ОСНОВА P U T И», {user_name}!</b>\n\n"
                f"Я помогу тебе изменить свою жизнь через систему дисциплины и силы.\n\n"
                f"🎁 <b>Получи подарок:</b>\n"
                f"«7-дневный трекер дисциплины и силы»\n\n"
                f"Этот трекер поможет тебе:\n"
                f"• Создать устойчивые привычки\n"
                f"• Развить внутреннюю дисциплину\n"
                f"• Достичь поставленных целей\n"
                f"• Стать сильнее каждый день\n\n"
                f"Нажми кнопку ниже, чтобы забрать подарок! 🎁"
            )
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=welcome_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            logger.info(f"Отправлено приветственное сообщение пользователю {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки приветственного сообщения пользователю {chat_id}: {e}")
            return False
    
    async def send_lead_magnet_message(
        self,
        chat_id: int,
        lead_magnet_name: str,
        message_text: Optional[str] = None,
        file_url: Optional[str] = None,
        lead_magnet_type: str = "pdf",
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """
        Отправка сообщения с лид-магнитом.
        
        Args:
            chat_id: ID чата
            lead_magnet_name: Название лид-магнита
            message_text: Дополнительный текст
            file_url: Ссылка на файл
            lead_magnet_type: Тип лид-магнита
            reply_markup: Клавиатура
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        try:
            text = f"🎁 <b>Ваш подарок готов!</b>\n\n📋 <b>{lead_magnet_name}</b>\n\n"
            
            if message_text:
                text += f"{message_text}\n\n"
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            logger.info(f"Отправлен лид-магнит '{lead_magnet_name}' пользователю {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки лид-магнита пользователю {chat_id}: {e}")
            return False
    
    async def send_warmup_message(
        self,
        chat_id: int,
        title: str,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """
        Отправка сообщения прогрева.
        
        Args:
            chat_id: ID чата
            title: Заголовок сообщения
            text: Текст сообщения
            reply_markup: Клавиатура
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        try:
            full_text = f"🔥 <b>{title}</b>\n\n{text}"
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=full_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            logger.info(f"Отправлено сообщение прогрева '{title}' пользователю {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения прогрева пользователю {chat_id}: {e}")
            return False
    
    async def send_offer_message(
        self,
        chat_id: int,
        offer_text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """
        Отправка оффера.
        
        Args:
            chat_id: ID чата
            offer_text: Текст оффера
            reply_markup: Клавиатура
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=offer_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            logger.info(f"Отправлен оффер пользователю {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки оффера пользователю {chat_id}: {e}")
            return False
    
    async def send_follow_up_message(
        self,
        chat_id: int,
        follow_up_text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """
        Отправка дожима.
        
        Args:
            chat_id: ID чата
            follow_up_text: Текст дожима
            reply_markup: Клавиатура
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=follow_up_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            logger.info(f"Отправлен дожим пользователю {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки дожима пользователю {chat_id}: {e}")
            return False
    
    async def check_channel_subscription(self, user_id: int) -> bool:
        """
        Проверка подписки пользователя на канал.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если пользователь подписан на канал
        """
        try:
            member = await self.bot.get_chat_member(
                chat_id=settings.CHANNEL_ID,
                user_id=user_id
            )
            
            # Проверяем статус подписки
            is_subscribed = member.status in ['member', 'administrator', 'creator']
            
            logger.info(f"Проверка подписки пользователя {user_id}: {'подписан' if is_subscribed else 'не подписан'}")
            return is_subscribed
            
        except (BadRequest, Forbidden) as e:
            logger.warning(f"Не удалось проверить подписку пользователя {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка проверки подписки пользователя {user_id}: {e}")
            return False
    
    async def send_subscription_required_message(
        self,
        chat_id: int,
        channel_username: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """
        Отправка сообщения о необходимости подписки на канал.
        
        Args:
            chat_id: ID чата
            channel_username: Username канала
            reply_markup: Клавиатура
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        try:
            text = (
                f"📺 <b>Подпишитесь на канал для получения подарка!</b>\n\n"
                f"Чтобы получить лид-магнит, необходимо подписаться на основной канал проекта:\n\n"
                f"🔗 @{channel_username}\n\n"
                f"После подписки нажмите кнопку «Проверить подписку»"
            )
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
            logger.info(f"Отправлено сообщение о необходимости подписки пользователю {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о подписке пользователю {chat_id}: {e}")
            return False
    
    async def send_error_message(
        self,
        chat_id: int,
        error_text: str = "Произошла ошибка. Попробуйте позже."
    ) -> bool:
        """
        Отправка сообщения об ошибке.
        
        Args:
            chat_id: ID чата
            error_text: Текст ошибки
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"❌ {error_text}",
                parse_mode="HTML"
            )
            
            logger.info(f"Отправлено сообщение об ошибке пользователю {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения об ошибке пользователю {chat_id}: {e}")
            return False
    
    async def send_success_message(
        self,
        chat_id: int,
        success_text: str
    ) -> bool:
        """
        Отправка сообщения об успехе.
        
        Args:
            chat_id: ID чата
            success_text: Текст успеха
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"✅ {success_text}",
                parse_mode="HTML"
            )
            
            logger.info(f"Отправлено сообщение об успехе пользователю {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения об успехе пользователю {chat_id}: {e}")
            return False
    
    async def get_bot_info(self) -> Dict[str, Any]:
        """
        Получение информации о боте.
        
        Returns:
            Dict[str, Any]: Информация о боте
        """
        try:
            bot_info = await self.bot.get_me()
            return {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name,
                "can_join_groups": bot_info.can_join_groups,
                "can_read_all_group_messages": bot_info.can_read_all_group_messages,
                "supports_inline_queries": bot_info.supports_inline_queries
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о боте: {e}")
            return {}
