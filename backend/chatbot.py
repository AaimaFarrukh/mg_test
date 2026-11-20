import re
import uuid
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from .config import settings
from .database import execute, query


def _safe_orders(customer_id: str) -> list[dict]:
    return query(
        """SELECT po_no, product, colour, qty_pcs, promised_ship_date, revised_ship_date,
                  status, shipped_qty, carrier, tracking_no
           FROM orders WHERE customer_id = ? ORDER BY order_date DESC""", [customer_id]
    )


def _ticket_intent(message: str) -> bool:
    return bool(re.search(r"\b(cancel|change|complaint|complain|issue|problem)\b", message, re.I))


def answer(customer_id: str, message: str) -> tuple[str, str | None]:
    orders = _safe_orders(customer_id)
    if _ticket_intent(message):
        po = next((o["po_no"] for o in orders if o["po_no"].lower() in message.lower()), None)
        ticket_id = f"T-{uuid.uuid4().hex[:8].upper()}"
        execute(
            "INSERT INTO support_tickets VALUES (?, ?, ?, ?, ?, 'Pending')",
            [ticket_id, customer_id, po, message, datetime.now(timezone.utc)],
        )
        return f"I've logged support ticket {ticket_id}. Your account manager will follow up.", ticket_id
    if re.search(r"\b(other|another|all customers|someone else|internal|margin|price|credit)\b", message, re.I):
        return "I can only help with your own shipment information and customer-visible order details.", None
    if not orders:
        return "I could not find any order information for your account.", None
    requested_pos = re.findall(r"\bPO[- ]?\d+\b", message, re.I)
    for requested in requested_pos:
        normalized = re.sub(r"^PO[- ]?", "PO-", requested.upper())
        matched = next((o for o in orders if o["po_no"].upper() == normalized), None)
        if not matched:
            return f"I could not find {normalized} in your account.", None
    context = "\n".join(str(o) for o in orders)
    if settings.gemini_api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel("gemini-3.8-flash")
            prompt = ("Answer briefly using only the sanitized records below. Never invent values, "
                      "never discuss internal fields, and say unavailable when absent.\n"
                      f"Records:\n{context}\nQuestion: {message}")
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(model.generate_content, prompt)
            try:
                response = future.result(timeout=5)
                executor.shutdown(wait=False)
                return response.text, None
            except Exception:
                executor.shutdown(wait=False)
                raise
        except Exception:
            pass
    lower = message.lower()
    matches = [o for o in orders if o["po_no"].lower() in lower]
    selected = matches[0] if matches else orders[0]
    date = selected["revised_ship_date"] or selected["promised_ship_date"] or "not available"
    if "track" in lower:
        return f"Tracking for {selected['po_no']}: {selected['tracking_no'] or 'not available'}.", None
    if "how many" in lower and "delay" in lower:
        return f"You have {sum(str(o['status']).lower() == 'delayed' for o in orders)} delayed order(s).", None
    return f"{selected['po_no']} is {selected['status'] or 'not available'}, with expected ship date {date}.", None
