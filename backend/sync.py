from .auth import hash_password
from .database import connection
from .erp_client import fetch_snapshot


def _value(row: dict, *names, default=None):
    for name in names:
        if name in row:
            return row[name]
    return default


async def sync_erp() -> dict:
    customers, orders = await fetch_snapshot()
    customers_by_email: dict[str, dict] = {}
    for item in customers:
        email = str(_value(item, "portal_email", "email", default="")).strip().lower()
        if email:
            customers_by_email[email] = item
    orders_by_po: dict[str, dict] = {}
    for item in orders:
        po_no = str(_value(item, "po_no", "po_number", default="")).strip()
        if po_no:
            orders_by_po[po_no] = item
    customers = list(customers_by_email.values())
    orders = list(orders_by_po.values())
    with connection() as conn:
        conn.execute("BEGIN")
        try:
            conn.execute("""CREATE OR REPLACE TEMP TABLE staging_customers (
                customer_id VARCHAR, company_name VARCHAR, contact_name VARCHAR,
                portal_email VARCHAR, country VARCHAR, account_manager VARCHAR, password_hash VARCHAR
            )""")
            conn.execute("""CREATE OR REPLACE TEMP TABLE staging_orders (
                po_no VARCHAR, customer_id VARCHAR, style_no VARCHAR, product VARCHAR,
                colour VARCHAR, qty_pcs INTEGER, unit_price_usd DOUBLE, order_date DATE,
                promised_ship_date DATE, revised_ship_date DATE, status VARCHAR,
                shipped_qty INTEGER, carrier VARCHAR, tracking_no VARCHAR,
                customer_instructions VARCHAR, internal_note VARCHAR, margin_pct DOUBLE
            )""")
            conn.execute("DELETE FROM staging_customers")
            conn.execute("DELETE FROM staging_orders")
            for item in customers:
                cid = str(_value(item, "customer_id", "id"))
                email = _value(item, "portal_email", "email", default=f"{cid}@mg-apparel.example")
                conn.execute(
                    "INSERT INTO staging_customers VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [cid, _value(item, "company_name", "company"), _value(item, "contact_name"),
                     email, _value(item, "country"), _value(item, "account_manager"),
                     hash_password("Portal@2026")],
                )
            for item in orders:
                conn.execute(
                    "INSERT INTO staging_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [str(_value(item, "po_no", "po_number")), str(_value(item, "customer_id")),
                     _value(item, "style_no"), _value(item, "product"), _value(item, "colour", "color"),
                     _value(item, "qty_pcs", "quantity"), _value(item, "unit_price_usd"),
                     _value(item, "order_date"), _value(item, "promised_ship_date"),
                     _value(item, "revised_ship_date"), _value(item, "status"),
                     _value(item, "shipped_qty"), _value(item, "carrier"), _value(item, "tracking_no"),
                     _value(item, "customer_instructions"), _value(item, "internal_note"),
                     _value(item, "margin_pct")],
                )
            staging_duplicates = conn.execute(
                """SELECT portal_email, count(*) AS duplicate_count
                   FROM staging_customers GROUP BY portal_email
                   HAVING count(*) > 1"""
            ).fetchall()
            if staging_duplicates:
                raise RuntimeError(f"Duplicate staging customer emails: {staging_duplicates}")
            conn.execute("DROP TABLE customers")
            conn.execute("""CREATE TABLE customers (
                customer_id VARCHAR PRIMARY KEY,
                company_name VARCHAR NOT NULL,
                contact_name VARCHAR,
                portal_email VARCHAR UNIQUE NOT NULL,
                country VARCHAR,
                account_manager VARCHAR,
                password_hash VARCHAR NOT NULL
            )""")
            written_emails: set[str] = set()
            for row in conn.execute("SELECT * FROM staging_customers").fetchall():
                normalized_row = list(row)
                normalized_row[3] = str(normalized_row[3]).strip().lower()
                if normalized_row[3] in written_emails:
                    continue
                conn.execute(
                    "DELETE FROM customers WHERE customer_id = ? OR trim(lower(portal_email)) = ?",
                    [normalized_row[0], normalized_row[3]],
                )
                conn.execute(
                    "INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?)",
                    normalized_row,
                )
                written_emails.add(normalized_row[3])
            conn.execute("DROP TABLE orders")
            conn.execute("""CREATE TABLE orders (
                po_no VARCHAR PRIMARY KEY,
                customer_id VARCHAR NOT NULL,
                style_no VARCHAR,
                product VARCHAR,
                colour VARCHAR,
                qty_pcs INTEGER,
                unit_price_usd DOUBLE,
                order_date DATE,
                promised_ship_date DATE,
                revised_ship_date DATE,
                status VARCHAR,
                shipped_qty INTEGER,
                carrier VARCHAR,
                tracking_no VARCHAR,
                customer_instructions VARCHAR,
                internal_note VARCHAR,
                margin_pct DOUBLE
            )""")
            written_pos: set[str] = set()
            for row in conn.execute("SELECT * FROM staging_orders").fetchall():
                po_no = str(row[0]).strip()
                if po_no in written_pos:
                    continue
                conn.execute(
                    "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    list(row),
                )
                written_pos.add(po_no)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    return {"customers": len(customers), "orders": len(orders)}
