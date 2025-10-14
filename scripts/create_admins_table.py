"""
Скрипт для создания таблицы admins.
"""

import sqlite3
from pathlib import Path

# Путь к базе данных
DB_PATH = Path(__file__).parent.parent / "leadbot.db"


def create_admins_table():
    """Создает таблицу admins если её нет."""
    
    if not DB_PATH.exists():
        print(f"❌ Ошибка: База данных не найдена по пути: {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже таблица
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='admins'"
        )
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            print("✅ Таблица admins уже существует")
            conn.close()
            return True
        
        # Создаем таблицу
        cursor.execute("""
            CREATE TABLE admins (
                id VARCHAR(36) PRIMARY KEY,
                telegram_id BIGINT NOT NULL UNIQUE,
                username VARCHAR(255),
                full_name VARCHAR(255),
                is_active BOOLEAN NOT NULL DEFAULT 1,
                access_level BIGINT NOT NULL DEFAULT 1,
                added_by_id BIGINT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME
            )
        """)
        
        # Создаем индекс
        cursor.execute("""
            CREATE INDEX ix_admins_telegram_id ON admins(telegram_id)
        """)
        
        conn.commit()
        
        print("✅ Таблица admins успешно создана")
        print("✅ Индекс ix_admins_telegram_id создан")
        
        # Проверяем результат
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admins'")
        if cursor.fetchone():
            print("✅ Проверка: таблица успешно создана")
            conn.close()
            return True
        else:
            print("❌ Ошибка: таблица не была создана")
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
    print("🔄 Создание таблицы admins...")
    print(f"📁 Путь к БД: {DB_PATH}")
    print()
    
    success = create_admins_table()
    
    if success:
        print("\n🎉 Миграция успешно завершена!")
        print("\n📋 Следующие шаги:")
        print("   1. Перезапустите бота: systemctl restart leadbot")
        print("   2. Используйте /admin → Администраторы для управления")
        return 0
    else:
        print("\n💥 Миграция завершилась с ошибкой!")
        return 1


if __name__ == "__main__":
    exit(main())

