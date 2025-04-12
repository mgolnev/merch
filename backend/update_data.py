import pandas as pd
import requests
import xml.etree.ElementTree as ET
from io import BytesIO
import os
from datetime import datetime
import sqlite3

def download_xml_feed(url):
    """Скачивает XML фид по указанной ссылке"""
    print("Скачивание XML фида...")
    response = requests.get(url)
    response.raise_for_status()
    return response.content

def process_excel_data(file_path):
    """Обрабатывает данные из Excel файла"""
    print("Обработка Excel файла...")
    df = pd.read_excel(file_path)
    
    # Группируем по артикулу и считаем конверсию
    grouped = df.groupby('Артикул').agg({
        'Просмотры': 'sum',
        'Добавления в корзину': 'sum',
        'Заказы': 'sum'
    }).reset_index()
    
    grouped['Конверсия'] = (grouped['Заказы'] / grouped['Просмотры'] * 100).round(2)
    
    return grouped

def extract_xml_data(xml_content):
    """Извлекает данные из XML фида"""
    print("Извлечение данных из XML...")
    root = ET.fromstring(xml_content)
    data = []
    
    for offer in root.findall('.//offer'):
        article = offer.find('article').text
        price = float(offer.find('price').text)
        image = offer.find('picture').text if offer.find('picture') is not None else None
        
        data.append({
            'Артикул': article,
            'Цена': price,
            'Изображение': image
        })
    
    return pd.DataFrame(data)

def merge_data(excel_data, xml_data):
    """Объединяет данные из Excel и XML"""
    print("Объединение данных...")
    merged = pd.merge(excel_data, xml_data, on='Артикул', how='left')
    return merged

def save_results(df, output_dir='data'):
    """Сохраняет результаты в Excel файл"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'merged_data_{timestamp}.xlsx')
    
    print(f"Сохранение результатов в {output_file}...")
    df.to_excel(output_file, index=False)
    return output_file

def update_metrics():
    conn = sqlite3.connect('merchandise.db')
    cursor = conn.cursor()
    
    try:
        # Обновляем просмотры на основе product_views
        cursor.execute('''
            UPDATE product 
            SET views = COALESCE(product_views, 0)
        ''')
        
        # Обновляем конверсии на основе orders_net
        cursor.execute('''
            UPDATE product 
            SET conversions = COALESCE(orders_net, 0)
        ''')
        
        # Обновляем sizes_available с базовым набором размеров для демонстрации
        cursor.execute('''
            UPDATE product 
            SET sizes_available = '["XS", "S", "M", "L", "XL"]'
            WHERE sizes_available = '[]' OR sizes_available IS NULL
        ''')
        
        conn.commit()
        print("Данные успешно обновлены!")
        
        # Выводим статистику
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN views > 0 THEN 1 ELSE 0 END) as with_views,
                SUM(CASE WHEN conversions > 0 THEN 1 ELSE 0 END) as with_conversions
            FROM product
        ''')
        stats = cursor.fetchone()
        print(f"\nСтатистика:")
        print(f"Всего товаров: {stats[0]}")
        print(f"Товаров с просмотрами: {stats[1]}")
        print(f"Товаров с конверсиями: {stats[2]}")
        
    except Exception as e:
        print(f"Ошибка при обновлении данных: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    # URL XML фида
    xml_url = "https://storage-cdn11.gloria-jeans.ru/catalog/feeds/AnyQuery-gjStore.xml"
    
    try:
        # Шаг 1: Скачиваем XML фид
        xml_content = download_xml_feed(xml_url)
        
        # Шаг 2: Обрабатываем Excel файл
        excel_data = process_excel_data('data.xlsx')
        
        # Шаг 3: Извлекаем данные из XML
        xml_data = extract_xml_data(xml_content)
        
        # Шаг 4: Объединяем данные
        merged_data = merge_data(excel_data, xml_data)
        
        # Шаг 5: Сохраняем результаты
        output_file = save_results(merged_data)
        
        print(f"\nОбновление данных успешно завершено!")
        print(f"Результаты сохранены в файл: {output_file}")
        
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    main()

if __name__ == '__main__':
    update_metrics() 