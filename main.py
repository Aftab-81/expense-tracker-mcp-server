from fastmcp import FastMCP
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "expense.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

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
                description TEXT DEFAULT ''
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

@mcp.tool
def list_expenses_till_date(start_date, end_date):
    """
    Lists expenses entries within the given date range
    """

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date DESC", (start_date, end_date))
        cols = [column[0] for column in cursor.description]
        return [dict(zip(cols, rows)) for rows in cursor.fetchall()]

@mcp.tool
def summarise(start_date, end_date, category = None):
    """
    Summarise expenses by category within an inclusive date range
    """
    with sqlite3.connect(DB_PATH) as conn:
        query = (
            """
            SELECT category, SUM(amount)
            FROM expenses 
            WHERE date BETWEEN ? AND ?
            """
        )
        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY category ORDER BY category ASC"
        cursor = conn.execute(query, params)
        cols = [column[0] for column in cursor.description]
        return [dict(zip(cols, rows)) for rows in cursor.fetchall()]

@mcp.tool
def delete_all_expense(confirm: bool = False):
    """
    Deletes all expense records from the database (keeps the table structure).
    """
    if not confirm:
        return {"status": "error", "message": "Confirmation required"}

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("DELETE FROM expenses")
        deleted_count = cursor.rowcount
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'expenses'") # Reset the auto-increment counter
        return {"status": "success", "deleted_count": deleted_count}

@mcp.tool
def delete_expense(expense_id: int):
    """
    Deletes a single expense entry by its id.
    Use list_expenses first to find the id.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        if cursor.rowcount == 0:
            return {"status": "error", "message": f"No expense found with id {expense_id}"}
        deleted_count = cursor.rowcount
        return {"status": "success", "deleted_count": deleted_count}

@mcp.tool
def update_expense(expense_id: int, date: str = None, amount: float = None, category: str = None, subcategory: str = None, description: str = None):
    """
    Updates an existing expense entry by its id.
    Use list_expenses first to find the id.
    """
    with sqlite3.connect(DB_PATH) as conn:
        # Build the update query dynamically based on provided parameters
        fields_to_update = []
        params = []

        if date is not None:
            fields_to_update.append("date = ?")
            params.append(date)
        if amount is not None:
            fields_to_update.append("amount = ?")
            params.append(amount)
        if category is not None:
            fields_to_update.append("category = ?")
            params.append(category)
        if subcategory is not None:
            fields_to_update.append("subcategory = ?")
            params.append(subcategory)
        if description is not None:
            fields_to_update.append("description = ?")
            params.append(description)

        if not fields_to_update:
            return {"status": "error", "message": "No fields provided for update"}

        params.append(expense_id)
        query = f"UPDATE expenses SET {', '.join(fields_to_update)} WHERE id = ?"
        cursor = conn.execute(query, params)

        if cursor.rowcount == 0:
            return {"status": "error", "message": f"No expense found with id {expense_id}"}

        return {"status": "success", "updated_count": cursor.rowcount}


## expense -> is just lije http:// or file// -- Its the name that we chose it. It doesn't need to be a real protocol.
## categories -> is the name of the resource that we are exposing. It can be anything, but it should be unique within the context of the MCP server.
## mime_type -> is the type of the resource that we are exposing. In our case JSON
@mcp.resource("expense://categories", mime_type = "application/json")
def get_categories():
    """
    Returns the list of categories and subcategories from the categories.json file.
    """
    with open(CATEGORIES_PATH, "r") as f:
        return f.read()

if __name__ == "__main__":
    mcp.run()


    