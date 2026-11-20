from datetime import date, datetime
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    role: str
    user: dict


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class TicketUpdate(BaseModel):
    status: str


class CustomerOrder(BaseModel):
    po_no: str
    style_no: str | None = None
    product: str | None = None
    colour: str | None = None
    qty_pcs: int | None = None
    order_date: date | None = None
    expected_ship_date: date | None = None
    status: str | None = None
    shipped_qty: int | None = None
    carrier: str | None = None
    tracking_no: str | None = None
