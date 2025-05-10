from app.database.connection import get_db_connection
from typing import Dict, List, Any
import json

def get_all_categories():
    """Получение всех уникальных категорий из feed_categories"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name FROM feed_categories
            WHERE is_active = 1
            ORDER BY id
        """)
        categories = [{"id": row["id"], "name": row["name"]} for row in cursor.fetchall()]
        return categories

def get_category_products(category_id: int, scored: bool = True):
    """Получение продуктов категории с скорингом"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Получаем текущие веса
        cursor.execute("SELECT * FROM weights ORDER BY id DESC LIMIT 1")
        weights = cursor.fetchone()
        
        # Получаем продукты категории
        cursor.execute("""
        SELECT p.sku, p.name, p.price, p.oldprice, p.discount, p.gender, 
               p.categories as category, p.image_url, p.sale_start_date, p.available,
               p.sessions, p.product_views, p.cart_additions, 
               p.checkout_starts, p.orders_gross, p.orders_net,
               co.position
        FROM products p
        LEFT JOIN category_order co ON p.sku = co.sku AND co.category = ?
        WHERE p.categories = ?
        ORDER BY co.position IS NULL, co.position
        """, (category_id, category_id))
        
        products = []
        from app.services.product_service import calculate_score
        
        for row in cursor.fetchall():
            product = dict(row)
            
            # Добавляем рассчитанный скор если нужно
            if scored:
                product['score'] = calculate_score(product, weights)
            
            products.append(product)
        
        return products

def update_category_order(sku: str, category_id: str, position: int):
    """Обновление позиции товара в категории"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Проверяем, существует ли такой товар в указанной категории
        cursor.execute("""
        SELECT 1 FROM products 
        WHERE sku = ? AND categories = ?
        """, (sku, category_id))
        
        if not cursor.fetchone():
            return False, "Товар не найден в указанной категории"
        
        # Обновляем или вставляем запись
        cursor.execute("""
        INSERT OR REPLACE INTO category_order (sku, category, position)
        VALUES (?, ?, ?)
        """, (sku, category_id, position))
        
        conn.commit()
        return True, "Позиция обновлена"

def reset_category_order(category_id: str):
    """Сброс порядка товаров в категории"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        DELETE FROM category_order
        WHERE category = ?
        """, (category_id,))
        conn.commit()
        
        return True, f"Порядок товаров в категории {category_id} сброшен"

def export_category_data(category_id: str):
    """Экспорт данных категории в JSON формат"""
    products = get_category_products(category_id)
    return json.dumps(products, ensure_ascii=False) 