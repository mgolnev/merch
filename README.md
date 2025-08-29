# Мерч - Система для анализа товаров

Веб-приложение для анализа товаров, расчета скоринга и управления категориями.

## 🚀 Быстрый запуск для продакшена

### Требования
- Docker и Docker Compose
- Минимум 2GB RAM
- 1GB свободного места на диске

### Развертывание на сервере

1. **Клонировать репозиторий:**
```bash
git clone <url-репозитория>
cd мерч
```

2. **Настроить переменные окружения:**
```bash
cp env.example .env
# Отредактировать .env файл, изменив SECRET_KEY
```

3. **Запустить в продакшене:**
```bash
docker-compose up -d
```

4. **Проверить статус:**
```bash
docker-compose ps
docker-compose logs -f web
```

**Приложение будет доступно по адресу http://your-server-ip**

### Структура для продакшена

В Docker образ включаются только необходимые файлы:
- `app/` - код приложения
- `templates/` - HTML шаблоны  
- `static/` - статические файлы
- `merchandise.db` - база данных
- `requirements.txt` - зависимости
- `run.py` - точка входа

## 🔧 Разработка

Для локальной разработки:

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск в режиме разработки
docker-compose -f docker-compose.yml -f docker-compose.override.yml up
```

Приложение будет доступно по адресу http://localhost:5001

## Структура проекта

```
.
├── app/                    # Основной код приложения
│   ├── __init__.py         # Инициализация Flask приложения
│   ├── routes/             # Маршруты API
│   ├── services/           # Бизнес-логика
│   ├── database/           # Работа с БД
│   └── utils/              # Утилиты
├── static/                 # Статические файлы
├── templates/              # HTML шаблоны
├── merchandise.db          # База данных SQLite
├── docker-compose.yml      # Конфигурация Docker Compose
├── Dockerfile              # Dockerfile
├── nginx.conf              # Конфигурация Nginx
├── requirements.txt        # Зависимости Python
└── run.py                  # Точка входа в приложение
```

## 📋 Инструкции для CTO

### Мониторинг и логи
```bash
# Просмотр логов приложения
docker-compose logs -f web

# Просмотр логов nginx
docker-compose logs -f nginx

# Статус контейнеров
docker-compose ps
```

### Обновление данных
Для обновления данных товаров используйте скрипты в папке `scripts/`:
```bash
# 1. Обработка данных из Excel и фида
python scripts/build_processed_data.py

# 2. Импорт обработанных данных в БД
python scripts/import_processed_data_to_db.py

# 3. Импорт категорий из фида
python scripts/import_feed_categories.py
```

### Резервное копирование
```bash
# Создание бэкапа базы данных
cp merchandise.db merchandise_backup_$(date +%Y%m%d_%H%M%S).db

# Восстановление из бэкапа
cp merchandise_backup_YYYYMMDD_HHMMSS.db merchandise.db
```

### Масштабирование
- Приложение использует SQLite, для высоких нагрузок рекомендуется PostgreSQL
- Nginx настроен для статических файлов и проксирования
- Gunicorn запускается с 4 воркерами (настраивается в Dockerfile)

## 🎯 Основные функции

- **Просмотр и фильтрация товаров** - по категориям, полу, цене
- **Расчет скоринга товаров** - на основе метрик (сессии, заказы, выручка)
- **Управление весами** - настройка коэффициентов для расчета скоринга
- **Экспорт/импорт** - категории и товары в JSON/CSV формате
- **Управление порядком** - drag-and-drop для изменения порядка товаров
- **Глобальный порядок** - сохранение порядка для всех товаров 