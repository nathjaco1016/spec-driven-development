import json
import uuid
from datetime import datetime, timezone

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from src.database import db
from src.models import (
    AlertCreate,
    AlertListResponse,
    AlertResponse,
    AlertStatus,
    AssignRequest,
    RiskLevel,
    StatusHistoryEntry,
    StatusUpdateRequest,
    SummaryResponse,
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


@router.get("", response_model=AlertListResponse)
def list_alerts(
    status: AlertStatus | None = Query(default=None),
    risk_level: RiskLevel | None = Query(default=None),
    analyst_id: str | None = Query(default=None),
    created_after: datetime | None = Query(default=None),
    created_before: datetime | None = Query(default=None),
    show_pii: Literal["true", "false"] | None = Query(default=None),
):
    conditions = []
    params = []

    if status is not None:
        conditions.append("a.status = ?")
        params.append(status.value)

    if risk_level is not None:
        conditions.append("a.risk_level = ?")
        params.append(risk_level.value)

    if analyst_id is not None:
        if analyst_id == "unassigned":
            conditions.append("a.analyst_id IS NULL")
        else:
            conditions.append("a.analyst_id = ?")
            params.append(analyst_id)

    if created_after is not None:
        conditions.append("a.created_at >= ?")
        params.append(created_after.isoformat())

    if created_before is not None:
        conditions.append("a.created_at <= ?")
        params.append(created_before.isoformat())

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f"""
        SELECT a.*, t.id AS t_id, t.amount, t.merchant_name, t.merchant_category,
               t.location, t.timestamp, t.card_id, t.account_id
        FROM alerts a
        JOIN transactions t ON a.transaction_id = t.id
        {where}
        ORDER BY a.created_at DESC
    """

    with db() as conn:
        rows = conn.execute(query, params).fetchall()

    reveal_pii = show_pii == "true"
    alerts = []
    for row in rows:
        tx = TransactionResponse(
            id=row["t_id"],
            amount=row["amount"],
            merchant_name=row["merchant_name"],
            merchant_category=row["merchant_category"],
            location=row["location"],
            timestamp=row["timestamp"],
            card_id=row["card_id"],
            account_id=row["account_id"],
        )
        if not reveal_pii:
            tx = mask_transaction(tx)
        history = [StatusHistoryEntry(**e) for e in json.loads(row["status_history"])]
        alerts.append(AlertResponse(
            id=row["id"],
            transaction_id=row["transaction_id"],
            transaction=tx,
            risk_score=row["risk_score"],
            risk_level=row["risk_level"],
            status=row["status"],
            analyst_id=row["analyst_id"],
            contains_pii=bool(row["contains_pii"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            status_history=history,
        ))

    return AlertListResponse(alerts=alerts, total=len(alerts))


@router.get("/summary", response_model=SummaryResponse)
def get_summary():
    by_status = {s.value: 0 for s in AlertStatus}
    by_risk_level = {r.value: 0 for r in RiskLevel}
    total_alerts = 0
    resolution_times = []

    with db() as conn:
        for row in conn.execute("SELECT status, risk_level, created_at, status_history FROM alerts").fetchall():
            total_alerts += 1
            by_status[row["status"]] += 1
            by_risk_level[row["risk_level"]] += 1

            status = AlertStatus(row["status"])
            if status in TERMINAL_STATUSES:
                history = json.loads(row["status_history"])
                terminal_entry = next(
                    (e for e in reversed(history) if AlertStatus(e["status"]) in TERMINAL_STATUSES),
                    None,
                )
                if terminal_entry:
                    created = datetime.fromisoformat(row["created_at"])
                    resolved = datetime.fromisoformat(terminal_entry["timestamp"])
                    resolution_times.append((resolved - created).total_seconds())

    avg = sum(resolution_times) / len(resolution_times) if resolution_times else None

    return SummaryResponse(
        total_alerts=total_alerts,
        by_status=by_status,
        by_risk_level=by_risk_level,
        avg_resolution_time_seconds=avg,
    )


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
