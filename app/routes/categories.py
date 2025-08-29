from flask import Blueprint, jsonify, request, send_file
from app.services.category_service import (
    get_all_categories, 
    get_category_products, 
    update_category_order,
    reset_category_order, 
    export_category_data
)
from app.utils.validation import InputValidator, ValidationError
import io
import csv
import json
from app.database.connection import get_db_connection

categories_bp = Blueprint('categories', __name__)

@categories_bp.route('/api/categories')
def get_categories():
    """API для получения всех категорий"""
    try:
        categories = get_all_categories()
        return jsonify(categories)
    except Exception as e:
        return jsonify({"error": f"Ошибка при получении категорий: {str(e)}"}), 500

@categories_bp.route('/api/categories/<int:category_number>')
def get_category(category_number):
    """API для получения продуктов определенной категории"""
    try:
        # Получаем все категории
        categories = get_all_categories()
        
        # Проверяем, существует ли запрошенная категория
        if category_number < 0 or category_number >= len(categories):
            return jsonify({"error": "Категория не найдена"}), 404
        
        category_id = categories[category_number]
        products = get_category_products(category_id)
        
        return jsonify({
            "category": category_id,
            "products": products
        })
    except Exception as e:
        return jsonify({"error": f"Ошибка при получении категории: {str(e)}"}), 500

@categories_bp.route('/api/category_order', methods=['POST'])
def update_category_order_route():
    """API для обновления порядка товаров в категории"""
    try:
        data = request.get_json()
        
        # Валидация входных данных
        validated_data = InputValidator.validate_category_order(data)
        
        # Обновление позиции
        success, message = update_category_order(
            validated_data['sku'],
            validated_data['category_id'],
            validated_data['position']
        )
        
        if success:
            return jsonify({"message": message})
        else:
            return jsonify({"error": message}), 400
            
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Ошибка при обновлении порядка: {str(e)}"}), 500

@categories_bp.route('/api/reset_category_order', methods=['POST'])
def reset_category_order():
    """API для сброса ручных позиций в категории"""
    try:
        data = request.json
        category_id = data.get('category_id')
        
        if not category_id:
            return jsonify({"error": "Не указан category_id"}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Удаляем все записи для данной категории из таблицы category_order
            cursor.execute('''
                DELETE FROM category_order 
                WHERE category = ?
            ''', (category_id,))
            conn.commit()
            
        return jsonify({"message": "Порядок категории успешно сброшен"})
    except Exception as e:
        return jsonify({"error": f"Ошибка при сбросе порядка категории: {str(e)}"}), 500

@categories_bp.route('/api/export_category/<int:category_number>')
def export_category(category_number):
    """API для экспорта категории в CSV формат (только sku, category_id, position)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name 
                FROM feed_categories 
                WHERE category_number = ? AND is_active = 1
            """, (category_number,))
            category = cursor.fetchone()
            if not category:
                return jsonify({"error": "Категория не найдена"}), 404
            
            db_category_id = category['id']
            # Получаем товары с позициями из category_order
            cursor.execute("""
                SELECT 
                    p.sku,
                    ? as category_number,
                    co.position
                FROM products p
                JOIN product_categories pc ON p.sku = pc.sku AND pc.category_id = ?
                LEFT JOIN category_order co ON p.sku = co.sku AND co.category = ?
                ORDER BY 
                    CASE WHEN co.position IS NOT NULL THEN 1 ELSE 2 END,
                    co.position,
                    p.sku
            """, (category_number, db_category_id, category_number))
            products = cursor.fetchall()
        # Создаем CSV в памяти
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(['sku', 'category_number', 'position'])
        for product in products:
            writer.writerow([
                product['sku'],
                product['category_number'],
                product['position'] if product['position'] is not None else ''
            ])
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'category_{category["name"]}_products.csv'
        )
    except Exception as e:
        return jsonify({"error": f"Ошибка при экспорте категории: {str(e)}"}), 500

