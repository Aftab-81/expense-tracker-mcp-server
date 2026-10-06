from fastmcp import FastMCP
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "expense.db")

mcp = FastMCP(name = "ExpenseTracker")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                description TEXT DEFAULT '',
            )
        """)

init_db()

@mcp.tool
def add_expense(date, amount, category, subcategory = '', description = ''):
    """
    Adds a new expense to the database.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("INSERT INTO expenses (date, amount, category, subcategory, description) VALUES (?, ?, ?, ?, ?)", (date, amount, category, subcategory, description))
        return {"status": "success", "id": cursor.lastrowid}

@mcp.tool
def list_expenses():
    """
    Lists all expense entries from the database.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT * FROM expenses ORDER BY date DESC")
        cols = [column[0] for column in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

if __name__ == "__main__":
    mcp.run()