# 🚀 Инструкция по развертыванию проекта "Мерч"

## 📋 Требования

- Docker и Docker Compose
- Минимум 2GB RAM
- 10GB свободного места на диске

## 🛠️ Быстрое развертывание

### 1. Клонирование и подготовка

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd мерч

# Создайте .env файл
cat > .env << EOF
SECRET_KEY=your-super-secret-key-change-this-in-production
FLASK_ENV=production
FLASK_APP=run.py
DATABASE_URL=sqlite:///merchandise.db
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
EOF

# Создайте директорию для логов
mkdir -p logs/nginx
```

### 2. Сборка и запуск

```bash
# Сборка образов
docker-compose build

# Запуск сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps
```

### 3. Проверка работоспособности

```bash
# Проверка логов
docker-compose logs web
docker-compose logs nginx

# Проверка доступности
curl http://localhost/
```

## 🔧 Конфигурация

### Переменные окружения (.env)

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `SECRET_KEY` | Секретный ключ Flask | `change-this-in-production` |
| `FLASK_ENV` | Окружение Flask | `production` |
| `DATABASE_URL` | URL базы данных | `sqlite:///merchandise.db` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

### Порты

- **80** - HTTP (Nginx)
- **443** - HTTPS (Nginx, для будущего SSL)
- **8000** - Flask приложение (внутренний)

## 📊 Мониторинг

### Проверка здоровья сервисов

```bash
# Статус контейнеров
docker-compose ps

# Логи приложения
docker-compose logs -f web

# Логи Nginx
docker-compose logs -f nginx
```

### Метрики производительности

```bash
# Использование ресурсов
docker stats

# Проверка доступности API
curl http://localhost/api/categories
curl http://localhost/api/products
```

## 🔄 Обновление

### Обновление кода

```bash
# Остановка сервисов
docker-compose down

# Получение обновлений
git pull

# Пересборка и запуск
docker-compose build
docker-compose up -d
```

### Обновление базы данных

```bash
# Резервная копия
cp merchandise.db merchandise.db.backup

# Обновление данных
docker-compose exec web python build_processed_data.py
docker-compose exec web python import_processed_data_to_db.py
```

## 🛡️ Безопасность

### Рекомендации по безопасности

1. **Измените SECRET_KEY** в .env файле
2. **Настройте SSL/TLS** для HTTPS
3. **Ограничьте доступ** к портам
4. **Регулярно обновляйте** образы Docker
5. **Мониторьте логи** на предмет подозрительной активности

### Настройка SSL (опционально)

```bash
# Создайте SSL сертификаты
mkdir -p ssl
# Поместите сертификаты в ssl/ директорию

# Обновите nginx.conf для SSL
# Добавьте блок server для порта 443
```

## 📝 Логирование

### Структура логов

```
logs/
├── nginx/
│   ├── access.log
│   └── error.log
└── app/
    ├── gunicorn.log
    └── flask.log
```

### Ротация логов

```bash
# Настройте logrotate для автоматической ротации
sudo nano /etc/logrotate.d/merch
```

## 🔍 Устранение неполадок

### Частые проблемы

1. **Порт 80 занят**
   ```bash
   sudo lsof -i :80
   sudo systemctl stop apache2  # если используется Apache
   ```

2. **Недостаточно памяти**
   ```bash
   # Уменьшите количество workers в Dockerfile
   # Измените --workers 4 на --workers 2
   ```

3. **Проблемы с базой данных**
   ```bash
   # Проверьте права доступа
   ls -la merchandise.db
   # Восстановите из резервной копии
   cp merchandise.db.backup merchandise.db
   ```

### Команды диагностики

```bash
# Проверка сетевых соединений
docker-compose exec web netstat -tulpn

# Проверка процессов
docker-compose exec web ps aux

# Проверка файловой системы
docker-compose exec web df -h
```

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs`
2. Проверьте статус контейнеров: `docker-compose ps`
3. Проверьте ресурсы: `docker stats`
4. Обратитесь к документации или создайте issue

## 🎯 Готово!

После успешного развертывания приложение будет доступно по адресу:
- **http://localhost/** - основной интерфейс
- **http://localhost/api/** - API endpoints

Удачного использования! 🚀
