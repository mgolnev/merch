-- Добавляем столбец multiplier, если его еще нет
ALTER TABLE category_scoring ADD COLUMN multiplier DECIMAL(10,2) DEFAULT 1.0;

-- Обновляем существующие записи, устанавливая multiplier равным manual_multiplier
UPDATE category_scoring SET multiplier = manual_multiplier WHERE multiplier IS NULL;

-- Добавляем новые колонки
ALTER TABLE category_scoring ADD COLUMN manual_score REAL;
ALTER TABLE category_scoring ADD COLUMN position INTEGER;
ALTER TABLE category_scoring ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Конвертируем старые данные
UPDATE category_scoring 
SET manual_score = base_score * manual_multiplier
WHERE manual_multiplier IS NOT NULL;

-- Удаляем старую колонку
ALTER TABLE category_scoring DROP COLUMN manual_multiplier; 