import pytest

VALID_TRANSACTION = {
    "amount": 199.99,
    "merchant_name": "Delta Airlines",
    "merchant_category": "travel",
    "location": "Atlanta, GA",
    "timestamp": "2024-02-01T08:00:00Z",
    "card_id": "4111111111115678",
    "account_id": "ACC1234567890",
}


def create_transaction(client):
    return client.post("/transactions", json=VALID_TRANSACTION).json()


def create_alert(client, risk_score=0.75):
    tx = create_transaction(client)
    return client.post("/alerts", json={"transaction_id": tx["id"], "risk_score": risk_score}).json()


def assign(client, alert_id, analyst_id="analyst-1"):
    return client.patch(f"/alerts/{alert_id}/assign", json={"analyst_id": analyst_id})


def transition(client, alert_id, status, changed_by="analyst-1"):
    return client.patch(f"/alerts/{alert_id}/status", json={"status": status, "changed_by": changed_by})


# ---------------------------------------------------------------------------
# Valid transitions
# ---------------------------------------------------------------------------

def test_pending_to_under_review(client):
    alert = create_alert(client)
    assign(client, alert["id"])
    response = transition(client, alert["id"], "under_review")
    assert response.status_code == 200
    assert response.json()["status"] == "under_review"


def test_under_review_to_confirmed_fraud(client):
    alert = create_alert(client)
    assign(client, alert["id"])
    transition(client, alert["id"], "under_review")
    response = transition(client, alert["id"], "confirmed_fraud")
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed_fraud"


def test_under_review_to_false_positive(client):
    alert = create_alert(client)
    assign(client, alert["id"])
    transition(client, alert["id"], "under_review")
    response = transition(client, alert["id"], "false_positive")
    assert response.status_code == 200
    assert response.json()["status"] == "false_positive"


def test_under_review_to_escalated(client):
    alert = create_alert(client)
    assign(client, alert["id"])
    transition(client, alert["id"], "under_review")
    response = transition(client, alert["id"], "escalated")
    assert response.status_code == 200
    assert response.json()["status"] == "escalated"


def test_transition_appends_status_history(client):
    alert = create_alert(client)
    assign(client, alert["id"])
    data = transition(client, alert["id"], "under_review", changed_by="reviewer-99").json()
    assert len(data["status_history"]) == 2
    assert data["status_history"][1]["status"] == "under_review"
    assert data["status_history"][1]["changed_by"] == "reviewer-99"
    assert "timestamp" in data["status_history"][1]


# ---------------------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("target", ["confirmed_fraud", "false_positive", "escalated"])
def test_pending_to_terminal_returns_409(client, target):
    alert = create_alert(client)
    response = transition(client, alert["id"], target)
    assert response.status_code == 409


def test_pending_to_under_review_without_analyst_returns_409(client):
    alert = create_alert(client)
    response = transition(client, alert["id"], "under_review")
    assert response.status_code == 409


def test_under_review_to_pending_returns_409(client):
    alert = create_alert(client)
    assign(client, alert["id"])
    transition(client, alert["id"], "under_review")
    response = transition(client, alert["id"], "pending")
    assert response.status_code == 409


@pytest.mark.parametrize("target", ["pending", "under_review", "false_positive", "escalated"])
def test_confirmed_fraud_to_any_returns_409(client, target):
    alert = create_alert(client)
    assign(client, alert["id"])
    transition(client, alert["id"], "under_review")
    transition(client, alert["id"], "confirmed_fraud")
    response = transition(client, alert["id"], target)
    assert response.status_code == 409


@pytest.mark.parametrize("target", ["pending", "under_review", "confirmed_fraud", "escalated"])
def test_false_positive_to_any_returns_409(client, target):
    alert = create_alert(client)
    assign(client, alert["id"])
    transition(client, alert["id"], "under_review")
    transition(client, alert["id"], "false_positive")
    response = transition(client, alert["id"], target)
    assert response.status_code == 409


