from flask import Flask, render_template, jsonify, request, send_file, redirect, url_for
import sqlite3
import json
import csv
import io
from typing import List, Tuple, Any, Optional, Dict, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, date

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('merchandise.db')
    cursor = conn.cursor()
    
    # Создаем таблицу products
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        sku TEXT PRIMARY KEY,
        name TEXT,
        price REAL,
        oldprice REAL,
        discount REAL,
        gender TEXT,
        category TEXT,
        image_url TEXT,
        sale_start_date TEXT,
        available BOOLEAN DEFAULT 0
    )
    ''')
    
    # Создаем таблицу product_metrics
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS product_metrics (
        sku TEXT PRIMARY KEY,
        sessions INTEGER DEFAULT 0,
        product_views INTEGER DEFAULT 0,
        cart_additions INTEGER DEFAULT 0,
        checkout_starts INTEGER DEFAULT 0,
        orders_gross INTEGER DEFAULT 0,
        orders_net INTEGER DEFAULT 0,
        FOREIGN KEY (sku) REFERENCES products(sku)
    )
    ''')
    
    # Создаем таблицу weights
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS weights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sessions_weight REAL DEFAULT 1.0,
        views_weight REAL DEFAULT 1.0,
        cart_weight REAL DEFAULT 1.0,
        checkout_weight REAL DEFAULT 1.0,
        orders_gross_weight REAL DEFAULT 1.0,
        orders_net_weight REAL DEFAULT 1.0,
        discount_penalty REAL DEFAULT 0.0,
        dnp_weight REAL DEFAULT 1.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Создаем таблицу category_order
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS category_order (
        sku TEXT,
        category TEXT,
        position INTEGER,
        PRIMARY KEY (sku, category),
        FOREIGN KEY (sku) REFERENCES products(sku)
    )
    ''')
    
    # Добавляем начальные веса, если таблица пуста
    cursor.execute('SELECT COUNT(*) FROM weights')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
        INSERT INTO weights (
            sessions_weight,
            views_weight,
            cart_weight,
            checkout_weight,
            orders_gross_weight,
            orders_net_weight,
            discount_penalty,
            dnp_weight
        ) VALUES (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0)
        ''')
    
    conn.commit()
    conn.close()

# Инициализируем базу данных при запуске
init_db()

class ValidationError(Exception):
    """Кастомное исключение для ошибок валидации"""
    pass

class Gender(Enum):
    """Enum для валидных значений пола"""
    ALL = 'all'
    GIRLS = 'Девочки'
    WOMEN = 'Женщины'
    BOYS = 'Мальчики'
    MEN = 'Мужчины'
    UNISEX = 'Унисекс'
    EMPTY = 'empty'

@dataclass
class ProductFilters:
    """Класс для хранения фильтров продуктов"""
    category: str = 'all'
    page: int = 1
    hide_no_price: bool = True
    search: str = ''
    gender: str = 'all'
    per_page: int = 20
    sku: str = ''

