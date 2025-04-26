import pytest
import sqlite3
import json
import io
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def setup_test_data(test_db):
    """Добавляет тестовые данные перед каждым тестом"""
    with test_db:
        # Очищаем таблицы
        test_db.execute('DELETE FROM products')
        test_db.execute('DELETE FROM category_scoring')
        test_db.execute('DELETE FROM weights')
        
        # Добавляем тестовые данные
        test_db.execute('''
            INSERT INTO products (sku, name, category, image_url)
            VALUES 
                ('TEST1', 'Test Product 1', 'Test Category', 'http://test.com/img1.jpg'),
                ('TEST2', 'Test Product 2', 'Test Category', 'http://test.com/img2.jpg')
        ''')
        
        test_db.execute('''
            INSERT INTO weights (
                sessions_weight, views_weight, cart_weight, 
                checkout_weight, orders_gross_weight, orders_net_weight, discount_penalty
            ) VALUES (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0)
        ''')

def test_get_categories(client):
    """Тест получения списка категорий"""
    response = client.get('/api/categories')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert 'Test Category' in data

def test_get_category_scoring(client, test_db):
    """Тест получения скоринга для категории"""
    # Добавляем тестовые данные скоринга
    test_db.execute('''
        INSERT INTO category_scoring (sku, category, base_score, manual_score, position)
        VALUES ('TEST1', 'Test Category', 1.0, 1.5, 1)
    ''')
    test_db.commit()
    
    response = client.get('/api/category_scoring?category=Test Category')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) >= 1
    assert any(item['sku'] == 'TEST1' and item['manual_score'] == 1.5 for item in data)

def test_update_category_scoring(client):
    """Тест обновления скоринга для товара"""
    data = {
        'sku': 'TEST1',
        'category': 'Test Category',
        'manual_score': 1.5,
        'position': 1
    }
    
    response = client.post('/api/update_category_scoring', json=data)
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result['status'] == 'success'

def test_batch_update_category_scoring(client):
    """Тест пакетного обновления скоринга"""
    data = {
        'category': 'Test Category',
        'items': [
            {
                'sku': 'TEST1',
                'manual_score': 2.0,
                'position': 1
            },
            {
                'sku': 'TEST2',
                'manual_score': 1.5,
                'position': 2
            }
        ]
    }
    
    response = client.post('/api/batch_update_category_scoring', json=data)
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result['status'] == 'success'

def test_export_category_scoring(client, test_db):
    """Тест экспорта скоринга в CSV"""
    # Добавляем тестовые данные
    test_db.execute('''
        INSERT INTO category_scoring (sku, category, base_score, manual_score, position)
        VALUES ('TEST1', 'Test Category', 1.0, 1.5, 1)
    ''')
    test_db.commit()
    
    response = client.get('/api/export_category_scoring?category=Test Category')
    assert response.status_code == 200
    assert response.mimetype == 'text/csv'
    assert 'attachment' in response.headers['Content-Disposition']
    
    # Проверяем содержимое CSV
    content = response.data.decode('utf-8')
    assert 'TEST1' in content
    assert 'Test Product 1' in content

def test_import_category_scoring(client):
    """Тест импорта скоринга из CSV"""
    csv_data = 'SKU,Наименование,Базовый скор,Итоговый скор\nTEST1,Test Product 1,1.0,2.0\n'
    
    response = client.post('/api/import_category_scoring',
                         data={'file': (io.BytesIO(csv_data.encode()), 'test.csv')},
                         content_type='multipart/form-data')
    
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result['status'] == 'success'

def test_invalid_category_scoring(client):
    """Тест обработки невалидных данных"""
    # Тест с несуществующей категорией
    response = client.get('/api/category_scoring?category=NonExistent')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 0
    
    # Тест с невалидным manual_score
    data = {
        'sku': 'TEST1',
        'category': 'Test Category',
        'manual_score': 'invalid',
        'position': 1
    }
    response = client.post('/api/update_category_scoring', json=data)
    assert response.status_code == 400
    
    # Тест с невалидным position
    data = {
        'sku': 'TEST1',
        'category': 'Test Category',
        'manual_score': 1.5,
        'position': -1
    }
    response = client.post('/api/update_category_scoring', json=data)
    assert response.status_code == 400 