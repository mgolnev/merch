import sqlite3

def create_category_order_table():
    conn = sqlite3.connect('merchandise.db')
    cursor = conn.cursor()
    
    # Создаем таблицу для хранения порядка товаров в категориях
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS category_order (
        sku TEXT,
        category TEXT,
        position INTEGER,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (sku, category),
        FOREIGN KEY (sku) REFERENCES products(sku)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Таблица category_order успешно создана!")

if __name__ == "__main__":
    create_category_order_table() 