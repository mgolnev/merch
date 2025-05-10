from app.database.connection import get_db_connection
from app.utils.query_builder import QueryBuilder
from app.utils.validation import ProductFilters
from typing import List, Dict, Any
import json
from datetime import datetime

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
    
    # Бонус за новизну товара (sale_start_date)
    sale_start_weight = weights_dict.get('sale_start_weight', 1.0)
    sale_start_date = product.get('sale_start_date')
    if sale_start_date:
        try:
            start_date = datetime.strptime(sale_start_date, "%Y-%m-%d")
            days_since_start = (datetime.now() - start_date).days
            # Если товар только поступил или поступит — максимальный бонус
            if days_since_start <= 0:
                sale_bonus = 1.0
            # Если товару до 30 дней — бонус линейно убывает
            elif days_since_start < 30:
                sale_bonus = (30 - days_since_start) / 30
            else:
                sale_bonus = 0.0
            score += sale_bonus * sale_start_weight
        except Exception:
            pass
    
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
        weights_dict = dict(weights)
        
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
        else:
            products_query = f"""
                SELECT p.*
                FROM {from_clause}
                WHERE {where_clause}
            """
            cursor.execute(products_query, params)
            rows = cursor.fetchall()
        
        # Собираем все уникальные даты старта
        sale_dates = set()
        for row in rows:
            date_str = row['sale_start_date']
            if date_str and date_str != '':
                try:
                    date_obj = datetime.strptime(date_str, "%d.%m.%Y")
                except ValueError:
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    except Exception:
                        continue
                sale_dates.add(date_obj)
        if not sale_dates:
            sale_dates = {datetime(2000, 1, 1)}
        sale_dates_sorted = sorted(sale_dates)
        date_to_index = {d: i for i, d in enumerate(sale_dates_sorted)}
        n = len(sale_dates_sorted)
        sale_start_weight = weights_dict.get('sale_start_weight', 1.0)
        def novelty_bonus(date_str):
            if not date_str or date_str == '':
                return sale_start_weight
            try:
                date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            except ValueError:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                except Exception:
                    return sale_start_weight
            idx = date_to_index.get(date_obj)
            if idx is None:
                return sale_start_weight
            return sale_start_weight * (idx + 1)
        
        products = []
        for row in rows:
            product = dict(row)
            product['score'] = calculate_score(product, weights)
            product['has_image'] = bool(product.get('image_url'))
            if 'categories' in product:
                product['category'] = product['categories']
                product['categories'] = [product['categories']]
            # Бонус за новизну теперь умножается на sale_start_weight
            product['score'] += novelty_bonus(product.get('sale_start_date'))
            products.append(product)
        
        # Сортировка и пагинация как раньше
        if filters.category != 'all':
            products.sort(key=lambda x: (
                1 if x.get('position') is None else 0,
                x.get('position') if x.get('position') is not None else 999999,
                -x['score']
            ))
            total = len(products)
            products = products[offset:offset + filters.per_page]
        else:
            products.sort(key=lambda x: -x['score'])
            total = len(products)
            products = products[offset:offset + filters.per_page]
        
        return {
            'products': products,
            'total': total,
            'page': filters.page,
            'per_page': filters.per_page,
            'total_pages': (total + filters.per_page - 1) // filters.per_page
        } 