import sqlite3

def get_table_info():
    conn = sqlite3.connect('merchandise.db')
    cursor = conn.cursor()
    
    # Получаем информацию о колонках таблицы
    cursor.execute("PRAGMA table_info(product)")
    columns = cursor.fetchall()
    
    print("\nСтруктура таблицы product:")
    for col in columns:
        print(f"Колонка: {col[1]}, Тип: {col[2]}")
    
    # Получаем пример данных
    cursor.execute("SELECT * FROM product LIMIT 1")
    row = cursor.fetchone()
    if row:
        print("\nПример данных:")
        for i, col in enumerate(columns):
            print(f"{col[1]}: {row[i]}")
    
    conn.close()

if __name__ == '__main__':
    get_table_info() 