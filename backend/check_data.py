import sqlite3
import pandas as pd

# Подключение к базе данных
conn = sqlite3.connect('merchandise.db')

# Чтение данных из таблицы product
query = "SELECT * FROM product"
df = pd.read_sql_query(query, conn)

# Вывод первых 5 строк
print("\nПервые 5 записей в таблице product:")
print(df.head())

# Вывод информации о таблице
print("\nИнформация о таблице:")
print(f"Количество строк: {len(df)}")
print(f"Количество колонок: {len(df.columns)}")
print("\nКолонки таблицы:")
print(df.columns.tolist())

# Закрытие соединения
conn.close() 