from app.database.connection import get_db_connection
from typing import Dict, Any, Tuple

def get_current_weights() -> Dict[str, Any]:
    """Получение текущих весов"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM weights ORDER BY id DESC LIMIT 1")
        weights = dict(cursor.fetchone())
        return weights

def update_weights(weight_data: Dict[str, float]) -> Tuple[bool, str]:
    """Обновление весов"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Подготовка запроса на вставку новых весов
            query = """
            INSERT INTO weights (
                sessions_weight,
                views_weight,
                cart_weight,
                checkout_weight,
                orders_gross_weight,
                orders_net_weight,
                discount_penalty,
                sale_start_weight
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(query, (
                weight_data.get('sessions_weight', 1.0),
                weight_data.get('views_weight', 1.0),
                weight_data.get('cart_weight', 1.0),
                weight_data.get('checkout_weight', 1.0),
                weight_data.get('orders_gross_weight', 1.0),
                weight_data.get('orders_net_weight', 1.0),
                weight_data.get('discount_penalty', 0.0),
                weight_data.get('sale_start_weight', 1.0)
            ))
            
            conn.commit()
            return True, "Веса успешно обновлены"
    except Exception as e:
        return False, f"Ошибка при обновлении весов: {str(e)}"

def reset_weights() -> Tuple[bool, str]:
    """Сброс весов до значений по умолчанию"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Вставка весов по умолчанию
            query = """
            INSERT INTO weights (
                sessions_weight,
                views_weight,
                cart_weight,
                checkout_weight,
                orders_gross_weight,
                orders_net_weight,
                discount_penalty,
                sale_start_weight
            ) VALUES (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0)
            """
            
            cursor.execute(query)
            conn.commit()
            return True, "Веса успешно сброшены до значений по умолчанию"
    except Exception as e:
        return False, f"Ошибка при сбросе весов: {str(e)}" 