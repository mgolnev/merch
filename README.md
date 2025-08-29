# 🛍️ Каталог товаров "Мерч"

Современное веб-приложение для управления каталогом товаров с системой скоринга, категоризацией и удобным интерфейсом.

## ✨ Возможности

- 📊 **Система скоринга** - автоматическое ранжирование товаров
- 🏷️ **Категоризация** - иерархическая структура категорий
- 🎨 **Фэшн-режим** - просмотр товаров в стиле fashion-журнала
- 📱 **Адаптивный дизайн** - работает на всех устройствах
- 🔍 **Фильтрация** - поиск по названию, категории, полу
- 📈 **Экспорт данных** - выгрузка в CSV
- 🎯 **Кастомная сортировка** - ручное управление порядком товаров

## 🚀 Быстрое развертывание

### Требования
- Docker и Docker Compose
- Минимум 2GB RAM
- 10GB свободного места

### Автоматическое развертывание

```bash
# Клонирование репозитория
git clone <repository-url>
cd мерч

# Запуск автоматического развертывания
./deploy.sh
```

### Ручное развертывание

```bash
# Создание .env файла
cat > .env << EOF
SECRET_KEY=your-super-secret-key-change-this-in-production
FLASK_ENV=production
FLASK_APP=run.py
DATABASE_URL=sqlite:///merchandise.db
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
EOF

# Создание директорий
mkdir -p logs/nginx

# Сборка и запуск
docker-compose build
docker-compose up -d
```

## 📋 Управление

### Основные команды

```bash
# Статус сервисов
docker-compose ps

# Логи приложения
docker-compose logs web

# Логи Nginx
docker-compose logs nginx

# Остановка
docker-compose down

# Перезапуск
docker-compose restart
```

### Обновление данных

```bash
# Резервная копия
cp merchandise.db merchandise.db.backup

# Обновление данных
docker-compose exec web python build_processed_data.py
docker-compose exec web python import_processed_data_to_db.py
```

## 🌐 Доступ

После развертывания приложение доступно по адресам:
- **http://localhost/** - основной интерфейс
- **http://localhost/api/** - API endpoints

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

## 🛡️ Безопасность

### Рекомендации

1. **Измените SECRET_KEY** в .env файле
2. **Настройте SSL/TLS** для HTTPS
3. **Ограничьте доступ** к портам
4. **Регулярно обновляйте** образы Docker
5. **Мониторьте логи** на предмет подозрительной активности

## 📊 Мониторинг

### Проверка здоровья

```bash
# Статус контейнеров
docker-compose ps

# Использование ресурсов
docker stats

# Проверка API
curl http://localhost/api/categories
curl http://localhost/api/products
```

## 🔍 Устранение неполадок

### Частые проблемы

1. **Порт 80 занят**
   ```bash
   sudo lsof -i :80
   sudo systemctl stop apache2
   ```

2. **Недостаточно памяти**
   ```bash
   # Уменьшите количество workers в Dockerfile
   # Измените --workers 4 на --workers 2
   ```

3. **Проблемы с базой данных**
   ```bash
   ls -la merchandise.db
   cp merchandise.db.backup merchandise.db
   ```

## 📝 Логирование

Логи сохраняются в директории `logs/`:
- `logs/nginx/` - логи Nginx
- `logs/app/` - логи приложения

## 🤝 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs`
2. Проверьте статус: `docker-compose ps`
3. Проверьте ресурсы: `docker stats`
4. Обратитесь к документации или создайте issue

## 📄 Лицензия

Проект разработан для внутреннего использования.

---

**Удачного использования! 🚀** 