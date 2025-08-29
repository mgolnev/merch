#!/bin/bash

# 🚀 Скрипт автоматического развертывания проекта "Мерч"
# Автор: AI Assistant
# Версия: 1.0

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка зависимостей
check_dependencies() {
    print_info "Проверка зависимостей..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker не установлен. Установите Docker и попробуйте снова."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose не установлен. Установите Docker Compose и попробуйте снова."
        exit 1
    fi
    
    print_success "Все зависимости установлены"
}

# Создание .env файла
create_env_file() {
    print_info "Создание .env файла..."
    
    if [ ! -f .env ]; then
        cat > .env << EOF
# Конфигурация приложения
SECRET_KEY=your-super-secret-key-change-this-in-production
FLASK_ENV=production
FLASK_APP=run.py

# Настройки базы данных
DATABASE_URL=sqlite:///merchandise.db

# Настройки сервера
HOST=0.0.0.0
PORT=8000

# Настройки логирования
LOG_LEVEL=INFO
EOF
        print_success ".env файл создан"
    else
        print_warning ".env файл уже существует"
    fi
}

# Создание директорий
create_directories() {
    print_info "Создание необходимых директорий..."
    
    mkdir -p logs/nginx
    mkdir -p logs/app
    
    print_success "Директории созданы"
}

# Проверка портов
check_ports() {
    print_info "Проверка доступности портов..."
    
    if lsof -Pi :80 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Порт 80 занят. Возможно, потребуется остановить другие сервисы."
    fi
    
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Порт 8000 занят. Возможно, потребуется остановить другие сервисы."
    fi
}

# Сборка образов
build_images() {
    print_info "Сборка Docker образов..."
    
    docker-compose build --no-cache
    
    print_success "Образы собраны"
}

# Запуск сервисов
start_services() {
    print_info "Запуск сервисов..."
    
    docker-compose up -d
    
    print_success "Сервисы запущены"
}

# Проверка работоспособности
check_health() {
    print_info "Проверка работоспособности..."
    
    # Ждем запуска сервисов
    sleep 10
    
    # Проверяем статус контейнеров
    if docker-compose ps | grep -q "Up"; then
        print_success "Все контейнеры запущены"
    else
        print_error "Не все контейнеры запущены"
        docker-compose ps
        exit 1
    fi
    
    # Проверяем доступность приложения
    if curl -f http://localhost/ > /dev/null 2>&1; then
        print_success "Приложение доступно по адресу http://localhost/"
    else
        print_warning "Приложение пока недоступно. Проверьте логи: docker-compose logs"
    fi
}

# Показ информации
show_info() {
    echo
    print_success "🎉 Развертывание завершено!"
    echo
    echo -e "${BLUE}Доступные адреса:${NC}"
    echo -e "  🌐 Основной интерфейс: ${GREEN}http://localhost/${NC}"
    echo -e "  🔌 API: ${GREEN}http://localhost/api/${NC}"
    echo
    echo -e "${BLUE}Полезные команды:${NC}"
    echo -e "  📊 Статус сервисов: ${YELLOW}docker-compose ps${NC}"
    echo -e "  📝 Логи приложения: ${YELLOW}docker-compose logs web${NC}"
    echo -e "  🌐 Логи Nginx: ${YELLOW}docker-compose logs nginx${NC}"
    echo -e "  🛑 Остановка: ${YELLOW}docker-compose down${NC}"
    echo -e "  🔄 Перезапуск: ${YELLOW}docker-compose restart${NC}"
    echo
    echo -e "${BLUE}Следующие шаги:${NC}"
    echo -e "  1. Измените SECRET_KEY в .env файле"
    echo -e "  2. Настройте SSL сертификаты для HTTPS"
    echo -e "  3. Настройте мониторинг и логирование"
    echo
}

# Основная функция
main() {
    echo -e "${BLUE}🚀 Запуск автоматического развертывания проекта 'Мерч'${NC}"
    echo
    
    check_dependencies
    create_env_file
    create_directories
    check_ports
    build_images
    start_services
    check_health
    show_info
}

# Обработка аргументов командной строки
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        print_info "Остановка сервисов..."
        docker-compose down
        print_success "Сервисы остановлены"
        ;;
    "restart")
        print_info "Перезапуск сервисов..."
        docker-compose restart
        print_success "Сервисы перезапущены"
        ;;
    "logs")
        print_info "Показ логов..."
        docker-compose logs -f
        ;;
    "status")
        print_info "Статус сервисов..."
        docker-compose ps
        ;;
    "clean")
        print_warning "Очистка всех контейнеров и образов..."
        docker-compose down -v --rmi all
        print_success "Очистка завершена"
        ;;
    *)
        echo "Использование: $0 {deploy|stop|restart|logs|status|clean}"
        echo
        echo "Команды:"
        echo "  deploy   - Развертывание проекта (по умолчанию)"
        echo "  stop     - Остановка сервисов"
        echo "  restart  - Перезапуск сервисов"
        echo "  logs     - Показ логов"
        echo "  status   - Статус сервисов"
        echo "  clean    - Очистка всех контейнеров и образов"
        exit 1
        ;;
esac
