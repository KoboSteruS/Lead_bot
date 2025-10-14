# 🚀 Инструкция по развертыванию обновлений на сервере

## 📦 Что нового в этом обновлении

1. ✅ **Загрузка файлов для лид-магнитов** - можно прикреплять PDF, документы, фото
2. ✅ **Управление админами** - добавление/удаление админов по Telegram ID прямо из бота
3. ✅ **Полное редактирование сценариев прогрева** - название, описание, сообщения
4. ✅ **Полное редактирование продуктов** - название, описание, цена, ссылка, оффер
5. ✅ **Исправлены ошибки** с callback handlers и UUID

## 🔧 Быстрое развертывание (3 команды)

```bash
# 1. Обновите код
cd ~/Lead_bot
git pull origin main

# 2. Выполните миграции (ВСЕ В ОДНОМ СКРИПТЕ!)
bash migrate_all.sh

# 3. Перезапустите бота
systemctl restart leadbot
```

**Готово!** ✅

---

## 📝 Подробная инструкция

### Шаг 1: Подготовка

```bash
# Подключитесь к серверу
ssh root@vjaceslavs.scukins.fvds.ru

# Перейдите в директорию проекта
cd ~/Lead_bot

# Остановите бота (опционально, для чистоты)
systemctl stop leadbot
```

### Шаг 2: Обновление кода

```bash
# Получите последние изменения
git pull origin main

# Проверьте статус
git status
git log --oneline -5
```

### Шаг 3: Миграция базы данных

**Способ 1: Автоматический (рекомендуется)** ⭐

```bash
bash migrate_all.sh
```

Этот скрипт:
- ✅ Добавит `telegram_file_id` в `lead_magnets`
- ✅ Создаст таблицу `admins`
- ✅ Проверит все изменения
- ✅ Покажет результат

**Способ 2: По отдельности**

```bash
# Миграция 1: telegram_file_id
bash migrate.sh

# Миграция 2: таблица admins
python3 scripts/create_admins_table.py
```

**Способ 3: Вручную через SQL**

```bash
sqlite3 leadbot.db <<EOF
-- Добавляем telegram_file_id
ALTER TABLE lead_magnets ADD COLUMN telegram_file_id TEXT;

-- Создаем таблицу admins
CREATE TABLE IF NOT EXISTS admins (
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

CREATE INDEX IF NOT EXISTS ix_admins_telegram_id ON admins(telegram_id);
EOF
```

### Шаг 4: Проверка миграции

```bash
# Проверьте структуру БД
sqlite3 leadbot.db "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"

# Должны увидеть таблицу admins
```

### Шаг 5: Перезапуск бота

```bash
# Вариант 1: через systemctl
systemctl start leadbot
systemctl status leadbot

# Вариант 2: через supervisorctl
supervisorctl restart leadbot
supervisorctl status leadbot

# Вариант 3: вручную
pkill -f "python.*main.py"
nohup python3 main.py > /dev/null 2>&1 &
```

### Шаг 6: Проверка логов

```bash
# Вариант 1: через journalctl
journalctl -u leadbot -f

# Вариант 2: через файлы логов
tail -f logs/leadbot*.log

# Вариант 3: последние 50 строк
tail -50 logs/leadbot*.log
```

**Что должно появиться:**
```
INFO | Telegram бот успешно запущен
INFO | Регистрация всех обработчиков
INFO | Планировщик задач запущен
```

**Чего НЕ должно быть:**
```
❌ no such column: lead_magnets.telegram_file_id
❌ no such table: admins
❌ cannot access local variable 'LeadMagnetType'
```

---

## 🎯 Использование новых функций

### 1. Загрузка файлов для лид-магнитов

**В боте:**
```
/admin → 🎁 Лид-магниты → ➕ Добавить
Введите название: "Мой PDF гайд"
[Прикрепите файл PDF]
✅ Лид-магнит создан!
```

**Что происходит:**
- Файл сохраняется в Telegram (file_id)
- Пользователям отправляется напрямую
- Не нужен внешний хостинг

