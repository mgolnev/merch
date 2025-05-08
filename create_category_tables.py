import sqlite3

def create_category_tables():
    """Создание таблиц для работы с категориями из фида"""
    conn = sqlite3.connect('merchandise.db')
    cursor = conn.cursor()
    
    # Создаем таблицу для категорий из фида
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feed_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_number INTEGER NOT NULL,  -- Номер категории для контент-менеджеров
        name TEXT NOT NULL,
        parent_id INTEGER,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES feed_categories(id),
        UNIQUE(category_number)  -- Уникальный номер категории
    )
    ''')
    
    # Создаем таблицу для связи товаров с категориями
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS product_categories (
        sku TEXT,
        category_id INTEGER,
        is_primary BOOLEAN DEFAULT 0,  -- основная категория
        position INTEGER,              -- позиция в категории
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (sku, category_id),
        FOREIGN KEY (sku) REFERENCES products(sku),
        FOREIGN KEY (category_id) REFERENCES feed_categories(id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Таблицы для категорий успешно созданы!")

if __name__ == '__main__':
    create_category_tables() 