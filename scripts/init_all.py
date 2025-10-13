"""
Скрипт для полной инициализации базы данных.

Создает все необходимые данные для работы бота "ОСНОВА P U T И".
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from app.core.database import init_database


async def init_all():
    """Полная инициализация всех данных."""
    
    try:
        logger.info("🚀 Начинаем полную инициализацию...")
        
        # 1. Инициализируем базу данных
        logger.info("📊 Инициализируем базу данных...")
        await init_database()
        logger.info("✅ База данных инициализирована")
        
        # 2. Инициализируем лид-магниты
        logger.info("🎁 Инициализируем лид-магниты...")
        from scripts.init_lead_magnets import create_default_lead_magnets
        await create_default_lead_magnets()
        logger.info("✅ Лид-магниты созданы")
        
        # 3. Инициализируем трипвайер
        logger.info("💰 Инициализируем трипвайер...")
        from scripts.init_tripwire import create_default_tripwire
        await create_default_tripwire()
        logger.info("✅ Трипвайер создан")
        
        # 4. Инициализируем сценарий прогрева
        logger.info("🔥 Инициализируем сценарий прогрева...")
        from scripts.init_warmup import create_default_warmup_scenario
        await create_default_warmup_scenario()
        logger.info("✅ Сценарий прогрева создан")
        
        logger.info("🎉 Полная инициализация завершена успешно!")
        logger.info("🤖 Теперь можно запускать бота!")
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise


async def main():
    """Основная функция."""
    try:
        await init_all()
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Настраиваем логирование
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Запускаем инициализацию
    asyncio.run(main())
