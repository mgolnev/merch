import sqlite3
import xml.etree.ElementTree as ET

FEED_FILE = 'feed.xml'
DB_FILE = 'merchandise.db'

def import_feed_categories():
    # Парсим XML-фид
    tree = ET.parse(FEED_FILE)
    root = tree.getroot()

    # Ищем все категории
    categories = []
    for cat in root.findall('.//category'):
        cat_id = int(cat.attrib['id'])
        name = cat.text.strip()
        parent_id = int(cat.attrib['parentId']) if 'parentId' in cat.attrib else None
        categories.append((cat_id, name, parent_id))

    # Подключаемся к базе
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Сначала импортируем категории без parent_id
    for cat_id, name, parent_id in categories:
        if parent_id is None:
            cursor.execute('''
                INSERT OR REPLACE INTO feed_categories (category_number, name, parent_id, is_active)
                VALUES (?, ?, NULL, 1)
            ''', (cat_id, name))

    # Затем импортируем категории с parent_id
    for cat_id, name, parent_id in categories:
        if parent_id is not None:
            cursor.execute('''
                INSERT OR REPLACE INTO feed_categories (category_number, name, parent_id, is_active)
                VALUES (?, ?, (SELECT id FROM feed_categories WHERE category_number = ?), 1)
            ''', (cat_id, name, parent_id))

    conn.commit()
    print(f'Импортировано категорий: {len(categories)}')
    conn.close()

if __name__ == '__main__':
    import_feed_categories() 