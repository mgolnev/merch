from app.database.connection import get_db_connection

def init_db():
    """Инициализация базы данных"""
    with get_db_connection() as conn:
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
            category TEXT,
            image_url TEXT,
            sale_start_date TEXT,
            available BOOLEAN DEFAULT 0
        )
        ''')
        
        # Создаем таблицу product_metrics
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_metrics (
            sku TEXT PRIMARY KEY,
            sessions INTEGER DEFAULT 0,
            product_views INTEGER DEFAULT 0,
            cart_additions INTEGER DEFAULT 0,
            checkout_starts INTEGER DEFAULT 0,
            orders_gross INTEGER DEFAULT 0,
            orders_net INTEGER DEFAULT 0,
            FOREIGN KEY (sku) REFERENCES products(sku)
        )
        ''')
        
        # Создаем таблицу weights
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
            dnp_weight REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Создаем таблицу category_order
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS category_order (
            sku TEXT,
            category TEXT,
            position INTEGER,
            PRIMARY KEY (sku, category),
            FOREIGN KEY (sku) REFERENCES products(sku)
        )
        ''')
        
        # Добавляем начальные веса, если таблица пуста
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
                discount_penalty,
                dnp_weight
            ) VALUES (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0)
            ''')
        
        conn.commit() 