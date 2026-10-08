from fastmcp import FastMCP
import os
import sqlite3
import json

# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "expense.db")
CATEGORIES_PATH = os.path.join(BASE_DIR, "categories.json")

mcp = FastMCP(name="ExpenseTracker")


# ---------------------------------------------------------
# Database helper
# ---------------------------------------------------------

def get_connection():
    """
    Creates a READ/WRITE SQLite connection.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)

    # Make sure SQLite uses normal read/write mode.
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    return conn


def init_db():
    """
    Creates the expenses table if it does not exist.
    """

    # Make sure the directory exists
    os.makedirs(BASE_DIR, exist_ok=True)

    with get_connection() as conn:
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

        conn.commit()


# Initialize database when server starts
init_db()


# ---------------------------------------------------------
# ADD EXPENSE
# ---------------------------------------------------------

@mcp.tool
def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    description: str = ""
):
    """
    Adds a new expense to the SQLite database.
    """

    try:
        with get_connection() as conn:

            cursor = conn.execute(
                """
                INSERT INTO expenses
                (date, amount, category, subcategory, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    date,
                    amount,
                    category,
                    subcategory,
                    description
                )
            )

            conn.commit()

            expense_id = cursor.lastrowid

        return {
            "status": "success",
            "message": "Expense added successfully",
            "id": expense_id,
            "date": date,
            "amount": amount,
            "category": category,
            "subcategory": subcategory,
            "description": description
        }

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": f"Database error: {str(e)}",
            "database_path": DB_PATH
        }


# ---------------------------------------------------------
# LIST ALL EXPENSES
# ---------------------------------------------------------

@mcp.tool
def list_expenses():
    """
    Lists all expense entries from the database.
    """

    try:
        with get_connection() as conn:

            cursor = conn.execute("""
                SELECT id, date, amount, category,
                       subcategory, description
                FROM expenses
                ORDER BY date DESC, id DESC
            """)

            rows = cursor.fetchall()

            columns = [
                column[0]
                for column in cursor.description
            ]

            return [
                dict(zip(columns, row))
                for row in rows
            ]

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ---------------------------------------------------------
# LIST EXPENSES BY DATE RANGE
# ---------------------------------------------------------

