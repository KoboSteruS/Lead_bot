# Миграция: Управление администраторами через админ-панель

## 📋 Что изменилось

Добавлена система управления администраторами через админ-панель бота.

### Новые возможности:
- ➕ Добавление админов по Telegram ID прямо из бота
- 🗑 Удаление админов из БД
- 📊 Просмотр всех админов (.env + БД)
- 👨‍💼 Раздел "Администраторы" в админ-панели

### Новая таблица в базе данных:
```sql
CREATE TABLE admins (
    id VARCHAR(36) PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    full_name VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    access_level BIGINT NOT NULL DEFAULT 1,
    added_by_id BIGINT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME
);
```

## 🚀 Инструкция для миграции на сервере

### ⭐ Вариант 1: Автоматическая миграция (РЕКОМЕНДУЕТСЯ)

Этот скрипт выполнит ВСЕ необходимые миграции автоматически:

```bash
cd ~/Lead_bot
git pull origin main
bash migrate_all.sh
```

**Что делает скрипт:**
1. ✅ Добавляет `telegram_file_id` в `lead_magnets`
2. ✅ Создает таблицу `admins`
3. ✅ Проверяет все изменения
4. ✅ Показывает статус

### Вариант 2: Python скрипт

```bash
cd ~/Lead_bot
python3 scripts/create_admins_table.py
```

### Вариант 3: Ручное создание через SQLite

```bash
cd ~/Lead_bot
sqlite3 leadbot.db <<EOF
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

## ✅ Проверка миграции

После выполнения миграции проверьте структуру:

```bash
sqlite3 leadbot.db "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
```

Вы должны увидеть таблицу `admins` в списке.

## 🔄 Перезапуск бота

```bash
systemctl restart leadbot
# или
supervisorctl restart leadbot
# или
pkill -f "python.*main.py" && nohup python3 main.py &
```

## 📊 Проверка логов

```bash
journalctl -u leadbot -f
# или
tail -f logs/leadbot*.log
```

Ошибки должны исчезнуть:
- ✅ `no such table: admins`
- ✅ `no such column: lead_magnets.telegram_file_id`

## 🎯 Использование новой функции

После миграции и перезапуска бота:

### Добавление администратора:

1. Откройте бота
2. `/admin` → "👨‍💼 Администраторы"
3. Нажмите "➕ Добавить администратора"
4. Введите Telegram ID нового админа
5. Готово! Пользователь теперь может использовать `/admin`

### Удаление администратора:

1. `/admin` → "👨‍💼 Администраторы"
2. Нажмите "🗑 Удалить администратора"
3. Введите Telegram ID админа
4. Админ удален (только из БД, не из .env)

### Как узнать Telegram ID:

1. Напишите боту @userinfobot
2. Он пришлет ваш ID
3. Или попросите пользователя написать вашему боту /start
4. ID появится в логах

## 💡 Как это работает

### Система двух уровней:

1. **Админы из .env** (приоритет):
   - Хранятся в файле `.env`
   - Нельзя удалить через админ-панель
   - Всегда имеют доступ
   - Переменная: `ADMIN_IDS=1670311707,987654321`

2. **Админы из БД**:
   - Добавляются через админ-панель
   - Можно удалить через админ-панель
   - Хранятся в таблице `admins`

### Проверка прав:

При входе в админ-панель проверяются ОБА источника:
```python
# Сначала .env
if user_id in settings.admin_ids_list:
    return True

# Потом БД
admin = await admin_service.get_admin_by_telegram_id(user_id)
if admin and admin.is_active:
    return True
```

## ⚠️ Важно

- Админы из .env **нельзя** удалить через админ-панель
- Админ не может удалить сам себя
- Удаление админа из БД = деактивация (не полное удаление)
- Для полного удаления используйте SQL напрямую

## 🐛 Troubleshooting

### Ошибка: "no such table: admins"

**Решение:** Выполните миграцию:
```bash
bash migrate_all.sh
```

### Ошибка: "cannot import name 'async_sessionmaker'"

**Решение:** Используйте простой скрипт без Python:
```bash
bash migrate_all.sh
```

### Таблица уже существует

Если скрипт сообщает, что таблица уже существует - всё в порядке, миграция уже выполнена.

## 📝 Структура таблицы admins

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | VARCHAR(36) | UUID администратора |
| telegram_id | BIGINT | Telegram ID (уникальный) |
| username | VARCHAR(255) | Username в Telegram |
| full_name | VARCHAR(255) | Полное имя |
| is_active | BOOLEAN | Активен ли админ |
| access_level | BIGINT | Уровень доступа (1-100) |
| added_by_id | BIGINT | Кто добавил админа |
| created_at | DATETIME | Дата создания |
| updated_at | DATETIME | Дата обновления |

## 🎯 Примеры использования

### Добавить админа через Python:

```python
from app.core.database import get_db_session
from app.services.admin_service import AdminService

async with get_db_session() as session:
    admin_service = AdminService(session)
    await admin_service.add_admin(
        telegram_id=123456789,
        username="new_admin",
        full_name="Новый Админ",
        added_by_id=1670311707
    )
```

### Проверить права админа:

```python
from app.bot.utils import is_admin

if await is_admin(user_id):
    # Пользователь - админ
    pass
```

### Получить всех админов:

```python
from app.bot.utils import get_all_admin_ids

admin_ids = await get_all_admin_ids()
# Вернет список из .env + БД
```

## 📦 Файлы миграции

- `migrate_all.sh` - автоматическая миграция (bash)
- `scripts/create_admins_table.py` - Python скрипт
- `migration.sql` - SQL скрипт
- `MIGRATION_ADMINS.md` - эта инструкция

