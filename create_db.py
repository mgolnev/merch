import pandas as pd
import sqlite3
from datetime import datetime

def create_database(db_name='merchandise.db'):
    """Создание базы данных и таблиц"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Создаем таблицу products
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        sku TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT,
        gender TEXT,
        image_url TEXT,
        price DECIMAL(10,2),
        oldprice DECIMAL(10,2),
        discount DECIMAL(5,2)
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
        quantity INTEGER,
        orders_gross INTEGER,
        orders_net INTEGER,
        revenue_gross DECIMAL(10,2),
        revenue_net DECIMAL(10,2),
        FOREIGN KEY (sku) REFERENCES products(sku)
    )
    ''')

    conn.commit()
    return conn

def import_data(conn, excel_file='processed_data.xlsx'):
    """Импорт данных из Excel в базу данных"""
    cursor = conn.cursor()
    df = pd.read_excel(excel_file)
    
    print(f"Загружено {len(df)} строк из Excel")
    
    # Импорт данных в таблицу products
    for _, row in df.iterrows():
        try:
            cursor.execute('''
            INSERT OR REPLACE INTO products (
                sku, name, category, gender, image_url,
                price, oldprice, discount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['Артикул'],
                row['Название товара'],
                row['max_Категория'],
                row['gender'],
                row['image_url'],
                row['price'],
                row['oldprice'],
                row['discount']
            ))
            
            # Импорт метрик
            cursor.execute('''
            INSERT OR REPLACE INTO product_metrics (
                sku, sessions, product_views, cart_additions,
                checkout_starts, quantity, orders_gross, orders_net,
                revenue_gross, revenue_net
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['Артикул'],
                row['Сессии'],
                row['Карточка товара'],
                row['Добавление в корзину'],
                row['Начало чекаута'],
                row['Кол-во товаров'],
                row['Заказы (gross)'],
                row['Заказы (net)'],
                row['Выручка без НДС'],
                row['Выручка без НДС (net)']
            ))
            
        except Exception as e:
            print(f"Ошибка при импорте строки {row['Артикул']}: {e}")
            continue
    
    conn.commit()

def verify_data(conn):
    """Проверка импортированных данных"""
    cursor = conn.cursor()
    
    # Проверяем количество записей в каждой таблице
    for table in ['products', 'product_metrics']:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"\nКоличество записей в таблице {table}: {count}")
        
        # Показываем пример данных
        cursor.execute(f"SELECT * FROM {table} LIMIT 1")
        columns = [description[0] for description in cursor.description]
        row = cursor.fetchone()
        print(f"\nПример записи из {table}:")
        for col, val in zip(columns, row):
            print(f"{col}: {val}")

if __name__ == "__main__":
    # Создаем базу данных
    conn = create_database()
    
    # Импортируем данные
    import_data(conn)
    
    # Проверяем результат
    verify_data(conn)
    
    # Закрываем соединение
    conn.close()
    
    print("\nБаза данных успешно создана и заполнена данными!") 