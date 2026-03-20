import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.database import db
from src.models import TransactionCreate, TransactionResponse

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _row_to_response(row) -> TransactionResponse:
    return TransactionResponse(
        id=row["id"],
        amount=row["amount"],
        merchant_name=row["merchant_name"],
        merchant_category=row["merchant_category"],
        location=row["location"],
        timestamp=row["timestamp"],
        card_id=row["card_id"],
        account_id=row["account_id"],
    )


@router.post("", response_model=TransactionResponse, status_code=201)
def create_transaction(body: TransactionCreate):
    transaction_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            """
            INSERT INTO transactions
                (id, amount, merchant_name, merchant_category, location, timestamp, card_id, account_id)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction_id,
                body.amount,
                body.merchant_name,
                body.merchant_category.value,
                body.location,
                body.timestamp.isoformat(),
                body.card_id,
                body.account_id,
            ),
        )
        row = conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
        ).fetchone()
    return _row_to_response(row)


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: str):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _row_to_response(row)
