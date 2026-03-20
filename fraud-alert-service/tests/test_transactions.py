import pytest

VALID_PAYLOAD = {
    "amount": 49.99,
    "merchant_name": "Best Buy",
    "merchant_category": "electronics",
    "location": "Charlotte, NC",
    "timestamp": "2024-01-15T10:30:00Z",
    "card_id": "4111111111111234",
    "account_id": "ACC9876543210",
}


# ---------------------------------------------------------------------------
# POST /transactions
# ---------------------------------------------------------------------------

def test_create_transaction_returns_201(client):
    response = client.post("/transactions", json=VALID_PAYLOAD)
    assert response.status_code == 201


def test_create_transaction_returns_generated_id(client):
    response = client.post("/transactions", json=VALID_PAYLOAD)
    data = response.json()
    assert "id" in data
    # id was not in the request body
    assert data["id"] not in VALID_PAYLOAD.values()


def test_create_transaction_returns_all_fields(client):
    response = client.post("/transactions", json=VALID_PAYLOAD)
    data = response.json()
    for field in ("amount", "merchant_name", "merchant_category", "location", "timestamp"):
        assert field in data


def test_create_transaction_missing_required_field(client):
    for field in VALID_PAYLOAD:
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != field}
        response = client.post("/transactions", json=payload)
        assert response.status_code == 422, f"Expected 422 when '{field}' is missing"


def test_create_transaction_amount_zero_returns_422(client):
    payload = {**VALID_PAYLOAD, "amount": 0}
    response = client.post("/transactions", json=payload)
    assert response.status_code == 422


def test_create_transaction_amount_negative_returns_422(client):
    payload = {**VALID_PAYLOAD, "amount": -10.00}
    response = client.post("/transactions", json=payload)
    assert response.status_code == 422


def test_create_transaction_invalid_merchant_category(client):
    payload = {**VALID_PAYLOAD, "merchant_category": "invalid_category"}
    response = client.post("/transactions", json=payload)
    assert response.status_code == 422


def test_create_transaction_invalid_timestamp(client):
    payload = {**VALID_PAYLOAD, "timestamp": "not-a-date"}
    response = client.post("/transactions", json=payload)
    assert response.status_code == 422


def test_create_transaction_extra_fields_rejected(client):
    payload = {**VALID_PAYLOAD, "unexpected_field": "value"}
    response = client.post("/transactions", json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize("category", [
    "electronics", "travel", "groceries", "gas_station", "restaurant",
    "entertainment", "healthcare", "utilities", "cash_advance", "other",
])
def test_create_transaction_all_valid_categories(client, category):
    payload = {**VALID_PAYLOAD, "merchant_category": category}
    response = client.post("/transactions", json=payload)
    assert response.status_code == 201
    assert response.json()["merchant_category"] == category


# ---------------------------------------------------------------------------
# GET /transactions/{id}
# ---------------------------------------------------------------------------

def test_get_transaction_returns_200(client):
    created = client.post("/transactions", json=VALID_PAYLOAD).json()
    response = client.get(f"/transactions/{created['id']}")
    assert response.status_code == 200


def test_get_transaction_returns_correct_data(client):
    created = client.post("/transactions", json=VALID_PAYLOAD).json()
    fetched = client.get(f"/transactions/{created['id']}").json()
    assert fetched["id"] == created["id"]
    assert fetched["amount"] == VALID_PAYLOAD["amount"]
    assert fetched["merchant_name"] == VALID_PAYLOAD["merchant_name"]


def test_get_transaction_not_found(client):
    response = client.get("/transactions/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_get_transaction_pii_masked_by_default(client):
    """PII fields are masked in responses but full values are preserved in storage."""
    created = client.post("/transactions", json=VALID_PAYLOAD).json()
    fetched = client.get(f"/transactions/{created['id']}").json()
    assert fetched["card_id"] == "****1234"
    assert fetched["account_id"] != VALID_PAYLOAD["account_id"]
    # show_pii=true reveals the stored values
    full = client.get(f"/transactions/{created['id']}?show_pii=true").json()
    assert full["card_id"] == VALID_PAYLOAD["card_id"]
    assert full["account_id"] == VALID_PAYLOAD["account_id"]
