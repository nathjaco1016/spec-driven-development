import json
import uuid
from datetime import datetime, timezone

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from src.database import db
from src.models import (
    AlertCreate,
    AlertResponse,
    AlertStatus,
    AssignRequest,
    StatusHistoryEntry,
    StatusUpdateRequest,
    TERMINAL_STATUSES,
    VALID_TRANSITIONS,
    TransactionResponse,
    derive_risk_level,
)
from src.pii import mask_transaction

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _build_alert_response(alert_row, tx_row, show_pii: bool = False) -> AlertResponse:
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
    if not show_pii:
        transaction = mask_transaction(transaction)
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
def get_alert(alert_id: str, show_pii: Literal["true", "false"] | None = Query(default=None)):
    with db() as conn:
        alert_row = conn.execute(
            "SELECT * FROM alerts WHERE id = ?", (alert_id,)
        ).fetchone()
        if alert_row is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        tx_row = conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (alert_row["transaction_id"],)
        ).fetchone()
    return _build_alert_response(alert_row, tx_row, show_pii=(show_pii == "true"))


@router.patch("/{alert_id}/assign", response_model=AlertResponse)
def assign_analyst(alert_id: str, body: AssignRequest):
    now = datetime.now(timezone.utc)
    with db() as conn:
        alert_row = conn.execute(
            "SELECT * FROM alerts WHERE id = ?", (alert_id,)
        ).fetchone()
        if alert_row is None:
            raise HTTPException(status_code=404, detail="Alert not found")

        current_status = AlertStatus(alert_row["status"])
        if current_status in TERMINAL_STATUSES:
            raise HTTPException(status_code=409, detail="Cannot assign analyst to a terminal alert")

        conn.execute(
            "UPDATE alerts SET analyst_id = ?, updated_at = ? WHERE id = ?",
            (body.analyst_id, now.isoformat(), alert_id),
        )
        alert_row = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        tx_row = conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (alert_row["transaction_id"],)
        ).fetchone()
    return _build_alert_response(alert_row, tx_row)


@router.patch("/{alert_id}/status", response_model=AlertResponse)
def update_status(alert_id: str, body: StatusUpdateRequest):
    now = datetime.now(timezone.utc)
    with db() as conn:
        alert_row = conn.execute(
            "SELECT * FROM alerts WHERE id = ?", (alert_id,)
        ).fetchone()
        if alert_row is None:
            raise HTTPException(status_code=404, detail="Alert not found")

        current_status = AlertStatus(alert_row["status"])
        allowed = VALID_TRANSITIONS.get(current_status, set())
        if body.status not in allowed:
            raise HTTPException(status_code=409, detail=f"Invalid transition: {current_status} → {body.status}")

        if body.status == AlertStatus.under_review and alert_row["analyst_id"] is None:
            raise HTTPException(status_code=409, detail="Cannot move to under_review without an assigned analyst")

        history = json.loads(alert_row["status_history"])
        history.append({"status": body.status.value, "timestamp": now.isoformat(), "changed_by": body.changed_by})

        conn.execute(
            "UPDATE alerts SET status = ?, status_history = ?, updated_at = ? WHERE id = ?",
            (body.status.value, json.dumps(history), now.isoformat(), alert_id),
        )
        alert_row = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        tx_row = conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (alert_row["transaction_id"],)
        ).fetchone()
    return _build_alert_response(alert_row, tx_row)
