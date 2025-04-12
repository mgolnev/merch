from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import pandas as pd
import json
from datetime import datetime
import os

app = Flask(__name__, static_folder='static')
CORS(app)  # Разрешаем CORS для всех доменов

def get_db_connection():
    conn = sqlite3.connect('merchandise.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db_connection()
    query = "SELECT * FROM product"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/products/stats', methods=['GET'])
def get_stats():
    conn = get_db_connection()
    query = """
        SELECT 
            COUNT(*) as total_products,
            AVG(sessions) as avg_sessions,
            AVG(product_views) as avg_views,
            AVG(orders_net) as avg_orders,
            SUM(revenue_net) as total_revenue
        FROM product
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return jsonify(df.to_dict(orient='records')[0])

@app.route('/api/products/categories', methods=['GET'])
def get_categories():
    conn = get_db_connection()
    query = """
        SELECT 
            category,
            COUNT(*) as product_count,
            AVG(revenue_net) as avg_revenue
        FROM product
        GROUP BY category
        ORDER BY product_count DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/products/category/<category>', methods=['GET'])
def get_products_by_category(category):
    conn = get_db_connection()
    query = """
        SELECT *
        FROM product
        WHERE category = ?
        ORDER BY revenue_net DESC
    """
    df = pd.read_sql_query(query, conn, params=[category])
    conn.close()
    return jsonify(df.to_dict(orient='records'))

def calculate_product_score(views, conversions, has_sizes):
    # Веса факторов (можно настроить)
    VIEWS_WEIGHT = 0.4
    CONVERSIONS_WEIGHT = 0.5
    SIZES_WEIGHT = 0.1
    
    # Нормализация значений
    normalized_views = min(views / 1000, 1.0)  # Предполагаем, что 1000 просмотров - максимум
    normalized_conversions = min(conversions / 100, 1.0)  # Предполагаем, что 100 конверсий - максимум
    
    # Расчет итогового скора
    score = (normalized_views * VIEWS_WEIGHT + 
             normalized_conversions * CONVERSIONS_WEIGHT + 
             (1 if has_sizes else 0) * SIZES_WEIGHT)
    
    return score

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
    limit = int(request.args.get('limit', 20))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Получаем отсортированные товары
        query = '''
            SELECT 
                id, 
                name, 
                article, 
                price, 
                image_url, 
                COALESCE(views, 0) as views,
                COALESCE(conversions, 0) as conversions,
                COALESCE(sizes_available, '[]') as sizes_available,
                (
                    COALESCE(views, 0) * 0.4 + 
                    COALESCE(conversions, 0) * 0.5 + 
                    CASE WHEN json_array_length(COALESCE(sizes_available, '[]')) > 0 THEN 1 ELSE 0 END * 0.1
                ) as score
            FROM product
        '''
        params = []
        
        if category:
            query += ' WHERE category = ?'
            params.append(category)
            
        query += ' ORDER BY score DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        products = cursor.fetchall()
        
        # Форматируем результат
        result = []
        for product in products:
            result.append({
                'id': product['id'],
                'name': product['name'],
                'article': product['article'],
                'price': product['price'],
                'image_url': product['image_url'],
                'views': product['views'],
                'conversions': product['conversions'],
                'sizes_available': json.loads(product['sizes_available']),
                'score': product['score']
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/products/<int:product_id>/view', methods=['POST'])
def increment_product_views(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE product SET views = COALESCE(views, 0) + 1 WHERE id = ?', (product_id,))
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
    app.run(debug=True, port=5001) 