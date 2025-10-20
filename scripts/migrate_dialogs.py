"""
Скрипт миграции для создания таблиц диалогов.

Добавляет таблицы для системы диалогов в существующую базу данных.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from app.core.database import get_db_session
from app.models.dialog import Dialog, DialogQuestion, DialogAnswer
from app.core.database import engine


async def create_dialog_tables():
    """Создание таблиц для системы диалогов."""
    
    try:
        logger.info("🔄 Создание таблиц для системы диалогов...")
        
        # Создаем таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Dialog.metadata.create_all)
            await conn.run_sync(DialogQuestion.metadata.create_all)
            await conn.run_sync(DialogAnswer.metadata.create_all)
        
        logger.info("✅ Таблицы диалогов созданы успешно!")
        
        # Проверяем создание таблиц
        async with get_db_session() as session:
            from sqlalchemy import text
            
            # Проверяем таблицу dialogs
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='dialogs'"))
            if result.fetchone():
                logger.info("✅ Таблица 'dialogs' создана")
            else:
                logger.error("❌ Таблица 'dialogs' не создана")
            
            # Проверяем таблицу dialog_questions
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='dialog_questions'"))
            if result.fetchone():
                logger.info("✅ Таблица 'dialog_questions' создана")
            else:
                logger.error("❌ Таблица 'dialog_questions' не создана")
            
            # Проверяем таблицу dialog_answers
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='dialog_answers'"))
            if result.fetchone():
                logger.info("✅ Таблица 'dialog_answers' создана")
            else:
                logger.error("❌ Таблица 'dialog_answers' не создана")
        
        logger.info("🎉 Миграция таблиц диалогов завершена!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания таблиц диалогов: {e}")
        raise


async def main():
    """Основная функция."""
    try:
        logger.info("🚀 Начинаем миграцию таблиц диалогов...")
        await create_dialog_tables()
        logger.info("✅ Миграция завершена успешно!")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
