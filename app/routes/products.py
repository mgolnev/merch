from flask import Blueprint, jsonify, request
from app.services.product_service import get_products
from app.utils.validation import InputValidator, ValidationError

products_bp = Blueprint('products', __name__)

@products_bp.route('/api/products')
def get_products_route():
    """API для получения продуктов с фильтрами и пагинацией"""
    try:
        filters = InputValidator.validate_product_filters(request.args)
        result = get_products(filters)
        return jsonify(result)
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Внутренняя ошибка сервера: {str(e)}"}), 500 