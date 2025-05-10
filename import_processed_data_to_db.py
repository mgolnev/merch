import pandas as pd
import sqlite3
import ast

DB_FILE = 'merchandise.db'
DATA_FILE = 'processed_data.xlsx'

def main():
    df = pd.read_excel(DATA_FILE)
    # --- Импорт категорий ---
    cat_map = {}
    for cats, ids in zip(df['categories'], df['category_ids']):
        cats_split = [c.strip() for c in str(cats).split('||')]
        if isinstance(ids, str):
            try:
                ids = ast.literal_eval(ids)
            except Exception:
                ids = []
        for cat_name, cat_id in zip(cats_split, ids):
            cat_map[cat_id] = cat_name.strip()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    # Очищаем feed_categories
    cur.execute('DELETE FROM feed_categories')
    # Заливаем только реально используемые категории
    for cat_id, cat_name in cat_map.items():
        short_name = cat_name.split('|')[-1].strip()
        cur.execute('INSERT INTO feed_categories (id, name, category_number) VALUES (?, ?, ?)', (cat_id, short_name, cat_id))
    # --- Импорт товаров и связей ---
    # Получаем все sku из файла
    all_skus = set(df['sku'].astype(str))
    # Удаляем из products все товары, которых нет в файле
    cur.execute('SELECT sku FROM products')
    db_skus = set(row[0] for row in cur.fetchall())
    to_delete = db_skus - all_skus
    if to_delete:
        cur.executemany('DELETE FROM products WHERE sku = ?', [(sku,) for sku in to_delete])
        cur.executemany('DELETE FROM product_categories WHERE sku = ?', [(sku,) for sku in to_delete])
        # Можно добавить очистку других связанных таблиц, если нужно
    # Обновляем/добавляем товары
    for _, row in df.iterrows():
        sku = str(row['sku'])
        # Все поля
        name = str(row.get('name', ''))
        price = float(row.get('price', 0))
        oldprice = float(row.get('oldprice', 0))
        discount = float(row.get('discount', 0))
        gender = str(row.get('gender', ''))
        image_url = str(row.get('image_url', ''))
        sessions = int(row.get('sessions', 0))
        product_views = int(row.get('product_views', 0))
        cart_additions = int(row.get('cart_additions', 0))
        checkout_starts = int(row.get('checkout_starts', 0))
        orders_gross = int(row.get('orders_gross', 0))
        orders_net = int(row.get('orders_net', 0))
        revenue_vat = float(row.get('revenue_vat', 0))
        revenue_net = float(row.get('revenue_net', 0))
        sale_start_date = str(row.get('sale_start_date', '01.01.2000'))
        categories = str(row.get('categories', ''))
        url = str(row.get('url', ''))
        # upsert в products
        cur.execute('''
            INSERT INTO products (sku, name, price, oldprice, discount, gender, image_url, sessions, product_views, cart_additions, checkout_starts, orders_gross, orders_net, revenue_vat, revenue_net, sale_start_date, categories, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sku) DO UPDATE SET
                name=excluded.name,
                price=excluded.price,
                oldprice=excluded.oldprice,
                discount=excluded.discount,
                gender=excluded.gender,
                image_url=excluded.image_url,
                sessions=excluded.sessions,
                product_views=excluded.product_views,
                cart_additions=excluded.cart_additions,
                checkout_starts=excluded.checkout_starts,
                orders_gross=excluded.orders_gross,
                orders_net=excluded.orders_net,
                revenue_vat=excluded.revenue_vat,
                revenue_net=excluded.revenue_net,
                sale_start_date=excluded.sale_start_date,
                categories=excluded.categories,
                url=excluded.url
        ''', (sku, name, price, oldprice, discount, gender, image_url, sessions, product_views, cart_additions, checkout_starts, orders_gross, orders_net, revenue_vat, revenue_net, sale_start_date, categories, url))
        # Обновляем связи с категориями
        cur.execute('DELETE FROM product_categories WHERE sku = ?', (sku,))
        # category_ids может быть строкой вида '[1, 2, 3]' — преобразуем
        cat_ids = row.get('category_ids', [])
        if isinstance(cat_ids, str):
            try:
                cat_ids = ast.literal_eval(cat_ids)
            except Exception:
                cat_ids = []
        for cat_id in cat_ids:
            cur.execute('INSERT INTO product_categories (sku, category_id) VALUES (?, ?)', (sku, cat_id))
    conn.commit()
    conn.close()
    print('Импорт завершён!')

if __name__ == '__main__':
    main() 