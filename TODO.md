# TODO

## Refactor Proposals
-

## New Feature Proposals
-

## In Progress

### State Machine (SPECS/state-machine.md)
- [ ] Add `AssignRequest` and `StatusUpdateRequest` Pydantic models to `src/models.py`
- [ ] Add `PATCH /alerts/{id}/assign` endpoint to `src/routes/alerts.py`
- [ ] Add `PATCH /alerts/{id}/status` endpoint to `src/routes/alerts.py` with transition validation
- [ ] Write `tests/test_state_machine.py` covering all acceptance criteria

