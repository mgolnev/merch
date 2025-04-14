from flask import Flask, render_template, jsonify, request
import sqlite3
import json

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('merchandise.db')
    conn.row_factory = sqlite3.Row
    return conn

def calculate_score(product):
    # Базовый скор
    score = 1.0
    
    # Получаем сохраненные веса из базы данных или используем значения по умолчанию
    conn = get_db_connection()
    weights = conn.execute('SELECT * FROM weights ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()
    
    if weights:
        # Применяем веса к метрикам
        if product['sessions']:
            score *= (1 + (weights['sessions_weight'] - 1) * (product['sessions'] / 100))
        if product['product_views']:
            score *= (1 + (weights['views_weight'] - 1) * (product['product_views'] / 100))
        if product['cart_additions']:
            score *= (1 + (weights['cart_weight'] - 1) * (product['cart_additions'] / 10))
        if product['checkout_starts']:
            score *= (1 + (weights['checkout_weight'] - 1) * (product['checkout_starts'] / 10))
        if product['orders_gross']:
            score *= (1 + (weights['orders_gross_weight'] - 1) * (product['orders_gross'] / 5))
        if product['orders_net']:
            score *= (1 + (weights['orders_net_weight'] - 1) * (product['orders_net'] / 5))
        
        # Применяем штраф за скидку
        if product['discount'] and weights['discount_penalty']:
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
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 30, type=int)
    hide_no_price = request.args.get('hide_no_price', 'true').lower() == 'true'
    offset = (page - 1) * per_page
    
    conn = get_db_connection()
    
    price_filter = "AND p.price IS NOT NULL AND p.price > 0" if hide_no_price else ""
    
    # Получаем общее количество товаров для пагинации
    if category == 'all':
        total = conn.execute(f'SELECT COUNT(*) as count FROM products p WHERE 1=1 {price_filter}').fetchone()['count']
        products = conn.execute(f'''
            SELECT p.*, pm.* 
            FROM products p 
            LEFT JOIN product_metrics pm ON p.sku = pm.sku
            WHERE 1=1 {price_filter}
            LIMIT ? OFFSET ?
        ''', (per_page, offset)).fetchall()
    else:
        total = conn.execute(f'SELECT COUNT(*) as count FROM products p WHERE category = ? {price_filter}', 
                           (category,)).fetchone()['count']
        products = conn.execute(f'''
            SELECT p.*, pm.* 
            FROM products p 
            LEFT JOIN product_metrics pm ON p.sku = pm.sku
            WHERE p.category = ? {price_filter}
            LIMIT ? OFFSET ?
        ''', (category, per_page, offset)).fetchall()
    
    conn.close()
    
    # Преобразуем результаты и добавляем скор
    products_with_score = []
    for product in products:
        product_dict = dict(product)
        product_dict['score'] = calculate_score(product_dict)
        products_with_score.append(product_dict)
    
    # Сортируем по скору
    products_with_score.sort(key=lambda x: x['score'], reverse=True)
    
    return jsonify({
        'products': products_with_score,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
        'hide_no_price': hide_no_price
    })

@app.route('/api/categories')
def get_categories():
    conn = get_db_connection()
    categories = conn.execute('SELECT DISTINCT category FROM products').fetchall()
    conn.close()
    return jsonify([dict(category) for category in categories])

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