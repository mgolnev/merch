import pandas as pd
import sqlite3
import xml.etree.ElementTree as ET
import ast

DB_FILE = 'merchandise.db'
DATA_FILE = 'processed_data.xlsx'
FEED_FILE = 'feed.xml'

def main():
    # 1. Загружаем processed_data.xlsx
    df = pd.read_excel(DATA_FILE)
    all_cat_ids = set()
    for val in df['category_ids']:
        if isinstance(val, str):
            try:
                ids = ast.literal_eval(val)
            except Exception:
                ids = []
        else:
            ids = val if isinstance(val, list) else []
        all_cat_ids.update(ids)
    # 2. Парсим feed.xml для получения названий и иерархии
    tree = ET.parse(FEED_FILE)
    root = tree.getroot()
    cat_map = {}
    for category in root.findall('.//category'):
        cat_id = category.get('id')
        if cat_id and cat_id.isdigit():
            cat_map[int(cat_id)] = {
                'id': int(cat_id),
                'name': category.text.strip(),
                'parent_id': int(category.get('parentId')) if category.get('parentId') and category.get('parentId').isdigit() else None
            }
    # 3. Собираем всех родителей
    needed_ids = set(all_cat_ids)
    for cat_id in list(all_cat_ids):
        current = cat_map.get(cat_id)
        while current and current['parent_id']:
            needed_ids.add(current['parent_id'])
            current = cat_map.get(current['parent_id'])
    # 4. Очищаем feed_categories
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('DELETE FROM feed_categories')
    # 5. Добавляем только нужные категории
    for cat_id in sorted(needed_ids):
        cat = cat_map.get(cat_id)
        if cat:
            cur.execute('INSERT INTO feed_categories (id, name, parent_id, category_number) VALUES (?, ?, ?, ?)',
                        (cat['id'], cat['name'], cat['parent_id'], cat['id']))
    conn.commit()
    conn.close()
    print('feed_categories успешно обновлена!')

if __name__ == '__main__':
    main() 