@categories_bp.route('/api/category_order_bulk', methods=['POST'])
def update_category_order_bulk():
    """API для массового обновления порядка товаров в категории"""
    try:
        data = request.json
        if not isinstance(data, list):
            return jsonify({"error": "Ожидается массив позиций"}), 400
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for position in data:
                sku = position.get('sku')
                category_id = position.get('category_id')
                pos = position.get('position')
                
                if not all([sku, category_id, pos is not None]):
                    return jsonify({"error": "Неверный формат данных"}), 400
                    
                # Обновляем позицию в таблице category_order
                cursor.execute('''
                    INSERT OR REPLACE INTO category_order (sku, category, position)
                    VALUES (?, ?, ?)
                ''', (sku, category_id, pos))
                
            conn.commit()
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": f"Ошибка при обновлении порядка: {str(e)}"}), 500

@categories_bp.route('/api/global_order_bulk', methods=['POST'])
def update_global_order_bulk():
    """API для массового обновления глобального порядка всех товаров"""
    try:
        data = request.json
        if not isinstance(data, list):
            return jsonify({"error": "Ожидается массив позиций"}), 400
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Создаем таблицу для глобального порядка, если её нет
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS global_product_order (
                    sku TEXT PRIMARY KEY,
                    position INTEGER NOT NULL
                )
            ''')
            
            for position in data:
                sku = position.get('sku')
                pos = position.get('position')
                
                if not all([sku, pos is not None]):
                    return jsonify({"error": "Неверный формат данных"}), 400
                    
                cursor.execute('''
                    INSERT OR REPLACE INTO global_product_order (sku, position)
                    VALUES (?, ?)
                ''', (sku, pos))
                
            conn.commit()
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": f"Ошибка при обновлении глобального порядка: {str(e)}"}), 500

@categories_bp.route('/api/export_all_products')
def export_all_products():
    """API для экспорта всех товаров в CSV формат"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем все товары с их глобальными позициями
            cursor.execute('''
                SELECT 
                    p.sku,
                    p.name,
                    p.price,
                    p.oldprice,
                    p.discount,
                    p.gender,
                    p.image_url,
                    p.url,
                    p.sessions,
                    p.product_views,
                    p.cart_additions,
                    p.checkout_starts,
                    p.orders_gross,
                    p.orders_net,
                    p.revenue_vat,
                    p.revenue_net,
                    p.sale_start_date,
                    p.categories,
                    gpo.position as global_position
                FROM products p
                LEFT JOIN global_product_order gpo ON p.sku = gpo.sku
                ORDER BY 
                    CASE WHEN gpo.position IS NOT NULL THEN 1 ELSE 2 END,
                    gpo.position,
                    p.sku
            ''')
            products = cursor.fetchall()
            
        # Создаем CSV в памяти
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        
        # Заголовки
        writer.writerow([
            'sku', 'name', 'price', 'oldprice', 'discount', 'gender', 
            'image_url', 'url', 'sessions', 'product_views', 'cart_additions',
            'checkout_starts', 'orders_gross', 'orders_net', 'revenue_vat',
            'revenue_net', 'sale_start_date', 'categories', 'global_position'
        ])
        
        # Данные
        for product in products:
            writer.writerow([
                product['sku'],
                product['name'],
                product['price'],
                product['oldprice'],
                product['discount'],
                product['gender'],
                product['image_url'],
                product['url'],
                product['sessions'],
                product['product_views'],
                product['cart_additions'],
                product['checkout_starts'],
                product['orders_gross'],
                product['orders_net'],
                product['revenue_vat'],
                product['revenue_net'],
                product['sale_start_date'],
                product['categories'],
                product['global_position'] if product['global_position'] is not None else ''
            ])
            
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='all_products_export.csv'
        )
    except Exception as e:
        return jsonify({"error": f"Ошибка при экспорте всех товаров: {str(e)}"}), 500 