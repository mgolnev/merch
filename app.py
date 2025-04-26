from flask import Flask, render_template, jsonify, request, send_file
import sqlite3
import json
import csv
import io

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
        
        # Получаем все товары с метриками и порядком в категории
        query = f"""
            WITH CategoryRanks AS (
                SELECT 
                    p.sku,
                    p.max_Категория,
                    RANK() OVER (
                        PARTITION BY p.max_Категория 
                        ORDER BY 
                            CASE 
                                WHEN co.position IS NOT NULL THEN 1
                                ELSE 2
                            END,
                            co.position,
                            -pm.sessions DESC,
                            -pm.product_views DESC
                    ) as category_rank,
                    co.position as category_position
                FROM products p
                LEFT JOIN product_metrics pm ON p.sku = pm.sku
                LEFT JOIN category_order co ON p.sku = co.sku AND co.category = p.max_Категория
            )
            SELECT 
                p.*,
                pm.*,
                cr.category_position,
                cr.category_rank,
                RANK() OVER (ORDER BY 
                    COALESCE(pm.sessions, 0) DESC,
                    COALESCE(pm.product_views, 0) DESC
                ) as global_rank
            FROM products p 
            LEFT JOIN product_metrics pm ON p.sku = pm.sku
            LEFT JOIN CategoryRanks cr ON p.sku = cr.sku
            WHERE {where_clause}
        """
        
        print(f"Executing query: {query} with params: {params}")
        products = conn.execute(query, params).fetchall()
        
        # Получаем веса для расчета скоринга
        weights = conn.execute("SELECT * FROM weights ORDER BY id DESC LIMIT 1").fetchone()
        
        # Преобразуем товары в словари и добавляем скоринг
        products_list = []
        for product in products:
            product_dict = dict(product)
            # Вычисляем скор на основе весов (не зависит от ручной сортировки)
            product_dict['score'] = calculate_score(product_dict, weights)
            products_list.append(product_dict)
        
        # Сортируем товары
        if category != 'all':
            # В категории: сначала по ручным позициям, потом по скору
            products_list.sort(
                key=lambda x: (
                    0 if x['category_position'] is not None else 1,
                    x['category_position'] if x['category_position'] is not None else float('inf'),
                    -x['score']
                )
            )
        else:
            # В общем каталоге: только по скору
            products_list.sort(key=lambda x: -x['score'])
        
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
        print(f"Error: {str(e)}")
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

@app.route('/api/category_score', methods=['POST'])
def update_category_score():
    data = request.json
    sku = data.get('sku')
    category = data.get('category')
    score = data.get('score')
    
    if not all([sku, category, score]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT OR REPLACE INTO category_scores (sku, category, score)
            VALUES (?, ?, ?)
        ''', (sku, category, score))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/category_order', methods=['POST'])
def update_category_order():
    data = request.json
    sku = data.get('sku')
    category = data.get('category')
    position = data.get('position')
    
    if not all([sku, category, position]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT OR REPLACE INTO category_order (sku, category, position)
            VALUES (?, ?, ?)
        ''', (sku, category, position))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/reset_weights', methods=['POST'])
def reset_weights():
    conn = get_db_connection()
    try:
        # Сбрасываем веса к значениям по умолчанию
        conn.execute('''
            INSERT INTO weights (
                sessions_weight,
                views_weight,
                cart_weight,
                checkout_weight,
                orders_gross_weight,
                orders_net_weight,
                discount_penalty
            ) VALUES (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0)
        ''')
        
        # Удаляем все ручные позиции
        conn.execute('DELETE FROM category_order')
        
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/reset_category_order', methods=['POST'])
def reset_category_order():
    data = request.json
    category = data.get('category')
    
    if not category:
        return jsonify({'status': 'error', 'message': 'Не указана категория'}), 400
    
    conn = get_db_connection()
    try:
        # Удаляем ручные позиции только для указанной категории
        conn.execute('DELETE FROM category_order WHERE category = ?', (category,))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/export_category/<category>')
def export_category(category):
    conn = get_db_connection()
    try:
        # Получаем данные о позициях товаров в категории
        query = """
            WITH CategoryRanks AS (
                SELECT 
                    p.sku,
                    p.max_Категория,
                    RANK() OVER (
                        PARTITION BY p.max_Категория 
                        ORDER BY 
                            CASE 
                                WHEN co.position IS NOT NULL THEN 1
                                ELSE 2
                            END,
                            co.position,
                            -pm.sessions DESC,
                            -pm.product_views DESC
                    ) as category_rank,
                    co.position as category_position
                FROM products p
                LEFT JOIN product_metrics pm ON p.sku = pm.sku
                LEFT JOIN category_order co ON p.sku = co.sku AND co.category = p.max_Категория
                WHERE p.max_Категория = ?
            )
            SELECT 
                p.sku,
                cr.category_position,
                cr.category_rank
            FROM products p 
            LEFT JOIN CategoryRanks cr ON p.sku = cr.sku
            WHERE p.max_Категория = ?
            ORDER BY 
                CASE 
                    WHEN cr.category_position IS NOT NULL THEN 1
                    ELSE 2
                END,
                cr.category_position,
                cr.category_rank
        """
        
        products = conn.execute(query, (category, category)).fetchall()
        
        # Создаем CSV в памяти
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Артикул', 'Позиция в категории'])
        
        for product in products:
            writer.writerow([
                product['sku'],
                product['category_position'] if product['category_position'] is not None else product['category_rank']
            ])
        
        # Подготавливаем файл для отправки
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'{category}_positions.csv'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=3001) 