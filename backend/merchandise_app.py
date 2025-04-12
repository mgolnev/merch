from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime
import os

app = Flask(__name__, static_folder='static')
CORS(app)

# Начальные значения весов факторов
DEFAULT_WEIGHTS = {
    'views_weight': 0.3,
    'cart_conversion_weight': 0.3,
    'purchase_conversion_weight': 0.3,
    'sizes_weight': 0.1
}

# Глобальные веса факторов
factor_weights = DEFAULT_WEIGHTS.copy()

def get_db_connection():
    conn = sqlite3.connect('merchandise.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/weights', methods=['GET', 'POST'])
def manage_weights():
    global factor_weights
    
    if request.method == 'GET':
        return jsonify(factor_weights)
    
    if request.method == 'POST':
        try:
            new_weights = request.get_json()
            # Проверяем, что сумма весов равна 1
            total_weight = sum(new_weights.values())
            if abs(total_weight - 1.0) > 0.001:  # Допускаем небольшую погрешность
                return jsonify({'error': 'Сумма весов должна быть равна 1'}), 400
            
            factor_weights = new_weights
            return jsonify({'status': 'success', 'weights': factor_weights})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT DISTINCT category FROM product WHERE category IS NOT NULL')
        categories = [row['category'] for row in cursor.fetchall()]
        return jsonify(categories)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/products/merchandising', methods=['GET'])
def get_merchandised_products():
    category = request.args.get('category', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    offset = (page - 1) * per_page
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Базовый запрос для подсчета общего количества товаров
        count_query = 'SELECT COUNT(*) as total FROM product'
        count_params = []
        if category:
            count_query += ' WHERE category = ?'
            count_params.append(category)
        
        cursor.execute(count_query, count_params)
        total_items = cursor.fetchone()['total']
        
        # Получаем отсортированные товары
        query = '''
            SELECT 
                id, 
                name,
                article, 
                price, 
                image_url,
                product_views as views,
                add_to_cart,
                orders_gross,
                CASE 
                    WHEN product_views > 0 THEN ROUND(CAST(add_to_cart AS FLOAT) / product_views * 100, 2)
                    ELSE 0 
                END as view_to_cart,
                CASE 
                    WHEN product_views > 0 THEN ROUND(CAST(orders_gross AS FLOAT) / product_views * 100, 2)
                    ELSE 0 
                END as conversions,
                sizes_available,
                (
                    -- Нормализованные просмотры
                    COALESCE(product_views, 0) * ? +
                    -- Конверсия просмотр-в-корзину
                    CASE 
                        WHEN product_views > 0 THEN (CAST(add_to_cart AS FLOAT) / product_views) * ?
                        ELSE 0 
                    END +
                    -- Конверсия в покупку
                    CASE 
                        WHEN product_views > 0 THEN (CAST(orders_gross AS FLOAT) / product_views) * ?
                        ELSE 0 
                    END +
                    -- Наличие размеров
                    CASE WHEN json_array_length(COALESCE(sizes_available, '[]')) > 0 THEN ? ELSE 0 END
                ) as score
            FROM product
        '''
        params = [
            factor_weights['views_weight'],
            factor_weights['cart_conversion_weight'] * 100,
            factor_weights['purchase_conversion_weight'] * 100,
            factor_weights['sizes_weight']
        ]
        
        if category:
            query += ' WHERE category = ?'
            params.append(category)
            
        query += ' ORDER BY score DESC LIMIT ? OFFSET ?'
        params.extend([per_page, offset])
        
        cursor.execute(query, params)
        products = cursor.fetchall()
        
        # Форматируем результат
        result = []
        for product in products:
            result.append({
                'id': product['id'],
                'name': product['name'] or product['article'],
                'article': product['article'],
                'price': product['price'],
                'image_url': product['image_url'],
                'views': product['views'],
                'add_to_cart': product['add_to_cart'],
                'orders': product['orders_gross'],
                'view_to_cart': product['view_to_cart'],
                'conversions': product['conversions'],
                'sizes_available': json.loads(product['sizes_available'] or '[]'),
                'score': product['score']
            })
        
        return jsonify({
            'items': result,
            'total': total_items,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_items + per_page - 1) // per_page,
            'weights': factor_weights
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/products/<int:product_id>/view', methods=['POST'])
def increment_product_views(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE product SET product_views = COALESCE(product_views, 0) + 1 WHERE id = ?', (product_id,))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/products/<int:product_id>/conversion', methods=['POST'])
def increment_product_conversions(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE product SET conversions = COALESCE(conversions, 0) + 1 WHERE id = ?', (product_id,))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    app.run(debug=True, port=3001) 