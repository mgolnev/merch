import pandas as pd
import xml.etree.ElementTree as ET
import sqlite3
from typing import Dict, List, Any
import logging

def import_excel_data(file_path: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(file_path)
        
        # Маппинг колонок с русского на английский
        column_mapping = {
            'Артикул': 'sku',
            'Сессии': 'sessions',
            'Карточка товара': 'product_views',
            'Добавление в корзину': 'add_to_cart',
            'Начало чекаута': 'checkout_starts',
            'Кол-во товаров': 'quantity',
            'Заказы (gross)': 'orders_gross',
            'Заказы (net)': 'orders_net',
            'Выручка без НДС': 'revenue_gross',
            'Выручка без НДС (net)': 'revenue_net',
            'Название товара': 'product_name',
            'max_Категория': 'category',
            'price': 'price',
            'oldprice': 'old_price',
            'discount': 'discount',
            'image_url': 'image_url'
        }
        
        # Переименовываем колонки
        df = df.rename(columns=column_mapping)
        
        # Заполняем пропущенные значения нулями для числовых колонок
        numeric_columns = ['sessions', 'product_views', 'add_to_cart', 'checkout_starts',
                         'quantity', 'orders_gross', 'orders_net', 'revenue_gross', 'revenue_net']
        df[numeric_columns] = df[numeric_columns].fillna(0)
        
        return df
    except Exception as e:
        logging.error(f"Error importing Excel data: {str(e)}")
        raise

def import_xml_data(file_path: str) -> Dict[str, Any]:
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        data = {}
        
        for offer in root.findall('.//offer'):
            sku = offer.get('id')
            if sku:
                data[sku] = {
                    'description': offer.findtext('description', ''),
                    'category': offer.findtext('category', '')
                }
        
        return data
    except Exception as e:
        logging.error(f"Error importing XML data: {str(e)}")
        raise

def insert_data_to_db(df: pd.DataFrame, xml_data: Dict[str, Any], db_path: str):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Создаем таблицы если они не существуют
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            sku TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            category TEXT,
            price REAL,
            old_price REAL,
            discount REAL
        )
        ''')
        
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
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_images (
            sku TEXT,
            image_url TEXT,
            FOREIGN KEY (sku) REFERENCES products(sku),
            PRIMARY KEY (sku, image_url)
        )
        ''')
        
        # Вставляем данные в таблицу products
        for _, row in df.iterrows():
            description = xml_data.get(row['sku'], {}).get('description', '')
            cursor.execute('''
            INSERT OR REPLACE INTO products (sku, name, description, category, price, old_price, discount)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['sku'],
                row['product_name'],
                description,
                row['category'],
                row['price'],
                row['old_price'],
                row['discount']
            ))
            
            # Вставляем метрики
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
            
            # Вставляем изображения
            if pd.notna(row['image_url']):
                cursor.execute('''
                INSERT OR REPLACE INTO product_images (sku, image_url)
                VALUES (?, ?)
                ''', (row['sku'], row['image_url']))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logging.error(f"Error inserting data to database: {str(e)}")
        raise

def check_data(db_path: str):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем количество записей в каждой таблице
        tables = ['products', 'product_metrics', 'product_images']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"Records in {table}: {count}")
        
        # Проверяем несколько случайных записей
        cursor.execute('''
        SELECT p.sku, p.name, p.category, m.sessions, m.revenue_net
        FROM products p
        JOIN product_metrics m ON p.sku = m.sku
        LIMIT 5
        ''')
        
        print("\nSample records:")
        for row in cursor.fetchall():
            print(row)
        
        conn.close()
        
    except Exception as e:
        logging.error(f"Error checking data: {str(e)}")
        raise 