@mcp.tool
def list_expenses_till_date(
    start_date: str,
    end_date: str
):
    """
    Lists expenses within the given inclusive date range.
    """

    try:
        with get_connection() as conn:

            cursor = conn.execute(
                """
                SELECT id, date, amount, category,
                       subcategory, description
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (start_date, end_date)
            )

            rows = cursor.fetchall()

            columns = [
                column[0]
                for column in cursor.description
            ]

            return [
                dict(zip(columns, row))
                for row in rows
            ]

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ---------------------------------------------------------
# SUMMARISE
# ---------------------------------------------------------

@mcp.tool
def summarise(
    start_date: str,
    end_date: str,
    category: str = None
):
    """
    Summarises expenses by category within an inclusive date range.
    """

    try:
        query = """
            SELECT
                category,
                SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """

        params = [
            start_date,
            end_date
        ]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += """
            GROUP BY category
            ORDER BY category ASC
        """

        with get_connection() as conn:

            cursor = conn.execute(
                query,
                params
            )

            rows = cursor.fetchall()

            columns = [
                column[0]
                for column in cursor.description
            ]

            return [
                dict(zip(columns, row))
                for row in rows
            ]

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ---------------------------------------------------------
# DELETE ALL
# ---------------------------------------------------------

@mcp.tool
def delete_all_expenses(confirm: bool = False):
    """
    Deletes all expense records.
    Requires explicit confirmation.
    """

    if not confirm:
        return {
            "status": "error",
            "message": "Confirmation required. Set confirm=true."
        }

    try:
        with get_connection() as conn:

            cursor = conn.execute(
                "DELETE FROM expenses"
            )

            deleted_count = cursor.rowcount

            conn.execute(
                "DELETE FROM sqlite_sequence "
                "WHERE name = 'expenses'"
            )

            conn.commit()

        return {
            "status": "success",
            "deleted_count": deleted_count
        }

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ---------------------------------------------------------
# DELETE SINGLE EXPENSE
# ---------------------------------------------------------

@mcp.tool
def delete_expense(expense_id: int):
    """
    Deletes a single expense by ID.
    """

    try:
        with get_connection() as conn:

            cursor = conn.execute(
                "DELETE FROM expenses WHERE id = ?",
                (expense_id,)
            )

            if cursor.rowcount == 0:
                return {
                    "status": "error",
                    "message": f"No expense found with id {expense_id}"
                }

            conn.commit()

            return {
                "status": "success",
                "deleted_count": cursor.rowcount,
                "id": expense_id
            }

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ---------------------------------------------------------
# UPDATE EXPENSE
# ---------------------------------------------------------

@mcp.tool
def update_expense(
    expense_id: int,
    date: str = None,
    amount: float = None,
    category: str = None,
    subcategory: str = None,
    description: str = None
):
    """
    Updates an existing expense.
    """

    fields = []
    params = []

    if date is not None:
        fields.append("date = ?")
        params.append(date)

    if amount is not None:
        fields.append("amount = ?")
        params.append(amount)

    if category is not None:
        fields.append("category = ?")
        params.append(category)

    if subcategory is not None:
        fields.append("subcategory = ?")
        params.append(subcategory)

    if description is not None:
        fields.append("description = ?")
        params.append(description)

    if not fields:
        return {
            "status": "error",
            "message": "No fields provided for update"
        }

    params.append(expense_id)

    query = f"""
        UPDATE expenses
        SET {", ".join(fields)}
        WHERE id = ?
    """

    try:
        with get_connection() as conn:

            cursor = conn.execute(
                query,
                params
            )

            if cursor.rowcount == 0:
                return {
                    "status": "error",
                    "message": f"No expense found with id {expense_id}"
                }

            conn.commit()

            return {
                "status": "success",
                "updated_count": cursor.rowcount,
                "id": expense_id
            }

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ---------------------------------------------------------
# DATABASE STATUS / DEBUG TOOL
# ---------------------------------------------------------

@mcp.tool
def database_status():
    """
    Returns information about the SQLite database.
    Useful for diagnosing connection and permission problems.
    """

    try:
        exists = os.path.exists(DB_PATH)

        if not exists:
            return {
                "status": "error",
                "message": "Database file does not exist",
                "database_path": DB_PATH
            }

        with get_connection() as conn:

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

            conn.commit()

            # Test an actual write
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _write_test (
                    id INTEGER PRIMARY KEY
                )
            """)

            conn.commit()

            return {
                "status": "success",
                "database_path": DB_PATH,
                "database_exists": True,
                "database_writable": True,
                "absolute_path": os.path.abspath(DB_PATH)
            }

    except Exception as e:
        return {
            "status": "error",
            "database_path": DB_PATH,
            "database_writable": False,
            "error_type": type(e).__name__,
            "error": str(e)
        }


# ---------------------------------------------------------
# RESOURCE
# ---------------------------------------------------------
# expense -> is just lije http:// or file// -- Its the name that we chose it. It doesn't need to be a real protocol.
# categories -> is the name of the resource that we are exposing. It can be anything, but it should be unique within the context of the MCP server.
# mime_type -> is the type of the resource that we are exposing. In our case JSON


@mcp.resource(
    "expense://categories",
    mime_type="application/json"
)
def get_categories():
    """
    Returns categories and subcategories from categories.json.
    """

    with open(
        CATEGORIES_PATH,
        "r",
        encoding="utf-8"
    ) as f:
        return f.read()


# ---------------------------------------------------------
# START SERVER
# ---------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("ExpenseTracker MCP Server")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print(f"Database exists: {os.path.exists(DB_PATH)}")
    print(f"Database directory: {BASE_DIR}")
    print("=" * 60)

    mcp.run()