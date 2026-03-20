# Feature Spec: Alert Filtering and Listing

## Goal
- Provide a flexible query interface for listing and filtering fraud alerts, enabling analysts to efficiently triage their workload by status, risk level, assignment, and time range.

## Scope
- In: GET /alerts with query parameters for filtering and sorting
- Out: Individual alert retrieval (see alerts spec), summary aggregation (see summary-stats spec)

## Requirements

### Filter Parameters (all optional, combinable)
- `status` — filter by alert status (e.g., `?status=pending`). Accepts a single value.
- `risk_level` — filter by risk level (e.g., `?risk_level=critical`). Accepts a single value.
- `analyst_id` — filter by assigned analyst (e.g., `?analyst_id=analyst_42`). Use `unassigned` as a special value to find alerts with no analyst.
- `created_after` — ISO 8601 datetime, return alerts created on or after this time
- `created_before` — ISO 8601 datetime, return alerts created on or before this time
- When multiple filters are provided, they are combined with AND logic

### Response Format
- Returns an object with `alerts` (array) and `total` (integer)
- Results are sorted by `created_at` descending (newest first)
- Each alert in the array includes all fields (with PII masked by default)
- Empty results return `{"alerts": [], "total": 0}` — not 404

## Acceptance Criteria

### Single Filters
- [ ] GET /alerts with no filters returns all alerts
- [ ] GET /alerts?status=pending returns only pending alerts
- [ ] GET /alerts?risk_level=critical returns only critical alerts
- [ ] GET /alerts?analyst_id=analyst_1 returns only alerts assigned to analyst_1
- [ ] GET /alerts?analyst_id=unassigned returns only unassigned alerts
- [ ] GET /alerts?created_after=<datetime> returns alerts created on or after that time
- [ ] GET /alerts?created_before=<datetime> returns alerts created on or before that time

### Combined Filters
- [ ] GET /alerts?status=pending&risk_level=high returns alerts matching both conditions
- [ ] GET /alerts?status=under_review&analyst_id=analyst_1 returns correct intersection
- [ ] GET /alerts?created_after=<t1>&created_before=<t2> returns alerts within the date range

### Edge Cases
- [ ] Invalid status value returns 422
- [ ] Invalid risk_level value returns 422
- [ ] Invalid datetime format for created_after or created_before returns 422
- [ ] Filters that match zero alerts return {"alerts": [], "total": 0} with 200 status
- [ ] Date range where created_after > created_before returns empty results (not an error)
- [ ] Results are sorted by created_at descending by default