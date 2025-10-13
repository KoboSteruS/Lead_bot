"""
Основной класс Telegram бота.

Содержит инициализацию и настройку бота.
"""

import asyncio
from telegram import Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from loguru import logger

from config.settings import settings
from app.core.database import init_database, close_database
from app.services.scheduler_service import SchedulerService




class TelegramBot:
    """Основной класс Telegram бота."""
    
    def __init__(self):
        """Инициализация бота."""
        self.bot = Bot(token=settings.BOT_TOKEN)
        self.application = Application.builder().token(settings.BOT_TOKEN).build()
        self.scheduler = None  # Инициализируем позже, после создания БД
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Настройка обработчиков команд."""
        # Регистрируем все обработчики
        from app.bot.handlers import register_handlers
        register_handlers(self.application)
        
        logger.info("Обработчики команд настроены")
    
    async def start(self) -> None:
        """Запуск бота."""
        try:
            # Инициализируем базу данных
            await init_database()
            logger.info("База данных инициализирована")
            
            # Создаем и запускаем планировщик (после БД!)
            self.scheduler = SchedulerService(self.bot)
            self.scheduler.start()
            logger.info("Планировщик задач запущен")
            
            # Запускаем бота
            logger.info("Запуск Telegram бота...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Telegram бот успешно запущен")
            
            # Держим бота запущенным
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                logger.info("Получен сигнал остановки")
            finally:
                await self.stop()
                
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise
    
    async def stop(self) -> None:
        """Остановка бота."""
        try:
            logger.info("Остановка Telegram бота...")
            
            # Останавливаем планировщик
            if self.scheduler:
                self.scheduler.stop()
            
            # Останавливаем бота
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            
            # Закрываем соединение с базой данных
            await close_database()
            
            logger.info("Telegram бот успешно остановлен")
            
        except Exception as e:
            logger.error(f"Ошибка остановки бота: {e}")
    
    async def get_me(self) -> dict:
        """
        Получение информации о боте.
        
        Returns:
            dict: Информация о боте
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
    
    async def send_message_to_user(self, user_id: int, text: str, **kwargs) -> bool:
        """
        Отправка сообщения пользователю.
        
        Args:
            user_id: ID пользователя
            text: Текст сообщения
            **kwargs: Дополнительные параметры
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        try:
            await self.bot.send_message(chat_id=user_id, text=text, **kwargs)
            logger.info(f"Сообщение отправлено пользователю {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
            return False
    
    # Временно отключено - не используем группу
    # async def send_message_to_group(self, text: str, **kwargs) -> bool:
    #     """
    #     Отправка сообщения в группу.
    #     
    #     Args:
    #         text: Текст сообщения
    #         **kwargs: Дополнительные параметры
    #         
    #     Returns:
    #         bool: True если сообщение отправлено успешно
    #     """
    #     try:
    #         await self.bot.send_message(chat_id=settings.telegram_group_id, text=text, **kwargs)
    #         logger.info(f"Сообщение отправлено в группу {settings.telegram_group_id}")
    #         return True
    #     except Exception as e:
    #         logger.error(f"Ошибка отправки сообщения в группу: {e}")
    #         return False
