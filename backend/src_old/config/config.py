import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Конфигурация базы данных
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///merchandise.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Секретный ключ
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here') 