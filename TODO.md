# TODO

## Refactor Proposals
-

## New Feature Proposals
-

## In Progress

### Filtering (SPECS/filtering.md)
- [ ] Add `AlertListResponse` Pydantic model (`alerts` array + `total`) to `src/models.py`
- [ ] Implement `GET /alerts` in `src/routes/alerts.py` with all filter params and `show_pii` support
- [ ] Write `tests/test_filtering.py` covering all acceptance criteria
- NOTE: Apply `show_pii` masking to list results (deferred from PII masking spec)



