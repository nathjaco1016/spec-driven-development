from src.models import TransactionResponse


def mask_value(value: str) -> str:
    if len(value) <= 4:
        return "****"
    return f"****{value[-4:]}"


def mask_transaction(tx: TransactionResponse) -> TransactionResponse:
    return tx.model_copy(update={
        "card_id": mask_value(tx.card_id),
        "account_id": mask_value(tx.account_id),
    })
