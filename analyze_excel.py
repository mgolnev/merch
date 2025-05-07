import pandas as pd
import logging

def analyze_excel(file_path):
    try:
        # Читаем Excel файл
        df = pd.read_excel(file_path)
        
        # Выводим основную информацию о датафрейме
        print("\n=== Основная информация о файле ===")
        print(f"Количество строк: {len(df)}")
        print(f"Количество столбцов: {len(df.columns)}")
        print("\nСтолбцы в файле:")
        for col in df.columns:
            print(f"- {col}")
        
        # Проверяем пропущенные значения
        print("\n=== Пропущенные значения ===")
        missing_values = df.isnull().sum()
        print(missing_values[missing_values > 0])
        
        # Проверяем типы данных
        print("\n=== Типы данных ===")
        print(df.dtypes)
        
        # Проверяем уникальные значения в ключевых столбцах
        print("\n=== Уникальные значения в ключевых столбцах ===")
        key_columns = ['Артикул', 'Название товара', 'price', 'oldprice', 'discount', 'gender', 'max_Категория']
        for col in key_columns:
            if col in df.columns:
                print(f"\n{col}:")
                print(f"Количество уникальных значений: {df[col].nunique()}")
                print("Примеры значений:")
                print(df[col].head())
        
        # Проверяем числовые столбцы
        print("\n=== Статистика числовых столбцов ===")
        numeric_columns = ['price', 'oldprice', 'discount', 'Сессии', 'Карточка товара', 
                         'Добавление в корзину', 'Начало чекаута', 'Заказы (gross)', 'Заказы (net)']
        for col in numeric_columns:
            if col in df.columns:
                print(f"\n{col}:")
                print(df[col].describe())
        
    except Exception as e:
        print(f"Ошибка при анализе файла: {str(e)}")

if __name__ == "__main__":
    analyze_excel('processed_data.xlsx') 