# Feature Spec: Alerts

## Goal
- Provide endpoints for creating and retrieving fraud alerts that wrap a flagged transaction with risk assessment data and lifecycle tracking.

## Scope
- In: Creating alerts linked to transactions, retrieving alerts by ID, risk score validation, automatic risk level derivation, timestamp generation
- Out: Alert status transitions (see state-machine spec), alert filtering/listing (see filtering spec), summary statistics (see summary-stats spec)

## Requirements
- Each alert must have a unique `id` (UUID, server-generated)
- Required fields on creation: `transaction_id`, `risk_score`
- `transaction_id` must reference an existing transaction
- A transaction can only have one alert (no duplicate alerts for the same transaction)
- `risk_score` must be a float between 0.0 and 1.0 inclusive
- `risk_level` is automatically derived from `risk_score` — never provided by the client:
  - `low`: 0.0 <= score < 0.3
  - `medium`: 0.3 <= score < 0.6
  - `high`: 0.6 <= score < 0.8
  - `critical`: 0.8 <= score <= 1.0
- `status` is initialized to `pending` on creation
- `analyst_id` is null on creation
- `contains_pii` is set to `true` by default (since the linked transaction contains card_id and account_id)
- `created_at` is server-generated at creation time
- `updated_at` is server-generated and updated on any modification
- `status_history` is initialized with one entry: `{status: "pending", timestamp: <created_at>, changed_by: "system"}`
- GET response returns the alert with its linked transaction's PII fields masked by default

## Acceptance Criteria
- [ ] POST /alerts creates an alert and returns it with generated UUID, pending status, and derived risk_level
- [ ] POST /alerts returns 422 for missing transaction_id or risk_score
- [ ] POST /alerts returns 404 if transaction_id does not reference an existing transaction
- [ ] POST /alerts returns 409 if an alert already exists for the given transaction_id
- [ ] POST /alerts returns 422 for risk_score < 0.0
- [ ] POST /alerts returns 422 for risk_score > 1.0
- [ ] POST /alerts returns 422 for non-numeric risk_score
- [ ] Risk level is correctly derived at boundary: score 0.0 → low
- [ ] Risk level is correctly derived at boundary: score 0.29 → low
- [ ] Risk level is correctly derived at boundary: score 0.3 → medium
- [ ] Risk level is correctly derived at boundary: score 0.59 → medium
- [ ] Risk level is correctly derived at boundary: score 0.6 → high
- [ ] Risk level is correctly derived at boundary: score 0.79 → high
- [ ] Risk level is correctly derived at boundary: score 0.8 → critical
- [ ] Risk level is correctly derived at boundary: score 1.0 → critical
- [ ] Alert is created with status "pending" and a single status_history entry
- [ ] GET /alerts/{id} returns the alert with all fields populated
- [ ] GET /alerts/{id} returns 404 for nonexistent alert ID
- [ ] Client cannot override risk_level, status, or created_at on creation