class InputValidator:
    """Класс для валидации входных данных"""
    
    MAX_SEARCH_LENGTH = 100
    ALLOWED_PER_PAGE = [20, 50, 100, 200, 500]
    
    @staticmethod
    def validate_product_filters(args):
        try:
            page = args.get('page', '1')
            if page == 'all':
                page = 1
            else:
                page = int(page)
                if page < 1:
                    raise ValidationError("page должен быть положительным числом")
            
            per_page = int(args.get('per_page', '20'))
            if per_page < 1:
                raise ValidationError("per_page должен быть положительным числом")
            
            hide_no_price = args.get('hide_no_price', 'true').lower() == 'true'
            search = args.get('search', '')
            gender = args.get('gender', 'all')
            category = args.get('category', 'all')
            sku = args.get('sku', '')
            
            return type('Filters', (), {
                'page': page,
                'per_page': per_page,
                'hide_no_price': hide_no_price,
                'search': search,
                'gender': gender,
                'category': category,
                'sku': sku
            })
        except ValueError as e:
            raise ValidationError(f"Ошибка валидации фильтров: {str(e)}")
    
    @staticmethod
    def validate_category_order(data):
        if not isinstance(data, dict):
            raise ValidationError("Данные должны быть объектом")
        
        required_fields = ['sku', 'category_id', 'position']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Отсутствует обязательное поле: {field}")
        
        if not isinstance(data['position'], int) or data['position'] < 0:
            raise ValidationError("position должен быть неотрицательным целым числом")
        
        return data
    
    @staticmethod
    def validate_integer(value: Union[str, int], field_name: str, min_value: Optional[int] = None, max_value: Optional[int] = None, allowed_values: Optional[List[int]] = None) -> int:
        """Валидация целочисленных значений"""
        try:
            # Если значение 'all', возвращаем 1
            if str(value).lower() == 'all':
                return 1
                
            value = int(value)
            if min_value is not None and value < min_value:
                raise ValidationError(f"{field_name} не может быть меньше {min_value}")
            if max_value is not None and value > max_value:
                raise ValidationError(f"{field_name} не может быть больше {max_value}")
            if allowed_values is not None and value not in allowed_values:
                raise ValidationError(f"{field_name} должен быть одним из {allowed_values}")
            return value
        except (TypeError, ValueError):
            raise ValidationError(f"{field_name} должен быть целым числом")
    
    @staticmethod
    def sanitize_string(
        value: Optional[str],
        field_name: str,
        max_length: int,
        required: bool = False
    ) -> str:
        """Санитизация строковых значений"""
        if value is None:
            if required:
                raise ValidationError(f"{field_name} обязательно для заполнения")
            return ''
            
        value = str(value).strip()
        if required and not value:
            raise ValidationError(f"{field_name} не может быть пустым")
            
        if len(value) > max_length:
            raise ValidationError(f"{field_name} не может быть длиннее {max_length} символов")
            
        # Базовая санитизация для предотвращения SQL-инъекций
        value = value.replace("'", "''")
        return value
    
    @staticmethod
    def validate_enum(value: str, field_name: str, enum_class: type) -> str:
        """Валидация значений enum"""
        try:
            return enum_class(value).value
        except ValueError:
            valid_values = [e.value for e in enum_class]
            raise ValidationError(f"{field_name} должен быть одним из {valid_values}")

    @staticmethod
    def validate_category_name(name: str) -> str:
        """Валидация имени категории"""
        if not name:
            raise ValidationError("Имя категории не может быть пустым")
        
        name = name.strip()
        if len(name) > 100:
            raise ValidationError("Имя категории не может быть длиннее 100 символов")
        
        return name

