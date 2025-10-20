#!/usr/bin/env python3
"""
Тестовый скрипт для проверки еженедельной аналитики.

Позволяет протестировать генерацию аналитики без отправки в Telegram.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from scripts.weekly_analytics import WeeklyAnalytics
from config.settings import settings


async def test_analytics():
    """Тестируем генерацию аналитики."""
    try:
        logger.info("🧪 Тестирование еженедельной аналитики...")
        
        # Создаем экземпляр аналитики
        analytics = WeeklyAnalytics(settings.BOT_TOKEN)
        
        # Получаем период
        analytics._get_week_period()
        logger.info(f"📅 Период: {analytics.week_start.strftime('%d.%m.%Y')} - {analytics.week_end.strftime('%d.%m.%Y')}")
        
        # Собираем аналитику
        user_data = await analytics.get_user_analytics()
        lead_magnet_data = await analytics.get_lead_magnet_analytics()
        warmup_data = await analytics.get_warmup_analytics()
        mailing_data = await analytics.get_mailing_analytics()
        product_data = await analytics.get_product_analytics()
        
        # Выводим результаты
        logger.info("📊 Результаты тестирования:")
        logger.info(f"👥 Пользователи: {user_data}")
        logger.info(f"🎁 Лид-магниты: {lead_magnet_data}")
        logger.info(f"🔥 Прогрев: {warmup_data}")
        logger.info(f"📢 Рассылки: {mailing_data}")
        logger.info(f"💰 Продукты: {product_data}")
        
        # Формируем полный отчет
        full_analytics = {
            "users": user_data,
            "lead_magnets": lead_magnet_data,
            "warmup": warmup_data,
            "mailings": mailing_data,
            "products": product_data,
            "overall_conversion": 0,
            "arpu": 0,
            "ltv": 0
        }
        
        # Вычисляем общие метрики
        if user_data.get("new_users_week", 0) > 0:
            full_analytics["overall_conversion"] = round(
                (product_data.get("sales_week", 0) / user_data["new_users_week"]) * 100, 2
            )
        
        if user_data.get("total_users", 0) > 0:
            full_analytics["arpu"] = round(product_data.get("revenue_week", 0) / user_data["total_users"], 2)
        
        full_analytics["ltv"] = full_analytics["arpu"] * 3
        
        # Генерируем отчет
        report = analytics.format_analytics_report(full_analytics)
        
        print("\n" + "="*50)
        print("📊 ТЕСТОВЫЙ ОТЧЕТ АНАЛИТИКИ")
        print("="*50)
        print(report)
        print("="*50)
        
        logger.info("✅ Тестирование завершено успешно!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования: {e}")
        return False


async def main():
    """Основная функция."""
    try:
        # Настраиваем логирование
        logger.remove()
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            colorize=True
        )
        
        success = await test_analytics()
        
        if success:
            logger.info("🎉 Тест прошел успешно!")
        else:
            logger.error("❌ Тест завершился с ошибками")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
