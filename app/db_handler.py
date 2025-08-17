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
        category TEXT,
        type TEXT NOT NULL CHECK(type IN ('income', 'expense'))
    )
    """)
    conn.commit()
    conn.close()


def add_transaction(date, description, amount, category=None, t_type="expense"):
    if amount <= 0:
        raise ValueError("Transaction amount must be positive.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (date, description, amount, category, type) 
        VALUES (?, ?, ?, ?, ?)
    """, (date, description, amount, category, t_type))
    conn.commit()
    conn.close()



def get_transactions():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    return df

def delete_transaction(transaction_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
