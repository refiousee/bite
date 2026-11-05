import sqlite3
from pathlib import Path

PROJECT_DIR = Path(r"C:\Users\user\bite")
DB_DIR = PROJECT_DIR / "database"
DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "bite.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS business_profile (
            business_id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL,
            business_category TEXT,
            opening_time TEXT,
            closing_time TEXT,
            default_minimum_stock INTEGER DEFAULT 5,
            default_safety_stock INTEGER DEFAULT 3,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            product_category TEXT,
            selling_price REAL NOT NULL,
            shelf_life_days INTEGER,
            minimum_stock INTEGER DEFAULT 5,
            safety_stock INTEGER DEFAULT 3,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id)
                REFERENCES business_profile(business_id),
            UNIQUE (business_id, product_name)
        );

        CREATE TABLE IF NOT EXISTS sales_history (
            sales_id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            sold_quantity INTEGER DEFAULT 0,
            stockout_status INTEGER DEFAULT 0,
            lost_demand_estimate INTEGER DEFAULT 0,
            selling_price REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id)
                REFERENCES business_profile(business_id),
            FOREIGN KEY (product_id)
                REFERENCES products(product_id),
            UNIQUE (business_id, product_id, date)
        );

        CREATE TABLE IF NOT EXISTS production_history (
            production_id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            opening_inventory INTEGER DEFAULT 0,
            production_quantity INTEGER DEFAULT 0,
            leftover_quantity INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id)
                REFERENCES business_profile(business_id),
            FOREIGN KEY (product_id)
                REFERENCES products(product_id),
            UNIQUE (business_id, product_id, date)
        );

        CREATE TABLE IF NOT EXISTS forecast_results (
            forecast_id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            forecast_date TEXT NOT NULL,
            horizon_days INTEGER,
            model_name TEXT,
            predicted_demand REAL,
            mae REAL,
            rmse REAL,
            mape REAL,
            data_quality TEXT,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id)
                REFERENCES business_profile(business_id),
            FOREIGN KEY (product_id)
                REFERENCES products(product_id)
        );

        CREATE TABLE IF NOT EXISTS production_recommendations (
            recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            forecast_id INTEGER,
            recommendation_date TEXT NOT NULL,
            forecasted_demand REAL,
            available_inventory INTEGER,
            safety_stock INTEGER,
            recommended_production INTEGER,
            estimated_leftover INTEGER,
            estimated_stockout INTEGER,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id)
                REFERENCES business_profile(business_id),
            FOREIGN KEY (product_id)
                REFERENCES products(product_id),
            FOREIGN KEY (forecast_id)
                REFERENCES forecast_results(forecast_id)
        );

        CREATE INDEX IF NOT EXISTS idx_sales_date
            ON sales_history(date);

        CREATE INDEX IF NOT EXISTS idx_sales_product
            ON sales_history(product_id);

        CREATE INDEX IF NOT EXISTS idx_production_date
            ON production_history(date);

        CREATE INDEX IF NOT EXISTS idx_forecast_product
            ON forecast_results(product_id);
        """)


def add_business(
    business_name,
    business_category,
    opening_time="07:00",
    closing_time="17:00",
    default_minimum_stock=5,
    default_safety_stock=3
):
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO business_profile (
                business_name, business_category,
                opening_time, closing_time,
                default_minimum_stock, default_safety_stock
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            business_name, business_category,
            opening_time, closing_time,
            default_minimum_stock, default_safety_stock
        ))
        return cursor.lastrowid


def get_business():
    with get_connection() as conn:
        row = conn.execute("""
            SELECT * FROM business_profile
            ORDER BY business_id LIMIT 1
        """).fetchone()
        return dict(row) if row else None


def update_business(business_id, **kwargs):
    allowed = [
        "business_name", "business_category",
        "opening_time", "closing_time",
        "default_minimum_stock", "default_safety_stock"
    ]

    updates = {k: v for k, v in kwargs.items() if k in allowed}

    if not updates:
        return False

    assignments = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [business_id]

    with get_connection() as conn:
        cursor = conn.execute(
            f"UPDATE business_profile SET {assignments}, "
            "updated_at = CURRENT_TIMESTAMP WHERE business_id = ?",
            values
        )
        return cursor.rowcount > 0


def add_product(
    business_id,
    product_name,
    product_category,
    selling_price,
    shelf_life_days,
    minimum_stock=5,
    safety_stock=3
):
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO products (
                business_id, product_name, product_category,
                selling_price, shelf_life_days,
                minimum_stock, safety_stock
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            business_id, product_name, product_category,
            selling_price, shelf_life_days,
            minimum_stock, safety_stock
        ))
        return cursor.lastrowid


def get_products(business_id=None, active_only=True):
    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if business_id is not None:
        query += " AND business_id = ?"
        params.append(business_id)

    if active_only:
        query += " AND is_active = 1"

    query += " ORDER BY product_id"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def check_database():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
        """).fetchall()
        return [row["name"] for row in rows]


def add_sales(
    business_id,
    product_id,
    date,
    sold_quantity,
    selling_price,
    stockout_status=0,
    lost_demand_estimate=None
):
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO sales_history (
                business_id,
                product_id,
                date,
                sold_quantity,
                stockout_status,
                lost_demand_estimate,
                selling_price
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            business_id,
            product_id,
            date,
            sold_quantity,
            stockout_status,
            lost_demand_estimate,
            selling_price
        ))

        return cursor.lastrowid


def get_sales(business_id, product_id=None):
    query = """
        SELECT *
        FROM sales_history
        WHERE business_id = ?
    """
    params = [business_id]

    if product_id is not None:
        query += " AND product_id = ?"
        params.append(product_id)

    query += " ORDER BY date ASC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def add_production(
    business_id,
    product_id,
    date,
    opening_inventory,
    production_quantity,
    leftover_quantity
):
    """Menyimpan riwayat produksi."""

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO production_history (
                business_id,
                product_id,
                date,
                opening_inventory,
                production_quantity,
                leftover_quantity
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                business_id,
                product_id,
                date,
                opening_inventory,
                production_quantity,
                leftover_quantity
            )
        )

        return cursor.lastrowid


def get_production(business_id, product_id=None):
    """Mengambil riwayat produksi berdasarkan bisnis dan produk."""

    query = """
        SELECT *
        FROM production_history
        WHERE business_id = ?
    """

    params = [business_id]

    if product_id is not None:
        query += " AND product_id = ?"
        params.append(product_id)

    query += " ORDER BY date ASC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

        return [dict(row) for row in rows]

