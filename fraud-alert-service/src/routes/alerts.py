import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from src.database import db
from src.models import (
    AlertCreate,
    AlertResponse,
    AlertStatus,
    StatusHistoryEntry,
    TransactionResponse,
    derive_risk_level,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _build_alert_response(alert_row, tx_row) -> AlertResponse:
    transaction = TransactionResponse(
        id=tx_row["id"],
        amount=tx_row["amount"],
        merchant_name=tx_row["merchant_name"],
        merchant_category=tx_row["merchant_category"],
        location=tx_row["location"],
        timestamp=tx_row["timestamp"],
        card_id=tx_row["card_id"],
        account_id=tx_row["account_id"],
    )
    history = [StatusHistoryEntry(**entry) for entry in json.loads(alert_row["status_history"])]
    return AlertResponse(
        id=alert_row["id"],
        transaction_id=alert_row["transaction_id"],
        transaction=transaction,
        risk_score=alert_row["risk_score"],
        risk_level=alert_row["risk_level"],
        status=alert_row["status"],
        analyst_id=alert_row["analyst_id"],
        contains_pii=bool(alert_row["contains_pii"]),
        created_at=alert_row["created_at"],
        updated_at=alert_row["updated_at"],
        status_history=history,
    )


@router.post("", response_model=AlertResponse, status_code=201)
def create_alert(body: AlertCreate):
    alert_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    risk_level = derive_risk_level(body.risk_score)
    initial_history = json.dumps([
        {"status": "pending", "timestamp": now.isoformat(), "changed_by": "system"}
    ])

    with db() as conn:
        tx_row = conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (str(body.transaction_id),)
        ).fetchone()
        if tx_row is None:
            raise HTTPException(status_code=404, detail="Transaction not found")

        existing = conn.execute(
            "SELECT id FROM alerts WHERE transaction_id = ?", (str(body.transaction_id),)
        ).fetchone()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Alert already exists for this transaction")

        conn.execute(
            """
            INSERT INTO alerts
                (id, transaction_id, risk_score, risk_level, status, analyst_id,
                 contains_pii, created_at, updated_at, status_history)
            VALUES (?, ?, ?, ?, 'pending', NULL, 1, ?, ?, ?)
            """,
            (
                alert_id,
                str(body.transaction_id),
                body.risk_score,
                risk_level.value,
                now.isoformat(),
                now.isoformat(),
                initial_history,
            ),
        )
        alert_row = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()

    return _build_alert_response(alert_row, tx_row)


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: str):
    with db() as conn:
        alert_row = conn.execute(
            "SELECT * FROM alerts WHERE id = ?", (alert_id,)
        ).fetchone()
        if alert_row is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        tx_row = conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (alert_row["transaction_id"],)
        ).fetchone()
    return _build_alert_response(alert_row, tx_row)
