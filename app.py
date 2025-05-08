from flask import Flask, render_template, jsonify, request, send_file, redirect, url_for
import sqlite3
import json
import csv
import io
from typing import List, Tuple, Any, Optional, Dict, Union
from dataclasses import dataclass
from enum import Enum

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
    def validate_product_filters(args: Dict[str, Any]) -> ProductFilters:
        """Валидация фильтров для продуктов"""
        try:
            # Валидация page
            page = InputValidator.validate_integer(
                args.get('page', 1),
                'page',
                min_value=1,
                max_value=1000
            )
            
            # Валидация per_page
            per_page = InputValidator.validate_integer(
                args.get('per_page', 20),
                'per_page',
                allowed_values=InputValidator.ALLOWED_PER_PAGE
            )
            
            # Валидация hide_no_price
            hide_no_price = str(args.get('hide_no_price', 'true')).lower() == 'true'
            
            # Валидация search
            search = InputValidator.sanitize_string(
                args.get('search', ''),
                'search',
                max_length=InputValidator.MAX_SEARCH_LENGTH
            )
            
            # Валидация gender
            gender = InputValidator.validate_enum(
                args.get('gender', 'all'),
                'gender',
                Gender
            )
            
            # Валидация category
            category = InputValidator.sanitize_string(
                args.get('category', 'all'),
                'category',
                max_length=100
            )
            
            # Валидация sku
            sku = InputValidator.sanitize_string(
                args.get('sku', ''),
                'sku',
                max_length=50
            )
            
            return ProductFilters(
                category=category,
                page=page,
                hide_no_price=hide_no_price,
                search=search,
                gender=gender,
                per_page=per_page,
                sku=sku
            )
            
        except ValidationError as e:
            raise ValidationError(f"Ошибка валидации фильтров: {str(e)}")
    
    @staticmethod
    def validate_category_order(data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация данных для обновления порядка категорий"""
        try:
            if not isinstance(data, dict):
                raise ValidationError("Неверный формат данных")
                
            required_fields = ['sku', 'category', 'position']
            for field in required_fields:
                if field not in data:
                    raise ValidationError(f"Отсутствует обязательное поле: {field}")
            
            # Валидация SKU
            sku = InputValidator.sanitize_string(data['sku'], 'sku', max_length=50)
            
            # Валидация category
            category = InputValidator.sanitize_string(data['category'], 'category', max_length=100)
            
            # Валидация position
            position = InputValidator.validate_integer(data['position'], 'position', min_value=1)
            
            return {
                'sku': sku,
                'category': category,
                'position': position
            }
            
        except ValidationError as e:
            raise ValidationError(f"Ошибка валидации order данных: {str(e)}")
    
    @staticmethod
    def validate_integer(
        value: Union[str, int],
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        allowed_values: Optional[List[int]] = None
    ) -> int:
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
        if sale_start_date is None:
            sale_start_date = '01.01.2000'  # Используем дату по умолчанию
            
        from datetime import datetime, date
        today = date.today()
        try:
            # Пробуем сначала формат DD.MM.YYYY
            sale_start = datetime.strptime(sale_start_date, '%d.%m.%Y').date()
        except ValueError:
            try:
                # Если не получилось, пробуем формат YYYY-MM-DD
                sale_start = datetime.strptime(sale_start_date, '%Y-%m-%d').date()
            except ValueError:
                # Если оба формата не подошли, используем дату по умолчанию
                sale_start = datetime.strptime('01.01.2000', '%d.%m.%Y').date()
        
        # Если дата начала продаж в прошлом, применяем штраф
        if sale_start < today:
            days_since_sale = (today - sale_start).days
            # Штраф увеличивается с течением времени
            penalty = min(1.0, days_since_sale / 365)  # Максимальный штраф через год
            score *= (1 - penalty * weights['dnp_weight'])
        # Если дата начала продаж в будущем, но товар уже продается - даем поощрение
        elif sale_start > today and product.get('available', False):
            days_until_sale = (sale_start - today).days
            # Поощрение увеличивается с удаленностью от официальной даты
            bonus = min(0.5, days_until_sale / 365)  # Максимальное поощрение 50%
            score *= (1 + bonus * weights['dnp_weight'])
        
        # Применяем штраф за скидку
        if product.get('discount') and weights['discount_penalty']:
            # Штраф увеличивается с ростом скидки и веса штрафа
            penalty = (product['discount'] / 100) * weights['discount_penalty']
            # Ограничиваем штраф, чтобы скор не становился отрицательным
            score *= max(0.01, 1 - penalty)
    
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
    try:
        # Валидация входных данных
        filters = InputValidator.validate_product_filters(request.args)
        
        conn = get_db_connection()
        try:
            query_builder = QueryBuilder()
            
            # Используем валидированные данные
            if filters.category != 'all':
                query_builder.add_condition("p.category = ?", filters.category)
            
            if filters.hide_no_price:
                query_builder.add_condition("p.price > 0")
            
            if filters.search:
                query_builder.add_condition("p.sku LIKE ?", f"%{filters.search}%")
            
            if filters.gender != 'all':
                if filters.gender == 'empty':
                    query_builder.add_condition("(p.gender IS NULL OR p.gender = '')")
                else:
                    query_builder.add_condition("p.gender = ?", filters.gender)
            
            if filters.sku:
                query_builder.add_condition("p.sku = ?", filters.sku)
            
            where_clause, params = query_builder.build()
            
            # Базовый запрос с WITH для рейтингов категорий
            base_query = f"""
                WITH CategoryRanks AS (
                    SELECT 
                        p.sku,
                        p.category,
                        RANK() OVER (
                            PARTITION BY p.category 
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
                    LEFT JOIN category_order co ON p.sku = co.sku AND co.category = p.category
                )
                SELECT 
                    p.sku,
                    p.name,
                    p.price,
                    p.oldprice,
                    p.discount,
                    p.gender,
                    p.category,
                    p.image_url,
                    p.sale_start_date,
                    p.available,
                    pm.sessions,
                    pm.product_views,
                    pm.cart_additions,
                    pm.checkout_starts,
                    pm.orders_gross,
                    pm.orders_net,
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
            
            products = conn.execute(base_query, params).fetchall()
            
            # Получаем веса для расчета скоринга через параметризованный запрос
            weights = conn.execute("SELECT * FROM weights ORDER BY id DESC LIMIT 1").fetchone()
            
            products_list = []
            for product in products:
                product_dict = dict(product)
                product_dict['score'] = calculate_score(product_dict, weights)
                products_list.append(product_dict)
            
            # Сортировка без SQL-инъекций (перенесена в Python)
            if filters.category != 'all':
                products_list.sort(
                    key=lambda x: (
                        0 if x['category_position'] is not None else 1,
                        x['category_position'] if x['category_position'] is not None else float('inf'),
                        -x['score']
                    )
                )
            else:
                products_list.sort(key=lambda x: -x['score'])
            
            # Если page=all, возвращаем только информацию о страницах
            if request.args.get('page') == 'all':
                total_products = len(products_list)
                total_pages = (total_products + filters.per_page - 1) // filters.per_page
                return jsonify({
                    'products': [],
                    'total_pages': total_pages,
                    'current_page': 1,
                    'total_products': total_products
                })
            
            # Иначе применяем пагинацию
            offset = (filters.page - 1) * filters.per_page
            total_products = len(products_list)
            total_pages = (total_products + filters.per_page - 1) // filters.per_page
            paginated_products = products_list[offset:offset + filters.per_page]
            
            return jsonify({
                'products': paginated_products,
                'total_pages': total_pages,
                'current_page': filters.page,
                'total_products': total_products
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories')
def get_categories():
    conn = get_db_connection()
    try:
        categories = conn.execute(
            'SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != ?',
            ('',)
        ).fetchall()
        return jsonify([dict(category) for category in categories if category['category']])
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
        validated_data = InputValidator.validate_category_order(request.json)
        
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT OR REPLACE INTO category_order (sku, category, position) VALUES (?, ?, ?)',
                (validated_data['sku'], validated_data['category'], validated_data['position'])
            )
            conn.commit()
            return jsonify({'status': 'success'})
        finally:
            conn.close()
            
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
                discount_penalty,
                dnp_weight
            ) VALUES (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0)
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
                    p.category,
                    RANK() OVER (
                        PARTITION BY p.category 
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
                LEFT JOIN category_order co ON p.sku = co.sku AND co.category = p.category
                WHERE p.category = ?
            )
            SELECT 
                p.sku,
                cr.category_position,
                cr.category_rank
            FROM products p 
            LEFT JOIN CategoryRanks cr ON p.sku = cr.sku
            WHERE p.category = ?
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

@app.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({'error': str(error)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=3001) 