import pandas as pd
import sqlite3

# Читаем данные из Excel
df = pd.read_excel('processed_data.xlsx')

# Подключаемся к базе данных
conn = sqlite3.connect('merchandise.db')
cursor = conn.cursor()

# Обновляем категории для каждого товара
for _, row in df.iterrows():
    cursor.execute('''
        UPDATE products 
        SET max_Категория = ? 
        WHERE sku = ?
    ''', (row['max_Категория'], row['Артикул']))

# Сохраняем изменения и закрываем соединение
conn.commit()
conn.close()

print("Категории успешно обновлены!") 