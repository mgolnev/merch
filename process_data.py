import pandas as pd
import xml.etree.ElementTree as ET
import requests
from io import BytesIO

def load_and_process_excel(excel_file='data.xlsx'):
    """Загрузка и обработка данных из Excel"""
    print("Загрузка данных из Excel...")
    df = pd.read_excel(excel_file)
    
    # Группировка числовых метрик по артикулу
    numeric_columns = [
        'Сессии', 'Карточка товара', 'Добавление в корзину',
        'Начало чекаута', 'Кол-во товаров', 'Заказы (gross)',
        'Заказы (net)', 'Выручка без НДС', 'Выручка без НДС (net)'
    ]
    
    # Группировка текстовых полей (берем первое значение)
    text_columns = [
        'Название товара', 'max_Категория'
    ]
    
    # Создаем словарь для агрегации
    agg_dict = {col: 'sum' for col in numeric_columns}
    agg_dict.update({col: 'first' for col in text_columns})
    
    # Группируем данные
    grouped_df = df.groupby('Артикул').agg(agg_dict)
    
    print(f"Обработано {len(grouped_df)} уникальных артикулов")
    return grouped_df

def process_xml_data(xml_url='https://storage-cdn11.gloria-jeans.ru/catalog/feeds/AnyQuery-gjStore.xml'):
    """Загрузка и обработка данных из XML"""
    print("Загрузка данных из XML...")
    
    try:
        # Загружаем XML
        response = requests.get(xml_url)
        response.raise_for_status()  # Проверяем успешность запроса
        root = ET.fromstring(response.content)
        
        # Создаем словарь для хранения данных
        products_data = {}
        
        # Обрабатываем каждый товар
        for offer in root.findall('.//offer'):
            product_id = offer.get('id')
            if product_id:
                # Получаем нужные данные
                name = offer.findtext('name', '')
                category = offer.findtext('category', '')
                price = float(offer.find('price').text) if offer.find('price') is not None else None
                oldprice = float(offer.find('oldprice').text) if offer.find('oldprice') is not None else price
                available = offer.get('available', 'false').lower() == 'true'
                gender = None
                for param in offer.findall('param'):
                    if param.get('name') == 'Пол':
                        gender = param.text
                        break
                
                # Получаем первое изображение
                first_picture = offer.find('picture')
                image_url = first_picture.text if first_picture is not None else None
                
                # Рассчитываем скидку
                discount = round(((oldprice - price) / oldprice * 100), 2) if oldprice and price and oldprice > price else 0
                
                # Сохраняем данные только для доступных товаров
                if available:
                    products_data[product_id] = {
                        'name': name,
                        'category': category,
                        'price': price,
                        'oldprice': oldprice,
                        'discount': discount,
                        'gender': gender,
                        'image_url': image_url,
                        'available': available
                    }
        
        print(f"Обработано {len(products_data)} товаров из XML")
        return products_data
    
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при загрузке XML: {e}")
        # Создаем пустой словарь для тестирования
        return {}

def merge_and_save_data(excel_df, xml_data, output_file='processed_data.xlsx', dnp_file='dnp.xlsx'):
    """Объединение данных и сохранение результата"""
    print("Объединение данных...")
    
    # Преобразуем индекс в колонку
    excel_df = excel_df.reset_index()
    
    # Создаем DataFrame из XML данных
    xml_df = pd.DataFrame.from_dict(xml_data, orient='index')
    xml_df.index.name = 'Артикул'
    xml_df = xml_df.reset_index()
    
    # Объединяем данные
    result_df = pd.merge(excel_df, xml_df, on='Артикул', how='outer')
    
    # === ДОБАВЛЯЕМ sale_start_date из dnp.xlsx ===
    try:
        dnp_df = pd.read_excel(dnp_file)
        dnp_df.columns = [col.lower() for col in dnp_df.columns]
        art_col = [c for c in dnp_df.columns if c == 'sku'][0]
        date_col = [c for c in dnp_df.columns if 'dnp' in c or 'дата' in c][0]
        dnp_map = dnp_df.set_index(art_col)[date_col].to_dict()
        def get_dnp(art):
            val = dnp_map.get(art, None)
            if not val or str(val).strip() == '-' or pd.isna(val):
                return ''
            return str(val)
        result_df['sale_start_date'] = result_df['Артикул'].map(get_dnp)
    except Exception as e:
        print(f'Не удалось добавить sale_start_date из dnp.xlsx: {e}')
        result_df['sale_start_date'] = ''
    
    # Заполняем пропущенные значения
    numeric_columns = ['Сессии', 'Карточка товара', 'Добавление в корзину',
                      'Начало чекаута', 'Кол-во товаров', 'Заказы (gross)',
                      'Заказы (net)', 'Выручка без НДС', 'Выручка без НДС (net)']
    result_df[numeric_columns] = result_df[numeric_columns].fillna(0)
    
    # Заполняем пропущенные значения для available
    result_df['available'] = result_df['available'].fillna(False)
    
    # Фильтруем только доступные товары
    result_df = result_df[result_df['available'] == True]

    # === Переименование всех колонок на латиницу ===
    column_rename = {
        'Артикул': 'sku',
        'Название товара': 'name',
        'max_Категория': 'category',
        'Сессии': 'sessions',
        'Карточка товара': 'product_views',
        'Добавление в корзину': 'cart_additions',
        'Начало чекаута': 'checkout_starts',
        'Заказы (gross)': 'orders_gross',
        'Заказы (net)': 'orders_net',
        'Кол-во товаров': 'quantity',
        'Выручка без НДС': 'revenue_no_vat',
        'Выручка без НДС (net)': 'revenue_net',
        # dnp больше не нужен, теперь есть sale_start_date
    }
    result_df = result_df.rename(columns=column_rename)

    # Сохраняем результат
    result_df.to_excel(output_file, index=False)
    print(f"Результат сохранен в {output_file}")
    
    # Выводим пример данных
    print("\nПример обработанных данных:")
    print(result_df.head())
    
    return result_df

if __name__ == "__main__":
    # Обработка Excel
    excel_df = load_and_process_excel()
    
    # Обработка XML
    xml_data = process_xml_data()
    
    # Объединение и сохранение
    result_df = merge_and_save_data(excel_df, xml_data, dnp_file='dnp.xlsx') 