#!/bin/bash

# Скрипт миграции для добавления telegram_file_id в lead_magnets
# Использование: bash migrate.sh

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

# Проверяем, существует ли уже колонка
echo "🔍 Проверка существующих колонок..."
COLUMNS=$(sqlite3 "$DB_PATH" "PRAGMA table_info(lead_magnets);" | grep telegram_file_id)

if [ ! -z "$COLUMNS" ]; then
    echo "✅ Колонка telegram_file_id уже существует!"
    echo "   Миграция не требуется."
    exit 0
fi

echo "➕ Добавление колонки telegram_file_id..."

# Выполняем миграцию
sqlite3 "$DB_PATH" "ALTER TABLE lead_magnets ADD COLUMN telegram_file_id TEXT;" 2>&1

# Проверяем результат
if [ $? -eq 0 ]; then
    echo "✅ Колонка успешно добавлена!"
    echo ""
    echo "📊 Структура таблицы lead_magnets:"
    sqlite3 "$DB_PATH" "PRAGMA table_info(lead_magnets);"
    echo ""
    echo "🎉 Миграция успешно завершена!"
    echo ""
    echo "📋 Следующие шаги:"
    echo "   1. Перезапустите бота:"
    echo "      systemctl restart leadbot"
    echo "      # или"
    echo "      supervisorctl restart leadbot"
    echo ""
    echo "   2. Проверьте логи:"
    echo "      journalctl -u leadbot -f"
    echo "      # или"
    echo "      tail -f logs/leadbot*.log"
    exit 0
else
    echo "❌ Ошибка при выполнении миграции!"
    exit 1
fi

