import sqlite3

DB_FILE = 'merchandise.db'

def clean_categories_and_links():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Удаляем все связи товаров с категориями
    cursor.execute('DELETE FROM product_categories')
    # Удаляем все категории
    cursor.execute('DELETE FROM feed_categories')
    conn.commit()
    print('Таблицы feed_categories и product_categories очищены!')
    conn.close()

if __name__ == '__main__':
    clean_categories_and_links() 