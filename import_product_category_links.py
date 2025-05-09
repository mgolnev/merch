import sqlite3
import xml.etree.ElementTree as ET

FEED_FILE = 'feed.xml'
DB_FILE = 'merchandise.db'

def import_product_category_links():
    # Парсим XML-фид
    tree = ET.parse(FEED_FILE)
    root = tree.getroot()

    # Собираем связи sku -> category_numbers
    product_links = []
    for offer in root.findall('.//offer'):
        sku = offer.attrib.get('id')
        if not sku:
            continue
            
        # Получаем все категории товара
        categories_elem = offer.find('categories')
        if categories_elem is not None:
            category_ids = []
            for cat_elem in categories_elem.findall('categoryId'):
                try:
                    category_number = int(cat_elem.text.strip())
                    category_ids.append(category_number)
                except (ValueError, AttributeError):
                    continue
            
            if category_ids:
                product_links.append((sku, category_ids))

    # Подключаемся к базе
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Получаем маппинг category_number -> id
    cursor.execute('SELECT id, category_number FROM feed_categories')
    cat_map = {row[1]: row[0] for row in cursor.fetchall()}

    # Добавляем связи
    count = 0
    for sku, category_numbers in product_links:
        for category_number in category_numbers:
            category_id = cat_map.get(category_number)
            if category_id:
                cursor.execute('''
                    INSERT OR REPLACE INTO product_categories (sku, category_id, position)
                    VALUES (?, ?, NULL)
                ''', (sku, category_id))
                count += 1

    conn.commit()
    print(f'Добавлено связей товаров с категориями: {count}')
    conn.close()

if __name__ == '__main__':
    import_product_category_links() 