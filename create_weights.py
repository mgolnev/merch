import sqlite3

def create_weights_table():
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect('products.db')
        cursor = conn.cursor()
        
        # Создаем таблицу весов категорий
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS category_weights (
            category TEXT PRIMARY KEY,
            views_weight REAL DEFAULT 0.3,
            cart_weight REAL DEFAULT 0.3,
            orders_weight REAL DEFAULT 0.4
        )
        ''')
        
        # Добавляем начальные веса для всех категорий
        cursor.execute('''
        INSERT OR IGNORE INTO category_weights (category, views_weight, cart_weight, orders_weight)
        SELECT DISTINCT category, 0.3, 0.3, 0.4
        FROM products
        ''')
        
        # Сохраняем изменения
        conn.commit()
        print("Таблица весов категорий успешно создана и заполнена!")
        
    except sqlite3.Error as e:
        print(f"Ошибка при создании таблицы весов: {str(e)}")
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_weights_table() 