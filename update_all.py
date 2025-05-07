import subprocess
import logging
import os
import time
import sqlite3
from datetime import datetime

def setup_logging():
    """Настройка логирования"""
    log_filename = f'update_all_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )

def run_script(script_name, description):
    """Запуск скрипта с логированием"""
    try:
        logging.info(f"=== {description} ===")
        logging.info(f"Запуск скрипта {script_name}...")
        result = subprocess.run(['python', script_name], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"Скрипт {script_name} успешно выполнен")
            if result.stdout:
                logging.info(f"Вывод скрипта {script_name}:\n{result.stdout}")
        else:
            logging.error(f"Ошибка при выполнении скрипта {script_name}:\n{result.stderr}")
            raise Exception(f"Скрипт {script_name} завершился с ошибкой")
    except Exception as e:
        logging.error(f"Ошибка при запуске скрипта {script_name}: {str(e)}")
        raise

def check_database():
    """Проверка состояния базы данных"""
    try:
        logging.info("=== Проверка базы данных ===")
        run_script('check_db.py', "Проверка целостности базы данных")
    except Exception as e:
        logging.error(f"Ошибка при проверке базы данных: {str(e)}")
        raise

def clean_database():
    """Очистка базы данных"""
    try:
        logging.info("=== Очистка базы данных ===")
        run_script('clean_db.py', "Очистка старых данных")
    except Exception as e:
        logging.error(f"Ошибка при очистке базы данных: {str(e)}")
        raise

def import_data():
    """Импорт данных из Excel и скачивание фида"""
    try:
        logging.info("=== Импорт данных ===")
        run_script('import_data.py', "Импорт данных из Excel и скачивание фида")
    except Exception as e:
        logging.error(f"Ошибка при импорте данных: {str(e)}")
        raise

def process_data():
    """Обработка и объединение данных"""
    try:
        logging.info("=== Обработка данных ===")
        run_script('process_data.py', "Обработка и объединение данных")
    except Exception as e:
        logging.error(f"Ошибка при обработке данных: {str(e)}")
        raise

def update_categories():
    """Обновление категорий товаров"""
    try:
        logging.info("=== Обновление категорий ===")
        run_script('update_categories.py', "Обновление категорий товаров")
    except Exception as e:
        logging.error(f"Ошибка при обновлении категорий: {str(e)}")
        raise

def restart_application():
    """Перезапуск приложения"""
    try:
        logging.info("=== Перезапуск приложения ===")
        # Находим и останавливаем текущий процесс приложения
        os.system("pkill -f 'python app.py'")
        time.sleep(2)  # Даем время на завершение процесса
        
        # Запускаем приложение заново
        subprocess.Popen(['python', 'app.py'])
        logging.info("Приложение успешно перезапущено")
    except Exception as e:
        logging.error(f"Ошибка при перезапуске приложения: {str(e)}")
        raise

def main():
    """Основная функция обновления данных"""
    setup_logging()
    
    try:
        logging.info("=== Начало процесса обновления данных ===")
        
        # Шаг 1: Проверка базы данных
        check_database()
        
        # Шаг 2: Очистка базы данных
        clean_database()
        
        # Шаг 2.5: Подготовка processed_data.xlsx
        run_script('prepare_processed_data.py', "Подготовка processed_data.xlsx")
        
        # === ОТЛАДКА: прямой импорт данных ===
        import import_data
        df = import_data.import_excel_data('processed_data.xlsx')
        xml_data = {}  # если не нужен XML, можно оставить пустым
        import_data.insert_data_to_db(df, xml_data, 'merchandise.db')
        
        # Шаг 3: Импорт данных (старый способ)
        # import_data()
        
        # Шаг 4: Обработка данных
        process_data()
        
        # Шаг 5: Обновление категорий
        update_categories()
        
        # Шаг 6: Перезапуск приложения
        restart_application()
        
        logging.info("=== Процесс обновления данных успешно завершен! ===")
        
    except Exception as e:
        logging.error(f"Критическая ошибка в процессе обновления данных: {str(e)}")
        raise

if __name__ == "__main__":
    main() 