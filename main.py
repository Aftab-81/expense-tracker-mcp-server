from fastmcp import FastMCP
import os
import asyncio
import aiosqlite


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Horizon's /app directory should not be used for SQLite writes.
# /tmp is writable in the current deployment environment.
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
# DATABASE INITIALIZATION
# ============================================================

async def init_db():
    """
    Initializes the SQLite database.

    aiosqlite is used so database operations are asynchronous.
    WAL mode improves concurrent read/write behavior.
    """

    async with aiosqlite.connect(
        DB_PATH,
        timeout=10
    ) as db:

        # Enable WAL for better concurrent access.
        await db.execute(
            "PRAGMA journal_mode=WAL;"
        )

        # Wait for a busy database instead of immediately failing.
        await db.execute(
            "PRAGMA busy_timeout=10000;"
        )

        await db.execute(
            "PRAGMA foreign_keys=ON;"
        )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                description TEXT DEFAULT ''
            )
        """)

        await db.commit()


# ============================================================
# ADD EXPENSE
# ============================================================

@mcp.tool
async def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    description: str = ""
):
    """
    Adds a new expense to the database.

    This function is asynchronous and uses aiosqlite.
    """

    try:

        async with aiosqlite.connect(
            DB_PATH,
            timeout=10
        ) as db:

            await db.execute(
                "PRAGMA busy_timeout=10000;"
            )

            cursor = await db.execute(
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

            await db.commit()

            expense_id = cursor.lastrowid

            await cursor.close()

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

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# LIST ALL EXPENSES
# ============================================================

@mcp.tool
async def list_expenses():
    """
    Lists all expense entries.
    """

    try:

        async with aiosqlite.connect(
            DB_PATH,
            timeout=10
        ) as db:

            await db.execute(
                "PRAGMA busy_timeout=10000;"
            )

            db.row_factory = aiosqlite.Row

            cursor = await db.execute("""
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

            rows = await cursor.fetchall()

            await cursor.close()

            return [
                dict(row)
                for row in rows
            ]

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# LIST EXPENSES BY DATE RANGE
# ============================================================

@mcp.tool
async def list_expenses_till_date(
    start_date: str,
    end_date: str
):
    """
    Lists expenses between two dates.

    Both dates are inclusive.
    Expected format: YYYY-MM-DD
    """

    try:

        async with aiosqlite.connect(
            DB_PATH,
            timeout=10
        ) as db:

            await db.execute(
                "PRAGMA busy_timeout=10000;"
            )

            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
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

            rows = await cursor.fetchall()

            await cursor.close()

            return [
                dict(row)
                for row in rows
            ]

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# SUMMARISE EXPENSES
# ============================================================

@mcp.tool
async def summarise(
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

        async with aiosqlite.connect(
            DB_PATH,
            timeout=10
        ) as db:

            await db.execute(
                "PRAGMA busy_timeout=10000;"
            )

            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                query,
                params
            )

            rows = await cursor.fetchall()

            await cursor.close()

            return [
                dict(row)
                for row in rows
            ]

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# DELETE ALL EXPENSES
# ============================================================

@mcp.tool
async def delete_all_expenses(
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

        async with aiosqlite.connect(
            DB_PATH,
            timeout=10
        ) as db:

            await db.execute(
                "PRAGMA busy_timeout=10000;"
            )

            cursor = await db.execute(
                "DELETE FROM expenses"
            )

            deleted_count = cursor.rowcount

            await db.execute(
                """
                DELETE FROM sqlite_sequence
                WHERE name = 'expenses'
                """
            )

            await db.commit()

            await cursor.close()

            return {
                "status": "success",
                "message": "All expenses deleted",
                "deleted_count": deleted_count
            }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# DELETE ONE EXPENSE
# ============================================================

@mcp.tool
async def delete_expense(
    expense_id: int
):
    """
    Deletes one expense using its ID.
    """

    try:

        async with aiosqlite.connect(
            DB_PATH,
            timeout=10
        ) as db:

            await db.execute(
                "PRAGMA busy_timeout=10000;"
            )

            cursor = await db.execute(
                """
                DELETE FROM expenses
                WHERE id = ?
                """,
                (expense_id,)
            )

            if cursor.rowcount == 0:

                await cursor.close()

                return {
                    "status": "error",
                    "message": (
                        f"No expense found with id "
                        f"{expense_id}"
                    )
                }

            deleted_count = cursor.rowcount

            await db.commit()

            await cursor.close()

            return {
                "status": "success",
                "message": "Expense deleted successfully",
                "deleted_count": deleted_count,
                "id": expense_id
            }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# UPDATE EXPENSE
# ============================================================

@mcp.tool
async def update_expense(
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

        async with aiosqlite.connect(
            DB_PATH,
            timeout=10
        ) as db:

            await db.execute(
                "PRAGMA busy_timeout=10000;"
            )

            cursor = await db.execute(
                query,
                params
            )

            if cursor.rowcount == 0:

                await cursor.close()

                return {
                    "status": "error",
                    "message": (
                        f"No expense found with id "
                        f"{expense_id}"
                    )
                }

            updated_count = cursor.rowcount

            await db.commit()

            await cursor.close()

            return {
                "status": "success",
                "message": "Expense updated successfully",
                "updated_count": updated_count,
                "id": expense_id
            }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# DATABASE STATUS
# ============================================================

@mcp.tool
async def database_status():
    """
    Checks whether the SQLite database can be opened,
    written to and read from.
    """

    try:

        async with aiosqlite.connect(
            DB_PATH,
            timeout=10
        ) as db:

            await db.execute(
                "PRAGMA busy_timeout=10000;"
            )

            await db.execute("""
                CREATE TABLE IF NOT EXISTS _write_test (
                    id INTEGER PRIMARY KEY
                )
            """)

            await db.execute(
                """
                INSERT OR REPLACE INTO _write_test (id)
                VALUES (1)
                """
            )

            await db.commit()

            cursor = await db.execute(
                """
                SELECT id
                FROM _write_test
                WHERE id = 1
                """
            )

            row = await cursor.fetchone()

            await cursor.close()

            await db.execute(
                """
                DELETE FROM _write_test
                WHERE id = 1
                """
            )

            await db.commit()

        return {
            "status": "success",
            "database_path": DB_PATH,
            "database_exists": os.path.exists(DB_PATH),
            "database_writable": True,
            "database_readable": row is not None,
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
async def get_categories():
    """
    Returns categories and subcategories from categories.json.
    """

    # File reading is small, but using async-friendly file I/O
    # is preferable in an async server.
    loop = asyncio.get_running_loop()

    def read_file():
        with open(
            CATEGORIES_PATH,
            "r",
            encoding="utf-8"
        ) as f:
            return f.read()

    return await loop.run_in_executor(
        None,
        read_file
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    # Initialize the database before starting MCP.
    asyncio.run(init_db())

    print("=" * 60)
    print("ExpenseTracker MCP Server")
    print("=" * 60)
    print(f"Database path: {DB_PATH}")
    print(f"Database exists: {os.path.exists(DB_PATH)}")
    print("Database driver: aiosqlite")
    print("SQLite journal mode: WAL")
    print("=" * 60)

    mcp.run()