class QueryBuilder:
    """Класс для построения SQL-запросов"""
    def __init__(self):
        self.conditions = []
        self.params = []
    
    def add_condition(self, condition: str, param: Any = None):
        """Добавление условия в WHERE"""
        self.conditions.append(condition)
        if param is not None:
            self.params.append(param)
    
    def build(self) -> Tuple[str, List[Any]]:
        """Построение WHERE части запроса"""
        if not self.conditions:
            return "1=1", self.params
        return " AND ".join(self.conditions), self.params

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
        
        # Применяем вес DNP для товаров с датой начала продаж
        sale_start_date = product.get('sale_start_date')
        if sale_start_date and isinstance(sale_start_date, str):
            try:
                # Пробуем сначала формат DD.MM.YYYY
                sale_start = datetime.strptime(sale_start_date, '%d.%m.%Y').date()
            except ValueError:
                try:
                    # Если не получилось, пробуем формат YYYY-MM-DD
                    sale_start = datetime.strptime(sale_start_date, '%Y-%m-%d').date()
                except ValueError:
                    # Если оба формата не подошли, пропускаем
                    sale_start = None
            
            if sale_start:
                today = date.today()
                # Если дата начала продаж в прошлом, применяем штраф
                if sale_start < today:
                    days_since_sale = (today - sale_start).days
                    # Штраф увеличивается с течением времени, но не более 50%
                    penalty = min(0.5, days_since_sale / 365)  # Максимальный штраф 50%
                    score *= (1 - penalty * weights['dnp_weight'])
                # Если дата начала продаж в будущем, но товар уже продается - даем поощрение
                elif sale_start > today and product.get('available', False):
                    days_until_sale = (sale_start - today).days
                    # Поощрение увеличивается с удаленностью от официальной даты
                    bonus = min(0.5, days_until_sale / 365)  # Максимальное поощрение 50%
                    score *= (1 + bonus * weights['dnp_weight'])
        
        # Применяем штраф за скидку
        if product.get('discount') and weights['discount_penalty']:
            # Штраф увеличивается с ростом скидки и веса штрафа, но не более 50%
            penalty = min(0.5, (product['discount'] / 100) * weights['discount_penalty'])
            score *= (1 - penalty)
    
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
            'discount_penalty': weights['discount_penalty'],
            'dnp_weight': weights['dnp_weight']
        }
    else:
        weights_dict = {
            'sessions_weight': 1.0,
            'views_weight': 1.0,
            'cart_weight': 1.0,
            'checkout_weight': 1.0,
            'orders_gross_weight': 1.0,
            'orders_net_weight': 1.0,
            'discount_penalty': 0.0,
            'dnp_weight': 1.0
        }
    
    return render_template('weights.html', weights=weights_dict)

