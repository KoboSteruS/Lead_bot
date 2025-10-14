"""
Утилиты для проверки прав администратора.
"""

from typing import Optional
from loguru import logger

from app.core.database import get_db_session
from app.services.admin_service import AdminService
from config.settings import settings


async def is_admin(telegram_id: int) -> bool:
    """
    Проверить, является ли пользователь администратором.
    Проверяет как .env файл, так и базу данных.
    
    Args:
        telegram_id: ID пользователя в Telegram
        
    Returns:
        True если админ, иначе False
    """
    # Проверяем в .env (приоритет)
    if telegram_id in settings.admin_ids_list:
        return True
    
    # Проверяем в базе данных
    try:
        async with get_db_session() as session:
            admin_service = AdminService(session)
            admin = await admin_service.get_admin_by_telegram_id(telegram_id)
            
            if admin and admin.is_active:
                return True
    except Exception as e:
        logger.error(f"Ошибка проверки админа {telegram_id}: {e}")
    
    return False


async def get_all_admin_ids() -> list[int]:
    """
    Получить список всех Telegram ID администраторов.
    Объединяет админов из .env и базы данных.
    
    Returns:
        Список ID админов
    """
    admin_ids = list(settings.admin_ids_list)
    
    try:
        async with get_db_session() as session:
            admin_service = AdminService(session)
            admins = await admin_service.get_all_admins()
            
            for admin in admins:
                if admin.telegram_id not in admin_ids:
                    admin_ids.append(admin.telegram_id)
    except Exception as e:
        logger.error(f"Ошибка получения списка админов: {e}")
    
    return admin_ids

