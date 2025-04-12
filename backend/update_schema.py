import sqlite3

def update_schema():
    conn = sqlite3.connect('merchandise.db')
    cursor = conn.cursor()
    
    try:
        # Создаем временную таблицу с новой структурой
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article TEXT,
                name TEXT,
                sessions INTEGER,
                product_views INTEGER,
                add_to_cart INTEGER,
                checkout_starts INTEGER,
                orders_gross INTEGER,
                orders_net INTEGER,
                revenue_gross REAL,
                revenue_net REAL,
                category TEXT,
                view_to_cart REAL,
                cart_to_checkout REAL,
                checkout_to_order REAL,
                view_to_order REAL,
                price REAL,
                image_url TEXT,
                views INTEGER DEFAULT 0,
                conversions REAL DEFAULT 0,
                sizes_available TEXT DEFAULT '[]',
                score REAL DEFAULT 0,
                last_updated TIMESTAMP
            )
        ''')
        
        # Копируем данные из старой таблицы в новую
        cursor.execute('''
            INSERT INTO product_new (
                article, sessions, product_views, add_to_cart, 
                checkout_starts, orders_gross, orders_net, 
                revenue_gross, revenue_net, category, 
                view_to_cart, cart_to_checkout, checkout_to_order, 
                view_to_order, price, image_url, last_updated
            )
            SELECT 
                article, sessions, product_views, add_to_cart, 
                checkout_starts, orders_gross, orders_net, 
                revenue_gross, revenue_net, category, 
                view_to_cart, cart_to_checkout, checkout_to_order, 
                view_to_order, price, image_url, last_updated
            FROM product
        ''')
        
        # Обновляем name на основе article
        cursor.execute('UPDATE product_new SET name = article')
        
        # Удаляем старую таблицу
        cursor.execute('DROP TABLE IF EXISTS product')
        
        # Переименовываем новую таблицу
        cursor.execute('ALTER TABLE product_new RENAME TO product')
        
        # Создаем индексы для ускорения работы
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_score ON product(score)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_category ON product(category)')
        
        conn.commit()
        print("Схема базы данных успешно обновлена!")
        
    except Exception as e:
        print(f"Ошибка при обновлении схемы: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    update_schema() 