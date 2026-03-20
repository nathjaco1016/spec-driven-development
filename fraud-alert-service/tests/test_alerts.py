import pytest

VALID_TRANSACTION = {
    "amount": 249.99,
    "merchant_name": "Apple Store",
    "merchant_category": "electronics",
    "location": "Charlotte, NC",
    "timestamp": "2024-01-15T10:30:00Z",
    "card_id": "4111111111111234",
    "account_id": "ACC9876543210",
}


def create_transaction(client):
    return client.post("/transactions", json=VALID_TRANSACTION).json()


def create_alert(client, transaction_id, risk_score=0.75):
    return client.post("/alerts", json={"transaction_id": transaction_id, "risk_score": risk_score})


# ---------------------------------------------------------------------------
# POST /alerts
# ---------------------------------------------------------------------------

def test_create_alert_returns_201(client):
    tx = create_transaction(client)
    response = create_alert(client, tx["id"])
    assert response.status_code == 201


def test_create_alert_returns_generated_id(client):
    tx = create_transaction(client)
    data = create_alert(client, tx["id"]).json()
    assert "id" in data
    assert data["id"] != tx["id"]


def test_create_alert_status_is_pending(client):
    tx = create_transaction(client)
    data = create_alert(client, tx["id"]).json()
    assert data["status"] == "pending"


def test_create_alert_analyst_id_is_null(client):
    tx = create_transaction(client)
    data = create_alert(client, tx["id"]).json()
    assert data["analyst_id"] is None


def test_create_alert_contains_pii_true(client):
    tx = create_transaction(client)
    data = create_alert(client, tx["id"]).json()
    assert data["contains_pii"] is True


def test_create_alert_initial_status_history(client):
    tx = create_transaction(client)
    data = create_alert(client, tx["id"]).json()
    assert len(data["status_history"]) == 1
    entry = data["status_history"][0]
    assert entry["status"] == "pending"
    assert entry["changed_by"] == "system"
    assert "timestamp" in entry


def test_create_alert_has_created_at_and_updated_at(client):
    from datetime import datetime
    tx = create_transaction(client)
    data = create_alert(client, tx["id"]).json()
    # Both timestamps must be valid ISO datetimes
    created = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
    updated = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
    # On creation they should be equal
    assert created == updated


def test_create_alert_embeds_transaction(client):
    tx = create_transaction(client)
    data = create_alert(client, tx["id"]).json()
    assert "transaction" in data
    assert data["transaction"]["id"] == tx["id"]


def test_create_alert_missing_transaction_id(client):
    response = client.post("/alerts", json={"risk_score": 0.5})
    assert response.status_code == 422


def test_create_alert_missing_risk_score(client):
    tx = create_transaction(client)
    response = client.post("/alerts", json={"transaction_id": tx["id"]})
    assert response.status_code == 422


def test_create_alert_transaction_not_found(client):
    response = create_alert(client, "00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_create_alert_duplicate_transaction_returns_409(client):
    tx = create_transaction(client)
    create_alert(client, tx["id"])
    response = create_alert(client, tx["id"])
    assert response.status_code == 409


def test_create_alert_risk_score_below_zero(client):
    tx = create_transaction(client)
    response = create_alert(client, tx["id"], risk_score=-0.1)
    assert response.status_code == 422


def test_create_alert_risk_score_above_one(client):
    tx = create_transaction(client)
    response = create_alert(client, tx["id"], risk_score=1.1)
    assert response.status_code == 422


def test_create_alert_non_numeric_risk_score(client):
    tx = create_transaction(client)
    response = client.post("/alerts", json={"transaction_id": tx["id"], "risk_score": "high"})
    assert response.status_code == 422


def test_create_alert_extra_fields_rejected(client):
    tx = create_transaction(client)
    response = client.post("/alerts", json={
        "transaction_id": tx["id"],
        "risk_score": 0.5,
        "status": "confirmed_fraud",
    })
    assert response.status_code == 422


def test_create_alert_cannot_override_risk_level(client):
    tx = create_transaction(client)
    response = client.post("/alerts", json={
        "transaction_id": tx["id"],
        "risk_score": 0.5,
        "risk_level": "critical",
    })
    assert response.status_code == 422


def test_create_alert_cannot_override_created_at(client):
    tx = create_transaction(client)
    response = client.post("/alerts", json={
        "transaction_id": tx["id"],
        "risk_score": 0.5,
        "created_at": "2020-01-01T00:00:00Z",
    })
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Risk level derivation boundaries
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("score,expected_level", [
    (0.0,  "low"),
    (0.29, "low"),
    (0.3,  "medium"),
    (0.59, "medium"),
    (0.6,  "high"),
    (0.79, "high"),
    (0.8,  "critical"),
    (1.0,  "critical"),
])
def test_risk_level_boundary(client, score, expected_level):
    tx = create_transaction(client)
    data = create_alert(client, tx["id"], risk_score=score).json()
    assert data["risk_level"] == expected_level, (
        f"score={score} expected {expected_level}, got {data['risk_level']}"
    )


# ---------------------------------------------------------------------------
# GET /alerts/{id}
# ---------------------------------------------------------------------------

def test_get_alert_returns_200(client):
    tx = create_transaction(client)
    created = create_alert(client, tx["id"]).json()
    response = client.get(f"/alerts/{created['id']}")
    assert response.status_code == 200


def test_get_alert_returns_all_fields(client):
    tx = create_transaction(client)
    created = create_alert(client, tx["id"]).json()
    data = client.get(f"/alerts/{created['id']}").json()
    for field in ("id", "transaction_id", "transaction", "risk_score", "risk_level",
                  "status", "analyst_id", "contains_pii", "created_at", "updated_at",
                  "status_history"):
        assert field in data, f"Missing field: {field}"


def test_get_alert_not_found(client):
    response = client.get("/alerts/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_get_alert_matches_created(client):
    tx = create_transaction(client)
    created = create_alert(client, tx["id"], risk_score=0.65).json()
    fetched = client.get(f"/alerts/{created['id']}").json()
    assert fetched["id"] == created["id"]
    assert fetched["risk_score"] == 0.65
    assert fetched["risk_level"] == "high"
    assert fetched["transaction"]["id"] == tx["id"]
