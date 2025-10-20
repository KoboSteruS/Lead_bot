"""
Основной файл для запуска LeadBot.
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from loguru import logger
from app.core.database import init_database
from app.bot.bot import TelegramBot
from config.settings import settings


async def main():
    """Основная функция запуска LeadBot."""
    try:
        logger.info("Запуск LeadBot...")
        logger.info(f"Название: {settings.BOT_NAME}")
        logger.info(f"Режим отладки: {settings.DEBUG}")
        
        # Инициализируем базу данных
        await init_database()
        logger.info("База данных инициализирована")
        
        # Создаем и запускаем бота
        bot = TelegramBot()
        
        # Получаем информацию о боте
        try:
            bot_info = await bot.get_me()
            username = bot_info.get('username', 'unknown') if isinstance(bot_info, dict) else getattr(bot_info, 'username', 'unknown')
            logger.info(f"Бот запущен: @{username}")
        except Exception as e:
            logger.warning(f"Не удалось получить информацию о боте: {e}")
        
        # Запускаем бота
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Остановка бота по запросу пользователя")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise
    finally:
        logger.info("LeadBot остановлен")


if __name__ == "__main__":
    # Настраиваем логирование
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    if settings.LOG_FILE:
        os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)
        logger.add(
            settings.LOG_FILE,
            level=settings.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="1 day",
            retention="30 days"
        )
    
    # Запускаем бота
    asyncio.run(main())