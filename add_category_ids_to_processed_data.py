import pandas as pd
import sqlite3

# Загрузка данных
excel_file = 'processed_data.xlsx'
db_file = 'merchandise.db'
output_file = 'processed_data_with_ids.xlsx'

df = pd.read_excel(excel_file)

# Получаем маппинг: название категории -> id
conn = sqlite3.connect(db_file)
cursor = conn.cursor()
cursor.execute('SELECT id, name FROM feed_categories')
cat_map = {name.strip(): id_ for id_, name in cursor.fetchall()}
conn.close()

def get_category_ids(cat_string):
    if pd.isna(cat_string):
        return []
    # Разбиваем по '|' и убираем пробелы
    cats = [c.strip() for c in str(cat_string).split('|')]
    ids = [cat_map[c] for c in cats if c in cat_map]
    return ids

# Добавляем столбец с id категорий
# Если нужно только id самой последней категории в цепочке, используйте ids[-1] (если ids не пуст)
df['category_ids'] = df['categories'].apply(get_category_ids)
# df['main_category_id'] = df['category_ids'].apply(lambda ids: ids[-1] if ids else None)

# Сохраняем результат
print(f'Пример новых данных:\n', df[['sku', 'categories', 'category_ids']].head())
df.to_excel(output_file, index=False)
print(f'Готово! Файл сохранён как {output_file}') 