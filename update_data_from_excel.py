import pandas as pd
import sqlite3
import logging
from datetime import datetime
import os

def setup_logging():
    """Настройка логирования"""
    log_filename = f'update_excel_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )

def create_tables(conn):
    """Создание необходимых таблиц в базе данных"""
    cursor = conn.cursor()
    
    # Таблица продуктов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        sku TEXT PRIMARY KEY,
        name TEXT,
        category TEXT,
        price REAL,
        old_price REAL,
        discount REAL,
        gender TEXT,
        image_url TEXT
    )
    ''')
    
    # Таблица метрик
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS product_metrics (
        sku TEXT PRIMARY KEY,
        sessions INTEGER,
        product_views INTEGER,
        add_to_cart INTEGER,
        checkout_starts INTEGER,
        quantity INTEGER,
        orders_gross INTEGER,
        orders_net INTEGER,
        revenue_gross REAL,
        revenue_net REAL,
        FOREIGN KEY (sku) REFERENCES products(sku)
    )
    ''')
    
    # Таблица весов категорий
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS category_weights (
        category TEXT PRIMARY KEY,
        views_weight REAL DEFAULT 0.3,
        cart_weight REAL DEFAULT 0.3,
        orders_weight REAL DEFAULT 0.4
    )
    ''')
    
    # Таблица сезонных множителей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS seasonal_multipliers (
        season TEXT,
        category TEXT,
        multiplier REAL DEFAULT 1.0,
        PRIMARY KEY (season, category)
    )
    ''')
    
    conn.commit()

def clean_database(conn):
    """Очистка базы данных"""
    cursor = conn.cursor()
    tables = ['products', 'product_metrics', 'category_weights', 'seasonal_multipliers']
    
    for table in tables:
        cursor.execute(f'DELETE FROM {table}')
    
    conn.commit()
    logging.info("База данных очищена")

def import_excel_data(conn, excel_file='data.xlsx'):
    """Импорт данных из Excel"""
    try:
        # Проверяем существование файла
        if not os.path.exists(excel_file):
            raise FileNotFoundError(f"Файл {excel_file} не найден")
        
        # Загружаем данные из Excel
        df = pd.read_excel(excel_file)
        logging.info(f"Загружено {len(df)} записей из Excel")
        
        # Маппинг колонок
        column_mapping = {
            'Артикул': 'sku',
            'Название товара': 'name',
            'max_Категория': 'category',
            'price': 'price',
            'oldprice': 'old_price',
            'discount': 'discount',
            'Сессии': 'sessions',
            'Карточка товара': 'product_views',
            'Добавление в корзину': 'add_to_cart',
            'Начало чекаута': 'checkout_starts',
            'Кол-во товаров': 'quantity',
            'Заказы (gross)': 'orders_gross',
            'Заказы (net)': 'orders_net',
            'Выручка без НДС': 'revenue_gross',
            'Выручка без НДС (net)': 'revenue_net'
        }
        
        # Переименовываем колонки
        df = df.rename(columns=column_mapping)
        
        # Заполняем пропущенные значения
        numeric_columns = ['sessions', 'product_views', 'add_to_cart', 'checkout_starts',
                         'quantity', 'orders_gross', 'orders_net', 'revenue_gross', 'revenue_net']
        df[numeric_columns] = df[numeric_columns].fillna(0)
        
        # Вставляем данные в базу
        cursor = conn.cursor()
        for _, row in df.iterrows():
            # Вставляем в таблицу products
            cursor.execute('''
            INSERT OR REPLACE INTO products (sku, name, category, price, old_price, discount)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                row['sku'],
                row['name'],
                row['category'],
                row.get('price', 0),
                row.get('old_price', 0),
                row.get('discount', 0)
            ))
            
            # Вставляем в таблицу product_metrics
            cursor.execute('''
            INSERT OR REPLACE INTO product_metrics 
            (sku, sessions, product_views, add_to_cart, checkout_starts, 
             quantity, orders_gross, orders_net, revenue_gross, revenue_net)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['sku'],
                row['sessions'],
                row['product_views'],
                row['add_to_cart'],
                row['checkout_starts'],
                row['quantity'],
                row['orders_gross'],
                row['orders_net'],
                row['revenue_gross'],
                row['revenue_net']
            ))
        
        conn.commit()
        logging.info("Данные успешно импортированы в базу данных")
        
    except Exception as e:
        logging.error(f"Ошибка при импорте данных: {str(e)}")
        raise

