"""
Сервис для работы с лид-магнитами.

Содержит логику выдачи подарков пользователям.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, String
from loguru import logger

from app.models import LeadMagnet, UserLeadMagnet, User
from app.schemas import LeadMagnetCreate


class LeadMagnetService:
    """Сервис для управления лид-магнитами."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_active_lead_magnets(self) -> List[LeadMagnet]:
        """Получение всех активных лид-магнитов."""
        try:
            result = await self.session.execute(
                select(LeadMagnet)
                .where(LeadMagnet.is_active == True)
                .order_by(LeadMagnet.sort_order)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка получения активных лид-магнитов: {e}")
            return []
    
    async def get_lead_magnet_by_id(self, lead_magnet_id: str) -> Optional[LeadMagnet]:
        """Получение лид-магнита по ID."""
        try:
            # Если ID короткий (8 символов), ищем по частичному совпадению
            if len(lead_magnet_id) == 8:
                result = await self.session.execute(
                    select(LeadMagnet).where(LeadMagnet.id.cast(String).like(f"{lead_magnet_id}%"))
                )
                return result.scalar_one_or_none()
            else:
                # Полный UUID
                result = await self.session.execute(
                    select(LeadMagnet).where(LeadMagnet.id == lead_magnet_id)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка получения лид-магнита {lead_magnet_id}: {e}")
            return None
    
    async def create_lead_magnet(self, lead_magnet_data: LeadMagnetCreate) -> Optional[LeadMagnet]:
        """Создание нового лид-магнита."""
        try:
            lead_magnet = LeadMagnet(**lead_magnet_data.model_dump() if hasattr(lead_magnet_data, 'model_dump') else lead_magnet_data)
            self.session.add(lead_magnet)
            await self.session.commit()
            await self.session.refresh(lead_magnet)
            
            logger.info(f"Создан новый лид-магнит: {lead_magnet.name}")
            return lead_magnet
        except Exception as e:
            logger.error(f"Ошибка создания лид-магнита: {e}")
            await self.session.rollback()
            return None
    
    async def user_has_lead_magnet(self, user_id: str) -> bool:
        """Проверка, получал ли пользователь лид-магнит."""
        try:
            result = await self.session.execute(
                select(UserLeadMagnet).where(UserLeadMagnet.user_id == user_id)
            )
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Ошибка проверки лид-магнита пользователя {user_id}: {e}")
            return False
    
    async def give_lead_magnet_to_user(self, user_id: str) -> Optional[LeadMagnet]:
        """Выдача лид-магнита пользователю."""
        try:
            # Проверяем, получал ли пользователь уже лид-магнит
            if await self.user_has_lead_magnet(user_id):
                logger.info(f"Пользователь {user_id} уже получал лид-магнит")
                return None
            
            # Получаем активный лид-магнит
            lead_magnets = await self.get_active_lead_magnets()
            if not lead_magnets:
                logger.warning("Нет активных лид-магнитов")
                return None
            
            # Берем первый активный лид-магнит
            lead_magnet = lead_magnets[0]
            
            # Создаем запись о выдаче лид-магнита
            user_lead_magnet = UserLeadMagnet(
                user_id=user_id,
                lead_magnet_id=str(lead_magnet.id)
            )
            self.session.add(user_lead_magnet)
            await self.session.commit()
            
            logger.info(f"Выдан лид-магнит {lead_magnet.name} пользователю {user_id}")
            return lead_magnet
            
        except Exception as e:
            logger.error(f"Ошибка выдачи лид-магнита пользователю {user_id}: {e}")
            await self.session.rollback()
            return None
    
    async def get_user_lead_magnets(self, user_id: str) -> List[UserLeadMagnet]:
        """Получение всех лид-магнитов пользователя."""
        try:
            result = await self.session.execute(
                select(UserLeadMagnet)
                .where(UserLeadMagnet.user_id == user_id)
                .order_by(UserLeadMagnet.issued_at.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка получения лид-магнитов пользователя {user_id}: {e}")
            return []
    
    async def get_lead_magnet_stats(self) -> dict:
        """Получение статистики по лид-магнитам."""
        try:
            # Общее количество выданных лид-магнитов
            total_result = await self.session.execute(select(UserLeadMagnet))
            total_issued = len(total_result.scalars().all())
            
            # Количество уникальных пользователей
            unique_users_result = await self.session.execute(
                select(UserLeadMagnet.user_id).distinct()
            )
            unique_users = len(unique_users_result.scalars().all())
            
            # Статистика по типам лид-магнитов
            lead_magnets = await self.get_active_lead_magnets()
            type_stats = {}
            for lm in lead_magnets:
                result = await self.session.execute(
                    select(UserLeadMagnet).where(UserLeadMagnet.lead_magnet_id == str(lm.id))
                )
                type_stats[lm.name] = len(result.scalars().all())
            
            return {
                "total_issued": total_issued,
                "unique_users": unique_users,
                "type_stats": type_stats,
                "active_lead_magnets": len(lead_magnets)
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики лид-магнитов: {e}")
            return {
                "total_issued": 0,
                "unique_users": 0,
                "type_stats": {},
                "active_lead_magnets": 0
            }
    
    async def create_default_lead_magnet(self) -> Optional[LeadMagnet]:
        """Создание лид-магнита по умолчанию (7-дневный трекер)."""
        try:
            # Проверяем, есть ли уже лид-магнит с таким названием
            result = await self.session.execute(
                select(LeadMagnet).where(LeadMagnet.name == "7-дневный трекер дисциплины и силы")
            )
            if result.scalar_one_or_none():
                logger.info("Лид-магнит по умолчанию уже существует")
                return None
            
            # Создаем лид-магнит по умолчанию
            default_lead_magnet = LeadMagnet(
                name="7-дневный трекер дисциплины и силы",
                description="Трекер для отслеживания прогресса в дисциплине и силе воли",
                type="google_sheet",
                file_url="https://docs.google.com/spreadsheets/d/example",  # Замените на реальную ссылку
                message_text=(
                    "🎯 Этот трекер поможет вам:\n"
                    "• Отслеживать ежедневные привычки\n"
                    "• Измерять прогресс в дисциплине\n"
                    "• Видеть результаты за неделю\n"
                    "• Мотивировать себя на продолжение\n\n"
                    "📊 Используйте его каждый день для максимального эффекта!"
                ),
                is_active=True,
                sort_order=1
            )
            
            self.session.add(default_lead_magnet)
            await self.session.commit()
            await self.session.refresh(default_lead_magnet)
            
            logger.info("Создан лид-магнит по умолчанию")
            return default_lead_magnet
            
        except Exception as e:
            logger.error(f"Ошибка создания лид-магнита по умолчанию: {e}")
            await self.session.rollback()
            return None
    
    async def update_lead_magnet(self, lead_magnet_id: str, update_data: dict) -> Optional[LeadMagnet]:
        """Обновление лид-магнита."""
        try:
            lead_magnet = await self.get_lead_magnet_by_id(lead_magnet_id)
            if not lead_magnet:
                return None
            
            # Обновляем поля
            for field, value in update_data.items():
                if hasattr(lead_magnet, field) and value is not None:
                    setattr(lead_magnet, field, value)
            
            await self.session.commit()
            await self.session.refresh(lead_magnet)
            
            logger.info(f"Обновлен лид-магнит: {lead_magnet.name}")
            return lead_magnet
            
        except Exception as e:
            logger.error(f"Ошибка обновления лид-магнита {lead_magnet_id}: {e}")
            await self.session.rollback()
            return None
    
    async def delete_lead_magnet(self, lead_magnet_id: str) -> bool:
        """Удаление лид-магнита."""
        try:
            lead_magnet = await self.get_lead_magnet_by_id(lead_magnet_id)
            if not lead_magnet:
                return False
            
            # Удаляем все записи о выдаче этого лид-магнита
            await self.session.execute(
                select(UserLeadMagnet).where(UserLeadMagnet.lead_magnet_id == str(lead_magnet.id))
            )
            issued_records = await self.session.execute(
                select(UserLeadMagnet).where(UserLeadMagnet.lead_magnet_id == str(lead_magnet.id))
            )
            for record in issued_records.scalars().all():
                await self.session.delete(record)
            
            # Удаляем сам лид-магнит
            await self.session.delete(lead_magnet)
            await self.session.commit()
            
            logger.info(f"Удален лид-магнит: {lead_magnet.name}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления лид-магнита {lead_magnet_id}: {e}")
            await self.session.rollback()
            return False
    
    async def toggle_lead_magnet_status(self, lead_magnet_id: str) -> Optional[LeadMagnet]:
        """Переключение статуса лид-магнита (активен/неактивен)."""
        try:
            lead_magnet = await self.get_lead_magnet_by_id(lead_magnet_id)
            if not lead_magnet:
                return None
            
            lead_magnet.is_active = not lead_magnet.is_active
            await self.session.commit()
            await self.session.refresh(lead_magnet)
            
            status = "активирован" if lead_magnet.is_active else "деактивирован"
            logger.info(f"Лид-магнит {lead_magnet.name} {status}")
            return lead_magnet
            
        except Exception as e:
            logger.error(f"Ошибка переключения статуса лид-магнита {lead_magnet_id}: {e}")
            await self.session.rollback()
            return None
    
    async def get_all_lead_magnets(self) -> List[LeadMagnet]:
        """Получение всех лид-магнитов (включая неактивные)."""
        try:
            result = await self.session.execute(
                select(LeadMagnet)
                .order_by(LeadMagnet.sort_order.asc(), LeadMagnet.created_at.asc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка получения всех лид-магнитов: {e}")
            return []
    
    async def get_lead_magnets_by_type(self, magnet_type: str) -> List[LeadMagnet]:
        """Получение лид-магнитов по типу."""
        try:
            result = await self.session.execute(
                select(LeadMagnet)
                .where(LeadMagnet.type == magnet_type)
                .order_by(LeadMagnet.sort_order.asc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка получения лид-магнитов типа {magnet_type}: {e}")
            return []
