import time

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TX_BASE = {
    "amount": 150.00,
    "merchant_name": "Test Merchant",
    "merchant_category": "electronics",
    "location": "Charlotte, NC",
    "timestamp": "2024-04-01T10:00:00Z",
    "card_id": "4111111111111234",
    "account_id": "ACC0000000001",
}


def make_transaction(client, **overrides):
    return client.post("/transactions", json={**TX_BASE, **overrides}).json()


def make_alert(client, transaction_id, risk_score=0.5):
    return client.post("/alerts", json={"transaction_id": transaction_id, "risk_score": risk_score}).json()


def assign(client, alert_id, analyst_id="analyst-1"):
    return client.patch(f"/alerts/{alert_id}/assign", json={"analyst_id": analyst_id}).json()


def transition(client, alert_id, status, changed_by="analyst-1"):
    return client.patch(f"/alerts/{alert_id}/status", json={"status": status, "changed_by": changed_by}).json()


# ---------------------------------------------------------------------------
# No filters — returns all alerts
# ---------------------------------------------------------------------------

def test_list_alerts_no_filters_returns_all(client):
    for _ in range(3):
        tx = make_transaction(client)
        make_alert(client, tx["id"])
    response = client.get("/alerts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["alerts"]) == 3


def test_list_alerts_empty_returns_200(client):
    response = client.get("/alerts")
    assert response.status_code == 200
    assert response.json() == {"alerts": [], "total": 0}


# ---------------------------------------------------------------------------
# Single filters
# ---------------------------------------------------------------------------

def test_filter_by_status_pending(client):
    tx1 = make_transaction(client)
    tx2 = make_transaction(client)
    a1 = make_alert(client, tx1["id"])
    a2 = make_alert(client, tx2["id"])
    # Move a2 to under_review
    assign(client, a2["id"])
    transition(client, a2["id"], "under_review")

    data = client.get("/alerts?status=pending").json()
    assert data["total"] == 1
    assert data["alerts"][0]["id"] == a1["id"]


def test_filter_by_status_under_review(client):
    tx1 = make_transaction(client)
    tx2 = make_transaction(client)
    make_alert(client, tx1["id"])
    a2 = make_alert(client, tx2["id"])
    assign(client, a2["id"])
    transition(client, a2["id"], "under_review")

    data = client.get("/alerts?status=under_review").json()
    assert data["total"] == 1
    assert data["alerts"][0]["id"] == a2["id"]


def test_filter_by_risk_level_critical(client):
    tx1 = make_transaction(client)
    tx2 = make_transaction(client)
    make_alert(client, tx1["id"], risk_score=0.9)   # critical
    make_alert(client, tx2["id"], risk_score=0.3)   # medium

    data = client.get("/alerts?risk_level=critical").json()
    assert data["total"] == 1
    assert data["alerts"][0]["risk_level"] == "critical"


def test_filter_by_analyst_id(client):
    tx1 = make_transaction(client)
    tx2 = make_transaction(client)
    a1 = make_alert(client, tx1["id"])
    a2 = make_alert(client, tx2["id"])
    assign(client, a1["id"], "analyst-42")
    assign(client, a2["id"], "analyst-99")

    data = client.get("/alerts?analyst_id=analyst-42").json()
    assert data["total"] == 1
    assert data["alerts"][0]["analyst_id"] == "analyst-42"


def test_filter_by_analyst_id_unassigned(client):
    tx1 = make_transaction(client)
    tx2 = make_transaction(client)
    a1 = make_alert(client, tx1["id"])
    a2 = make_alert(client, tx2["id"])
    assign(client, a2["id"], "analyst-1")

    data = client.get("/alerts?analyst_id=unassigned").json()
    assert data["total"] == 1
    assert data["alerts"][0]["id"] == a1["id"]


def test_filter_by_created_after(client):
    tx1 = make_transaction(client)
    a1 = make_alert(client, tx1["id"])
    after_ts = a1["created_at"]

    time.sleep(0.05)

    tx2 = make_transaction(client)
    a2 = make_alert(client, tx2["id"])

    data = client.get(f"/alerts?created_after={after_ts}").json()
    ids = [a["id"] for a in data["alerts"]]
    assert a2["id"] in ids
    assert a1["id"] in ids  # created_at >= boundary is inclusive


def test_filter_by_created_before(client):
    tx1 = make_transaction(client)
    a1 = make_alert(client, tx1["id"])
    before_ts = a1["created_at"]

    time.sleep(0.05)

    tx2 = make_transaction(client)
    make_alert(client, tx2["id"])

    data = client.get(f"/alerts?created_before={before_ts}").json()
    ids = [a["id"] for a in data["alerts"]]
    assert a1["id"] in ids
    assert len(ids) == 1


# ---------------------------------------------------------------------------
# Combined filters
# ---------------------------------------------------------------------------

def test_combined_status_and_risk_level(client):
    tx1 = make_transaction(client)
    tx2 = make_transaction(client)
    tx3 = make_transaction(client)
    a1 = make_alert(client, tx1["id"], risk_score=0.9)   # critical, pending
    a2 = make_alert(client, tx2["id"], risk_score=0.9)   # critical, under_review
    make_alert(client, tx3["id"], risk_score=0.3)         # medium, pending

    assign(client, a2["id"])
    transition(client, a2["id"], "under_review")

    data = client.get("/alerts?status=pending&risk_level=critical").json()
    assert data["total"] == 1
    assert data["alerts"][0]["id"] == a1["id"]


def test_combined_status_and_analyst_id(client):
    tx1 = make_transaction(client)
    tx2 = make_transaction(client)
    a1 = make_alert(client, tx1["id"])
    a2 = make_alert(client, tx2["id"])
    assign(client, a1["id"], "analyst-1")
    assign(client, a2["id"], "analyst-1")
    transition(client, a1["id"], "under_review")

    data = client.get("/alerts?status=under_review&analyst_id=analyst-1").json()
    assert data["total"] == 1
    assert data["alerts"][0]["id"] == a1["id"]


def test_combined_date_range(client):
    tx1 = make_transaction(client)
    a1 = make_alert(client, tx1["id"])
    time.sleep(0.05)
    tx2 = make_transaction(client)
    a2 = make_alert(client, tx2["id"])
    time.sleep(0.05)
    tx3 = make_transaction(client)
    make_alert(client, tx3["id"])

    after = a1["created_at"]
    before = a2["created_at"]
    data = client.get(f"/alerts?created_after={after}&created_before={before}").json()
    ids = [a["id"] for a in data["alerts"]]
    assert a1["id"] in ids
    assert a2["id"] in ids


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_invalid_status_returns_422(client):
    response = client.get("/alerts?status=not_a_status")
    assert response.status_code == 422


def test_invalid_risk_level_returns_422(client):
    response = client.get("/alerts?risk_level=extreme")
    assert response.status_code == 422


def test_invalid_created_after_returns_422(client):
    response = client.get("/alerts?created_after=not-a-date")
    assert response.status_code == 422


def test_invalid_created_before_returns_422(client):
    response = client.get("/alerts?created_before=not-a-date")
    assert response.status_code == 422


def test_filters_matching_zero_returns_empty(client):
    tx = make_transaction(client)
    make_alert(client, tx["id"])
    data = client.get("/alerts?status=confirmed_fraud").json()
    assert data == {"alerts": [], "total": 0}


def test_created_after_greater_than_before_returns_empty(client):
    tx = make_transaction(client)
    a = make_alert(client, tx["id"])
    data = client.get(f"/alerts?created_after={a['created_at']}&created_before=2020-01-01T00:00:00Z").json()
    assert data == {"alerts": [], "total": 0}


def test_results_sorted_by_created_at_descending(client):
    for _ in range(3):
        tx = make_transaction(client)
        make_alert(client, tx["id"])
        time.sleep(0.02)

    data = client.get("/alerts").json()
    timestamps = [a["created_at"] for a in data["alerts"]]
    assert timestamps == sorted(timestamps, reverse=True)


# ---------------------------------------------------------------------------
# PII masking on list endpoint
# ---------------------------------------------------------------------------

def test_list_alerts_masks_pii_by_default(client):
    tx = make_transaction(client)
    make_alert(client, tx["id"])
    data = client.get("/alerts").json()
    alert = data["alerts"][0]
    assert alert["transaction"]["card_id"] == "****1234"
    assert alert["transaction"]["account_id"] == "****0001"


def test_list_alerts_show_pii_true_reveals_values(client):
    tx = make_transaction(client)
    make_alert(client, tx["id"])
    data = client.get("/alerts?show_pii=true").json()
    alert = data["alerts"][0]
    assert alert["transaction"]["card_id"] == TX_BASE["card_id"]
    assert alert["transaction"]["account_id"] == TX_BASE["account_id"]