def update_category_weights(conn):
    """Обновление весов категорий"""
    cursor = conn.cursor()
    
    # Получаем все уникальные категории
    cursor.execute('SELECT DISTINCT category FROM products')
    categories = cursor.fetchall()
    
    # Добавляем веса для каждой категории
    for category in categories:
        cursor.execute('''
        INSERT OR IGNORE INTO category_weights (category, views_weight, cart_weight, orders_weight)
        VALUES (?, 0.3, 0.3, 0.4)
        ''', (category[0],))
    
    conn.commit()
    logging.info("Веса категорий обновлены")

def update_seasonal_multipliers(conn):
    """Обновление сезонных множителей"""
    cursor = conn.cursor()
    
    # Получаем все уникальные категории
    cursor.execute('SELECT DISTINCT category FROM products')
    categories = cursor.fetchall()
    
    # Добавляем множители для каждого сезона и категории
    seasons = ['spring', 'summer', 'autumn', 'winter']
    for season in seasons:
        for category in categories:
            cursor.execute('''
            INSERT OR IGNORE INTO seasonal_multipliers (season, category, multiplier)
            VALUES (?, ?, 1.0)
            ''', (season, category[0]))
    
    conn.commit()
    logging.info("Сезонные множители обновлены")

def save_processed_data(conn, output_file='processed_data.xlsx'):
    """Сохранение обработанных данных в Excel файл"""
    try:
        # Получаем данные из базы
        cursor = conn.cursor()
        
        # Получаем данные о продуктах и метриках
        cursor.execute('''
        SELECT p.*, pm.* 
        FROM products p 
        LEFT JOIN product_metrics pm ON p.sku = pm.sku
        ''')
        
        # Создаем DataFrame
        columns = [
            'sku', 'name', 'category', 'price', 'old_price', 'discount', 'gender', 'image_url',
            'sessions', 'product_views', 'add_to_cart', 'checkout_starts', 'quantity',
            'orders_gross', 'orders_net', 'revenue_gross', 'revenue_net'
        ]
        df = pd.DataFrame(cursor.fetchall(), columns=columns)
        
        # Сохраняем в Excel
        df.to_excel(output_file, index=False)
        logging.info(f"Обработанные данные сохранены в {output_file}")
        
        # Выводим пример данных
        print("\nПример обработанных данных:")
        print(df.head())
        
    except Exception as e:
        logging.error(f"Ошибка при сохранении обработанных данных: {str(e)}")
        raise

def main():
    """Основная функция обновления данных"""
    setup_logging()
    
    try:
        logging.info("=== Начало процесса обновления данных ===")
        
        # Подключаемся к базе данных
        conn = sqlite3.connect('products.db')
        
        # Создаем таблицы
        create_tables(conn)
        
        # Очищаем базу данных
        clean_database(conn)
        
        # Импортируем данные из Excel
        import_excel_data(conn)
        
        # Обновляем веса категорий
        update_category_weights(conn)
        
        # Обновляем сезонные множители
        update_seasonal_multipliers(conn)
        
        # Сохраняем обработанные данные
        save_processed_data(conn)
        
        # Закрываем соединение
        conn.close()
        
        logging.info("=== Процесс обновления данных успешно завершен! ===")
        
    except Exception as e:
        logging.error(f"Критическая ошибка в процессе обновления данных: {str(e)}")
        raise

if __name__ == "__main__":
    main() 