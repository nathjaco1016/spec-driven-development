from datetime import datetime
from enum import Enum
from typing import Optional
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
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "amount": 149.99,
                "merchant_name": "Best Buy",
                "merchant_category": "electronics",
                "location": "Charlotte, NC",
                "timestamp": "2024-05-01T14:30:00Z",
                "card_id": "4111111111111234",
                "account_id": "ACC0000000001",
            }
        },
    )

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


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertStatus(str, Enum):
    pending = "pending"
    under_review = "under_review"
    confirmed_fraud = "confirmed_fraud"
    false_positive = "false_positive"
    escalated = "escalated"


class StatusHistoryEntry(BaseModel):
    status: AlertStatus
    timestamp: datetime
    changed_by: str


class AlertCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "transaction_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "risk_score": 0.85,
            }
        },
    )

    transaction_id: UUID
    risk_score: float

    @field_validator("risk_score")
    @classmethod
    def risk_score_in_range(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("risk_score must be between 0.0 and 1.0 inclusive")
        return v


class AlertResponse(BaseModel):
    id: UUID
    transaction_id: UUID
    transaction: TransactionResponse
    risk_score: float
    risk_level: RiskLevel
    status: AlertStatus
    analyst_id: Optional[str]
    contains_pii: bool
    created_at: datetime
    updated_at: datetime
    status_history: list[StatusHistoryEntry]


TERMINAL_STATUSES = {AlertStatus.confirmed_fraud, AlertStatus.false_positive, AlertStatus.escalated}

VALID_TRANSITIONS = {
    AlertStatus.pending: {AlertStatus.under_review},
    AlertStatus.under_review: {AlertStatus.confirmed_fraud, AlertStatus.false_positive, AlertStatus.escalated},
}


class AssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analyst_id: str


class StatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: AlertStatus
    changed_by: str


class SummaryResponse(BaseModel):
    total_alerts: int
    by_status: dict[str, int]
    by_risk_level: dict[str, int]
    avg_resolution_time_seconds: Optional[float]


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse]
    total: int


def derive_risk_level(score: float) -> RiskLevel:
    if score < 0.3:
        return RiskLevel.low
    if score < 0.6:
        return RiskLevel.medium
    if score < 0.8:
        return RiskLevel.high
    return RiskLevel.critical
