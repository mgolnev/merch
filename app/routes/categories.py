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
        category_id = InputValidator.validate_integer(
            data.get('category_id'),
            'category_id',
            min_value=1
        )
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE product_categories 
                SET position = NULL 
                WHERE category_id = ?
            ''', (category_id,))
            conn.commit()
            
        return jsonify({"status": "success"})
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Ошибка при сбросе ручных позиций: {str(e)}"}), 500

@categories_bp.route('/api/export_category/<int:category_id>')
def export_category(category_id):
    """API для экспорта категории в CSV формат (только sku, category_id, position)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name 
                FROM feed_categories 
                WHERE id = ? AND is_active = 1
            """, (category_id,))
            category = cursor.fetchone()
            if not category:
                return jsonify({"error": "Категория не найдена"}), 404
            # Получаем только нужные поля
            cursor.execute("""
                SELECT 
                    p.sku,
                    pc.category_id,
                    pc.position
                FROM products p
                LEFT JOIN product_categories pc ON p.sku = pc.sku AND pc.category_id = ?
                WHERE pc.category_id = ?
                ORDER BY 
                    CASE WHEN pc.position IS NOT NULL THEN 1 ELSE 2 END,
                    pc.position
            """, (category_id, category_id))
            products = cursor.fetchall()
        # Создаем CSV в памяти
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(['sku', 'category_id', 'position'])
        for product in products:
            writer.writerow([
                product['sku'],
                product['category_id'],
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
                    
                cursor.execute('''
                    UPDATE product_categories 
                    SET position = ? 
                    WHERE sku = ? AND category_id = ?
                ''', (pos, sku, category_id))
                
            conn.commit()
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": f"Ошибка при обновлении порядка: {str(e)}"}), 500 