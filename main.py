from fastmcp import FastMCP
import os
import sqlite3


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# /app is the application directory in Horizon and should not
# be used for SQLite write operations.
#
# /tmp is writable by the running container.
DB_PATH = "/tmp/expense.db"

CATEGORIES_PATH = os.path.join(
    BASE_DIR,
    "categories.json"
)


# ============================================================
# MCP SERVER
# ============================================================

mcp = FastMCP(name="ExpenseTracker")


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Creates a read/write SQLite connection.

    The database is stored in /tmp because the application
    directory (/app) is not writable in the Horizon container.
    """

    return sqlite3.connect(
        DB_PATH,
        timeout=10
    )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    """
    Creates the expenses table if it does not already exist.
    """

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


# Initialize database when the MCP server starts
init_db()


# ============================================================
# ADD EXPENSE
# ============================================================

@mcp.tool
def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    description: str = ""
):
    """
    Adds a new expense to the database.
    """

    try:

        with get_connection() as conn:

            cursor = conn.execute(
                """
                INSERT INTO expenses
                (
                    date,
                    amount,
                    category,
                    subcategory,
                    description
                )
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

            return {
                "status": "success",
                "message": "Expense added successfully",
                "id": cursor.lastrowid,
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


# ============================================================
# LIST ALL EXPENSES
# ============================================================

@mcp.tool
def list_expenses():
    """
    Lists all expense entries from the database.
    """

    try:

        with get_connection() as conn:

            cursor = conn.execute("""
                SELECT
                    id,
                    date,
                    amount,
                    category,
                    subcategory,
                    description
                FROM expenses
                ORDER BY date DESC, id DESC
            """)

            columns = [
                column[0]
                for column in cursor.description
            ]

            rows = cursor.fetchall()

            return [
                dict(zip(columns, row))
                for row in rows
            ]

    except sqlite3.Error as e:

        return {
            "status": "error",
            "message": f"Database error: {str(e)}"
        }


# ============================================================
# LIST EXPENSES BETWEEN TWO DATES
# ============================================================

@mcp.tool
def list_expenses_till_date(
    start_date: str,
    end_date: str
):
    """
    Lists expenses between start_date and end_date.
    Both dates are inclusive.

    Expected format:
    YYYY-MM-DD
    """

    try:

        with get_connection() as conn:

            cursor = conn.execute(
                """
                SELECT
                    id,
                    date,
                    amount,
                    category,
                    subcategory,
                    description
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (
                    start_date,
                    end_date
                )
            )

            columns = [
                column[0]
                for column in cursor.description
            ]

            rows = cursor.fetchall()

            return [
                dict(zip(columns, row))
                for row in rows
            ]

    except sqlite3.Error as e:

        return {
            "status": "error",
            "message": f"Database error: {str(e)}"
        }


# ============================================================
# SUMMARISE EXPENSES
# ============================================================

@mcp.tool
def summarise(
    start_date: str,
    end_date: str,
    category: str = None
):
    """
    Summarises expenses by category within an inclusive
    date range.
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

            query += """
                AND category = ?
            """

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

            columns = [
                column[0]
                for column in cursor.description
            ]

            rows = cursor.fetchall()

            return [
                dict(zip(columns, row))
                for row in rows
            ]

    except sqlite3.Error as e:

        return {
            "status": "error",
            "message": f"Database error: {str(e)}"
        }


# ============================================================
# DELETE ALL EXPENSES
# ============================================================

@mcp.tool
def delete_all_expenses(
    confirm: bool = False
):
    """
    Deletes all expense records.

    Requires confirm=True.
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

            # Reset AUTOINCREMENT sequence
            conn.execute(
                """
                DELETE FROM sqlite_sequence
                WHERE name = 'expenses'
                """
            )

            conn.commit()

            return {
                "status": "success",
                "message": "All expenses deleted",
                "deleted_count": deleted_count
            }

    except sqlite3.Error as e:

        return {
            "status": "error",
            "message": f"Database error: {str(e)}"
        }


# ============================================================
# DELETE ONE EXPENSE
# ============================================================

@mcp.tool
def delete_expense(
    expense_id: int
):
    """
    Deletes one expense using its ID.
    """

    try:

        with get_connection() as conn:

            cursor = conn.execute(
                """
                DELETE FROM expenses
                WHERE id = ?
                """,
                (expense_id,)
            )

            if cursor.rowcount == 0:

                return {
                    "status": "error",
                    "message": (
                        f"No expense found with id "
                        f"{expense_id}"
                    )
                }

            conn.commit()

            return {
                "status": "success",
                "message": "Expense deleted successfully",
                "deleted_count": cursor.rowcount,
                "id": expense_id
            }

    except sqlite3.Error as e:

        return {
            "status": "error",
            "message": f"Database error: {str(e)}"
        }


# ============================================================
# UPDATE EXPENSE
# ============================================================

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

    Only the fields supplied by the caller are updated.
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
                    "message": (
                        f"No expense found with id "
                        f"{expense_id}"
                    )
                }

            conn.commit()

            return {
                "status": "success",
                "message": "Expense updated successfully",
                "updated_count": cursor.rowcount,
                "id": expense_id
            }

    except sqlite3.Error as e:

        return {
            "status": "error",
            "message": f"Database error: {str(e)}"
        }


# ============================================================
# DATABASE STATUS
# ============================================================

@mcp.tool
def database_status():
    """
    Tests whether the SQLite database can actually be
    created, opened, read and written.
    """

    try:

        # Test database connection
        with get_connection() as conn:

            # Test table creation
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _write_test (
                    id INTEGER PRIMARY KEY
                )
            """)

            # Test actual INSERT
            conn.execute(
                """
                INSERT INTO _write_test (id)
                VALUES (1)
                """
            )

            # Test DELETE
            conn.execute(
                """
                DELETE FROM _write_test
                WHERE id = 1
                """
            )

            conn.commit()

        return {
            "status": "success",
            "database_path": DB_PATH,
            "database_exists": os.path.exists(DB_PATH),
            "database_writable": True,
            "message": "SQLite read/write test passed"
        }

    except Exception as e:

        return {
            "status": "error",
            "database_path": DB_PATH,
            "database_exists": os.path.exists(DB_PATH),
            "database_writable": False,
            "error_type": type(e).__name__,
            "error": str(e)
        }


# ============================================================
# CATEGORIES RESOURCE
# ============================================================

@mcp.resource(
    "expense://categories",
    mime_type="application/json"
)
def get_categories():
    """
    Returns the categories.json file.
    """

    with open(
        CATEGORIES_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        return f.read()


# ============================================================
# START MCP SERVER
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("ExpenseTracker MCP Server")
    print("=" * 60)
    print(f"Database path: {DB_PATH}")
    print(f"Database exists: {os.path.exists(DB_PATH)}")
    print("=" * 60)

    mcp.run()