@pytest.mark.parametrize("target", ["pending", "under_review", "confirmed_fraud", "false_positive"])
def test_escalated_to_any_returns_409(client, target):
    alert = create_alert(client)
    assign(client, alert["id"])
    transition(client, alert["id"], "under_review")
    transition(client, alert["id"], "escalated")
    response = transition(client, alert["id"], target)
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Analyst assignment
# ---------------------------------------------------------------------------

def test_assign_to_pending_alert_succeeds(client):
    alert = create_alert(client)
    response = assign(client, alert["id"], "analyst-42")
    assert response.status_code == 200
    assert response.json()["analyst_id"] == "analyst-42"


def test_assign_to_under_review_alert_succeeds(client):
    alert = create_alert(client)
    assign(client, alert["id"])
    transition(client, alert["id"], "under_review")
    response = assign(client, alert["id"], "analyst-99")
    assert response.status_code == 200
    assert response.json()["analyst_id"] == "analyst-99"


def test_assign_to_confirmed_fraud_returns_409(client):
    alert = create_alert(client)
    assign(client, alert["id"])
    transition(client, alert["id"], "under_review")
    transition(client, alert["id"], "confirmed_fraud")
    response = assign(client, alert["id"], "analyst-99")
    assert response.status_code == 409


def test_assign_to_false_positive_returns_409(client):
    alert = create_alert(client)
    assign(client, alert["id"])
    transition(client, alert["id"], "under_review")
    transition(client, alert["id"], "false_positive")
    response = assign(client, alert["id"], "analyst-99")
    assert response.status_code == 409


def test_assign_to_escalated_returns_409(client):
    alert = create_alert(client)
    assign(client, alert["id"])
    transition(client, alert["id"], "under_review")
    transition(client, alert["id"], "escalated")
    response = assign(client, alert["id"], "analyst-99")
    assert response.status_code == 409


def test_assign_updates_updated_at(client):
    import time
    alert = create_alert(client)
    original_updated_at = alert["updated_at"]
    time.sleep(0.01)
    data = assign(client, alert["id"]).json()
    assert data["updated_at"] != original_updated_at


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

def test_new_alert_has_one_history_entry(client):
    alert = create_alert(client)
    assert len(alert["status_history"]) == 1
    assert alert["status_history"][0]["status"] == "pending"


def test_full_workflow_history_has_three_entries(client):
    alert = create_alert(client)
    assign(client, alert["id"])
    transition(client, alert["id"], "under_review", changed_by="analyst-1")
    data = transition(client, alert["id"], "confirmed_fraud", changed_by="analyst-1").json()
    assert len(data["status_history"]) == 3
    assert data["status_history"][0]["status"] == "pending"
    assert data["status_history"][1]["status"] == "under_review"
    assert data["status_history"][2]["status"] == "confirmed_fraud"


def test_history_is_chronological(client):
    alert = create_alert(client)
    assign(client, alert["id"])
    transition(client, alert["id"], "under_review")
    data = transition(client, alert["id"], "confirmed_fraud").json()
    timestamps = [e["timestamp"] for e in data["status_history"]]
    assert timestamps == sorted(timestamps)


def test_history_records_changed_by(client):
    alert = create_alert(client)
    assign(client, alert["id"])
    data = transition(client, alert["id"], "under_review", changed_by="supervisor-7").json()
    assert data["status_history"][1]["changed_by"] == "supervisor-7"


def test_previous_history_entries_unchanged(client):
    alert = create_alert(client)
    assign(client, alert["id"])
    transition(client, alert["id"], "under_review", changed_by="analyst-1")
    data = transition(client, alert["id"], "confirmed_fraud", changed_by="analyst-1").json()
    # First entry must still be the original pending/system entry
    assert data["status_history"][0]["status"] == "pending"
    assert data["status_history"][0]["changed_by"] == "system"
