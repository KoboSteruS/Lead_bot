#!/bin/bash

# Скрипт для настройки еженедельной отправки аналитики через cron

echo "🔧 Настройка еженедельной аналитики..."

# Получаем текущую директорию проекта
PROJECT_DIR=$(pwd)
SCRIPT_PATH="$PROJECT_DIR/scripts/weekly_analytics.py"
PYTHON_PATH=$(which python3)

# Проверяем существование скрипта
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Скрипт weekly_analytics.py не найден в $SCRIPT_PATH"
    exit 1
fi

# Проверяем Python
if [ -z "$PYTHON_PATH" ]; then
    echo "❌ Python3 не найден"
    exit 1
fi

echo "✅ Найден Python: $PYTHON_PATH"
echo "✅ Найден скрипт: $SCRIPT_PATH"

# Создаем cron задачу (каждый понедельник в 9:00)
CRON_JOB="0 9 * * 1 cd $PROJECT_DIR && $PYTHON_PATH $SCRIPT_PATH >> logs/weekly_analytics.log 2>&1"

echo "📅 Создаем cron задачу:"
echo "   $CRON_JOB"

# Добавляем задачу в crontab
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

if [ $? -eq 0 ]; then
    echo "✅ Cron задача успешно добавлена!"
    echo ""
    echo "📋 Текущие cron задачи:"
    crontab -l
    echo ""
    echo "📝 Аналитика будет отправляться каждый понедельник в 9:00"
    echo "📁 Логи будут сохраняться в logs/weekly_analytics.log"
    echo ""
    echo "🔧 Для удаления задачи выполните:"
    echo "   crontab -e"
    echo "   (удалите строку с weekly_analytics.py)"
else
    echo "❌ Ошибка добавления cron задачи"
    exit 1
fi