@app.route('/api/products')
def get_products():
    """Получение списка товаров с фильтрацией"""
    try:
        # Получаем параметры фильтрации
        category = request.args.get('category', 'all')
        page = request.args.get('page', '1')
        hide_no_price = request.args.get('hide_no_price', 'true').lower() == 'true'
        search = request.args.get('search', '')
        gender = request.args.get('gender', 'all')
        per_page = int(request.args.get('per_page', 20))
        
        # Валидация параметров
        if page == 'all':
            page = 1
        elif not page.isdigit():
            raise ValueError("page должен быть целым числом")
        else:
            page = int(page)
        
        # Подключаемся к базе данных
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем текущие веса
        cursor.execute('SELECT * FROM weights ORDER BY id DESC LIMIT 1')
        weights = cursor.fetchone()
        
        # --- Считаем total_count отдельным простым запросом ---
        count_query = '''
            SELECT COUNT(DISTINCT p.sku) 
            FROM products p
            LEFT JOIN product_categories pc ON p.sku = pc.sku
            LEFT JOIN feed_categories fc ON pc.category_id = fc.id
            WHERE 1=1
        '''
        count_params = []
        if category != 'all':
            count_query += ' AND fc.category_number = ?'
            count_params.append(int(category))
        if hide_no_price:
            count_query += ' AND p.price > 0'
        if search:
            count_query += ' AND (p.sku LIKE ? OR p.name LIKE ?)'
            search_param = f'%{search}%'
            count_params.extend([search_param, search_param])
        if gender != 'all':
            count_query += ' AND p.gender = ?'
            count_params.append(gender)
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]
        
        # Формируем основной запрос с сортировкой и пагинацией
        query = '''
            WITH ProductScores AS (
                SELECT 
                    p.sku,
                    p.name,
                    p.price,
                    p.oldprice,
                    p.discount,
                    p.gender,
                    p.image_url,
                    p.sale_start_date,
                    p.available,
                    COALESCE(pm.sessions, 0) as sessions,
                    COALESCE(pm.product_views, 0) as product_views,
                    COALESCE(pm.cart_additions, 0) as cart_additions,
                    COALESCE(pm.checkout_starts, 0) as checkout_starts,
                    COALESCE(pm.orders_gross, 0) as orders_gross,
                    COALESCE(pm.orders_net, 0) as orders_net,
                    CASE 
                        WHEN pc.position IS NOT NULL THEN 1
                        ELSE 2
                    END as has_position,
                    COALESCE(pc.position, 999999) as position,
                    GROUP_CONCAT(DISTINCT fc.name) as category_names,
                    GROUP_CONCAT(DISTINCT fc.category_number) as category_numbers,
                    p.url
                FROM products p 
                LEFT JOIN product_metrics pm ON p.sku = pm.sku 
                LEFT JOIN product_categories pc ON p.sku = pc.sku
                LEFT JOIN feed_categories fc ON pc.category_id = fc.id
                WHERE 1=1
        '''
        params = []
        if category != 'all':
            query += ' AND fc.category_number = ?'
            params.append(int(category))
        if hide_no_price:
            query += ' AND p.price > 0'
        if search:
            query += ' AND (p.sku LIKE ? OR p.name LIKE ?)'
            search_param = f'%{search}%'
            params.extend([search_param, search_param])
        if gender != 'all':
            query += ' AND p.gender = ?'
            params.append(gender)
        query += '''
            GROUP BY p.sku
            )
            SELECT * FROM ProductScores
        '''
        
        # --- Сортировка ---
        if category == 'all':
            # Без сортировки и лимита в SQL
            cursor.execute(query, params)
            products = cursor.fetchall()
            result = []
            for product in products:
                product_dict = {
                    'sku': product['sku'],
                    'name': product['name'],
                    'price': product['price'],
                    'oldprice': product['oldprice'],
                    'discount': product['discount'],
                    'gender': product['gender'],
                    'image_url': product['image_url'],
                    'sale_start_date': product['sale_start_date'],
                    'available': bool(product['available']),
                    'sessions': product['sessions'],
                    'product_views': product['product_views'],
                    'cart_additions': product['cart_additions'],
                    'checkout_starts': product['checkout_starts'],
                    'orders_gross': product['orders_gross'],
                    'orders_net': product['orders_net'],
                    'categories': product['category_names'].split(',') if product['category_names'] else [],
                    'category_numbers': [int(x) for x in product['category_numbers'].split(',')] if product['category_numbers'] else [],
                    'url': product['url']
                }
                product_dict['score'] = calculate_score(product_dict, weights)
                result.append(product_dict)
            result.sort(key=lambda x: x['score'], reverse=True)
            start = (page - 1) * per_page
            end = start + per_page
            result = result[start:end]
        else:
            # Получаем все товары для выбранной категории (без LIMIT)
            cursor.execute(query, params)
            products = cursor.fetchall()
            with_position = []
            without_position = []
            for product in products:
                product_dict = {
                    'sku': product['sku'],
                    'name': product['name'],
                    'price': product['price'],
                    'oldprice': product['oldprice'],
                    'discount': product['discount'],
                    'gender': product['gender'],
                    'image_url': product['image_url'],
                    'sale_start_date': product['sale_start_date'],
                    'available': bool(product['available']),
                    'sessions': product['sessions'],
                    'product_views': product['product_views'],
                    'cart_additions': product['cart_additions'],
                    'checkout_starts': product['checkout_starts'],
                    'orders_gross': product['orders_gross'],
                    'orders_net': product['orders_net'],
                    'categories': product['category_names'].split(',') if product['category_names'] else [],
                    'category_numbers': [int(x) for x in product['category_numbers'].split(',')] if product['category_numbers'] else [],
                    'has_position': product['has_position'],
                    'position': product['position'],
                    'url': product['url']
                }
                product_dict['score'] = calculate_score(product_dict, weights)
                if product['has_position'] == 1:
                    with_position.append(product_dict)
                else:
                    without_position.append(product_dict)
            # Сортируем с позицией по position, без позиции — по скору
            with_position.sort(key=lambda x: (x['position'] if x['position'] is not None else 999999))
            without_position.sort(key=lambda x: x['score'], reverse=True)
            result = with_position + without_position
            start = (page - 1) * per_page
            end = start + per_page
            result = result[start:end]
        
        total_pages = (total_count + per_page - 1) // per_page
        
        return jsonify({
            'products': result,
            'page': page,
            'total_pages': total_pages,
            'total_count': total_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories')
def get_categories():
    """Получение списка всех категорий"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Получаем id, category_number и name всех категорий
        cursor.execute('''
            SELECT id, category_number, name 
            FROM feed_categories 
            WHERE is_active = 1
            ORDER BY name
        ''')
        categories_list = [{'id': row[0], 'category_number': row[1], 'name': row[2]} for row in cursor.fetchall()]
        conn.close()
        return jsonify(categories_list)
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/<int:category_number>')
def get_category(category_number):
    conn = get_db_connection()
    try:
        # Получаем информацию о категории
        category = conn.execute('''
            SELECT 
                c.id,
                c.category_number,
                c.name,
                c.parent_id,
                c.is_active,
                c.created_at,
                p.name as parent_name,
                p.category_number as parent_number,
                COUNT(pc.sku) as product_count
            FROM feed_categories c
            LEFT JOIN feed_categories p ON c.parent_id = p.id
            LEFT JOIN product_categories pc ON c.id = pc.category_id
            WHERE c.category_number = ?
            GROUP BY c.id
        ''', (category_number,)).fetchone()
        
        if not category:
            return jsonify({'error': 'Категория не найдена'}), 404
        
        # Получаем дочерние категории
        children = conn.execute('''
            SELECT 
                id,
                category_number,
                name,
                is_active,
                (SELECT COUNT(*) FROM product_categories WHERE category_id = feed_categories.id) as product_count
            FROM feed_categories
            WHERE parent_id = ?
            ORDER BY category_number
        ''', (category['id'],)).fetchall()
        
        return jsonify({
            'id': category['id'],
            'category_number': category['category_number'],
            'name': category['name'],
            'is_active': bool(category['is_active']),
            'parent': {
                'id': category['parent_id'],
                'name': category['parent_name'],
                'category_number': category['parent_number']
            } if category['parent_id'] else None,
            'product_count': category['product_count'],
            'children': [{
                'id': child['id'],
                'category_number': child['category_number'],
                'name': child['name'],
                'is_active': bool(child['is_active']),
                'product_count': child['product_count']
            } for child in children]
        })
    finally:
        conn.close()

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
                discount_penalty,
                dnp_weight
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            float(weights.get('sessions_weight', 1.0)),
            float(weights.get('views_weight', 1.0)),
            float(weights.get('cart_weight', 1.0)),
            float(weights.get('checkout_weight', 1.0)),
            float(weights.get('orders_gross_weight', 1.0)),
            float(weights.get('orders_net_weight', 1.0)),
            float(weights.get('discount_penalty', 0.0)),
            float(weights.get('dnp_weight', 1.0))
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
    try:
        # Валидация входных данных
        data = request.json
        sku = data.get('sku')
        category_number = data.get('category_number')
        position = data.get('position')
        
        if not all([sku, category_number, position]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        try:
            # Получаем ID категории по номеру
            category = conn.execute(
                'SELECT id FROM feed_categories WHERE category_number = ?',
                (category_number,)
            ).fetchone()
            
            if not category:
                return jsonify({'error': 'Категория не найдена'}), 404
            
            # Проверяем существование товара
            product = conn.execute(
                'SELECT sku FROM products WHERE sku = ?',
                (sku,)
            ).fetchone()
            
            if not product:
                return jsonify({'error': 'Товар не найден'}), 404
            
            # Обновляем позицию товара в категории
            conn.execute('''
                INSERT OR REPLACE INTO product_categories (sku, category_id, position)
                VALUES (?, ?, ?)
            ''', (
                sku,
                category['id'],
                position
            ))
            
            conn.commit()
            return jsonify({'status': 'success'})
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset_weights', methods=['POST'])
def reset_weights():
    conn = get_db_connection()
    try:
        # Получаем текущие веса
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM weights ORDER BY id DESC LIMIT 1')
        current_weights = cursor.fetchone()
        
        # Проверяем, изменились ли веса
        if current_weights and all(current_weights[field] == value for field, value in {
            'sessions_weight': 1.0,
            'views_weight': 1.0,
            'cart_weight': 1.0,
            'checkout_weight': 1.0,
            'orders_gross_weight': 1.0,
            'orders_net_weight': 1.0,
            'discount_penalty': 0.0,
            'dnp_weight': 1.0
        }.items()):
            return jsonify({'status': 'success', 'message': 'Веса уже сброшены'})
        
        # Сбрасываем только веса
        conn.execute('''
            INSERT INTO weights (
                sessions_weight,
                views_weight,
                cart_weight,
                checkout_weight,
                orders_gross_weight,
                orders_net_weight,
                discount_penalty,
                dnp_weight
            ) VALUES (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0)
        ''')
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Веса успешно сброшены'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/reset_category_order', methods=['POST'])
def reset_category_order():
    data = request.json
    category_number = data.get('category_number')
    if not category_number:
        return jsonify({'status': 'error', 'message': 'Не указан номер категории'}), 400
    conn = get_db_connection()
    try:
        # Получаем id категории по номеру
        category = conn.execute('SELECT id FROM feed_categories WHERE category_number = ?', (category_number,)).fetchone()
        if not category:
            return jsonify({'status': 'error', 'message': 'Категория не найдена'}), 404
        category_id = category['id']
        # Обнуляем позиции в product_categories для этой категории, но сохраняем связи
        conn.execute('UPDATE product_categories SET position = NULL WHERE category_id = ?', (category_id,))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/export_category/<int:category_number>')
def export_category(category_number):
    conn = get_db_connection()
    try:
        # Получаем ID и номер категории
        category = conn.execute(
            'SELECT id, name, category_number FROM feed_categories WHERE category_number = ?',
            (category_number,)
        ).fetchone()
        
        if not category:
            return jsonify({'error': 'Категория не найдена'}), 404
        
        # Получаем все товары из категории (даже без позиции)
        query = """
            SELECT 
                p.sku,
                ? as category_id,  -- подставляем номер категории
                pc.position
            FROM products p 
            LEFT JOIN product_categories pc ON p.sku = pc.sku AND pc.category_id = ?
            WHERE pc.category_id = ? OR (
                pc.category_id IS NULL AND EXISTS (
                    SELECT 1 FROM product_categories pc2 WHERE pc2.sku = p.sku AND pc2.category_id = ?
                )
            )
            ORDER BY 
                CASE WHEN pc.position IS NOT NULL THEN 1 ELSE 2 END,
                pc.position
        """
        products = conn.execute(query, (category['category_number'], category['id'], category['id'], category['id'])).fetchall()
        
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
            download_name=f'{category["name"]}_positions.csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/import_category/<int:category_number>', methods=['POST'])
def import_category(category_number):
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
        
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Поддерживаются только CSV файлы'}), 400
    
    conn = get_db_connection()
    try:
        # Получаем ID категории
        category = conn.execute(
            'SELECT id FROM feed_categories WHERE category_number = ?',
            (category_number,)
        ).fetchone()
        
        if not category:
            return jsonify({'error': 'Категория не найдена'}), 404
        
        # Читаем CSV файл
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        # Подготавливаем данные для вставки
        positions = []
        for row in csv_input:
            try:
                sku = row['Артикул']
                position = int(row['Позиция в категории'])
                if position < 0:
                    raise ValueError("Позиция не может быть отрицательной")
                positions.append((sku, category['id'], position))
            except (KeyError, ValueError) as e:
                return jsonify({'error': f'Ошибка в строке {csv_input.line_num}: {str(e)}'}), 400
        
        # Проверяем существование всех SKU
        skus = [p[0] for p in positions]
        existing_skus = set(row[0] for row in conn.execute(
            'SELECT sku FROM products WHERE sku IN ({})'.format(','.join('?' * len(skus))),
            skus
        ).fetchall())
        
        missing_skus = set(skus) - existing_skus
        if missing_skus:
            return jsonify({
                'error': 'Следующие артикулы не найдены в базе: ' + ', '.join(missing_skus)
            }), 400
        
        # Обновляем позиции
        conn.executemany(
            'INSERT OR REPLACE INTO product_categories (sku, category_id, position) VALUES (?, ?, ?)',
            positions
        )
        conn.commit()
        
        return jsonify({'message': 'Позиции успешно обновлены'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/categories', methods=['POST'])
def create_or_update_category():
    try:
        data = request.json
        category_number = InputValidator.validate_integer(
            data.get('category_number'),
            'category_number',
            min_value=1
        )
        name = InputValidator.validate_category_name(data.get('name'))
        parent_id = data.get('parent_id')
        is_active = bool(data.get('is_active', True))
        
        conn = get_db_connection()
        try:
            # Проверяем существование родительской категории
            if parent_id:
                parent = conn.execute(
                    'SELECT id FROM feed_categories WHERE id = ?',
                    (parent_id,)
                ).fetchone()
                if not parent:
                    return jsonify({'error': 'Родительская категория не найдена'}), 404
            
            # Проверяем уникальность номера категории
            existing = conn.execute(
                'SELECT id FROM feed_categories WHERE category_number = ?',
                (category_number,)
            ).fetchone()
            
            if existing:
                # Обновляем существующую категорию
                conn.execute('''
                    UPDATE feed_categories 
                    SET name = ?, parent_id = ?, is_active = ?
                    WHERE category_number = ?
                ''', (name, parent_id, is_active, category_number))
            else:
                # Создаем новую категорию
                conn.execute('''
                    INSERT INTO feed_categories (category_number, name, parent_id, is_active)
                    VALUES (?, ?, ?, ?)
                ''', (category_number, name, parent_id, is_active))
            
            conn.commit()
            return jsonify({'status': 'success'})
        finally:
            conn.close()
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/category_order_bulk', methods=['POST'])
def update_category_order_bulk():
    try:
        data = request.json
        if not isinstance(data, list):
            return jsonify({'error': 'Ожидался список объектов'}), 400
        if not data:
            return jsonify({'error': 'Пустой список'}), 400
        # Проверяем, что у всех есть нужные поля
        for item in data:
            if not all(k in item for k in ('sku', 'category_number', 'position')):
                return jsonify({'error': 'Каждый объект должен содержать sku, category_number, position'}), 400
        category_number = data[0]['category_number']
        conn = get_db_connection()
        try:
            # Получаем id категории по номеру
            category = conn.execute('SELECT id FROM feed_categories WHERE category_number = ?', (category_number,)).fetchone()
            if not category:
                return jsonify({'error': 'Категория не найдена'}), 404
            category_id = category['id']
            if data:  # Только если массив не пустой
                # Удаляю все старые связи для этой категории
                conn.execute('DELETE FROM product_categories WHERE category_id = ?', (category_id,))
                # Проверяем существование всех sku
                skus = [item['sku'] for item in data]
                existing_skus = set(row[0] for row in conn.execute(
                    'SELECT sku FROM products WHERE sku IN ({})'.format(','.join('?' * len(skus))),
                    skus
                ).fetchall())
                missing_skus = set(skus) - existing_skus
                if missing_skus:
                    return jsonify({'error': 'Следующие артикулы не найдены в базе: ' + ', '.join(missing_skus)}), 400
                # Обновляем позиции
                positions = [(item['sku'], category_id, item['position']) for item in data]
                conn.executemany(
                    'INSERT OR REPLACE INTO product_categories (sku, category_id, position) VALUES (?, ?, ?)',
                    positions
                )
            conn.commit()
            return jsonify({'status': 'success'})
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({'error': str(error)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=3001) 