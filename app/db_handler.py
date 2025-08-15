import sqlite3
import pandas as pd

DB_PATH = "data/transactions.db"

def create_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_transaction(date, description, amount, category=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO transactions (date, description, amount, category) VALUES (?, ?, ?, ?)",
                   (date, description, amount, category))
    conn.commit()
    conn.close()

def get_transactions():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    return df
