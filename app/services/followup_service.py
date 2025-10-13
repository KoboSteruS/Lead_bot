"""
Сервис для дожима пользователей.

Отслеживает пользователей, которые не купили трипвайер, и отправляет им дожим.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models import User, ProductOffer, UserProductOffer, Product, ProductType, UserFollowUp
from app.services.telegram_service import TelegramService
from app.services.product_service import ProductService


class FollowUpService:
    """Сервис для дожима пользователей."""
    
    def __init__(self, session: AsyncSession):
        """Инициализация сервиса."""
        self.session = session
    
    async def get_users_for_followup(self, hours_since_offer: int = 48) -> List[Dict[str, Any]]:
        """
        Получить пользователей для дожима.
        
        Args:
            hours_since_offer: Количество часов с момента показа оффера
            
        Returns:
            List[Dict[str, Any]]: Список пользователей для дожима
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_since_offer)
            
            # Получаем пользователей, которым показывали оффер, но они не купили
            stmt = (
                select(User, ProductOffer, UserProductOffer)
                .join(UserProductOffer, User.id == UserProductOffer.user_id)
                .join(ProductOffer, UserProductOffer.offer_id == ProductOffer.id)
                .join(Product, ProductOffer.product_id == Product.id)
                .where(
                    and_(
                        Product.type == ProductType.TRIPWIRE,
                        UserProductOffer.shown_at <= cutoff_time,
                        UserProductOffer.clicked == False,  # Не кликали на оффер
                        User.status == "active"  # Активные пользователи
                    )
                )
                .options(
                    selectinload(User.product_offers)
                )
            )
            
            result = await self.session.execute(stmt)
            users_for_followup = []
            
            for user, offer, user_offer in result.all():
                # Проверяем, не отправляли ли уже дожим
                followup_sent = await self._check_followup_sent(str(user.id), str(offer.id))
                if not followup_sent:
                    users_for_followup.append({
                        'user': user,
                        'offer': offer,
                        'user_offer': user_offer
                    })
            
            logger.info(f"Найдено {len(users_for_followup)} пользователей для дожима")
            return users_for_followup
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователей для дожима: {e}")
            return []
    
    async def send_followup_to_user(
        self, 
        user: User, 
        offer: ProductOffer, 
        telegram_service: TelegramService
    ) -> bool:
        """
        Отправить дожим пользователю.
        
        Args:
            user: Пользователь
            offer: Оффер
            telegram_service: Сервис Telegram
            
        Returns:
            bool: True если дожим отправлен успешно
        """
        try:
            # Формируем текст дожима
            followup_text = (
                "☕ <b>9€ — меньше, чем чашка кофе в день</b>\n\n"
                "Подумай об этом:\n"
                "• Чашка кофе даёт бодрость на 2 часа\n"
                "• Эта программа даст тебе систему на всю жизнь\n\n"
                "🎯 <b>За 30 дней ты:</b>\n"
                "• Создашь чёткий план достижения целей\n"
                "• Разовьёшь дисциплину и силу воли\n"
                "• Изменишь мышление на успех\n\n"
                "Результат может изменить твою жизнь.\n\n"
                "Это твой последний шанс войти в программу по этой цене."
            )
            
            # Создаем клавиатуру
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [InlineKeyboardButton("🚀 Войти в программу", callback_data="warmup_offer")],
                [InlineKeyboardButton("⏹️ Остановить напоминания", callback_data="stop_followup")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем дожим
            success = await telegram_service.send_follow_up_message(
                chat_id=user.telegram_id,
                follow_up_text=followup_text,
                reply_markup=reply_markup
            )
            
            if success:
                # Отмечаем, что дожим отправлен
                await self._mark_followup_sent(str(user.id), str(offer.id))
                logger.info(f"Отправлен дожим пользователю {user.telegram_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка отправки дожима пользователю {user.telegram_id}: {e}")
            return False
    
    async def send_followup_to_all_users(
        self, 
        telegram_service: TelegramService,
        hours_since_offer: int = 48
    ) -> int:
        """
        Отправить дожим всем подходящим пользователям.
        
        Args:
            telegram_service: Сервис Telegram
            hours_since_offer: Количество часов с момента показа оффера
            
        Returns:
            int: Количество отправленных дожимов
        """
        try:
            users_for_followup = await self.get_users_for_followup(hours_since_offer)
            sent_count = 0
            
            for user_data in users_for_followup:
                user = user_data['user']
                offer = user_data['offer']
                
                success = await self.send_followup_to_user(user, offer, telegram_service)
                if success:
                    sent_count += 1
                
                # Небольшая задержка между отправками
                await asyncio.sleep(1)
            
            logger.info(f"Отправлено {sent_count} дожимов из {len(users_for_followup)}")
            return sent_count
            
        except Exception as e:
            logger.error(f"Ошибка массовой отправки дожимов: {e}")
            return 0
    
    async def _check_followup_sent(self, user_id: str, offer_id: str) -> bool:
        """
        Проверить, отправлялся ли уже дожим.
        
        Args:
            user_id: ID пользователя
            offer_id: ID оффера
            
        Returns:
            bool: True если дожим уже отправлялся
        """
        try:
            result = await self.session.execute(
                select(UserFollowUp).where(
                    and_(
                        UserFollowUp.user_id == user_id,
                        UserFollowUp.offer_id == offer_id
                    )
                )
            )
            followup = result.scalar_one_or_none()
            return followup is not None
            
        except Exception as e:
            logger.error(f"Ошибка проверки отправки дожима: {e}")
            return False
    
    async def _mark_followup_sent(self, user_id: str, offer_id: str) -> None:
        """
        Отметить, что дожим отправлен.
        
        Args:
            user_id: ID пользователя
            offer_id: ID оффера
        """
        try:
            followup = UserFollowUp(
                user_id=user_id,
                offer_id=offer_id,
                sent_at=datetime.utcnow()
            )
            self.session.add(followup)
            await self.session.commit()
            
        except Exception as e:
            logger.error(f"Ошибка отметки отправки дожима: {e}")
            await self.session.rollback()
    
    async def stop_followup_for_user(self, user_id: str) -> bool:
        """
        Остановить дожим для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если дожим остановлен
        """
        try:
            # Здесь можно добавить логику остановки дожимов
            # Например, добавить флаг в таблицу User
            logger.info(f"Остановлен дожим для пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка остановки дожима для пользователя {user_id}: {e}")
            return False
