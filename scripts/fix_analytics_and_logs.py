#!/usr/bin/env python3
"""
Скрипт для исправления проблем с аналитикой и логами.

Проверяет и исправляет:
1. Создание папки для логов
2. Проверку сценариев прогрева
3. Создание недостающих данных
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from app.core.database import get_db_session
from app.services.warmup_service import WarmupService
from app.services.lead_magnet_service import LeadMagnetService
from app.services.user_service import UserService
from config.settings import settings


async def fix_logging():
    """Исправляем настройки логирования."""
    logger.info("🔧 Исправляем настройки логирования...")
    
    # Создаем папку для логов
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        logger.info(f"✅ Создана папка для логов: {log_dir}")
    
    # Проверяем права на запись
    try:
        test_file = os.path.join(log_dir, "test.log")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        logger.info("✅ Права на запись в папку логов: OK")
    except Exception as e:
        logger.error(f"❌ Ошибка записи в папку логов: {e}")


async def check_warmup_scenarios():
    """Проверяем и создаем сценарии прогрева."""
    logger.info("🔥 Проверяем сценарии прогрева...")
    
    try:
        async with get_db_session() as session:
            warmup_service = WarmupService(session)
            
            # Проверяем активный сценарий
            active_scenario = await warmup_service.get_active_scenario()
            
            if not active_scenario:
                logger.warning("⚠️ Активный сценарий прогрева не найден")
                
                # Создаем сценарий по умолчанию
                scenario = await warmup_service.create_default_scenario()
                logger.info(f"✅ Создан сценарий прогрева: {scenario.name}")
            else:
                logger.info(f"✅ Активный сценарий найден: {active_scenario.name}")
                logger.info(f"   Сообщений в сценарии: {len(active_scenario.messages)}")
            
            # Получаем статистику
            stats = await warmup_service.get_warmup_stats()
            logger.info(f"📊 Статистика прогрева: {stats}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки сценариев прогрева: {e}")


async def check_lead_magnets():
    """Проверяем лид-магниты."""
    logger.info("🎁 Проверяем лид-магниты...")
    
    try:
        async with get_db_session() as session:
            lead_magnet_service = LeadMagnetService(session)
            
            # Проверяем активные лид-магниты
            active_magnets = await lead_magnet_service.get_active_lead_magnets()
            
            if not active_magnets:
                logger.warning("⚠️ Активные лид-магниты не найдены")
                
                # Создаем лид-магнит по умолчанию
                default_magnet = await lead_magnet_service.create_default_lead_magnet()
                if default_magnet:
                    logger.info(f"✅ Создан лид-магнит по умолчанию: {default_magnet.name}")
                else:
                    logger.warning("⚠️ Не удалось создать лид-магнит по умолчанию")
            else:
                logger.info(f"✅ Найдено активных лид-магнитов: {len(active_magnets)}")
                for magnet in active_magnets:
                    logger.info(f"   - {magnet.name}")
            
            # Получаем статистику
            stats = await lead_magnet_service.get_lead_magnet_stats()
            logger.info(f"📊 Статистика лид-магнитов: {stats}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки лид-магнитов: {e}")


async def check_users():
    """Проверяем пользователей."""
    logger.info("👥 Проверяем пользователей...")
    
    try:
        async with get_db_session() as session:
            user_service = UserService(session)
            
            # Получаем всех пользователей
            users = await user_service.get_all_users()
            logger.info(f"✅ Всего пользователей: {len(users)}")
            
            # Получаем статистику
            stats = await user_service.get_user_statistics()
            logger.info(f"📊 Статистика пользователей: {stats}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки пользователей: {e}")


async def main():
    """Основная функция."""
    try:
        logger.info("🚀 Запуск исправления аналитики и логов...")
        
        # Исправляем логирование
        await fix_logging()
        
        # Проверяем компоненты системы
        await check_warmup_scenarios()
        await check_lead_magnets()
        await check_users()
        
        logger.info("🎉 Исправление завершено успешно!")
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise


if __name__ == "__main__":
    # Настраиваем логирование для скрипта
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        colorize=True
    )
    
    asyncio.run(main())
