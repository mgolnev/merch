import pandas as pd
import xml.etree.ElementTree as ET
import sqlite3
from typing import Dict, List, Any
import logging

def import_excel_data(file_path: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(file_path)
        # Удаляем дублирующиеся столбцы
        df = df.loc[:, ~df.columns.duplicated()]
        print('DEBUG: столбцы после удаления дубликатов:', list(df.columns))
        
        # Маппинг колонок с русского на английский
        column_mapping = {
            'Артикул': 'sku',
            'Название товара': 'name',
            'price': 'price',
            'oldprice': 'oldprice',
            'discount': 'discount',
            'gender': 'gender',
            'max_Категория': 'max_Категория',
            'image_url': 'image_url',
            # Метрики
            'Сессии': 'sessions',
            'Карточка товара': 'product_views',
            'Добавление в корзину': 'cart_additions',
            'Начало чекаута': 'checkout_starts',
            'Заказы (gross)': 'orders_gross',
            'Заказы (net)': 'orders_net',
        }
        
        # Переименовываем колонки
        df = df.rename(columns=column_mapping)
        
        # Заполняем пропущенные значения нулями для числовых колонок
        numeric_columns = ['sessions', 'product_views', 'cart_additions', 'checkout_starts', 'orders_gross', 'orders_net', 'price', 'oldprice', 'discount']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        
        return df
    except Exception as e:
        print(f'Ошибка при импорте Excel: {e}')
        return pd.DataFrame()

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
        
        # Создаем таблицу products с нужной структурой
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
        
        # === ОТЛАДКА: выводим строку по артикулу GDR030090-2 ===
        print('DEBUG: строка из DataFrame по GDR030090-2:')
        print(df[df['sku'] == 'GDR030090-2'])
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_metrics (
            sku TEXT PRIMARY KEY,
            sessions INTEGER,
            product_views INTEGER,
            add_to_cart INTEGER,
            checkout_starts INTEGER,
            orders_gross INTEGER,
            orders_net INTEGER,
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
            try:
                def get_scalar(val):
                    if isinstance(val, pd.Series):
                        return val.iloc[0]
                    return val
                # Для поля name: если 'name' пустой, использовать 'Название товара'
                name_val = get_scalar(row['name']) if 'name' in row and pd.notna(get_scalar(row['name'])) else None
                if not name_val and 'Название товара' in row and pd.notna(get_scalar(row['Название товара'])):
                    name_val = str(get_scalar(row['Название товара']))
                values = [
                    str(get_scalar(row['sku'])) if pd.notna(get_scalar(row['sku'])) else None,
                    name_val if name_val else None,
                    float(get_scalar(row['price'])) if pd.notna(get_scalar(row['price'])) else None,
                    float(get_scalar(row['oldprice'])) if pd.notna(get_scalar(row['oldprice'])) else None,
                    float(get_scalar(row['discount'])) if pd.notna(get_scalar(row['discount'])) else None,
                    str(get_scalar(row['gender'])) if pd.notna(get_scalar(row['gender'])) else None,
                    str(get_scalar(row['max_Категория'])) if pd.notna(get_scalar(row['max_Категория'])) else None,
                    str(get_scalar(row['image_url'])) if pd.notna(get_scalar(row['image_url'])) else None
                ]
                if str(get_scalar(row['sku'])) == 'GDR030090-2':
                    print('DEBUG: значения всех полей для GDR030090-2:')
                    for col in row.index:
                        print(f"{col}: {get_scalar(row[col])}")
                    print(f"name_val: {name_val}")
            except KeyError as e:
                print(f'ОШИБКА: отсутствует столбец {e}')
                continue
            cursor.execute('''
            INSERT OR REPLACE INTO products (sku, name, price, oldprice, discount, gender, max_Категория, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', values)
            
            # Вставляем метрики
            cursor.execute('''
            INSERT OR REPLACE INTO product_metrics 
            (sku, sessions, product_views, add_to_cart, checkout_starts, 
             orders_gross, orders_net)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['sku'],
                row['sessions'],
                row['product_views'],
                row['cart_additions'],
                row['checkout_starts'],
                row['orders_gross'],
                row['orders_net']
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
        SELECT p.sku, p.name, p.category, m.sessions
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