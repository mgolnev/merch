import pandas as pd
import sqlite3
from datetime import datetime

# Подключение к базе данных
conn = sqlite3.connect('merchandise.db')
cursor = conn.cursor()

# Чтение данных из Excel
print("Чтение данных из Excel...")
df = pd.read_excel('../processed_data.xlsx')

# Добавление столбца last_updated с текущей датой
df['last_updated'] = datetime.now()

# Запись данных в базу данных
print("Запись данных в базу данных...")
df.to_sql('product', conn, if_exists='replace', index=False)

# Закрытие соединения
conn.close()

print("Импорт данных успешно завершен!") 