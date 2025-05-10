from flask import Blueprint, jsonify, request
from app.services.weights_service import get_current_weights, update_weights, reset_weights
from app.utils.validation import ValidationError

weights_bp = Blueprint('weights', __name__)

@weights_bp.route('/api/weights')
def get_weights():
    """API для получения текущих весов"""
    try:
        current_weights = get_current_weights()
        return jsonify(current_weights)
    except Exception as e:
        return jsonify({"error": f"Ошибка при получении весов: {str(e)}"}), 500

@weights_bp.route('/api/update_weights', methods=['POST'])
def update_weights_route():
    """API для обновления весов"""
    try:
        weight_data = request.get_json()
        
        if not weight_data or not isinstance(weight_data, dict):
            return jsonify({"error": "Необходимо передать данные весов в формате JSON"}), 400
        
        # Валидация входных данных
        for key, value in weight_data.items():
            try:
                weight_data[key] = float(value)
            except (ValueError, TypeError):
                return jsonify({"error": f"Значение {key} должно быть числом"}), 400
        
        success, message = update_weights(weight_data)
        
        if success:
            return jsonify({"message": message})
        else:
            return jsonify({"error": message}), 400
            
    except Exception as e:
        return jsonify({"error": f"Ошибка при обновлении весов: {str(e)}"}), 500

@weights_bp.route('/api/reset_weights', methods=['POST'])
def reset_weights_route():
    """API для сброса весов до значений по умолчанию"""
    try:
        success, message = reset_weights()
        
        if success:
            return jsonify({"message": message})
        else:
            return jsonify({"error": message}), 400
            
    except Exception as e:
        return jsonify({"error": f"Ошибка при сбросе весов: {str(e)}"}), 500 