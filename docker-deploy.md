# Деплой приложения с использованием Docker

## Подготовка

1. Установите Docker и Docker Compose:
   - [Инструкции по установке Docker](https://docs.docker.com/get-docker/)
   - [Инструкции по установке Docker Compose](https://docs.docker.com/compose/install/)

2. Запустите Docker демон (если еще не запущен):
   - На macOS: запустите приложение Docker Desktop
   - На Linux: `sudo systemctl start docker`
   - На Windows: запустите Docker Desktop

## Деплой для разработки

Для разработки используйте:

```bash
# Сборка и запуск без Nginx для разработки
docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build
```

Приложение будет доступно по адресу: http://localhost:5000

## Деплой для продакшн

Для продакшена используйте:

```bash
# Создайте .env файл с безопасными настройками
cp env.example .env
# Отредактируйте .env и установите безопасный SECRET_KEY

# Сборка и запуск с Nginx
docker-compose --profile production up --build -d
```

Приложение будет доступно по адресу: http://localhost

## Управление контейнерами

```bash
# Просмотр запущенных контейнеров
docker-compose ps

# Остановка всех контейнеров
docker-compose down

# Просмотр логов
docker-compose logs -f web

# Перезапуск при изменении кода
docker-compose restart web
```

## Резервное копирование базы данных

```bash
# Копирование базы данных из контейнера
docker cp merch_web_1:/app/merchandise.db ./backups/merchandise_$(date +%Y%m%d).db
```

## Обновление приложения

```bash
# Остановка контейнеров
docker-compose down

# Загрузка обновлений
git pull

# Повторный запуск с обновленным кодом
docker-compose up --build -d
``` 