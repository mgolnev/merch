import sqlite3

def create_multipliers_table():
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect('products.db')
        cursor = conn.cursor()
        
        # Создаем таблицу сезонных множителей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS seasonal_multipliers (
            season TEXT,
            category TEXT,
            multiplier REAL DEFAULT 1.0,
            PRIMARY KEY (season, category)
        )
        ''')
        
        # Добавляем начальные множители для всех категорий и сезонов
        seasons = ['spring', 'summer', 'autumn', 'winter']
        
        # Получаем все уникальные категории из таблицы products
        cursor.execute('SELECT DISTINCT category FROM products')
        categories = cursor.fetchall()
        
        # Добавляем записи для каждой комбинации сезона и категории
        for season in seasons:
            for category in categories:
                cursor.execute('''
                INSERT OR IGNORE INTO seasonal_multipliers (season, category, multiplier)
                VALUES (?, ?, 1.0)
                ''', (season, category[0]))
        
        # Сохраняем изменения
        conn.commit()
        print("Таблица сезонных множителей успешно создана и заполнена!")
        
    except sqlite3.Error as e:
        print(f"Ошибка при создании таблицы множителей: {str(e)}")
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_multipliers_table() 