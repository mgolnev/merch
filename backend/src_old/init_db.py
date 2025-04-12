from app import app
from database import db
from models.merchandise import Merchandise

def init_db():
    with app.app_context():
        # Создаем все таблицы
        db.create_all()
        
        # Добавляем тестовые данные
        if not Merchandise.query.first():
            test_items = [
                Merchandise(name='Футболка', description='Хлопковая футболка', price=1000, quantity=50),
                Merchandise(name='Кепка', description='Бейсболка', price=500, quantity=30),
                Merchandise(name='Рюкзак', description='Городской рюкзак', price=2000, quantity=20)
            ]
            
            for item in test_items:
                db.session.add(item)
            
            db.session.commit()
            print('База данных инициализирована с тестовыми данными')
        else:
            print('База данных уже существует')

if __name__ == '__main__':
    init_db() 