#!/usr/bin/env python3
"""
Скрипт для сброса выданных лид-магнитов.

Используется для исправления состояния пользователей,
которые получили лид-магнит из-за багов.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from app.core.database import get_db_session
from app.services import UserService, LeadMagnetService
from app.models.lead_magnet import UserLeadMagnet
from sqlalchemy import delete


async def reset_all_lead_magnets():
    """Сброс всех выданных лид-магнитов."""
    try:
        logger.info("Начинаем сброс выданных лид-магнитов...")
        
        async with get_db_session() as session:
            user_service = UserService(session)
            lead_magnet_service = LeadMagnetService(session)
            
            # Получаем всех пользователей
            users = await user_service.get_all_users()
            logger.info(f"Найдено пользователей: {len(users)}")
            
            reset_count = 0
            
            for user in users:
                has_magnet = await lead_magnet_service.user_has_lead_magnet(str(user.id))
                if has_magnet:
                    logger.info(f"Сбрасываем лид-магнит для пользователя {user.telegram_id} ({user.full_name})")
                    
                    # Удаляем записи о выданных лид-магнитах
                    await session.execute(
                        delete(UserLeadMagnet).where(UserLeadMagnet.user_id == str(user.id))
                    )
                    reset_count += 1
            
            await session.commit()
            logger.info(f"Сброшено лид-магнитов для {reset_count} пользователей")
            
    except Exception as e:
        logger.error(f"Ошибка сброса лид-магнитов: {e}")
        raise


async def reset_user_lead_magnet(telegram_id: int):
    """Сброс лид-магнита для конкретного пользователя."""
    try:
        logger.info(f"Сбрасываем лид-магнит для пользователя {telegram_id}...")
        
        async with get_db_session() as session:
            user_service = UserService(session)
            lead_magnet_service = LeadMagnetService(session)
            
            # Получаем пользователя
            user = await user_service.get_user_by_telegram_id(telegram_id)
            if not user:
                logger.warning(f"Пользователь {telegram_id} не найден")
                return False
            
            has_magnet = await lead_magnet_service.user_has_lead_magnet(str(user.id))
            if not has_magnet:
                logger.info(f"Пользователь {telegram_id} не имеет записей о лид-магнитах")
                return False
            
            # Удаляем записи о выданных лид-магнитах
            await session.execute(
                delete(UserLeadMagnet).where(UserLeadMagnet.user_id == str(user.id))
            )
            await session.commit()
            
            logger.info(f"Лид-магнит сброшен для пользователя {telegram_id}")
            return True
            
    except Exception as e:
        logger.error(f"Ошибка сброса лид-магнита для пользователя {telegram_id}: {e}")
        return False


async def show_users_with_magnets():
    """Показать пользователей с лид-магнитами."""
    try:
        async with get_db_session() as session:
            user_service = UserService(session)
            lead_magnet_service = LeadMagnetService(session)
            
            users = await user_service.get_all_users()
            logger.info(f"Всего пользователей: {len(users)}")
            
            users_with_magnets = []
            
            for user in users:
                has_magnet = await lead_magnet_service.user_has_lead_magnet(str(user.id))
                if has_magnet:
                    users_with_magnets.append(user)
                    logger.info(f"Пользователь {user.telegram_id} ({user.full_name}) - получил лид-магнит")
            
            logger.info(f"Пользователей с лид-магнитами: {len(users_with_magnets)}")
            return users_with_magnets
            
    except Exception as e:
        logger.error(f"Ошибка получения пользователей: {e}")
        return []


async def main():
    """Основная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Управление выданными лид-магнитами")
    parser.add_argument("--show", action="store_true", help="Показать пользователей с лид-магнитами")
    parser.add_argument("--reset-all", action="store_true", help="Сбросить все выданные лид-магниты")
    parser.add_argument("--reset-user", type=int, help="Сбросить лид-магнит для конкретного пользователя (telegram_id)")
    
    args = parser.parse_args()
    
    if args.show:
        await show_users_with_magnets()
    elif args.reset_all:
        await reset_all_lead_magnets()
    elif args.reset_user:
        await reset_user_lead_magnet(args.reset_user)
    else:
        print("Использование:")
        print("  python scripts/reset_lead_magnets.py --show                    # Показать пользователей с лид-магнитами")
        print("  python scripts/reset_lead_magnets.py --reset-all              # Сбросить все лид-магниты")
        print("  python scripts/reset_lead_magnets.py --reset-user 5837301513  # Сбросить лид-магнит для пользователя")


if __name__ == "__main__":
    # Настраиваем логирование
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
    
    asyncio.run(main())
