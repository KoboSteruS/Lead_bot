"""
Скрипт для инициализации лид-магнитов в базе данных.

Создает базовые лид-магниты для проекта "ОСНОВА P U T И".
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from app.core.database import get_db_session
from app.services.lead_magnet_service import LeadMagnetService
from app.models.lead_magnet import LeadMagnetType


async def create_default_lead_magnets():
    """Создание лид-магнитов по умолчанию."""
    
    lead_magnets_data = [
        {
            "name": "7-дневный трекер дисциплины и силы",
            "description": "Практический инструмент для развития дисциплины и силы воли",
            "type": LeadMagnetType.GOOGLE_SHEET,
            "file_url": "https://docs.google.com/spreadsheets/d/your-sheet-id/edit?usp=sharing",
            "message_text": (
                "🎯 <b>Ваш трекер готов!</b>\n\n"
                "📋 <b>Что внутри:</b>\n"
                "• 7 дней структурированного трекинга\n"
                "• Категории: утренние ритуалы, физическая активность, обучение\n"
                "• Система оценок и мотивации\n"
                "• Автоматические расчеты прогресса\n\n"
                "💡 <b>Как использовать:</b>\n"
                "1. Откройте таблицу по ссылке ниже\n"
                "2. Создайте копию для себя\n"
                "3. Заполняйте каждый день\n"
                "4. Анализируйте прогресс\n\n"
                "🔥 <b>Результат:</b> За 7 дней вы заложите фундамент для устойчивых привычек!"
            ),
            "is_active": True,
            "sort_order": 1
        },
        {
            "name": "7-дневный трекер дисциплины и силы (PDF)",
            "description": "PDF версия трекера для печати",
            "type": LeadMagnetType.PDF,
            "file_url": "https://your-domain.com/files/7-day-tracker.pdf",
            "message_text": (
                "📄 <b>PDF версия трекера готова!</b>\n\n"
                "📋 <b>Преимущества PDF версии:</b>\n"
                "• Можно распечатать и заполнять от руки\n"
                "• Работает без интернета\n"
                "• Удобно брать с собой\n"
                "• Классический формат планирования\n\n"
                "💡 <b>Как использовать:</b>\n"
                "1. Скачайте PDF по ссылке ниже\n"
                "2. Распечатайте нужное количество копий\n"
                "3. Заполняйте каждый день\n"
                "4. Храните для анализа прогресса\n\n"
                "🔥 <b>Результат:</b> Физический трекер поможет лучше контролировать прогресс!"
            ),
            "is_active": True,
            "sort_order": 2
        }
    ]
    
    try:
        async with get_db_session() as session:
            lead_magnet_service = LeadMagnetService(session)
            
            for magnet_data in lead_magnets_data:
                # Проверяем, существует ли уже такой лид-магнит
                existing_magnets = await lead_magnet_service.get_all_lead_magnets()
                existing_names = [m.name for m in existing_magnets]
                
                if magnet_data["name"] not in existing_names:
                    # Создаем новый лид-магнит
                    lead_magnet = await lead_magnet_service.create_lead_magnet(magnet_data)
                    logger.info(f"✅ Создан лид-магнит: {lead_magnet.name}")
                else:
                    logger.info(f"⚠️ Лид-магнит уже существует: {magnet_data['name']}")
            
            logger.info("🎉 Инициализация лид-магнитов завершена!")
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания лид-магнитов: {e}")
        raise


async def main():
    """Основная функция."""
    try:
        logger.info("🚀 Начинаем инициализацию лид-магнитов...")
        await create_default_lead_magnets()
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
