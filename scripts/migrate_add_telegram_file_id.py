"""
Простой скрипт миграции для добавления колонки telegram_file_id.
Работает напрямую с SQLite без зависимостей от app.
"""

import sqlite3
import os
from pathlib import Path

# Путь к базе данных
DB_PATH = Path(__file__).parent.parent / "leadbot.db"


def add_telegram_file_id_column():
    """Добавляет колонку telegram_file_id в таблицу lead_magnets."""
    
    if not DB_PATH.exists():
        print(f"❌ Ошибка: База данных не найдена по пути: {DB_PATH}")
        return False
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже колонка
        cursor.execute("PRAGMA table_info(lead_magnets)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'telegram_file_id' in columns:
            print("✅ Колонка telegram_file_id уже существует в таблице lead_magnets")
            conn.close()
            return True
        
        # Добавляем колонку
        cursor.execute("ALTER TABLE lead_magnets ADD COLUMN telegram_file_id TEXT")
        conn.commit()
        
        print("✅ Колонка telegram_file_id успешно добавлена в таблицу lead_magnets")
        
        # Проверяем результат
        cursor.execute("PRAGMA table_info(lead_magnets)")
        columns_after = [row[1] for row in cursor.fetchall()]
        
        if 'telegram_file_id' in columns_after:
            print("✅ Проверка: колонка успешно создана")
            conn.close()
            return True
        else:
            print("❌ Ошибка: колонка не была создана")
            conn.close()
            return False
            
    except sqlite3.Error as e:
        print(f"❌ Ошибка SQLite: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


def main():
    """Главная функция."""
    print("🔄 Запуск миграции: добавление telegram_file_id в lead_magnets...")
    print(f"📁 Путь к БД: {DB_PATH}")
    
    success = add_telegram_file_id_column()
    
    if success:
        print("\n🎉 Миграция успешно завершена!")
        print("\n📋 Следующие шаги:")
        print("   1. Перезапустите бота: systemctl restart leadbot")
        print("   2. Проверьте логи: journalctl -u leadbot -f")
        return 0
    else:
        print("\n💥 Миграция завершилась с ошибкой!")
        return 1


if __name__ == "__main__":
    exit(main())

