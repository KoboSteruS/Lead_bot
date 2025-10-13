"""
Скрипт для инициализации сценария прогрева в базе данных.

Создает базовый сценарий прогрева для проекта "ОСНОВА P U T И".
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from app.core.database import get_db_session
from app.services.warmup_service import WarmupService
from app.models.warmup import WarmupMessageType


async def create_default_warmup_scenario():
    """Создание сценария прогрева по умолчанию."""
    
    try:
        async with get_db_session() as session:
            warmup_service = WarmupService(session)
            
            # Проверяем, есть ли уже активный сценарий
            existing_scenario = await warmup_service.get_active_scenario()
            
            if not existing_scenario:
                # Создаем сценарий прогрева по умолчанию
                scenario = await warmup_service.create_default_scenario()
                logger.info(f"✅ Создан сценарий прогрева: {scenario.name}")
            else:
                logger.info(f"⚠️ Сценарий прогрева уже существует: {existing_scenario.name}")
            
            logger.info("🎉 Инициализация сценария прогрева завершена!")
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания сценария прогрева: {e}")
        raise


async def main():
    """Основная функция."""
    try:
        logger.info("🚀 Начинаем инициализацию сценария прогрева...")
        await create_default_warmup_scenario()
        logger.info("✅ Инициализация завершена успешно!")
        
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
