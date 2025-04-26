import pytest
import sqlite3
import os

@pytest.fixture
def test_db():
    """Создает тестовую базу данных в памяти"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    
    # Создаем схему базы данных
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS products (
            sku TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            image_url TEXT
        );

        CREATE TABLE IF NOT EXISTS category_scoring (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL,
            category TEXT NOT NULL,
            base_score REAL,
            manual_score REAL,
            position INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(sku, category)
        );

        CREATE TABLE IF NOT EXISTS weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sessions_weight REAL DEFAULT 1.0,
            views_weight REAL DEFAULT 1.0,
            cart_weight REAL DEFAULT 1.0,
            checkout_weight REAL DEFAULT 1.0,
            orders_gross_weight REAL DEFAULT 1.0,
            orders_net_weight REAL DEFAULT 1.0,
            discount_penalty REAL DEFAULT 0.0
        );
    ''')
    
    # Добавляем тестовые данные
    conn.executescript('''
        INSERT INTO products (sku, name, category, image_url)
        VALUES 
            ('TEST1', 'Test Product 1', 'Test Category', 'http://test.com/img1.jpg'),
            ('TEST2', 'Test Product 2', 'Test Category', 'http://test.com/img2.jpg');

        INSERT INTO weights (
            sessions_weight, views_weight, cart_weight, 
            checkout_weight, orders_gross_weight, orders_net_weight, discount_penalty
        ) VALUES (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0);
    ''')
    
    conn.commit()
    
    yield conn
    
    conn.close()

@pytest.fixture
def app_with_db(app, test_db):
    """Настраивает приложение для использования тестовой базы данных"""
    def get_test_db():
        return test_db
    
    app.config['TESTING'] = True
    app.get_db = get_test_db
    
    return app

@pytest.fixture
def client(app_with_db):
    """Создает тестовый клиент"""
    return app_with_db.test_client() 