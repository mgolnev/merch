from app.database.connection import get_db_connection
from app.utils.query_builder import QueryBuilder
from app.utils.validation import ProductFilters
from typing import List, Dict, Any
import json

def calculate_score(product, weights):
    """Расчет скоринга для продукта"""
    # Базовый скор
    score = 0
    
    # Получаем метрики
    sessions = product.get('sessions', 0)
    views = product.get('product_views', 0)
    cart = product.get('cart_additions', 0)
    checkout = product.get('checkout_starts', 0)
    orders_gross = product.get('orders_gross', 0)
    orders_net = product.get('orders_net', 0)
    discount = product.get('discount', 0)
    
    # Конверсии
    session_to_view = views / sessions if sessions > 0 else 0
    view_to_cart = cart / views if views > 0 else 0
    cart_to_checkout = checkout / cart if cart > 0 else 0
    checkout_to_order = orders_gross / checkout if checkout > 0 else 0
    
    # Веса из объекта weights
    weights_dict = dict(weights)
    
    # Конверсионный скор (взвешенная сумма конверсий)
    score += session_to_view * weights_dict.get('sessions_weight', 1.0)
    score += view_to_cart * weights_dict.get('views_weight', 1.0)
    score += cart_to_checkout * weights_dict.get('cart_weight', 1.0)
    score += checkout_to_order * weights_dict.get('checkout_weight', 1.0)
    
    # Бонус за каждый заказ
    score += orders_gross * weights_dict.get('orders_gross_weight', 1.0)
    score += orders_net * weights_dict.get('orders_net_weight', 1.0)
    
    # Штраф за скидку (чем больше скидка, тем больше штраф)
    discount_penalty = weights_dict.get('discount_penalty', 0.0)
    score -= discount * discount_penalty if discount_penalty > 0 else 0
    
    return score

def get_products(filters: ProductFilters) -> Dict[str, Any]:
    """Получение списка продуктов с пагинацией и фильтрацией"""
    query_builder = QueryBuilder()
    join_product_categories = False
    
    # Применяем фильтры
    if filters.category != 'all':
        join_product_categories = True
        query_builder.add_condition("pc.category_id = ?", filters.category)
    
    if filters.hide_no_price:
        query_builder.add_condition("p.price > 0")
    
    if filters.gender != 'all':
        query_builder.add_condition("p.gender = ?", filters.gender)
    
    if filters.search:
        search_term = f"%{filters.search}%"
        query_builder.add_condition("(p.name LIKE ? OR p.sku LIKE ?)", search_term)
        query_builder.add_condition("(p.name LIKE ? OR p.sku LIKE ?)", search_term)
    
    if filters.sku:
        query_builder.add_condition("p.sku = ?", filters.sku)
    
    where_clause, params = query_builder.build()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Формируем FROM и JOIN
        from_clause = "products p"
        if join_product_categories:
            from_clause += " JOIN product_categories pc ON p.sku = pc.sku"
        
        # Получаем общее количество товаров для пагинации
        count_query = f"""
        SELECT COUNT(DISTINCT p.sku) as total
        FROM {from_clause}
        WHERE {where_clause}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # Получаем текущие веса
        cursor.execute("SELECT * FROM weights ORDER BY id DESC LIMIT 1")
        weights = cursor.fetchone()
        
        # Расчет пагинации
        offset = (filters.page - 1) * filters.per_page
        
        # Получаем продукты с учетом пагинации
        if filters.category != 'all':
            # Получаем все товары категории без сортировки и лимита
            products_query = f"""
                SELECT p.*, pc.position
                FROM {from_clause}
                WHERE {where_clause}
            """
            cursor.execute(products_query, params)
            rows = cursor.fetchall()
            products = []
            for row in rows:
                product = dict(row)
                product['score'] = calculate_score(product, weights)
                product['has_image'] = bool(product.get('image_url'))
                if 'categories' in product:
                    product['category'] = product['categories']
                    product['categories'] = [product['categories']]
                products.append(product)
            # Сортируем: сначала по наличию позиции, потом по позиции, потом по скору
            products.sort(key=lambda x: (
                1 if x.get('position') is None else 0,
                x.get('position') if x.get('position') is not None else 999999,
                -x['score']
            ))
            # Пагинация
            total = len(products)
            products = products[offset:offset + filters.per_page]
        else:
            # Для всех категорий: сортировка по скору и пагинация на Python-стороне
            products_query = f"""
                SELECT p.*
                FROM {from_clause}
                WHERE {where_clause}
            """
            cursor.execute(products_query, params)
            rows = cursor.fetchall()
            products = []
            for row in rows:
                product = dict(row)
                product['score'] = calculate_score(product, weights)
                product['has_image'] = bool(product.get('image_url'))
                if 'categories' in product:
                    product['category'] = product['categories']
                    product['categories'] = [product['categories']]
                products.append(product)
            # Сортировка по скору (по убыванию)
            products.sort(key=lambda x: -x['score'])
            # Пагинация
            total = len(products)
            products = products[offset:offset + filters.per_page]
        
        return {
            'products': products,
            'total': total,
            'page': filters.page,
            'per_page': filters.per_page,
            'total_pages': (total + filters.per_page - 1) // filters.per_page
        } 