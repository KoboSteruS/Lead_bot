-- Миграция: добавление поддержки файлов для лид-магнитов
-- Дата: 2025-10-14

-- Добавляем колонку telegram_file_id в таблицу lead_magnets
ALTER TABLE lead_magnets ADD COLUMN telegram_file_id TEXT;

-- Проверяем результат
SELECT 'Migration completed successfully!' as status;
PRAGMA table_info(lead_magnets);

