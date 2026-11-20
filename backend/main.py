from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .auth import create_token, current_user, require_role, verify_password
from .chatbot import answer
from .config import settings
from .database import execute, init_db, query
from .schemas import ChatRequest, LoginRequest, TicketUpdate
from .sync import sync_erp


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="MG Apparel Portal", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
api = APIRouter(prefix="/api")


@api.post("/auth/login")
def login(data: LoginRequest):
    if settings.admin_email and data.email == settings.admin_email and data.password == settings.admin_password:
        return {"access_token": create_token(data.email, "admin"), "role": "admin",
                "user": {"email": data.email}}
    rows = query("SELECT * FROM customers WHERE lower(portal_email) = lower(?)", [data.email])
    if not rows or not verify_password(data.password, rows[0]["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    customer = rows[0]
    user = {k: customer[k] for k in ("customer_id", "company_name", "contact_name", "portal_email")}
    return {"access_token": create_token(data.email, "customer", customer["customer_id"]),
            "role": "customer", "user": user}


@api.get("/auth/me")
def me(user: dict = Depends(current_user)):
    return user


@api.get("/customer/orders")
def customer_orders(status: str | None = None, search: str | None = None,
                    user: dict = Depends(require_role("customer"))):
    sql = """SELECT po_no, style_no, product, colour, qty_pcs, order_date,
                    COALESCE(revised_ship_date, promised_ship_date) expected_ship_date,
                    status, shipped_qty, carrier, tracking_no
             FROM orders WHERE customer_id = ?"""
    params = [user["customer_id"]]
    if status and status != "All":
        sql += " AND status = ?"; params.append(status)
    if search:
        sql += " AND lower(po_no) LIKE lower(?)"; params.append(f"%{search}%")
    sql += " ORDER BY order_date DESC"
    return query(sql, params)


@api.get("/customer/orders/{po_no}")
def customer_order(po_no: str, user: dict = Depends(require_role("customer"))):
    rows = query("""SELECT po_no, style_no, product, colour, qty_pcs, order_date,
                    COALESCE(revised_ship_date, promised_ship_date) expected_ship_date,
                    status, shipped_qty, carrier, tracking_no
                    FROM orders WHERE po_no = ? AND customer_id = ?""",
                 [po_no, user["customer_id"]])
    if not rows:
        raise HTTPException(404, "Order not found")
    return rows[0]


@api.post("/customer/chat")
def chat(data: ChatRequest, user: dict = Depends(require_role("customer"))):
    message, ticket_id = answer(user["customer_id"], data.message)
    return {"message": message, "ticket_id": ticket_id}


@api.get("/admin/dashboard")
def admin_dashboard(_: dict = Depends(require_role("admin"))):
    return {
        "customers": query("SELECT count(*) count FROM customers")[0]["count"],
        "orders": query("SELECT count(*) count FROM orders")[0]["count"],
        "tickets": query("SELECT count(*) count FROM support_tickets WHERE status != 'Resolved'")[0]["count"],
        "delayed": query("SELECT count(*) count FROM orders WHERE lower(status) = 'delayed'")[0]["count"],
    }


@api.get("/admin/customers")
def admin_customers(search: str | None = None, _: dict = Depends(require_role("admin"))):
    sql = "SELECT customer_id, company_name, contact_name, portal_email, country FROM customers"
    params = []
    if search:
        sql += " WHERE lower(company_name) LIKE lower(?) OR lower(customer_id) LIKE lower(?)"
        params = [f"%{search}%", f"%{search}%"]
    return query(sql + " ORDER BY company_name", params)


@api.get("/admin/orders")
def admin_orders(status: str | None = None, search: str | None = None,
                 _: dict = Depends(require_role("admin"))):
    sql = """SELECT o.po_no, o.customer_id, c.company_name, o.product, o.qty_pcs,
                    o.status, COALESCE(o.revised_ship_date, o.promised_ship_date) expected_ship_date,
                    o.tracking_no FROM orders o LEFT JOIN customers c ON c.customer_id=o.customer_id"""
    params = []
    clauses = []
    if status and status != "All":
        clauses.append("o.status = ?"); params.append(status)
    if search:
        clauses.append("(lower(o.po_no) LIKE lower(?) OR lower(c.company_name) LIKE lower(?))")
        params.extend([f"%{search}%", f"%{search}%"])
    if clauses: sql += " WHERE " + " AND ".join(clauses)
    return query(sql + " ORDER BY o.order_date DESC", params)


@api.get("/admin/tickets")
def admin_tickets(_: dict = Depends(require_role("admin"))):
    return query("""SELECT t.ticket_id, t.customer_id, c.company_name, t.po_no, t.message,
                    t.created_at, t.status FROM support_tickets t
                    LEFT JOIN customers c ON c.customer_id=t.customer_id
                    ORDER BY t.created_at DESC""")


@api.patch("/admin/tickets/{ticket_id}")
def update_ticket(ticket_id: str, data: TicketUpdate, _: dict = Depends(require_role("admin"))):
    if data.status not in {"Pending", "In Progress", "Resolved"}:
        raise HTTPException(400, "Invalid ticket status")
    execute("UPDATE support_tickets SET status = ? WHERE ticket_id = ?", [data.status, ticket_id])
    return {"ok": True}


@api.post("/admin/sync")
async def admin_sync(_: dict = Depends(require_role("admin"))):
    try:
        return await sync_erp()
    except Exception as exc:
        detail = str(exc).strip() or type(exc).__name__
        raise HTTPException(502, f"ERP synchronization failed: {detail}") from exc


app.include_router(api)
