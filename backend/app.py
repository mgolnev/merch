from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import os
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app)

# Загружаем данные из Excel
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data.xlsx")
df = pd.read_excel(DATA_FILE)
print(f"Данные из Excel успешно загружены. Строк: {len(df)}")
print(f"Доступные колонки: {df.columns.tolist()}")

# Очищаем и нормализуем артикулы в Excel
df['Артикул'] = df['Артикул'].astype(str).str.strip().str.upper()
print(f"Уникальных артикулов в Excel: {df['Артикул'].nunique()}")
print("Примеры артикулов из Excel:")
print(df['Артикул'].head().tolist())

# Загружаем и обрабатываем XML-фид
FEED_FILE = os.path.join(os.path.dirname(__file__), "feed.xml")

def parse_feed():
    print("Парсинг XML-фида...")
    tree = ET.parse(FEED_FILE)
    root = tree.getroot()
    
    feed_data = []
    article_examples = []
    for offer in root.findall('.//offer'):
        try:
            article = offer.find('.//vendorCode')
            if article is not None:
                article = article.text.strip().upper()
                if len(article_examples) < 5:  # Сохраняем первые 5 артикулов для примера
                    article_examples.append(article)
            else:
                continue
                
            name = offer.find('.//name')
            name = name.text if name is not None else None
            
            category = offer.find('.//category')
            category = category.text if category is not None else None
            
            pictures = offer.findall('.//picture')
            picture = pictures[0].text if pictures and len(pictures) > 0 else None
            
            if article:  # Добавляем только если есть артикул
                feed_data.append({
                    'article': article,
                    'name': name,
                    'category': category,
                    'picture': picture
                })
        except Exception as e:
            print(f"Ошибка при обработке товара: {e}")
            continue
    
    feed_df = pd.DataFrame(feed_data)
    print(f"Обработано товаров из фида: {len(feed_df)}")
    print(f"Уникальных артикулов в фиде: {feed_df['article'].nunique()}")
    print("Примеры артикулов из фида:")
    print(article_examples)
    print(f"Колонки в фиде: {feed_df.columns.tolist()}")
    return feed_df

# Загружаем данные из фида
feed_df = parse_feed()
print(f"Данные из фида загружены. Строк: {len(feed_df)}")

# Объединяем данные
feed_df['article'] = feed_df['article'].astype(str).str.strip().str.upper()

# Проверяем пересечение артикулов
excel_articles = set(df['Артикул'].unique())
feed_articles = set(feed_df['article'].unique())
common_articles = excel_articles.intersection(feed_articles)
print(f"Артикулов в Excel: {len(excel_articles)}")
print(f"Артикулов в фиде: {len(feed_articles)}")
print(f"Общих артикулов: {len(common_articles)}")

# Объединяем данные
merged_df = pd.merge(df, feed_df, left_on='Артикул', right_on='article', how='left')
print(f"Объединенные данные. Строк: {len(merged_df)}")
print(f"Строк с картинками: {merged_df['picture'].notna().sum()}")

# Проверяем качество объединения
print("Статистика объединения:")
print(f"Строк с данными из Excel: {len(df)}")
print(f"Строк с данными из фида: {len(feed_df)}")
print(f"Строк после объединения: {len(merged_df)}")
print(f"Строк без картинок: {merged_df['picture'].isna().sum()}")

@app.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        print("Запрос категорий...")
        # Используем max_Категория для категорий
        categories = df['max_Категория'].unique().tolist()
        # Удаляем NaN значения
        categories = [cat for cat in categories if pd.notna(cat)]
        print(f"Найдено категорий: {len(categories)}")
        print(f"Категории: {categories[:5]}...")  # Выводим первые 5 категорий для проверки
        return jsonify(categories)
    except Exception as e:
        print(f"Ошибка при получении категорий: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/products', methods=['POST'])
def get_products():
    try:
        data = request.json
        print(f"Получен запрос на товары: {data}")
        category = data.get('category')
        weights = data.get('weights', {
            'gross_sales': 0.4,
            'conversion': 0.3,
            'size_popularity': 0.3
        })
        
        print(f"Категория: {category}")
        print(f"Веса до нормализации: {weights}")
        
        # Проверяем наличие всех необходимых весов
        required_weights = ['gross_sales', 'conversion', 'size_popularity']
        if not all(key in weights for key in required_weights):
            print(f"Отсутствуют необходимые веса. Получено: {weights.keys()}")
            return jsonify({"error": "Missing required weights"}), 400
        
        # Нормализуем веса, если их сумма не равна 1
        weights_sum = sum(weights.values())
        if weights_sum != 0:  # Избегаем деления на ноль
            weights = {k: v/weights_sum for k, v in weights.items()}
        
        print(f"Веса после нормализации: {weights}")
        print(f"Сумма весов: {sum(weights.values())}")
        
        # Фильтруем по категории
        category_df = merged_df[merged_df['max_Категория'] == category].copy()
        print(f"Найдено товаров в категории {category}: {len(category_df)}")
        
        if len(category_df) == 0:
            return jsonify([])
        
        # Нормализуем метрики
        category_df['gross_sales'] = category_df['Заказы (gross)'].fillna(0)
        category_df['conversion'] = category_df['CR gross'].fillna(0)
        
        # Нормализация
        for col in ['gross_sales', 'conversion']:
            if category_df[col].max() != category_df[col].min():
                category_df[f'{col}_norm'] = (category_df[col] - category_df[col].min()) / \
                                          (category_df[col].max() - category_df[col].min())
            else:
                category_df[f'{col}_norm'] = 1.0
        
        # Рейтинг
        category_df['rating'] = (
            weights['gross_sales'] * category_df['gross_sales_norm'] +
            weights['conversion'] * category_df['conversion_norm']
        )
        
        # Сортировка
        category_df = category_df.sort_values('rating', ascending=False)
        
        # Формируем ответ
        result = []
        for _, row in category_df.iterrows():
            try:
                result.append({
                    'id': str(row['Артикул']),
                    'name': str(row['Название товара']),
                    'category': str(row['max_Категория']),
                    'gross_sales': int(row['Заказы (gross)']) if pd.notna(row['Заказы (gross)']) else 0,
                    'conversion': float(row['CR gross']) if pd.notna(row['CR gross']) else 0.0,
                    'rating': float(row['rating']) if pd.notna(row['rating']) else 0.0,
                    'image_url': str(row['picture']) if pd.notna(row['picture']) else None
                })
            except Exception as row_error:
                print(f"Ошибка при обработке строки: {row_error}")
                continue
        
        print(f"Отправляем {len(result)} товаров")
        return jsonify(result)
    except Exception as e:
        print(f"Ошибка при получении товаров: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8000, host='127.0.0.1') 