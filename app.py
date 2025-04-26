from flask import Flask, render_template, jsonify, request
import sqlite3
import json

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('merchandise.db')
    conn.row_factory = sqlite3.Row
    return conn

def calculate_score(product, weights):
    # Базовый скор
    score = 1.0
    
    if weights:
        # Применяем веса к метрикам
        if product.get('sessions'):
            score *= (1 + (weights['sessions_weight'] - 1) * (product['sessions'] / 100))
        if product.get('product_views'):
            score *= (1 + (weights['views_weight'] - 1) * (product['product_views'] / 100))
        if product.get('cart_additions'):
            score *= (1 + (weights['cart_weight'] - 1) * (product['cart_additions'] / 10))
        if product.get('checkout_starts'):
            score *= (1 + (weights['checkout_weight'] - 1) * (product['checkout_starts'] / 10))
        if product.get('orders_gross'):
            score *= (1 + (weights['orders_gross_weight'] - 1) * (product['orders_gross'] / 5))
        if product.get('orders_net'):
            score *= (1 + (weights['orders_net_weight'] - 1) * (product['orders_net'] / 5))
        
        # Применяем штраф за скидку
        if product.get('discount') and weights['discount_penalty']:
            score *= (1 - (product['discount'] / 100) * weights['discount_penalty'])
    
    return round(score, 2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/weights')
def weights_page():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM weights ORDER BY id DESC LIMIT 1')
    weights = cursor.fetchone()
    conn.close()
    
    if weights:
        weights_dict = {
            'sessions_weight': weights['sessions_weight'],
            'views_weight': weights['views_weight'],
            'cart_weight': weights['cart_weight'],
            'checkout_weight': weights['checkout_weight'],
            'orders_gross_weight': weights['orders_gross_weight'],
            'orders_net_weight': weights['orders_net_weight'],
            'discount_penalty': weights['discount_penalty']
        }
    else:
        weights_dict = {
            'sessions_weight': 1.0,
            'views_weight': 1.0,
            'cart_weight': 1.0,
            'checkout_weight': 1.0,
            'orders_gross_weight': 1.0,
            'orders_net_weight': 1.0,
            'discount_penalty': 0.0
        }
    
    return render_template('weights.html', weights=weights_dict)

@app.route('/api/products')
def get_products():
    category = request.args.get('category', 'all')
    page = int(request.args.get('page', 1))
    hide_no_price = request.args.get('hide_no_price', 'true').lower() == 'true'
    search = request.args.get('search', '')
    gender = request.args.get('gender', 'all')
    
    per_page = 12
    offset = (page - 1) * per_page
    
    conn = get_db_connection()
    
    try:
        # Базовые условия для WHERE
        where_conditions = []
        params = []
        
        if category != 'all':
            where_conditions.append("p.max_Категория = ?")
            params.append(category)
        
        if hide_no_price:
            where_conditions.append("p.price > 0")
        
        if search:
            where_conditions.append("p.sku LIKE ?")
            params.append(f"%{search}%")
        
        if gender != 'all':
            if gender == 'empty':
                where_conditions.append("(p.gender IS NULL OR p.gender = '')")
            else:
                where_conditions.append("p.gender = ?")
                params.append(gender)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Получаем все товары с метриками
        query = f"""
            SELECT p.*, pm.* 
            FROM products p 
            LEFT JOIN product_metrics pm ON p.sku = pm.sku
            WHERE {where_clause}
        """
        print(f"Executing query: {query} with params: {params}")  # Добавляем логирование
        products = conn.execute(query, params).fetchall()
        
        # Получаем веса для расчета скоринга
        weights = conn.execute("SELECT * FROM weights ORDER BY id DESC LIMIT 1").fetchone()
        
        # Преобразуем товары в словари и добавляем скоринг
        products_list = []
        for product in products:
            product_dict = dict(product)
            product_dict['score'] = calculate_score(product_dict, weights)
            products_list.append(product_dict)
        
        # Сортируем все товары по скору
        products_list.sort(key=lambda x: x['score'], reverse=True)
        
        # Получаем общее количество товаров
        total_products = len(products_list)
        total_pages = (total_products + per_page - 1) // per_page
        
        # Выбираем только нужную страницу
        paginated_products = products_list[offset:offset + per_page]
        
        return jsonify({
            'products': paginated_products,
            'total_pages': total_pages,
            'current_page': page
        })
    except Exception as e:
        print(f"Error: {str(e)}")  # Добавляем логирование ошибок
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/categories')
def get_categories():
    conn = get_db_connection()
    categories = conn.execute('SELECT DISTINCT max_Категория as category FROM products WHERE max_Категория IS NOT NULL AND max_Категория != ""').fetchall()
    conn.close()
    return jsonify([dict(category) for category in categories if category['category']])

@app.route('/api/update_weights', methods=['POST'])
def update_weights():
    weights = request.json
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO weights (
                sessions_weight,
                views_weight,
                cart_weight,
                checkout_weight,
                orders_gross_weight,
                orders_net_weight,
                discount_penalty
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            float(weights.get('sessions_weight', 1.0)),
            float(weights.get('views_weight', 1.0)),
            float(weights.get('cart_weight', 1.0)),
            float(weights.get('checkout_weight', 1.0)),
            float(weights.get('orders_gross_weight', 1.0)),
            float(weights.get('orders_net_weight', 1.0)),
            float(weights.get('discount_penalty', 0.0))
        ))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        conn.close()
        return jsonify({'status': 'error', 'message': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=3001) 