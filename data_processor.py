import pandas as pd
import numpy as np
import os
import xml.etree.ElementTree as ET

def process_excel_data(file_path):
    """
    Обработка данных из Excel файла:
    1. Выбор нужных столбцов
    2. Группировка по артикулу
    3. Расчет конверсий
    """
    print(f"Начинаю обработку файла: {file_path}")
    
    # Чтение Excel файла
    df = pd.read_excel(file_path)
    print(f"Прочитано строк: {len(df)}")
    
    # Выбор нужных столбцов
    columns_to_use = {
        'Артикул': 'article',
        'max_Категория': 'category',
        'Сессии': 'sessions',
        'Карточка товара': 'product_views',
        'Добавление в корзину': 'add_to_cart',
        'Начало чекаута': 'checkout_starts',
        'Заказы (gross)': 'orders_gross',
        'Заказы (net)': 'orders_net',
        'Выручка без НДС': 'revenue_gross',
        'Выручка без НДС (net)': 'revenue_net'
    }
    
    df = df[list(columns_to_use.keys())].rename(columns=columns_to_use)
    print("Выбраны и переименованы столбцы")
    
    # Группировка по артикулу и суммирование метрик
    metrics_to_sum = [
        'sessions', 'product_views', 'add_to_cart', 
        'checkout_starts', 'orders_gross', 'orders_net',
        'revenue_gross', 'revenue_net'
    ]
    
    # Для категории берем первое значение при группировке
    agg_dict = {metric: 'sum' for metric in metrics_to_sum}
    agg_dict['category'] = 'first'
    
    df_grouped = df.groupby('article').agg(agg_dict).reset_index()
    print(f"Данные сгруппированы по артикулу. Осталось строк: {len(df_grouped)}")
    
    # Расчет конверсий
    conversions = {
        'view_to_cart': df_grouped['add_to_cart'] / df_grouped['product_views'],
        'cart_to_checkout': df_grouped['checkout_starts'] / df_grouped['add_to_cart'],
        'checkout_to_order': df_grouped['orders_gross'] / df_grouped['checkout_starts'],
        'view_to_order': df_grouped['orders_gross'] / df_grouped['product_views']
    }
    
    # Добавляем конверсии в датафрейм
    for conv_name, conv_values in conversions.items():
        df_grouped[conv_name] = conv_values.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    print("Конверсии рассчитаны")
    
    # Базовая статистика
    print("\nСтатистика по конверсиям:")
    for conv_name in conversions.keys():
        mean_conv = df_grouped[conv_name].mean() * 100
        median_conv = df_grouped[conv_name].median() * 100
        print(f"{conv_name}:")
        print(f"  Средняя: {mean_conv:.2f}%")
        print(f"  Медиана: {median_conv:.2f}%")
    
    return df_grouped

def process_feed_data(feed_path):
    """
    Обработка XML фида:
    1. Извлечение артикула (offer id)
    2. Извлечение цены
    3. Извлечение первой картинки
    """
    print(f"Начинаю обработку фида: {feed_path}")
    
    # Создаем словарь для хранения данных
    feed_data = []
    
    # Парсим XML
    tree = ET.parse(feed_path)
    root = tree.getroot()
    
    # Проходим по всем товарам
    for offer in root.findall('.//offer'):
        offer_id = offer.get('id')
        
        # Получаем цену
        price_elem = offer.find('price')
        price = int(price_elem.text) if price_elem is not None else None
        
        # Получаем первую картинку
        picture_elem = offer.find('picture')
        picture = picture_elem.text if picture_elem is not None else None
        
        feed_data.append({
            'article': offer_id,
            'price': price,
            'image_url': picture
        })
    
    # Создаем DataFrame
    df_feed = pd.DataFrame(feed_data)
    print(f"Обработано товаров из фида: {len(df_feed)}")
    
    return df_feed

def merge_data(df_excel, df_feed):
    """
    Объединение данных из Excel и фида
    """
    print("Объединяю данные из Excel и фида...")
    
    # Объединяем по артикулу
    df_merged = pd.merge(
        df_excel,
        df_feed,
        on='article',
        how='left'
    )
    
    print(f"Итоговое количество строк: {len(df_merged)}")
    print(f"Товаров с ценами: {df_merged['price'].notna().sum()}")
    print(f"Товаров с картинками: {df_merged['image_url'].notna().sum()}")
    
    return df_merged

if __name__ == "__main__":
    # Пути к файлам относительно текущего скрипта
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(os.path.dirname(current_dir), "data.xlsx")
    feed_file = os.path.join(current_dir, "feed.xml")
    
    if not os.path.exists(data_file):
        print(f"Файл не найден: {data_file}")
        exit(1)
        
    if not os.path.exists(feed_file):
        print(f"Файл не найден: {feed_file}")
        exit(1)
    
    # Обработка Excel
    df_excel = process_excel_data(data_file)
    
    # Обработка фида
    df_feed = process_feed_data(feed_file)
    
    # Объединение данных
    df_final = merge_data(df_excel, df_feed)
    
    # Сохранение результатов
    output_file = os.path.join(os.path.dirname(current_dir), "processed_data.xlsx")
    df_final.to_excel(output_file, index=False)
    print(f"\nРезультаты сохранены в файл: {output_file}") 