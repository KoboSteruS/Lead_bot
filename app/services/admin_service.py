"""
Сервис для управления администраторами бота.
"""

from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.admin import Admin
from config.settings import settings


class AdminService:
    """Сервис для работы с администраторами."""
    
    def __init__(self, session: AsyncSession):
        """
        Инициализация сервиса.
        
        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        self.session = session
    
    async def get_all_admins(self) -> List[Admin]:
        """Получить всех администраторов."""
        try:
            stmt = select(Admin).where(Admin.is_active == True).order_by(Admin.created_at.desc())
            result = await self.session.execute(stmt)
            admins = list(result.scalars().all())
            logger.info(f"Получено {len(admins)} администраторов")
            return admins
        except Exception as e:
            logger.error(f"Ошибка получения администраторов: {e}")
            return []
    
    async def get_admin_by_telegram_id(self, telegram_id: int) -> Optional[Admin]:
        """
        Получить администратора по Telegram ID.
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            Admin или None
        """
        try:
            stmt = select(Admin).where(Admin.telegram_id == telegram_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка получения админа {telegram_id}: {e}")
            return None
    
    async def is_admin(self, telegram_id: int) -> bool:
        """
        Проверить, является ли пользователь администратором.
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            True если админ, иначе False
        """
        # Проверяем в базе данных
        admin = await self.get_admin_by_telegram_id(telegram_id)
        if admin and admin.is_active:
            return True
        
        # Проверяем в .env (для обратной совместимости)
        if telegram_id in settings.admin_ids_list:
            # Синхронизируем с БД
            await self.add_admin(
                telegram_id=telegram_id,
                username=None,
                full_name="Админ из .env",
                added_by_id=telegram_id
            )
            return True
        
        return False
    
    async def get_all_admin_ids(self) -> List[int]:
        """
        Получить список всех Telegram ID администраторов.
        
        Returns:
            Список ID админов
        """
        admins = await self.get_all_admins()
        admin_ids = [admin.telegram_id for admin in admins]
        
        # Добавляем админов из .env (для обратной совместимости)
        for admin_id in settings.admin_ids_list:
            if admin_id not in admin_ids:
                admin_ids.append(admin_id)
        
        return admin_ids
    
    async def add_admin(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        added_by_id: Optional[int] = None,
        access_level: int = 1
    ) -> Optional[Admin]:
        """
        Добавить нового администратора.
        
        Args:
            telegram_id: ID пользователя в Telegram
            username: Username в Telegram
            full_name: Полное имя
            added_by_id: ID админа, который добавляет
            access_level: Уровень доступа (1-100)
            
        Returns:
            Созданный Admin или None
        """
        try:
            # Проверяем, не существует ли уже
            existing = await self.get_admin_by_telegram_id(telegram_id)
            if existing:
                if not existing.is_active:
                    # Активируем заново
                    existing.is_active = True
                    await self.session.commit()
                    await self.session.refresh(existing)
                    logger.info(f"Админ {telegram_id} реактивирован")
                    return existing
                else:
                    logger.warning(f"Админ {telegram_id} уже существует")
                    return existing
            
            # Создаем нового админа
            admin = Admin(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                is_active=True,
                access_level=access_level,
                added_by_id=added_by_id
            )
            
            self.session.add(admin)
            await self.session.commit()
            await self.session.refresh(admin)
            
            logger.info(f"Добавлен новый администратор: {telegram_id} (@{username})")
            return admin
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка добавления администратора {telegram_id}: {e}")
            return None
    
    async def remove_admin(self, telegram_id: int) -> bool:
        """
        Удалить администратора (деактивировать).
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            True если успешно, иначе False
        """
        try:
            admin = await self.get_admin_by_telegram_id(telegram_id)
            if not admin:
                logger.warning(f"Админ {telegram_id} не найден")
                return False
            
            # Деактивируем вместо удаления
            admin.is_active = False
            await self.session.commit()
            
            logger.info(f"Администратор {telegram_id} деактивирован")
            return True
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка удаления администратора {telegram_id}: {e}")
            return False
    
    async def delete_admin_permanently(self, telegram_id: int) -> bool:
        """
        Полностью удалить администратора из БД.
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            True если успешно, иначе False
        """
        try:
            stmt = delete(Admin).where(Admin.telegram_id == telegram_id)
            result = await self.session.execute(stmt)
            await self.session.commit()
            
            if result.rowcount > 0:
                logger.info(f"Администратор {telegram_id} полностью удален")
                return True
            else:
                logger.warning(f"Админ {telegram_id} не найден для удаления")
                return False
                
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка полного удаления администратора {telegram_id}: {e}")
            return False
    
    async def update_admin_info(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None
    ) -> Optional[Admin]:
        """
        Обновить информацию об администраторе.
        
        Args:
            telegram_id: ID пользователя в Telegram
            username: Новый username
            full_name: Новое полное имя
            
        Returns:
            Обновленный Admin или None
        """
        try:
            admin = await self.get_admin_by_telegram_id(telegram_id)
            if not admin:
                return None
            
            if username is not None:
                admin.username = username
            if full_name is not None:
                admin.full_name = full_name
            
            await self.session.commit()
            await self.session.refresh(admin)
            
            logger.info(f"Информация об админе {telegram_id} обновлена")
            return admin
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка обновления информации об админе {telegram_id}: {e}")
            return None

