"""
Сервис для работы с пользователями.

Содержит бизнес-логику для управления пользователями.
"""

from typing import Optional, List
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, delete, or_
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models.user import User, UserStatus
from app.schemas.user import UserCreate, UserUpdate
from app.core.exceptions import UserException


class UserService:
    """Сервис для работы с пользователями."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_user(self, user_data: UserCreate) -> User:
        """
        Создание нового пользователя.
        
        Args:
            user_data: Данные для создания пользователя
            
        Returns:
            User: Созданный пользователь
            
        Raises:
            UserException: Если пользователь уже существует
        """
        try:
            # Проверяем, существует ли пользователь
            existing_user = await self.get_user_by_telegram_id(user_data.telegram_id)
            if existing_user:
                raise UserException(f"Пользователь с Telegram ID {user_data.telegram_id} уже существует")
            
            # Создаем нового пользователя
            user = User(**user_data.model_dump() if hasattr(user_data, 'model_dump') else user_data)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            
            logger.info(f"Создан новый пользователь: {user.telegram_id}")
            return user
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка создания пользователя: {e}")
            raise UserException(f"Не удалось создать пользователя: {e}")
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Получение пользователя по ID.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Optional[User]: Пользователь или None
        """
        try:
            # Конвертируем строку в UUID для SQL запроса
            uuid_obj = UUID(user_id) if isinstance(user_id, str) else user_id
            result = await self.session.execute(
                select(User).where(User.id == uuid_obj)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка получения пользователя по ID {user_id}: {e}")
            return None
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Получение пользователя по Telegram ID.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            Optional[User]: Пользователь или None
        """
        try:
            result = await self.session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка получения пользователя по Telegram ID {telegram_id}: {e}")
            return None
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """
        Обновление пользователя.
        
        Args:
            user_id: ID пользователя
            user_data: Данные для обновления
            
        Returns:
            Optional[User]: Обновленный пользователь или None
        """
        try:
            # Получаем пользователя
            user = await self.get_user_by_id(user_id)
            if not user:
                raise UserException(f"Пользователь с ID {user_id} не найден")
            
            # Обновляем только переданные поля
            update_data = user_data.dict(exclude_unset=True)
            if update_data:
                await self.session.execute(
                    update(User).where(User.id == user_id).values(**update_data)
                )
                await self.session.commit()
                await self.session.refresh(user)
                
                logger.info(f"Обновлен пользователь: {user_id}")
            
            return user
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка обновления пользователя {user_id}: {e}")
            raise UserException(f"Не удалось обновить пользователя: {e}")
    
    async def get_users(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[UserStatus] = None
    ) -> List[User]:
        """
        Получение списка пользователей с пагинацией.
        
        Args:
            skip: Количество записей для пропуска
            limit: Максимальное количество записей
            status: Фильтр по статусу
            
        Returns:
            List[User]: Список пользователей
        """
        try:
            query = select(User)
            
            if status:
                query = query.where(User.status == status)
            
            query = query.offset(skip).limit(limit)
            result = await self.session.execute(query)
            
            return result.scalars().all()
        
        except Exception as e:
            logger.error(f"Ошибка получения списка пользователей: {e}")
            return []

    async def get_users_count(self) -> int:
        """
        Получить общее количество пользователей.
        
        Returns:
            int: Количество пользователей
        """
        try:
            stmt = select(func.count(User.id))
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Ошибка получения количества пользователей: {e}")
            return 0

    async def get_active_users_count(self) -> int:
        """
        Получить количество активных пользователей.
        
        Returns:
            int: Количество активных пользователей
        """
        try:
            stmt = select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Ошибка получения количества активных пользователей: {e}")
            return 0

    async def get_recent_users(self, limit: int = 10) -> List[User]:
        """
        Получить список последних пользователей.
        
        Args:
            limit: Максимальное количество пользователей
            
        Returns:
            List[User]: Список последних пользователей
        """
        try:
            stmt = select(User).order_by(User.created_at.desc()).limit(limit)
            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка получения последних пользователей: {e}")
            return []
    
    async def add_user_to_group(self, user_id: str) -> bool:
        """
        Добавление пользователя в группу.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если успешно добавлен
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                raise UserException(f"Пользователь с ID {user_id} не найден")
            
            if user.is_in_group:
                logger.warning(f"Пользователь {user_id} уже в группе")
                return True
            
            # Обновляем статус пользователя
            await self.update_user(user_id, UserUpdate(
                status=UserStatus.ACTIVE,
                is_in_group=True
            ))
            
            logger.info(f"Пользователь {user_id} добавлен в группу")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления пользователя {user_id} в группу: {e}")
            return False
    
    async def remove_user_from_group(self, user_id: str) -> bool:
        """
        Удаление пользователя из группы.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если успешно удален
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                raise UserException(f"Пользователь с ID {user_id} не найден")
            
            if not user.is_in_group:
                logger.warning(f"Пользователь {user_id} не в группе")
                return True
            
            # Обновляем статус пользователя
            await self.update_user(user_id, UserUpdate(
                status=UserStatus.INACTIVE,
                is_in_group=False
            ))
            
            logger.info(f"Пользователь {user_id} удален из группы")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления пользователя {user_id} из группы: {e}")
            return False
    
    async def ban_user(self, user_id: str) -> bool:
        """
        Бан пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если успешно забанен
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                raise UserException(f"Пользователь с ID {user_id} не найден")
            
            # Обновляем статус пользователя
            await self.update_user(user_id, UserUpdate(
                status=UserStatus.BANNED,
                is_in_group=False
            ))
            
            logger.info(f"Пользователь {user_id} забанен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка бана пользователя {user_id}: {e}")
            return False
    
    async def update_user_subscription(self, user_id: str, subscription_end: datetime) -> bool:
        """
        Обновление подписки пользователя.
        
        Args:
            user_id: ID пользователя
            subscription_end: Дата окончания подписки
            
        Returns:
            bool: True если подписка обновлена
        """
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                logger.error(f"Пользователь {user_id} не найден")
                return False
            
            # Обновляем подписку
            user.subscription_until = subscription_end
            user.status = UserStatus.ACTIVE
            user.updated_at = datetime.utcnow()
            
            await self.session.commit()
            logger.info(f"Подписка пользователя {user_id} обновлена до {subscription_end}")
            return True
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка обновления подписки пользователя {user_id}: {e}")
            return False
    
    async def get_all_users(self, offset: int = 0, limit: int = 20) -> List[User]:
        """Получить всех пользователей с пагинацией."""
        try:
            result = await self.session.execute(
                select(User)
                .order_by(User.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Ошибка получения всех пользователей: {e}")
            return []
    
    async def search_users(self, query: str, limit: int = 20) -> List[User]:
        """Поиск пользователей по имени или telegram_id."""
        try:
            result = await self.session.execute(
                select(User)
                .where(
                    or_(
                        User.display_name.ilike(f"%{query}%"),
                        User.username.ilike(f"%{query}%"),
                        User.telegram_id.ilike(f"%{query}%")
                    )
                )
                .order_by(User.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Ошибка поиска пользователей: {e}")
            return []
    
    async def update_user_status(self, user_id: str, status: str) -> bool:
        """Обновить статус пользователя."""
        try:
            result = await self.session.execute(
                update(User)
                .where(User.id == user_id)
                .values(status=status)
            )
            await self.session.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка обновления статуса пользователя {user_id}: {e}")
            await self.session.rollback()
            return False
    
    async def delete_user(self, user_id: str) -> bool:
        """Удалить пользователя."""
        try:
            # Конвертируем строку в UUID для SQL запроса
            uuid_obj = UUID(user_id) if isinstance(user_id, str) else user_id
            result = await self.session.execute(
                delete(User).where(User.id == uuid_obj)
            )
            await self.session.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка удаления пользователя {user_id}: {e}")
            await self.session.rollback()
            return False
    
    async def get_users_by_status(self, status: str, limit: int = 50) -> List[User]:
        """Получить пользователей по статусу."""
        try:
            result = await self.session.execute(
                select(User)
                .where(User.status == status)
                .order_by(User.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Ошибка получения пользователей по статусу {status}: {e}")
            return []
    
    async def get_inactive_users(self, days: int = 7) -> List[User]:
        """Получить неактивных пользователей (не заходили N дней)."""
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = await self.session.execute(
                select(User)
                .where(User.last_activity_at < cutoff_date)
                .order_by(User.last_activity_at.asc())
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Ошибка получения неактивных пользователей: {e}")
            return []
    
    async def get_user_statistics(self) -> dict:
        """Получить детальную статистику пользователей."""
        try:
            from datetime import timedelta
            
            # Общая статистика
            total = await self.get_users_count()
            active = await self.get_active_users_count()
            
            # По статусам
            active_users = len(await self.get_users_by_status("active"))
            inactive_users = len(await self.get_users_by_status("inactive"))
            banned_users = len(await self.get_users_by_status("banned"))
            
            # По времени
            today = datetime.utcnow().date()
            week_ago = datetime.utcnow() - timedelta(days=7)
            month_ago = datetime.utcnow() - timedelta(days=30)
            
            new_today = await self.session.execute(
                select(func.count(User.id))
                .where(func.date(User.created_at) == today)
            )
            new_week = await self.session.execute(
                select(func.count(User.id))
                .where(User.created_at >= week_ago)
            )
            new_month = await self.session.execute(
                select(func.count(User.id))
                .where(User.created_at >= month_ago)
            )
            
            return {
                "total": total,
                "active": active_users,
                "inactive": inactive_users,
                "banned": banned_users,
                "new_today": new_today.scalar() or 0,
                "new_week": new_week.scalar() or 0,
                "new_month": new_month.scalar() or 0,
                "activity_rate": round((active / max(total, 1)) * 100, 1)
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики пользователей: {e}")
            return {
                "total": 0, "active": 0, "inactive": 0, "banned": 0,
                "new_today": 0, "new_week": 0, "new_month": 0, "activity_rate": 0
            }
    
    async def get_users_by_date_range(self, start_date: datetime, end_date: datetime) -> List[User]:
        """Получить пользователей за период."""
        try:
            result = await self.session.execute(
                select(User)
                .where(
                    and_(
                        User.created_at >= start_date,
                        User.created_at <= end_date
                    )
                )
                .order_by(User.created_at.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка получения пользователей за период: {e}")
            return []