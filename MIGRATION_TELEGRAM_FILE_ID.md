# Миграция: Добавление поддержки файлов для лид-магнитов

## 📋 Что изменилось

Добавлена возможность загружать файлы для лид-магнитов через Telegram вместо URL-ссылок.

### Новое поле в базе данных:
- `lead_magnets.telegram_file_id` (TEXT, nullable) - ID файла в Telegram для прямой отправки

## 🚀 Инструкция для миграции на сервере

### Вариант 1: Bash скрипт (САМЫЙ ПРОСТОЙ) ⭐

```bash
cd ~/Lead_bot
bash migrate.sh
```

### Вариант 2: Python скрипт (без зависимостей)

```bash
cd ~/Lead_bot
python3 scripts/migrate_add_telegram_file_id.py
```

### Вариант 3: Через SQL файл

```bash
cd ~/Lead_bot
sqlite3 leadbot.db < migration.sql
```

### Вариант 4: Ручная миграция через SQLite

```bash
cd ~/Lead_bot
sqlite3 leadbot.db

# В консоли SQLite:
ALTER TABLE lead_magnets ADD COLUMN telegram_file_id TEXT;
.quit
```

### Вариант 5: Одной командой

```bash
cd ~/Lead_bot && sqlite3 leadbot.db "ALTER TABLE lead_magnets ADD COLUMN telegram_file_id TEXT;"
```

## ✅ Проверка миграции

После выполнения миграции проверьте структуру таблицы:

```bash
sqlite3 leadbot.db "PRAGMA table_info(lead_magnets);"
```

Вы должны увидеть колонку `telegram_file_id` в списке.

## 🔄 Перезапуск бота

После миграции перезапустите бота:

```bash
systemctl restart leadbot
# или
supervisorctl restart leadbot
# или просто
pkill -f "python.*main.py"
python main.py
```

## 📊 Проверка логов

```bash
journalctl -u leadbot -f
# или
tail -f logs/leadbot*.log
```

Должно исчезнуть сообщение об ошибке:
```
no such column: lead_magnets.telegram_file_id
```

## 🎯 Использование новой функции

После миграции вы сможете:

1. `/admin` → "🎁 Лид-магниты" → "➕ Добавить"
2. Ввести название
3. **Прикрепить файл** (PDF, документ, фото, видео)
4. Файл будет сохранен с telegram_file_id и отправляться пользователям напрямую

## ⚠️ Важно

- Старые лид-магниты с URL продолжат работать как раньше
- Новые можно создавать как с файлом, так и с URL
- Миграция безопасна и не затрагивает существующие данные

## 🐛 Troubleshooting

### Ошибка: "table lead_magnets has no column named telegram_file_id"

**Решение:** Выполните миграцию заново:
```bash
python scripts/add_telegram_file_id_column.py
```

### Ошибка: "cannot access local variable 'LeadMagnetType'"

**Решение:** Убедитесь, что код обновлен до последней версии:
```bash
git pull origin main
systemctl restart leadbot
```

### Колонка уже существует

Если скрипт сообщает, что колонка уже существует - всё в порядке, миграция уже выполнена.

## 📝 Коммиты

- `feat: Add file upload support for lead magnets with Telegram file_id storage`
- `fix: Fix LeadMagnetType import and add migration script for telegram_file_id`

