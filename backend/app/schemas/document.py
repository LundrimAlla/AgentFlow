from typing import Annotated, Literal

from pydantic import Field

from app.schemas.chat import Contract, TraceStep


class DocumentRequest(Contract):
    sample_id: Literal["invoice-001"]
    turnstile_token: Annotated[str, Field(min_length=1, max_length=2048)]


class InvoiceItem(Contract):
    description: Annotated[str, Field(min_length=1, max_length=200)]
    quantity: Annotated[int, Field(gt=0, le=10000)]
    unit_price_cents: Annotated[int, Field(ge=0, le=10000000)]
    total_cents: Annotated[int, Field(ge=0, le=100000000)]


class Invoice(Contract):
    invoice_number: Annotated[str, Field(min_length=1, max_length=50)]
    invoice_date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    supplier: Annotated[str, Field(min_length=1, max_length=200)]
    customer: Annotated[str, Field(min_length=1, max_length=200)]
    currency: Literal["EUR"]
    items: Annotated[list[InvoiceItem], Field(min_length=1, max_length=10)]
    subtotal_cents: Annotated[int, Field(ge=0, le=100000000)]
    tax_cents: Annotated[int, Field(ge=0, le=100000000)]
    total_cents: Annotated[int, Field(ge=0, le=100000000)]


class DocumentResponse(Contract):
    request_id: str
    mode: Literal["live"]
    sample_id: Literal["invoice-001"]
    invoice: Invoice
    trace: list[TraceStep]
