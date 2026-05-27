"""
Finance domain Pydantic schemas.

Request schemas validate incoming API data; response schemas serialise
ORM objects via model_validate (from_attributes=True).

P&L calculation convention:
  gross_profit = total_revenue - total_cogs
  net_profit   = gross_profit  - total_expenses
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ── Requests ──────────────────────────────────────────────────────────────────

class CreateAccountRequest(BaseModel):
    account_code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=250)
    account_type: str = Field(..., description="asset|liability|equity|income|expense")
    parent_id: uuid.UUID | None = None


class CreateJournalLineRequest(BaseModel):
    account_id: uuid.UUID
    debit_amount: Decimal = Field(default=Decimal("0"), ge=0)
    credit_amount: Decimal = Field(default=Decimal("0"), ge=0)
    memo: str | None = None


class CreateJournalEntryRequest(BaseModel):
    entry_date: date
    description: str = Field(..., min_length=1, max_length=500)
    ref_type: str = Field(default="manual", description="sale|purchase|manual")
    ref_id: uuid.UUID | None = None
    lines: list[CreateJournalLineRequest] = Field(..., min_length=2)


# ── Responses ─────────────────────────────────────────────────────────────────

class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    parent_id: uuid.UUID | None
    account_code: str
    name: str
    account_type: str
    is_active: bool


class JournalLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    debit_amount: Decimal
    credit_amount: Decimal
    memo: str | None


class JournalEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    entry_number: str
    entry_date: date
    description: str
    ref_type: str
    ref_id: uuid.UUID | None
    status: str
    lines: list[JournalLineResponse]


# ── Reports ───────────────────────────────────────────────────────────────────

class TrialBalanceLine(BaseModel):
    """One row in the trial balance — one account, its debit/credit totals, net."""
    account_code: str
    name: str
    account_type: str
    total_debit: Decimal
    total_credit: Decimal
    net_balance: Decimal   # sign convention per account type (see finance.py models)


class TrialBalanceResponse(BaseModel):
    lines: list[TrialBalanceLine]
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool       # True when total_debit == total_credit


class ProfitAndLossReport(BaseModel):
    from_date: date | None
    to_date: date | None
    total_revenue: Decimal
    total_cogs: Decimal
    gross_profit: Decimal
    total_expenses: Decimal
    net_profit: Decimal
