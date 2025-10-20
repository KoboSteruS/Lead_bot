"""
Сервис для работы с рассылками.

Содержит логику создания и отправки массовых рассылок.
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, String, delete
from loguru import logger

from app.models.mailing import Mailing, MailingRecipient, MailingStatus
from app.models.user import User
from app.services.telegram_service import TelegramService


class MailingService:
    """Сервис для управления рассылками."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_mailing(
        self, 
        name: str, 
        message_text: str, 
        created_by: str
    ) -> Optional[Mailing]:
        """Создание новой рассылки."""
        try:
            mailing = Mailing(
                name=name,
                message_text=message_text,
                status=MailingStatus.DRAFT,
                created_by=created_by
            )
            
            self.session.add(mailing)
            await self.session.commit()
            await self.session.refresh(mailing)
            
            logger.info(f"Создана рассылка: {mailing.name}")
            return mailing
            
        except Exception as e:
            logger.error(f"Ошибка создания рассылки: {e}")
            await self.session.rollback()
            return None
    
    async def get_mailing_by_id(self, mailing_id: str) -> Optional[Mailing]:
        """Получение рассылки по ID."""
        try:
            # Если ID короткий (8 символов), ищем по частичному совпадению
            if len(mailing_id) == 8:
                result = await self.session.execute(
                    select(Mailing).where(Mailing.id.cast(String).like(f"{mailing_id}%"))
                )
                return result.scalar_one_or_none()
            else:
                # Полный UUID
                result = await self.session.execute(
                    select(Mailing).where(Mailing.id == mailing_id)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка получения рассылки {mailing_id}: {e}")
            return None
    
    async def get_all_mailings(self) -> List[Mailing]:
        """Получение всех рассылок."""
        try:
            result = await self.session.execute(
                select(Mailing)
                .order_by(Mailing.created_at.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка получения рассылок: {e}")
            return []
    
    async def update_mailing(self, mailing_id: str, update_data: dict) -> Optional[Mailing]:
        """Обновление рассылки."""
        try:
            mailing = await self.get_mailing_by_id(mailing_id)
            if not mailing:
                return None
            
            # Обновляем поля
            for field, value in update_data.items():
                if hasattr(mailing, field) and value is not None:
                    setattr(mailing, field, value)
            
            await self.session.commit()
            await self.session.refresh(mailing)
            
            logger.info(f"Обновлена рассылка: {mailing.name}")
            return mailing
            
        except Exception as e:
            logger.error(f"Ошибка обновления рассылки {mailing_id}: {e}")
            await self.session.rollback()
            return None
    
    async def delete_mailing(self, mailing_id: str) -> bool:
        """Удаление рассылки."""
        try:
            mailing = await self.get_mailing_by_id(mailing_id)
            if not mailing:
                return False
            
            # Удаляем получателей
            await self.session.execute(
                select(MailingRecipient).where(MailingRecipient.mailing_id == mailing_id)
            )
            
            # Удаляем саму рассылку
            await self.session.delete(mailing)
            await self.session.commit()
            
            logger.info(f"Удалена рассылка: {mailing.name}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления рассылки {mailing_id}: {e}")
            await self.session.rollback()
            return False
    
    async def prepare_mailing(self, mailing_id: str) -> Optional[Mailing]:
        """Подготовка рассылки - создание списка получателей."""
        try:
            mailing = await self.get_mailing_by_id(mailing_id)
            if not mailing:
                return None
            
            # Получаем всех пользователей
            users_result = await self.session.execute(select(User))
            users = users_result.scalars().all()
            
            # Создаем записи получателей
            recipients = []
            for user in users:
                recipient = MailingRecipient(
                    mailing_id=str(mailing.id),
                    user_id=str(user.id),
                    delivery_status="pending"
                )
                recipients.append(recipient)
            
            # Сохраняем получателей
            self.session.add_all(recipients)
            
            # Обновляем статистику рассылки
            mailing.total_recipients = len(users)
            mailing.status = MailingStatus.SCHEDULED
            mailing.started_at = datetime.utcnow()
            
            await self.session.commit()
            await self.session.refresh(mailing)
            
            logger.info(f"Подготовлена рассылка {mailing.name} для {len(users)} получателей")
            return mailing
            
        except Exception as e:
            logger.error(f"Ошибка подготовки рассылки {mailing_id}: {e}")
            await self.session.rollback()
            return None
    
    async def reset_mailing(self, mailing_id: str) -> Optional[Mailing]:
        """
        Сброс рассылки для повторной отправки.
        
        Args:
            mailing_id: ID рассылки
            
        Returns:
            Optional[Mailing]: Обновленная рассылка или None при ошибке
        """
        try:
            mailing = await self.get_mailing_by_id(mailing_id)
            
            if not mailing:
                logger.error(f"Рассылка {mailing_id} не найдена")
                return None
            
            # Удаляем всех получателей
            await self.session.execute(
                delete(MailingRecipient).where(MailingRecipient.mailing_id == str(mailing.id))
            )
            
            # Сбрасываем статистику
            mailing.status = MailingStatus.DRAFT
            mailing.total_recipients = 0
            mailing.sent_count = 0
            mailing.delivered_count = 0
            mailing.failed_count = 0
            mailing.started_at = None
            mailing.completed_at = None
            
            await self.session.commit()
            await self.session.refresh(mailing)
            
            logger.info(f"Рассылка {mailing.name} сброшена для повторной отправки")
            return mailing
            
        except Exception as e:
            logger.error(f"Ошибка сброса рассылки {mailing_id}: {e}")
            await self.session.rollback()
            return None
    
    async def send_mailing(self, mailing_id: str, bot) -> Optional[Mailing]:
        """Отправка рассылки."""
        try:
            mailing = await self.get_mailing_by_id(mailing_id)
            if not mailing:
                return None
            
            # Получаем список получателей
            recipients_result = await self.session.execute(
                select(MailingRecipient).where(
                    and_(
                        MailingRecipient.mailing_id == str(mailing.id),
                        MailingRecipient.delivery_status == "pending"
                    )
                )
            )
            recipients = recipients_result.scalars().all()
            
            if not recipients:
                logger.warning(f"Нет получателей для рассылки {mailing.name}")
                return mailing
            
            # Обновляем статус на "отправляется"
            mailing.status = MailingStatus.SENDING
            await self.session.commit()
            
            # Отправляем сообщения
            telegram_service = TelegramService(bot)
            sent_count = 0
            failed_count = 0
            
            for recipient in recipients:
                try:
                    # Получаем пользователя (конвертируем строку UUID в объект UUID)
                    user_result = await self.session.execute(
                        select(User).where(User.id == recipient.user_id)
                    )
                    user = user_result.scalar_one_or_none()
                    
                    if not user:
                        recipient.delivery_status = "failed"
                        recipient.error_message = "Пользователь не найден"
                        failed_count += 1
                        continue
                    
                    # Отправляем сообщение
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=mailing.message_text,
                        parse_mode="HTML"
                    )
                    
                    # Обновляем статус получателя
                    recipient.delivery_status = "delivered"
                    recipient.sent_at = datetime.utcnow()
                    sent_count += 1
                    
                    # Небольшая задержка между отправками
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения пользователю {recipient.user_id}: {e}")
                    recipient.delivery_status = "failed"
                    recipient.error_message = str(e)
                    failed_count += 1
                
                # Коммитим изменения для каждого получателя
                await self.session.commit()
            
            # Обновляем статистику рассылки
            mailing.sent_count = sent_count
            mailing.failed_count = failed_count
            mailing.delivered_count = sent_count  # В Telegram все отправленные считаются доставленными
            mailing.status = MailingStatus.COMPLETED
            mailing.completed_at = datetime.utcnow()
            
            await self.session.commit()
            await self.session.refresh(mailing)
            
            logger.info(f"Рассылка {mailing.name} завершена: {sent_count} отправлено, {failed_count} ошибок")
            return mailing
            
        except Exception as e:
            logger.error(f"Ошибка отправки рассылки {mailing_id}: {e}")
            await self.session.rollback()
            
            # Обновляем статус на "неудачная"
            mailing = await self.get_mailing_by_id(mailing_id)
            if mailing:
                mailing.status = MailingStatus.FAILED
                await self.session.commit()
            
            return None
    
    async def update_mailing(
        self,
        mailing_id: str,
        name: Optional[str] = None,
        message_text: Optional[str] = None
    ) -> Optional[Mailing]:
        """
        Обновление рассылки.
        
        Args:
            mailing_id: ID рассылки
            name: Новое название (опционально)
            message_text: Новый текст (опционально)
            
        Returns:
            Optional[Mailing]: Обновленная рассылка или None при ошибке
        """
        try:
            mailing = await self.get_mailing_by_id(mailing_id)
            
            if not mailing:
                logger.error(f"Рассылка {mailing_id} не найдена")
                return None
            
            # Обновляем только переданные поля
            if name is not None:
                mailing.name = name
            
            if message_text is not None:
                mailing.message_text = message_text
            
            await self.session.commit()
            await self.session.refresh(mailing)
            
            logger.info(f"Рассылка {mailing.name} обновлена")
            return mailing
            
        except Exception as e:
            logger.error(f"Ошибка обновления рассылки {mailing_id}: {e}")
            await self.session.rollback()
            return None
    
    async def delete_mailing(self, mailing_id: str) -> bool:
        """
        Удаление рассылки.
        
        Args:
            mailing_id: ID рассылки
            
        Returns:
            bool: True если рассылка удалена успешно
        """
        try:
            mailing = await self.get_mailing_by_id(mailing_id)
            
            if not mailing:
                logger.error(f"Рассылка {mailing_id} не найдена")
                return False
            
            # Удаляем всех получателей
            await self.session.execute(
                delete(MailingRecipient).where(MailingRecipient.mailing_id == str(mailing.id))
            )
            
            # Удаляем саму рассылку
            await self.session.delete(mailing)
            await self.session.commit()
            
            logger.info(f"Рассылка {mailing.name} удалена")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления рассылки {mailing_id}: {e}")
            await self.session.rollback()
            return False
    
    async def get_mailing_stats(self, mailing_id: str) -> Dict[str, Any]:
        """Получение статистики рассылки."""
        try:
            mailing = await self.get_mailing_by_id(mailing_id)
            if not mailing:
                return {}
            
            # Получаем статистику по статусам доставки
            status_stats = await self.session.execute(
                select(
                    MailingRecipient.delivery_status,
                    func.count(MailingRecipient.id).label('count')
                )
                .where(MailingRecipient.mailing_id == mailing_id)
                .group_by(MailingRecipient.delivery_status)
            )
            
            status_counts = {row.delivery_status: row.count for row in status_stats}
            
            return {
                "mailing": mailing,
                "total_recipients": mailing.total_recipients,
                "sent_count": mailing.sent_count,
                "delivered_count": mailing.delivered_count,
                "failed_count": mailing.failed_count,
                "status_counts": status_counts,
                "completion_rate": (mailing.delivered_count / mailing.total_recipients * 100) if mailing.total_recipients > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики рассылки {mailing_id}: {e}")
            return {}
    
    async def get_all_users_count(self) -> int:
        """Получение общего количества пользователей."""
        try:
            result = await self.session.execute(select(func.count(User.id)))
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Ошибка получения количества пользователей: {e}")
            return 0
