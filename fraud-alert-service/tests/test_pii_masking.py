import pytest

from src.pii import mask_value

VALID_TRANSACTION = {
    "amount": 99.99,
    "merchant_name": "Shell",
    "merchant_category": "gas_station",
    "location": "Charlotte, NC",
    "timestamp": "2024-03-01T12:00:00Z",
    "card_id": "4111111111117890",
    "account_id": "ACC1234567890",
}


def create_transaction(client, card_id="4111111111117890", account_id="ACC1234567890"):
    payload = {**VALID_TRANSACTION, "card_id": card_id, "account_id": account_id}
    return client.post("/transactions", json=payload).json()


def create_alert(client, transaction_id):
    return client.post("/alerts", json={"transaction_id": transaction_id, "risk_score": 0.5}).json()


# ---------------------------------------------------------------------------
# Unit: mask_value
# ---------------------------------------------------------------------------

def test_mask_value_shows_last_4():
    assert mask_value("1234567890") == "****7890"


def test_mask_value_exactly_4_chars():
    assert mask_value("1234") == "****"


def test_mask_value_fewer_than_4_chars():
    assert mask_value("AB") == "****"


def test_mask_value_empty_string():
    assert mask_value("") == "****"


def test_mask_value_long_string():
    assert mask_value("A" * 50 + "1234") == "****1234"


# ---------------------------------------------------------------------------
# Default masking — POST /transactions
# ---------------------------------------------------------------------------

def test_post_transaction_masks_card_id_by_default(client):
    data = create_transaction(client)
    assert data["card_id"] == "****7890"
    assert data["account_id"] != "ACC1234567890"


def test_post_transaction_masks_account_id_by_default(client):
    data = create_transaction(client)
    assert data["account_id"] == "****7890"


# ---------------------------------------------------------------------------
# Default masking — GET /transactions/{id}
# ---------------------------------------------------------------------------

def test_get_transaction_masks_by_default(client):
    tx = create_transaction(client)
    fetched = client.get(f"/transactions/{tx['id']}").json()
    assert fetched["card_id"] == "****7890"
    assert fetched["account_id"] == "****7890"


def test_get_transaction_masks_last_4(client):
    tx = create_transaction(client, card_id="1234567890", account_id="9876543210")
    fetched = client.get(f"/transactions/{tx['id']}").json()
    assert fetched["card_id"] == "****7890"
    assert fetched["account_id"] == "****3210"


# ---------------------------------------------------------------------------
# Default masking — GET /alerts/{id}
# ---------------------------------------------------------------------------

def test_get_alert_masks_embedded_transaction_by_default(client):
    tx = create_transaction(client)
    alert = create_alert(client, tx["id"])
    fetched = client.get(f"/alerts/{alert['id']}").json()
    assert fetched["transaction"]["card_id"] == "****7890"
    assert fetched["transaction"]["account_id"] == "****7890"


# ---------------------------------------------------------------------------
# Authorized access — show_pii=true
# ---------------------------------------------------------------------------

def test_get_transaction_show_pii_returns_full_values(client):
    tx = create_transaction(client)
    fetched = client.get(f"/transactions/{tx['id']}?show_pii=true").json()
    assert fetched["card_id"] == "4111111111117890"
    assert fetched["account_id"] == "ACC1234567890"


def test_post_transaction_show_pii_returns_full_values(client):
    data = client.post("/transactions?show_pii=true", json=VALID_TRANSACTION).json()
    assert data["card_id"] == "4111111111117890"
    assert data["account_id"] == "ACC1234567890"


def test_get_alert_show_pii_returns_full_values(client):
    tx = create_transaction(client)
    alert = create_alert(client, tx["id"])
    fetched = client.get(f"/alerts/{alert['id']}?show_pii=true").json()
    assert fetched["transaction"]["card_id"] == "4111111111117890"
    assert fetched["transaction"]["account_id"] == "ACC1234567890"


def test_show_pii_false_same_as_omitting(client):
    tx = create_transaction(client)
    masked = client.get(f"/transactions/{tx['id']}?show_pii=false").json()
    assert masked["card_id"] == "****7890"
    assert masked["account_id"] == "****7890"


# ---------------------------------------------------------------------------
# Consistency
# ---------------------------------------------------------------------------

def test_masking_does_not_affect_stored_data(client):
    tx = create_transaction(client)
    # Default response is masked
    masked = client.get(f"/transactions/{tx['id']}").json()
    assert masked["card_id"] == "****7890"
    # show_pii=true still returns the full original value from storage
    full = client.get(f"/transactions/{tx['id']}?show_pii=true").json()
    assert full["card_id"] == "4111111111117890"


def test_contains_pii_flag_is_true(client):
    tx = create_transaction(client)
    alert = create_alert(client, tx["id"])
    assert alert["contains_pii"] is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_short_card_id_fully_masked(client):
    tx = create_transaction(client, card_id="1234", account_id="5678")
    fetched = client.get(f"/transactions/{tx['id']}").json()
    assert fetched["card_id"] == "****"
    assert fetched["account_id"] == "****"


def test_very_long_pii_only_shows_last_4(client):
    long_id = "X" * 40 + "9999"
    tx = create_transaction(client, card_id=long_id, account_id=long_id)
    fetched = client.get(f"/transactions/{tx['id']}").json()
    assert fetched["card_id"] == "****9999"
    assert fetched["account_id"] == "****9999"


@pytest.mark.parametrize("bad_value", ["yes", "1", "TRUE", "on"])
def test_show_pii_non_boolean_returns_422(client, bad_value):
    tx = create_transaction(client)
    response = client.get(f"/transactions/{tx['id']}?show_pii={bad_value}")
    assert response.status_code == 422
