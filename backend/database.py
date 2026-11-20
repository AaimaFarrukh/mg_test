from pathlib import Path
from threading import Lock

import duckdb

DB_PATH = Path(__file__).resolve().parent.parent / "mg_apparel.db"
_lock = Lock()


def connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH))


def init_db() -> None:
    with _lock, connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id VARCHAR PRIMARY KEY, company_name VARCHAR NOT NULL,
                contact_name VARCHAR, portal_email VARCHAR UNIQUE NOT NULL,
                country VARCHAR, account_manager VARCHAR, password_hash VARCHAR NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orders (
                po_no VARCHAR PRIMARY KEY, customer_id VARCHAR NOT NULL, style_no VARCHAR,
                product VARCHAR, colour VARCHAR, qty_pcs INTEGER, unit_price_usd DOUBLE,
                order_date DATE, promised_ship_date DATE, revised_ship_date DATE,
                status VARCHAR, shipped_qty INTEGER, carrier VARCHAR, tracking_no VARCHAR,
                customer_instructions VARCHAR, internal_note VARCHAR, margin_pct DOUBLE
            );
            CREATE TABLE IF NOT EXISTS support_tickets (
                ticket_id VARCHAR PRIMARY KEY, customer_id VARCHAR NOT NULL, po_no VARCHAR,
                message VARCHAR NOT NULL, created_at TIMESTAMP NOT NULL,
                status VARCHAR NOT NULL DEFAULT 'Pending'
            );
            CREATE INDEX IF NOT EXISTS orders_customer_idx ON orders(customer_id);
            CREATE INDEX IF NOT EXISTS tickets_customer_idx ON support_tickets(customer_id);
            """
        )


def query(sql: str, params: list = []) -> list[dict]:
    with _lock, connection() as conn:
        result = conn.execute(sql, params)
        columns = [item[0] for item in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]


def execute(sql: str, params: list = []) -> None:
    with _lock, connection() as conn:
        conn.execute(sql, params)
