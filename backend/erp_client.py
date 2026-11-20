import httpx

from .config import settings


async def fetch_erp(path: str, params: dict | None = None):
    headers = {"X-API-Key": settings.erp_api_key}
    async with httpx.AsyncClient(base_url=settings.erp_base_url, timeout=20) as client:
        response = await client.get(path, params=params, headers=headers)
        response.raise_for_status()
        return response.json()


async def fetch_snapshot() -> tuple[list[dict], list[dict]]:
    customer_response = await fetch_erp("/v1/customers")
    customers = customer_response.get("data", []) if isinstance(customer_response, dict) else customer_response
    all_orders: list[dict] = []
    page = 1
    while True:
        try:
            data = await fetch_erp("/v1/orders", {"page": page, "page_size": 50})
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 503 and page > 1:
                break
            raise
        if isinstance(data, dict):
            rows = data.get("data", data.get("orders", []))
        else:
            rows = data
        all_orders.extend(rows)
        if len(rows) < 50:
            break
        page += 1
    return customers, all_orders
