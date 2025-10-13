"""
Сервис для планирования и отправки сообщений прогрева.

Управляет автоматической отправкой сообщений прогрева пользователям.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger

from app.core.database import get_db_session
from app.services.warmup_service import WarmupService
from app.services.telegram_service import TelegramService
from app.services.product_service import ProductService
from app.services.followup_service import FollowUpService
from app.models.warmup import WarmupMessageType
from app.models.product import ProductType


class SchedulerService:
    """Сервис для планирования задач."""
    
    def __init__(self, bot: Bot):
        """
        Инициализация сервиса.
        
        Args:
            bot: Экземпляр Telegram бота
        """
        self.bot = bot
        self.is_running = False
        self.task = None
    
    def start(self) -> None:
        """Запуск планировщика."""
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self._run_scheduler())
            logger.info("Планировщик задач запущен")
    
    def stop(self) -> None:
        """Остановка планировщика."""
        if self.is_running:
            self.is_running = False
            if self.task:
                self.task.cancel()
            logger.info("Планировщик задач остановлен")
    
    async def _run_scheduler(self) -> None:
        """Основной цикл планировщика."""
        # Небольшая задержка перед первой проверкой (для инициализации БД)
        await asyncio.sleep(5)
        
        while self.is_running:
            try:
                await self._process_warmup_messages()
                await self._process_followup_messages()
                await asyncio.sleep(60)  # Проверяем каждую минуту
            except asyncio.CancelledError:
                logger.info("Планировщик задач отменен")
                break
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                await asyncio.sleep(60)
    
    async def _process_warmup_messages(self) -> None:
        """Обработка сообщений прогрева."""
        try:
            async with get_db_session() as session:
                warmup_service = WarmupService(session)
                telegram_service = TelegramService(self.bot)
                product_service = ProductService(session)
                
                # Получаем пользователей, готовых к следующему сообщению
                ready_users = await warmup_service.get_users_ready_for_next_message()
                
                for user_data in ready_users:
                    user = user_data['user']
                    message = user_data['message']
                    user_warmup = user_data['user_warmup']
                    
                    try:
                        # Создаем клавиатуру в зависимости от типа сообщения
                        reply_markup = await self._create_message_keyboard(
                            message, product_service, user.id
                        )
                        
                        # Отправляем сообщение
                        success = await telegram_service.send_warmup_message(
                            chat_id=user.telegram_id,
                            title=message.title or "",
                            text=message.text,
                            reply_markup=reply_markup
                        )
                        
                        # Отмечаем сообщение как отправленное
                        await warmup_service.mark_message_sent(
                            user_id=str(user.id),
                            warmup_message_id=str(message.id),
                            success=success
                        )
                        
                        logger.info(f"Отправлено сообщение прогрева пользователю {user.telegram_id}: {message.title}")
                        
                    except Exception as e:
                        logger.error(f"Ошибка отправки сообщения пользователю {user.telegram_id}: {e}")
                        
                        # Отмечаем сообщение как неудачное
                        await warmup_service.mark_message_sent(
                            user_id=str(user.id),
                            warmup_message_id=str(message.id),
                            success=False,
                            error_message=str(e)
                        )
                
                if ready_users:
                    logger.info(f"Обработано {len(ready_users)} сообщений прогрева")
                    
        except Exception as e:
            logger.error(f"Ошибка обработки сообщений прогрева: {e}")
    
    async def _process_followup_messages(self) -> None:
        """Обработка дожимов."""
        try:
            async with get_db_session() as session:
                followup_service = FollowUpService(session)
                telegram_service = TelegramService(self.bot)
                
                # Отправляем дожим пользователям, которые не купили трипвайер
                sent_count = await followup_service.send_followup_to_all_users(
                    telegram_service=telegram_service,
                    hours_since_offer=48  # Через 2 дня
                )
                
                if sent_count > 0:
                    logger.info(f"Отправлено {sent_count} дожимов")
                    
        except Exception as e:
            logger.error(f"Ошибка обработки дожимов: {e}")
    
    async def _create_message_keyboard(
        self, 
        message, 
        product_service: ProductService, 
        user_id: int
    ) -> InlineKeyboardMarkup:
        """
        Создание клавиатуры для сообщения прогрева.
        
        Args:
            message: Сообщение прогрева
            product_service: Сервис продуктов
            user_id: ID пользователя
            
        Returns:
            InlineKeyboardMarkup: Клавиатура для сообщения
        """
        keyboard = []
        
        if message.message_type == WarmupMessageType.OFFER:
            # Для оффера добавляем кнопку "Войти в программу"
            keyboard.append([
                InlineKeyboardButton("🚀 Войти в программу", callback_data="warmup_offer")
            ])
            
        elif message.message_type == WarmupMessageType.FOLLOW_UP:
            # Для дожима тоже добавляем кнопку "Войти в программу"
            keyboard.append([
                InlineKeyboardButton("🚀 Войти в программу", callback_data="warmup_offer")
            ])
            
        elif message.message_type in [WarmupMessageType.PAIN_POINT, WarmupMessageType.SOLUTION, WarmupMessageType.SOCIAL_PROOF]:
            # Для информационных сообщений добавляем кнопку "Узнать больше"
            keyboard.append([
                InlineKeyboardButton("ℹ️ Узнать больше", callback_data="warmup_info")
            ])
        
        # Добавляем кнопку для остановки прогрева
        keyboard.append([
            InlineKeyboardButton("⏹️ Остановить прогрев", callback_data="warmup_stop")
        ])
        
        return InlineKeyboardMarkup(keyboard) if keyboard else None
    
    async def send_immediate_warmup_message(
        self, 
        user_id: int, 
        message_type: WarmupMessageType
    ) -> bool:
        """
        Отправка сообщения прогрева немедленно.
        
        Args:
            user_id: ID пользователя
            message_type: Тип сообщения
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        try:
            async with get_db_session() as session:
                warmup_service = WarmupService(session)
                telegram_service = TelegramService(self.bot)
                product_service = ProductService(session)
                
                # Получаем активный прогрев пользователя
                user_warmup = await warmup_service.get_user_active_warmup(str(user_id))
                if not user_warmup:
                    logger.warning(f"Нет активного прогрева для пользователя {user_id}")
                    return False
                
                # Получаем сценарий
                scenario = user_warmup.scenario
                if not scenario:
                    logger.warning(f"Нет сценария для прогрева пользователя {user_id}")
                    return False
                
                # Находим сообщение нужного типа
                target_message = None
                for message in scenario.messages:
                    if message.message_type == message_type and message.is_active:
                        target_message = message
                        break
                
                if not target_message:
                    logger.warning(f"Не найдено сообщение типа {message_type} для пользователя {user_id}")
                    return False
                
                # Создаем клавиатуру
                reply_markup = await self._create_message_keyboard(
                    target_message, product_service, user_id
                )
                
                # Отправляем сообщение
                success = await telegram_service.send_warmup_message(
                    chat_id=user_id,
                    title=target_message.title or "",
                    text=target_message.text,
                    reply_markup=reply_markup
                )
                
                if success:
                    # Отмечаем сообщение как отправленное
                    await warmup_service.mark_message_sent(
                        user_id=str(user_id),
                        warmup_message_id=str(target_message.id),
                        success=True
                    )
                
                return success
                
        except Exception as e:
            logger.error(f"Ошибка отправки немедленного сообщения прогрева пользователю {user_id}: {e}")
            return False
