"""
Скрипт для инициализации трипвайера в базе данных.

Создает базовый трипвайер "30 дней по книге Наполеона Хилла" за 9€.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from app.core.database import get_db_session
from app.services.product_service import ProductService
from app.models.product import ProductType


async def create_default_tripwire():
    """Создание трипвайера по умолчанию."""
    
    # Данные для трипвайера
    tripwire_data = {
        "name": "30 дней по книге Наполеона Хилла",
        "description": "Практическая программа по применению 13 принципов успеха из книги «Думай и богатей»",
        "type": ProductType.TRIPWIRE,
        "price": 900,  # 9€ в центах
        "currency": "EUR",
        "payment_url": "https://your-payment-domain.com/pay/tripwire",
        "offer_text": (
            "🚀 <b>30 дней по книге Наполеона Хилла</b>\n\n"
            "📚 <b>Что вы получите:</b>\n"
            "• 30 практических заданий на каждый день\n"
            "• Пошаговое внедрение 13 принципов успеха\n"
            "• Систему отчётности и контроля\n"
            "• Поддержку и мотивацию\n"
            "• Доступ к закрытому чату участников\n\n"
            "🎯 <b>Результат за 30 дней:</b>\n"
            "• Создадите чёткий план достижения целей\n"
            "• Разовьёте дисциплину и силу воли\n"
            "• Измените мышление на успех\n"
            "• Заложите фундамент для кардинальных изменений\n\n"
            "💰 <b>Цена: 9€</b>\n"
            "Это меньше, чем чашка кофе в день.\n"
            "Но результат может изменить вашу жизнь навсегда.\n\n"
            "Готовы начать?"
        ),
        "is_active": True,
        "sort_order": 1
    }
    
    # Данные для оффера
    offer_data = {
        "name": "Основной оффер - 30 дней по Хиллу",
        "text": (
            "🚀 <b>30 дней по книге Наполеона Хилла</b>\n\n"
            "📚 <b>Что вы получите:</b>\n"
            "• 30 практических заданий на каждый день\n"
            "• Пошаговое внедрение 13 принципов успеха\n"
            "• Систему отчётности и контроля\n"
            "• Поддержку и мотивацию\n"
            "• Доступ к закрытому чату участников\n\n"
            "🎯 <b>Результат за 30 дней:</b>\n"
            "• Создадите чёткий план достижения целей\n"
            "• Разовьёте дисциплину и силу воли\n"
            "• Измените мышление на успех\n"
            "• Заложите фундамент для кардинальных изменений\n\n"
            "💰 <b>Цена: 9€</b>\n"
            "Это меньше, чем чашка кофе в день.\n"
            "Но результат может изменить вашу жизнь навсегда.\n\n"
            "Готовы начать?"
        ),
        "price": 900,  # 9€ в центах
        "is_active": True
    }
    
    try:
        async with get_db_session() as session:
            product_service = ProductService(session)
            
            # Проверяем, существует ли уже трипвайер
            existing_tripwire = await product_service.get_active_product_by_type(ProductType.TRIPWIRE)
            
            if not existing_tripwire:
                # Создаем новый трипвайер
                tripwire = await product_service.create_product(tripwire_data)
                logger.info(f"✅ Создан трипвайер: {tripwire.name}")
                
                # Создаем оффер для трипвайера
                offer_data["product_id"] = tripwire.id.hex
                offer = await product_service.create_offer(offer_data)
                logger.info(f"✅ Создан оффер: {offer.name}")
                
            else:
                logger.info(f"⚠️ Трипвайер уже существует: {existing_tripwire.name}")
            
            logger.info("🎉 Инициализация трипвайера завершена!")
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания трипвайера: {e}")
        raise


async def main():
    """Основная функция."""
    try:
        logger.info("🚀 Начинаем инициализацию трипвайера...")
        await create_default_tripwire()
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
