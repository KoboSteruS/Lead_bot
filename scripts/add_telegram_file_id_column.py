"""
Скрипт для добавления колонки telegram_file_id в таблицу lead_magnets.
Используйте этот скрипт для миграции базы данных на сервере.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.core.database import engine
from loguru import logger


async def add_telegram_file_id_column():
    """Добавляет колонку telegram_file_id в таблицу lead_magnets."""
    try:
        async with engine.begin() as conn:
            # Проверяем, существует ли уже колонка
            result = await conn.execute(text("PRAGMA table_info(lead_magnets)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'telegram_file_id' in columns:
                logger.info("✅ Колонка telegram_file_id уже существует в таблице lead_magnets")
                return
            
            # Добавляем колонку
            await conn.execute(text(
                "ALTER TABLE lead_magnets ADD COLUMN telegram_file_id TEXT"
            ))
            
            logger.success("✅ Колонка telegram_file_id успешно добавлена в таблицу lead_magnets")
            
    except Exception as e:
        logger.error(f"❌ Ошибка добавления колонки: {e}")
        raise


async def main():
    """Главная функция."""
    logger.info("🔄 Запуск миграции: добавление telegram_file_id в lead_magnets...")
    
    try:
        await add_telegram_file_id_column()
        logger.success("🎉 Миграция успешно завершена!")
        
    except Exception as e:
        logger.error(f"💥 Ошибка миграции: {e}")
        sys.exit(1)
    
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

