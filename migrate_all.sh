#!/bin/bash

# Скрипт для выполнения всех необходимых миграций
# Использование: bash migrate_all.sh

echo "🔄 Миграция базы данных LeadBot..."
echo ""

# Путь к базе данных
DB_PATH="leadbot.db"

# Проверяем наличие БД
if [ ! -f "$DB_PATH" ]; then
    echo "❌ Ошибка: файл $DB_PATH не найден"
    exit 1
fi

echo "📁 База данных найдена: $DB_PATH"
echo ""

# Миграция 1: Добавление telegram_file_id
echo "📝 Миграция 1: Добавление telegram_file_id в lead_magnets..."
COLUMNS=$(sqlite3 "$DB_PATH" "PRAGMA table_info(lead_magnets);" | grep telegram_file_id)

if [ ! -z "$COLUMNS" ]; then
    echo "   ✅ Колонка telegram_file_id уже существует"
else
    sqlite3 "$DB_PATH" "ALTER TABLE lead_magnets ADD COLUMN telegram_file_id TEXT;" 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✅ Колонка telegram_file_id добавлена"
    else
        echo "   ❌ Ошибка добавления telegram_file_id"
        exit 1
    fi
fi

echo ""

# Миграция 2: Создание таблицы admins
echo "📝 Миграция 2: Создание таблицы admins..."
TABLE_EXISTS=$(sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='admins';" 2>&1)

if [ ! -z "$TABLE_EXISTS" ]; then
    echo "   ✅ Таблица admins уже существует"
else
    sqlite3 "$DB_PATH" <<EOF
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
);

CREATE INDEX ix_admins_telegram_id ON admins(telegram_id);
EOF
    
    if [ $? -eq 0 ]; then
        echo "   ✅ Таблица admins создана"
        echo "   ✅ Индекс ix_admins_telegram_id создан"
    else
        echo "   ❌ Ошибка создания таблицы admins"
        exit 1
    fi
fi

echo ""
echo "🎉 Все миграции успешно выполнены!"
echo ""
echo "📊 Текущая структура БД:"
echo ""
echo "📋 Таблицы:"
sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
echo ""
echo "📋 Следующие шаги:"
echo "   1. Перезапустите бота:"
echo "      systemctl restart leadbot"
echo "      # или"
echo "      supervisorctl restart leadbot"
echo ""
echo "   2. Проверьте логи:"
echo "      journalctl -u leadbot -f"
echo ""
echo "   3. Используйте /admin → Администраторы для управления админами"
echo ""

exit 0

