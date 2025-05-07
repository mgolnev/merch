import pandas as pd
import xml.etree.ElementTree as ET
import numpy as np
import requests

FEED_URL = "https://storage-cdn11.gloria-jeans.ru/catalog/feeds/AnyQuery-gjStore.xml"
FEED_LOCAL = "feed.xml"


def download_feed(url, local_path):
    print(f"Скачиваю фид: {url}")
    response = requests.get(url)
    response.raise_for_status()
    with open(local_path, 'wb') as f:
        f.write(response.content)
    print("Фид успешно скачан!")

def load_feed(feed_path):
    """Загрузка данных из XML-фида"""
    tree = ET.parse(feed_path)
    root = tree.getroot()
    feed_data = {}
    for offer in root.findall('.//offer'):
        sku = offer.get('id')
        if not sku:
            continue
        # Ищем param с name="Пол"
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
            'name': offer.findtext('name', default='')
        }
    return feed_data

def process_data(data_path, feed_path, output_path, dnp_path=None):
    # Читаем исходный Excel
    df = pd.read_excel(data_path)
    # Заменяем NaN на 0 для числовых и на пустую строку для текстовых
    for col in df.columns:
        if df[col].dtype in [np.float64, np.int64]:
            df[col] = df[col].fillna(0)
        else:
            df[col] = df[col].fillna('')
    # Группируем по артикулу
    agg_dict = {
        'Название товара': 'first',
        'max_Категория': 'first',
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
    # Загружаем данные из фида
    feed_data = load_feed(feed_path)
    # Добавляем данные из фида
    df_grouped['price'] = df_grouped['Артикул'].map(lambda x: feed_data.get(x, {}).get('price', 0))
    df_grouped['oldprice'] = df_grouped['Артикул'].map(lambda x: feed_data.get(x, {}).get('oldprice', 0))
    # discount рассчитываем как (1 - price/oldprice)*100, если oldprice > 0
    df_grouped['discount'] = df_grouped.apply(
        lambda row: round((1 - float(row['price'])/float(row['oldprice']))*100, 2) if float(row['oldprice']) > 0 else 0,
        axis=1
    )
    df_grouped['gender'] = df_grouped['Артикул'].map(lambda x: feed_data.get(x, {}).get('gender', ''))
    df_grouped['image_url'] = df_grouped['Артикул'].map(lambda x: feed_data.get(x, {}).get('image_url', ''))
    # Если Название товара пустое, подставляем из фида
    df_grouped['Название товара'] = df_grouped.apply(
        lambda row: row['Название товара'] if row['Название товара'] else feed_data.get(row['Артикул'], {}).get('name', ''), axis=1
    )
    # Фильтрация: удаляем строки без цены
    df_grouped = df_grouped[df_grouped['price'].astype(float) > 0]
    # --- ДОБАВЛЯЕМ DNP ---
    if dnp_path:
        dnp_df = pd.read_excel(dnp_path)
        # Ожидаем, что в dnp.xlsx есть столбцы: sku, dnp (или дата)
        dnp_df.columns = [col.lower() for col in dnp_df.columns]
        art_col = [c for c in dnp_df.columns if c == 'sku'][0]
        date_col = [c for c in dnp_df.columns if 'dnp' in c or 'дата' in c][0]
        dnp_map = dnp_df.set_index(art_col)[date_col].to_dict()
        def get_dnp(art):
            val = dnp_map.get(art, None)
            if not val or str(val).strip() == '-' or pd.isna(val):
                return '01.01.2000'
            return str(val)
        df_grouped['dnp'] = df_grouped['Артикул'].map(get_dnp)
    # Сохраняем итоговый файл
    df_grouped.to_excel(output_path, index=False)
    print(f'Файл {output_path} успешно создан!')

if __name__ == "__main__":
    download_feed(FEED_URL, FEED_LOCAL)
    process_data('data.xlsx', FEED_LOCAL, 'processed_data.xlsx', dnp_path='dnp.xlsx') 