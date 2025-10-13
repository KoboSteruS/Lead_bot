#!/usr/bin/env python3
"""
Скрипт для запуска бота клуба «ОСНОВА ПУТИ».
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    """Запуск бота."""
    try:
        from main import main as run_main
        await run_main()
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        print(f"Ошибка запуска бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
