import sqlite3
import json

def recalculate_metrics():
    conn = sqlite3.connect('merchandise.db')
    cursor = conn.cursor()
    
    try:
        # Получаем максимальные значения для нормализации
        cursor.execute('''
            SELECT 
                MAX(product_views) as max_views,
                MAX(orders_net) as max_orders,
                MAX(add_to_cart) as max_cart
            FROM product
            WHERE product_views > 0  -- Учитываем только товары с просмотрами
        ''')
        max_values = cursor.fetchone()
        max_views = max_values[0] or 1  # Избегаем деления на 0
        max_orders = max_values[1] or 1
        max_cart = max_values[2] or 1
        
        # Обновляем метрики
        cursor.execute('''
            UPDATE product 
            SET 
                views = product_views,
                conversions = CASE 
                    WHEN product_views > 0 THEN MIN(CAST(orders_net AS FLOAT) / product_views * 100, 100)
                    ELSE 0 
                END,
                view_to_cart = CASE 
                    WHEN product_views > 0 THEN MIN(CAST(add_to_cart AS FLOAT) / product_views * 100, 100)
                    ELSE 0 
                END,
                score = (
                    -- Нормализованные просмотры (0-0.3)
                    (CAST(product_views AS FLOAT) / ?) * 0.3 +
                    -- Конверсия просмотр-в-корзину (0-0.3)
                    MIN(CAST(add_to_cart AS FLOAT) / CASE WHEN product_views > 0 THEN product_views ELSE 1 END, 1) * 0.3 +
                    -- Конверсия в покупку (0-0.3)
                    MIN(CAST(orders_net AS FLOAT) / CASE WHEN product_views > 0 THEN product_views ELSE 1 END, 1) * 0.3 +
                    -- Наличие размеров (0 или 0.1)
                    CASE WHEN json_array_length(COALESCE(sizes_available, '[]')) > 0 THEN 0.1 ELSE 0 END
                )
            WHERE product_views > 0  -- Обновляем только товары с просмотрами
        ''', (max_views,))
        
        conn.commit()
        
        # Выводим статистику
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                AVG(views) as avg_views,
                AVG(conversions) as avg_conversion,
                AVG(view_to_cart) as avg_view_to_cart,
                AVG(score) as avg_score,
                MAX(score) as max_score
            FROM product
            WHERE views > 0
        ''')
        stats = cursor.fetchone()
        
        print("\nСтатистика после пересчета:")
        print(f"Всего товаров: {stats[0]}")
        print(f"Среднее количество просмотров: {stats[1]:.2f}")
        print(f"Средняя конверсия в покупку: {stats[2]:.2f}%")
        print(f"Средняя конверсия в корзину: {stats[3]:.2f}%")
        print(f"Средний скор: {stats[4]:.3f}")
        print(f"Максимальный скор: {stats[5]:.3f}")
        
        # Выводим топ-5 товаров по скору
        cursor.execute('''
            SELECT 
                article,
                views,
                view_to_cart,
                conversions,
                score,
                add_to_cart,
                orders_net
            FROM product
            WHERE views > 0
            ORDER BY score DESC
            LIMIT 5
        ''')
        
        print("\nТоп-5 товаров по скору:")
        print("Артикул | Просмотры | Корзина | Конв. в корзину | Покупки | Конв. в покупку | Скор")
        print("-" * 90)
        for row in cursor.fetchall():
            print(f"{row[0]} | {row[1]} | {row[5]} | {row[2]:.2f}% | {row[6]} | {row[3]:.2f}% | {row[4]:.3f}")
        
    except Exception as e:
        print(f"Ошибка при пересчете метрик: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    recalculate_metrics() 