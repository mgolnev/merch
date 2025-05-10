from typing import List, Tuple, Any, Optional, Dict, Union
from enum import Enum

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

class ProductFilters:
    """Класс для хранения фильтров продуктов"""
    def __init__(self, 
                 category: str = 'all',
                 page: int = 1,
                 hide_no_price: bool = True,
                 search: str = '',
                 gender: str = 'all',
                 per_page: int = 20,
                 sku: str = ''):
        self.category = category
        self.page = page
        self.hide_no_price = hide_no_price
        self.search = search
        self.gender = gender
        self.per_page = per_page
        self.sku = sku

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
            
            return ProductFilters(
                category=category,
                page=page,
                hide_no_price=hide_no_price,
                search=search,
                gender=gender,
                per_page=per_page,
                sku=sku
            )
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