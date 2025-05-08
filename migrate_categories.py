import sqlite3
import pandas as pd
from typing import Dict, List, Tuple

def get_unique_categories(conn: sqlite3.Connection) -> List[Tuple[str, int]]:
    """Получение уникальных категорий из таблицы products"""
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category FROM products WHERE category IS NOT NULL')
    categories = cursor.fetchall()
    return [(cat[0], i+1) for i, cat in enumerate(categories)]  # (name, number)

def migrate_categories():
    """Миграция категорий из старой структуры в новую"""
    conn = sqlite3.connect('merchandise.db')
    cursor = conn.cursor()
    
    try:
        # 1. Получаем уникальные категории
        categories = get_unique_categories(conn)
        
        # 2. Создаем записи в feed_categories
        for category_name, category_number in categories:
            cursor.execute('''
            INSERT OR IGNORE INTO feed_categories (category_number, name)
            VALUES (?, ?)
            ''', (category_number, category_name))
        
        # 3. Получаем маппинг категорий (name -> id)
        cursor.execute('SELECT id, name FROM feed_categories')
        category_mapping = {name: id for id, name in cursor.fetchall()}
        
        # 4. Переносим связи товаров с категориями
        cursor.execute('SELECT sku, category FROM products WHERE category IS NOT NULL')
        for sku, category in cursor.fetchall():
            if category in category_mapping:
                category_id = category_mapping[category]
                cursor.execute('''
                INSERT OR REPLACE INTO product_categories (sku, category_id, is_primary)
                VALUES (?, ?, 1)
                ''', (sku, category_id))
        
        conn.commit()
        print("Миграция категорий успешно завершена!")
        
        # Выводим статистику
        cursor.execute('SELECT COUNT(*) FROM feed_categories')
        categories_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM product_categories')
        product_categories_count = cursor.fetchone()[0]
        print(f"Перенесено категорий: {categories_count}")
        print(f"Перенесено связей товаров с категориями: {product_categories_count}")
        
    except Exception as e:
        print(f"Ошибка при миграции: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_categories() 