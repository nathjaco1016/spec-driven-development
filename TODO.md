# TODO

## Refactor Proposals
-

## New Feature Proposals
-

## In Progress

### Alerts (SPECS/alerts.md)
- [ ] Add Alert + StatusHistoryEntry Pydantic models to `src/models.py`
- [ ] Add `alerts` table to `src/database.py` (with `status_history` stored as JSON)
- [ ] Add `src/routes/alerts.py` with `POST /alerts` and `GET /alerts/{id}`
- [ ] Register alerts router in `src/main.py`
- [ ] Write tests covering all acceptance criteria in `tests/test_alerts.py`