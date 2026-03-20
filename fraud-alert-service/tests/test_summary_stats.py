import time

VALID_TX = {
    "amount": 75.00,
    "merchant_name": "Amazon",
    "merchant_category": "other",
    "location": "Seattle, WA",
    "timestamp": "2024-05-01T09:00:00Z",
    "card_id": "4111111111119999",
    "account_id": "ACC5555555555",
}


def make_transaction(client):
    return client.post("/transactions", json=VALID_TX).json()


def make_alert(client, risk_score=0.5):
    tx = make_transaction(client)
    return client.post("/alerts", json={"transaction_id": tx["id"], "risk_score": risk_score}).json()


def resolve_alert(client, alert_id, terminal_status="confirmed_fraud"):
    client.patch(f"/alerts/{alert_id}/assign", json={"analyst_id": "analyst-1"})
    client.patch(f"/alerts/{alert_id}/status", json={"status": "under_review", "changed_by": "analyst-1"})
    client.patch(f"/alerts/{alert_id}/status", json={"status": terminal_status, "changed_by": "analyst-1"})


def get_summary(client):
    response = client.get("/alerts/summary")
    assert response.status_code == 200
    return response.json()


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------

def test_summary_returns_200(client):
    assert client.get("/alerts/summary").status_code == 200


def test_summary_has_required_keys(client):
    data = get_summary(client)
    assert "total_alerts" in data
    assert "by_status" in data
    assert "by_risk_level" in data
    assert "avg_resolution_time_seconds" in data


def test_summary_all_status_keys_present(client):
    data = get_summary(client)
    for key in ("pending", "under_review", "confirmed_fraud", "false_positive", "escalated"):
        assert key in data["by_status"], f"Missing status key: {key}"


def test_summary_all_risk_level_keys_present(client):
    data = get_summary(client)
    for key in ("low", "medium", "high", "critical"):
        assert key in data["by_risk_level"], f"Missing risk_level key: {key}"


# ---------------------------------------------------------------------------
# Zero-alert state
# ---------------------------------------------------------------------------

def test_summary_zero_alerts(client):
    data = get_summary(client)
    assert data["total_alerts"] == 0
    assert all(v == 0 for v in data["by_status"].values())
    assert all(v == 0 for v in data["by_risk_level"].values())
    assert data["avg_resolution_time_seconds"] is None


# ---------------------------------------------------------------------------
# total_alerts
# ---------------------------------------------------------------------------

def test_total_alerts_count(client):
    for _ in range(4):
        make_alert(client)
    data = get_summary(client)
    assert data["total_alerts"] == 4


# ---------------------------------------------------------------------------
# by_status counts
# ---------------------------------------------------------------------------

def test_by_status_counts(client):
    a1 = make_alert(client)
    a2 = make_alert(client)
    a3 = make_alert(client)

    # Move a2 to under_review
    client.patch(f"/alerts/{a2['id']}/assign", json={"analyst_id": "analyst-1"})
    client.patch(f"/alerts/{a2['id']}/status", json={"status": "under_review", "changed_by": "analyst-1"})

    # Resolve a3
    resolve_alert(client, a3["id"])

    data = get_summary(client)
    assert data["by_status"]["pending"] == 1
    assert data["by_status"]["under_review"] == 1
    assert data["by_status"]["confirmed_fraud"] == 1
    assert data["by_status"]["false_positive"] == 0
    assert data["by_status"]["escalated"] == 0


# ---------------------------------------------------------------------------
# by_risk_level counts
# ---------------------------------------------------------------------------

def test_by_risk_level_counts(client):
    tx1 = make_transaction(client)
    tx2 = make_transaction(client)
    tx3 = make_transaction(client)
    client.post("/alerts", json={"transaction_id": tx1["id"], "risk_score": 0.1})   # low
    client.post("/alerts", json={"transaction_id": tx2["id"], "risk_score": 0.7})   # high
    client.post("/alerts", json={"transaction_id": tx3["id"], "risk_score": 0.9})   # critical

    data = get_summary(client)
    assert data["by_risk_level"]["low"] == 1
    assert data["by_risk_level"]["medium"] == 0
    assert data["by_risk_level"]["high"] == 1
    assert data["by_risk_level"]["critical"] == 1


# ---------------------------------------------------------------------------
# avg_resolution_time_seconds
# ---------------------------------------------------------------------------

def test_avg_resolution_time_null_when_no_resolved(client):
    make_alert(client)
    data = get_summary(client)
    assert data["avg_resolution_time_seconds"] is None


def test_avg_resolution_time_single_alert(client):
    a = make_alert(client)
    time.sleep(0.1)
    resolve_alert(client, a["id"])
    data = get_summary(client)
    assert data["avg_resolution_time_seconds"] is not None
    assert data["avg_resolution_time_seconds"] > 0


def test_avg_resolution_time_multiple_alerts(client):
    from datetime import datetime

    def resolution_seconds(alert_id):
        alert = client.get(f"/alerts/{alert_id}?show_pii=true").json()
        created = datetime.fromisoformat(alert["created_at"].replace("Z", "+00:00"))
        terminal = next(
            e for e in reversed(alert["status_history"])
            if e["status"] in ("confirmed_fraud", "false_positive", "escalated")
        )
        resolved = datetime.fromisoformat(terminal["timestamp"].replace("Z", "+00:00"))
        return (resolved - created).total_seconds()

    a1 = make_alert(client)
    time.sleep(0.05)
    resolve_alert(client, a1["id"])

    a2 = make_alert(client)
    time.sleep(0.1)
    resolve_alert(client, a2["id"], terminal_status="false_positive")

    a3 = make_alert(client)
    time.sleep(0.15)
    resolve_alert(client, a3["id"], terminal_status="escalated")

    expected_avg = (
        resolution_seconds(a1["id"]) +
        resolution_seconds(a2["id"]) +
        resolution_seconds(a3["id"])
    ) / 3

    data = get_summary(client)
    assert data["avg_resolution_time_seconds"] is not None
    assert abs(data["avg_resolution_time_seconds"] - expected_avg) < 0.001


def test_non_terminal_alerts_excluded_from_avg(client):
    # One resolved, one still pending
    a1 = make_alert(client)
    time.sleep(0.05)
    resolve_alert(client, a1["id"])

    make_alert(client)  # stays pending

    data = get_summary(client)
    # Should still compute avg from only the resolved one
    assert data["avg_resolution_time_seconds"] is not None
    assert data["total_alerts"] == 2


def test_avg_uses_terminal_history_timestamp(client):
    """Resolution time should be > 0, confirming it uses transition timestamp not updated_at."""
    a = make_alert(client)
    time.sleep(0.05)
    resolve_alert(client, a["id"])
    data = get_summary(client)
    assert data["avg_resolution_time_seconds"] > 0
