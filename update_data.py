import subprocess
import logging
import os
import time

def run_script(script_name):
    try:
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

def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('update_data.log'),
            logging.StreamHandler()
        ]
    )
    
    try:
        # Шаг 1: Импорт данных из Excel и скачивание фида
        logging.info("Начало процесса обновления данных...")
        run_script('import_data.py')
        
        # Шаг 2: Обработка и объединение данных
        logging.info("Запуск обработки данных...")
        run_script('process_data.py')
        
        # Шаг 3: Перезапуск приложения
        logging.info("Перезапуск приложения...")
        # Находим и останавливаем текущий процесс приложения
        os.system("pkill -f 'python app.py'")
        time.sleep(2)  # Даем время на завершение процесса
        
        # Запускаем приложение заново
        subprocess.Popen(['python', 'app.py'])
        
        logging.info("Процесс обновления данных успешно завершен!")
        
    except Exception as e:
        logging.error(f"Ошибка в процессе обновления данных: {str(e)}")
        raise

if __name__ == "__main__":
    main() 