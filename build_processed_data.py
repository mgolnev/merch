import pandas as pd
import xml.etree.ElementTree as ET
import numpy as np
import sqlite3

# Пути к файлам
DATA_FILE = 'data.xlsx'
DNP_FILE = 'dnp.xlsx'
FEED_FILE = 'feed.xml'
DB_FILE = 'merchandise.db'
OUTPUT_FILE = 'processed_data.xlsx'

# === 1. Загрузка и обработка Excel ===
def load_and_prepare_excel(data_file):
    df = pd.read_excel(data_file)
    # Заполнение NaN
    for col in df.columns:
        if df[col].dtype in [np.float64, np.int64]:
            df[col] = df[col].fillna(0)
        else:
            df[col] = df[col].fillna('')
    # Группировка по артикулу
    agg_dict = {
        'Артикул': 'first',
        'Название товара': 'first',
        'Сессии': 'sum',
        'Карточка товара': 'sum',
        'Добавление в корзину': 'sum',
        'Начало чекаута': 'sum',
        'Заказы (gross)': 'sum',
        'Заказы (net)': 'sum',
        'Выручка с НДС': 'sum',
        'Выручка без НДС (net)': 'sum',
    }
    df_grouped = df.groupby('Артикул', as_index=False).agg(agg_dict)
    return df_grouped

# === 1b. Загрузка дат начала продаж из dnp.xlsx ===
def load_sale_start_dates(dnp_file):
    dnp_df = pd.read_excel(dnp_file)
    # Ожидаем, что там есть столбцы 'sku' и 'sale_start_date' (или их аналоги)
    # Попробуем найти подходящие названия
    sku_col = None
    date_col = None
    for col in dnp_df.columns:
        if 'sku' in col.lower() or 'артикул' in col.lower():
            sku_col = col
        if 'sale_start_date' in col.lower() or 'дата' in col.lower():
            date_col = col
    if not sku_col or not date_col:
        raise Exception('Не найдены нужные столбцы в dnp.xlsx')
    sale_start_map = dict(zip(dnp_df[sku_col], dnp_df[date_col]))
    return sale_start_map

# === 2. Загрузка данных из фида ===
def load_feed(feed_path):
    tree = ET.parse(feed_path)
    root = tree.getroot()
    feed_data = {}
    categories = {}
    for category in root.findall('.//category'):
        cat_id = category.get('id')
        if cat_id:
            parent_id = category.get('parentId')
            name = category.text.strip()
            categories[cat_id] = {
                'id': cat_id,
                'name': name,
                'parent_id': parent_id
            }
    def get_all_categories(cat_id):
        result = []
        current = categories.get(cat_id)
        while current:
            result.append(current['name'])
            if current['parent_id']:
                current = categories.get(current['parent_id'])
            else:
                break
        return result
    for offer in root.findall('.//offer'):
        sku = offer.get('id')
        if not sku:
            continue
        category_ids_raw = [cat_id.text for cat_id in offer.findall('.//categoryId') if cat_id.text]
        category_chains = []
        category_ids = []
        for cat_id in category_ids_raw:
            chain = []
            current = categories.get(cat_id)
            while current:
                chain.append(current['name'])
                if current['parent_id']:
                    current = categories.get(current['parent_id'])
                else:
                    break
            if chain:
                category_chains.append(' | '.join(reversed(chain)))
                category_ids.append(int(cat_id))
        gender = ''
        for param in offer.findall('param'):
            if param.get('name') == 'Пол':
                gender = param.text or ''
                break
        feed_data[sku] = {
            'price': offer.findtext('price', default='0'),
            'oldprice': offer.findtext('oldprice', default='0'),
            'discount': offer.findtext('discount', default='0'),
            'gender': gender,
            'image_url': offer.findtext('picture', default=''),
            'name': offer.findtext('name', default=''),
            'categories_chain': category_chains,
            'category_ids': category_ids,
            'url': offer.findtext('url', default='')
        }
    return feed_data

# === 3. Основная обработка ===
def main():
    print('Загрузка и обработка Excel...')
    df = load_and_prepare_excel(DATA_FILE)
    print('Загрузка дат начала продаж из dnp.xlsx...')
    sale_start_map = load_sale_start_dates(DNP_FILE)
    print('Загрузка данных из фида...')
    feed_data = load_feed(FEED_FILE)
    # ВРЕМЕННЫЙ ОТЛАДОЧНЫЙ ВЫВОД
    print('DEBUG:', 'GKT027834-1', feed_data.get('GKT027834-1', {}))
    print('Объединение данных...')
    df['price'] = df['Артикул'].map(lambda x: feed_data.get(x, {}).get('price', 0))
    df['oldprice'] = df['Артикул'].map(lambda x: feed_data.get(x, {}).get('oldprice', 0))
    df['discount'] = df.apply(
        lambda row: round((1 - float(row['price'])/float(row['oldprice']))*100, 2) if float(row['oldprice']) > 0 else 0,
        axis=1
    )
    df['gender'] = df['Артикул'].map(lambda x: feed_data.get(x, {}).get('gender', ''))
    df['image_url'] = df['Артикул'].map(lambda x: feed_data.get(x, {}).get('image_url', ''))
    # --- Фильтрация: убираем товары без изображения ---
    df = df[df['image_url'].astype(str).str.strip() != '']
    # --- Переименование столбцов ---
    column_rename = {
        'Артикул': 'sku',
        'Название товара': 'name',
        'Сессии': 'sessions',
        'Карточка товара': 'product_views',
        'Добавление в корзину': 'cart_additions',
        'Начало чекаута': 'checkout_starts',
        'Заказы (gross)': 'orders_gross',
        'Заказы (net)': 'orders_net',
        'Выручка с НДС': 'revenue_vat',
        'Выручка без НДС (net)': 'revenue_net',
    }
    df = df.rename(columns=column_rename)
    # --- categories теперь содержит все цепочки категорий (через || если их несколько) ---
    df['categories'] = df['sku'].map(lambda x: ' || '.join(feed_data.get(x, {}).get('categories_chain', [])))
    # --- Добавляем category_ids ---
    df['category_ids'] = df['sku'].map(lambda x: feed_data.get(x, {}).get('category_ids', []))
    # --- Добавляем sale_start_date ---
    df['sale_start_date'] = df['sku'].map(lambda x: sale_start_map.get(x, '01.01.2000'))
    # --- Если sale_start_date равен '-', заменяем на 01.01.2000 ---
    df['sale_start_date'] = df['sale_start_date'].replace('-', '01.01.2000')
    # --- Добавляем url ---
    df['url'] = df['sku'].map(lambda x: feed_data.get(x, {}).get('url', ''))
    # --- Сохраняем результат ---
    df.to_excel(OUTPUT_FILE, index=False)
    print(f'Файл {OUTPUT_FILE} успешно создан!')
    print(df.head())

if __name__ == "__main__":
    main() 