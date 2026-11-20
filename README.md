# MG Apparel Customer Order Portal

MG Apparel is a secure customer workspace for shipment visibility and order support. Customers see only their own synchronized ERP orders, while operations staff use a separate admin console for all customers and support tickets. The chatbot answers from the authenticated customer's sanitized order records and can create follow-up tickets without changing orders.

## Prerequisites

- Python 3.12+
- Node.js 20+
- Access to the ERP network endpoint and (optionally) a Gemini API key

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item .env.example .env
```

Set `ERP_API_KEY`, `JWT_SECRET_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` in `.env`. Never expose these to the frontend.

Install the frontend:

```powershell
cd frontend
npm install
cd ..
```

## Run

Initialize the database and synchronize the ERP snapshot (the sync is never run during page views):

```powershell
python -c "from backend.database import init_db; init_db()"
uvicorn backend.main:app --reload
```

With the backend running, use an authenticated admin action `POST /api/admin/sync` to perform the initial sync. Start the frontend in another terminal:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:3000`. Test customers use password `Portal@2026`; their email addresses come from the ERP (the supplied examples include `erik@nordline.example`, `hannah@kestrel.example`, and `lena@urbanthread.example`). Admin credentials are the values configured in `.env`.

Run the evaluation script while the backend is running:

```powershell
python backend\eval.py
```

## Security and data handling

Customer endpoints derive `customer_id` only from the verified JWT and return no internal ERP fields. Customer-visible order fields are PO, style, product, colour, quantity, order date, effective shipping date, status, shipped quantity, carrier, and tracking number. Unit price, margin, internal notes, credit limit, and payment risk remain internal. Admin endpoints require a separate admin-role token.

The sync fetches customers once and orders in pages of 50, writes through staging tables inside a transaction, and replaces the local snapshot only after the complete fetch succeeds. Failed transactions preserve the previous dataset. Normal customer pages and chatbot requests use DuckDB only and never call the ERP.

## Known limitations


Gemini is optional; without `GEMINI_API_KEY`, the chatbot uses a deterministic database-backed fallback. The ERP adapter accepts common field aliases but may need adjustment if the live mock API uses different names. Production deployments should use HTTPS, a managed secret, and a scheduled or audited sync mechanism.
