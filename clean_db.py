import sqlite3

def clean_database():
    conn = sqlite3.connect('merchandise.db')
    cursor = conn.cursor()

    # Удаление лишней таблицы product
    cursor.execute("DROP TABLE IF EXISTS product")
    
    conn.commit()
    conn.close()
    print("База данных очищена от лишних таблиц!")

if __name__ == "__main__":
    clean_database() 