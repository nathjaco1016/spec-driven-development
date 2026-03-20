# TODO

## Refactor Proposals
-

## New Feature Proposals
-

## In Progress

### PII Masking (SPECS/pii-masking.md)
- [ ] Add `mask_pii` utility function to `src/pii.py`
- [ ] Apply masking to `POST /transactions` and `GET /transactions/{id}` responses (with `show_pii` query param)
- [ ] Apply masking to `GET /alerts/{id}` embedded transaction (with `show_pii` query param)
- [ ] Write `tests/test_pii_masking.py` covering all acceptance criteria
- NOTE: `GET /alerts` (list) masking deferred until filtering spec is implemented


