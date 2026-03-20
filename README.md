# Fraud Alert Validation Service

This project is essentially a REST API for storing fraud alerts, enforcing lifecycle transitions, and properly handling customer data to comply with Ally's PII sensitivity principles. 

I put everything in fraud-alert-service to keep the project separated from given spec-driven-dev environment. 

To test this, just follow the steps below and test out the interactive docs at `http://localhost:8000/docs`.

## Tech Stack

- **FastAPI** — REST framework with automatic OpenAPI/Swagger docs
- **Pydantic v2** — request validation and response serialization
- **SQLite** — lightweight persistent storage via Python's built-in `sqlite3`
- **pytest** + **httpx** — integration tests using `TestClient` with per-test isolated databases

## Setup

```bash
cd fraud-alert-service
pip install -r requirements.txt
```

## Run

```bash
uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Test

```bash
python -m pytest tests/ -v
```

## API Overview

- POST | `/transactions` | Create a transaction
- GET | `/transactions/{id}` | Get a transaction by ID
- POST | `/alerts` | Create an alert for a transaction
- GET | `/alerts` | List and filter alerts
- GET | `/alerts/summary` | Aggregated stats by status, risk level, and resolution time
- GET | `/alerts/{id}` | Get a single alert
- PATCH | `/alerts/{id}/assign` | Assign an analyst to an alert
- PATCH | `/alerts/{id}/status` | Transition alert status

## PII Masking

`card_id` and `account_id` are masked by default in all responses (e.g. `****1234`). Append `?show_pii=true` to any endpoint to reveal full values.

## Test Coverage

142 tests across 6 test files, each corresponding to a spec:

- `test_transactions.py` | 23 | Transaction creation, validation, field storage
- `test_alerts.py` | 30 | Alert creation, risk level derivation, boundary values
- `test_state_machine.py` | 33 | Status transitions, analyst assignment, audit trail
- `test_pii_masking.py` | 22 | Masking behavior, `show_pii` parameter, edge cases
- `test_filtering.py` | 21 | Filter parameters, combined filters, sort order
- `test_summary_stats.py` | 13 | Counts by status/risk level, resolution time calculation

Each test uses an isolated SQLite database via `tmp_path`, so tests are fully independent and leave no state behind.

## Spec Driven Dev

I have experience with spec driven development, so I essentially just used my standard workflow where I broke down my project into specs and wrote these out myself, used Claude to review these and enhance them if necessary (it's good at finding edge cases and such that I may have missed), then I added actionable TODO tasks before implementation. 

## Code Generation Tools Used

I used Claude as my primary code generation tool. 


