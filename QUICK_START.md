# 🚀 Быстрый старт - Каталог товаров "Мерч"

## 📋 Что нужно для развертывания

1. **Docker и Docker Compose** - установлены и запущены
2. **Минимум 2GB RAM** - для работы приложения
3. **10GB свободного места** - для образов и данных

## ⚡ Быстрое развертывание (3 шага)

### Шаг 1: Подготовка
```bash
# Клонируйте репозиторий
git clone <repository-url>
cd мерч

# Создайте .env файл
cat > .env << EOF
COMPOSE_PROJECT_NAME=merch
SECRET_KEY=your-super-secret-key-change-this-in-production
FLASK_ENV=production
FLASK_APP=run.py
DATABASE_URL=sqlite:///merchandise.db
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
EOF

# Создайте директории
mkdir -p logs/nginx
```

### Шаг 2: Запуск
```bash
# Сборка и запуск
docker-compose build
docker-compose up -d
```

### Шаг 3: Проверка
```bash
# Проверка статуса
docker-compose ps

# Проверка доступности
curl http://localhost/
```

## 🎯 Готово!

Приложение доступно по адресу: **http://localhost/**

## 📋 Полезные команды

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

## 🔧 Если что-то пошло не так

1. **Docker не запущен**
   ```bash
   # macOS
   open -a Docker
   
   # Linux
   sudo systemctl start docker
   ```

2. **Порт 80 занят**
   ```bash
   sudo lsof -i :80
   sudo systemctl stop apache2  # если используется Apache
   ```

3. **Проблемы с правами**
   ```bash
   sudo chown -R $USER:$USER .
   ```

## 📞 Поддержка

- 📖 Подробная документация: `DEPLOYMENT.md`
- 🚀 Автоматический скрипт: `./deploy.sh`
- 📝 Логи: `docker-compose logs`

---

**Удачного использования! 🚀**
