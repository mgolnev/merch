import sqlite3

def create_tables():
    conn = sqlite3.connect('merchandise.db')
    cursor = conn.cursor()

    # Создаем таблицу products
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        sku TEXT PRIMARY KEY,
        name TEXT,
        price REAL,
        oldprice REAL,
        discount REAL,
        gender TEXT,
        max_Категория TEXT,
        image_url TEXT
    )
    ''')

    # Создаем таблицу product_metrics
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS product_metrics (
        sku TEXT PRIMARY KEY,
        sessions INTEGER,
        product_views INTEGER,
        cart_additions INTEGER,
        checkout_starts INTEGER,
        orders_gross INTEGER,
        orders_net INTEGER,
        FOREIGN KEY (sku) REFERENCES products(sku)
    )
    ''')

    # Создаем таблицу weights для хранения весов скоринга
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS weights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sessions_weight REAL DEFAULT 1.0,
        views_weight REAL DEFAULT 1.0,
        cart_weight REAL DEFAULT 1.0,
        checkout_weight REAL DEFAULT 1.0,
        orders_gross_weight REAL DEFAULT 1.0,
        orders_net_weight REAL DEFAULT 1.0,
        discount_penalty REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Создаем таблицу category_order для хранения порядка товаров в категориях
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS category_order (
        sku TEXT,
        category TEXT,
        position INTEGER,
        PRIMARY KEY (sku, category),
        FOREIGN KEY (sku) REFERENCES products(sku)
    )
    ''')

    # Вставляем начальные веса, если таблица пуста
    cursor.execute('SELECT COUNT(*) FROM weights')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
        INSERT INTO weights (
            sessions_weight,
            views_weight,
            cart_weight,
            checkout_weight,
            orders_gross_weight,
            orders_net_weight,
            discount_penalty
        ) VALUES (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0)
        ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_tables() 