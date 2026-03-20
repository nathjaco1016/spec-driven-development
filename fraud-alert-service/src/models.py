from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MerchantCategory(str, Enum):
    electronics = "electronics"
    travel = "travel"
    groceries = "groceries"
    gas_station = "gas_station"
    restaurant = "restaurant"
    entertainment = "entertainment"
    healthcare = "healthcare"
    utilities = "utilities"
    cash_advance = "cash_advance"
    other = "other"


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: float
    merchant_name: str
    merchant_category: MerchantCategory
    location: str
    timestamp: datetime
    card_id: str
    account_id: str

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v


class TransactionResponse(BaseModel):
    id: UUID
    amount: float
    merchant_name: str
    merchant_category: MerchantCategory
    location: str
    timestamp: datetime
    card_id: str
    account_id: str