### 2. Управление администраторами

**Добавление:**
```
/admin → 👨‍💼 Администраторы → ➕ Добавить
Введите Telegram ID: 987654321
✅ Администратор добавлен!
```

**Удаление:**
```
/admin → 👨‍💼 Администраторы → 🗑 Удалить
Введите Telegram ID: 987654321
✅ Администратор удален!
```

**Просмотр:**
```
/admin → 👨‍💼 Администраторы

Вы увидите:
📌 Из .env файла (нельзя удалить):
   • 1670311707

💾 Из базы данных:
   ✅ Имя Админа
      ID: 987654321
      Username: @admin_username
```

### 3. Редактирование сценариев

```
/admin → 🔥 Прогрев → [Выбрать сценарий] → ✏️ Редактировать

Доступно:
• 📝 Изменить название
• 📄 Изменить описание
• ➕ Добавить сообщение
• 📋 Список сообщений
```

### 4. Редактирование продуктов

```
/admin → 💰 Трипвайеры → ✏️ [Продукт]

Доступно:
• 📝 Изменить название
• 📄 Изменить описание
• 💰 Изменить цену
• 🔗 Изменить ссылку
• 📋 Изменить текст оффера
```

---

## 🔍 Диагностика проблем

### Проблема 1: Бот не запускается

```bash
# Проверьте логи
journalctl -u leadbot -n 50

# Проверьте процессы
ps aux | grep python

# Проверьте порты
netstat -tulpn | grep python
```

### Проблема 2: Ошибки в логах

```bash
# Смотрите последние ошибки
journalctl -u leadbot | grep ERROR | tail -20

# Проверьте структуру БД
sqlite3 leadbot.db ".tables"
sqlite3 leadbot.db "PRAGMA table_info(admins);"
sqlite3 leadbot.db "PRAGMA table_info(lead_magnets);"
```

### Проблема 3: Админ-панель не работает

```bash
# Проверьте, есть ли админы
sqlite3 leadbot.db "SELECT * FROM admins;"

# Проверьте .env
cat .env | grep ADMIN_IDS
```

### Проблема 4: Файлы не отправляются

```bash
# Проверьте наличие telegram_file_id
sqlite3 leadbot.db "SELECT name, telegram_file_id FROM lead_magnets;"

# Проверьте логи при выдаче лид-магнита
journalctl -u leadbot -f
# Затем запросите лид-магнит в боте
```

---

## 📊 Статус после миграции

### Таблицы в БД:

```
admins                  ← НОВАЯ
lead_magnets           ← ОБНОВЛЕНА
mailings
mailing_recipients
product_offers
products
user_followups
user_lead_magnets
user_product_offers
user_warmup_messages
user_warmups
users
warmup_messages
warmup_scenarios
```

### Новые колонки:

- `lead_magnets.telegram_file_id` ← НОВАЯ

### Новые функции в админ-панели:

- 👨‍💼 Администраторы ← НОВЫЙ РАЗДЕЛ
- ✏️ Редактирование сценариев (полное)
- ✏️ Редактирование продуктов (полное)
- 📤 Загрузка файлов для лид-магнитов

---

## 📝 Коммиты этого обновления

```
✅ fix: Fix callback handler order and Message is not modified errors
✅ feat: Add file upload support for lead magnets with Telegram file_id storage
✅ fix: Fix LeadMagnetType import and add migration script for telegram_file_id
✅ docs: Add migration guide for telegram_file_id feature
✅ feat: Add multiple migration methods for telegram_file_id (bash, python, sql)
✅ feat: Add admin management system with DB storage and TG ID control
✅ docs: Add comprehensive admin management migration guide
```

---

## ✨ Итоговая команда для полного развертывания

```bash
cd ~/Lead_bot && \
git pull origin main && \
bash migrate_all.sh && \
systemctl restart leadbot && \
echo "✅ Развертывание завершено!" && \
journalctl -u leadbot -f
```

**Скопируйте и выполните - всё сделается автоматически!** 🚀

