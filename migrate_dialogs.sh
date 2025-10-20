#!/bin/bash

echo "🔄 Миграция системы диалогов..."

# Проверяем наличие базы данных
if [ ! -f "leadbot.db" ]; then
    echo "❌ База данных leadbot.db не найдена!"
    exit 1
fi

echo "📁 База данных найдена: leadbot.db"

# Создаем таблицы диалогов
echo "📝 Создание таблиц диалогов..."
python3 scripts/migrate_dialogs.py

if [ $? -eq 0 ]; then
    echo "✅ Таблицы диалогов созданы"
else
    echo "❌ Ошибка создания таблиц диалогов"
    exit 1
fi

# Создаем диалоги по умолчанию
echo "📝 Создание диалогов по умолчанию..."
python3 scripts/init_dialogs.py

if [ $? -eq 0 ]; then
    echo "✅ Диалоги по умолчанию созданы"
else
    echo "❌ Ошибка создания диалогов по умолчанию"
    exit 1
fi

echo "🎉 Миграция системы диалогов завершена!"
echo ""
echo "📋 Что было создано:"
echo "• Таблица dialogs"
echo "• Таблица dialog_questions" 
echo "• Таблица dialog_answers"
echo "• Диалог 'Часто задаваемые вопросы'"
echo "• Диалог 'Техническая поддержка'"
echo ""
echo "🚀 Система диалогов готова к использованию!"
