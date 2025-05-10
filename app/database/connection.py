import sqlite3
from contextlib import contextmanager
import os

DATABASE_PATH = os.environ.get('DATABASE_PATH', 'merchandise.db')

@contextmanager
def get_db_connection():
    """Контекстный менеджер для безопасной работы с соединением к БД"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close() 