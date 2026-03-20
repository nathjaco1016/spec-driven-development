# Fraud Alert Validation Service

This project is essentially a REST API for storing fraud alerts, enforcing lifecycle transitions, and properly handling customer data to comply with Ally's PII sensitivity principles. 

I put everything in fraud-alert-service to keep the project separated from given spec-driven-dev environment. 

To test this, just follow the steps below and test out the interactive docs at `http://localhost:8000/docs`.

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
