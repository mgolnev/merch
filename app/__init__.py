from flask import Flask
from flask_cors import CORS
import os

def create_app():
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Настройка CORS для безопасности API
    CORS(app)
    
    # Настройка секретного ключа
    app.secret_key = os.environ.get('SECRET_KEY', 'default-dev-key-change-in-production')
    
    # Регистрация blueprints
    from app.routes.products import products_bp
    from app.routes.categories import categories_bp
    from app.routes.weights import weights_bp
    from app.routes.main import main_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(weights_bp)
    
    # Инициализация БД
    from app.database.init import init_db
    init_db()
    
    return app 