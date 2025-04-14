import sqlite3

def check_database():
    conn = sqlite3.connect('merchandise.db')
    cursor = conn.cursor()

    # Проверка существования всех таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("\nСуществующие таблицы:")
    for table in tables:
        print(f"- {table[0]}")

    # Проверка структуры каждой таблицы
    print("\nСтруктура таблиц:")
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"\n{table_name}:")
        for column in columns:
            print(f"- {column[1]} ({column[2]})")

    # Проверка начальных данных
    print("\nПроверка начальных данных:")
    
    # Проверка весов категорий
    cursor.execute("SELECT * FROM category_weights")
    weights = cursor.fetchall()
    print("\nВеса категорий:")
    for weight in weights:
        print(f"Категория: {weight[0]}")
        print(f"- Просмотры: {weight[1]}")
        print(f"- Корзина: {weight[2]}")
        print(f"- Заказы: {weight[3]}")
        print(f"- Выручка: {weight[4]}")
        print(f"- Скидка: {weight[5]}")

    # Проверка сезонных множителей
    cursor.execute("SELECT * FROM seasonal_multipliers")
    multipliers = cursor.fetchall()
    print("\nСезонные множители:")
    for mult in multipliers:
        print(f"Сезон: {mult[0]}, Категория: {mult[1]}, Множитель: {mult[2]}")

    conn.close()

if __name__ == "__main__":
    check_database() 