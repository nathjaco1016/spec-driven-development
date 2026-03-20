# Feature Spec: Alert Lifecycle State Machine

## Goal
- Enforce a strict state machine governing how fraud alerts move through the analyst review pipeline, with full audit trail for every transition. This is the core business logic of the service.

## Scope
- In: Status transitions via PATCH endpoint, analyst assignment, transition validation, status_history tracking, business rules around assignment and resolution
- Out: Alert creation (see alerts spec), filtering by status (see filtering spec)

## Requirements

### Status Transitions
- Valid transitions:
  - `pending` → `under_review` (requires analyst_id to be assigned first)
  - `under_review` → `confirmed_fraud`
  - `under_review` → `false_positive`
  - `under_review` → `escalated`
- All other transitions are invalid and must be rejected with 409 Conflict
- Terminal states: `confirmed_fraud`, `false_positive` (no further transitions allowed)
- `escalated` is also terminal for the scope of this service

### Analyst Assignment
- PATCH /alerts/{id}/assign accepts `analyst_id` (string)
- Assignment is only allowed when status is `pending` or `under_review`
- Cannot assign to an alert in a terminal state (confirmed_fraud, false_positive, escalated)
- Assigning updates `updated_at`
- Re-assignment is allowed (analyst_id can be changed while alert is pending or under_review)

### Transition Rules
- PATCH /alerts/{id}/status accepts `status` (the target status) and `changed_by` (string identifier)
- Transitioning to `under_review` requires that `analyst_id` is not null (someone must own it)
- `changed_by` is recorded in the status_history entry for the transition
- Each transition appends to `status_history`: `{status: <new_status>, timestamp: <now>, changed_by: <value>}`
- `updated_at` is refreshed on every transition

### Audit Trail
- `status_history` is append-only — entries are never modified or deleted
- The full history is returned on GET /alerts/{id}
- History entries are ordered chronologically

## Acceptance Criteria

### Valid Transitions
- [x] pending → under_review succeeds when analyst_id is assigned
- [x] under_review → confirmed_fraud succeeds
- [x] under_review → false_positive succeeds
- [x] under_review → escalated succeeds
- [x] Each successful transition appends to status_history with correct status, timestamp, and changed_by

### Invalid Transitions
- [x] pending → confirmed_fraud returns 409
- [x] pending → false_positive returns 409
- [x] pending → escalated returns 409
- [x] under_review → pending returns 409
- [x] confirmed_fraud → any status returns 409
- [x] false_positive → any status returns 409
- [x] escalated → any status returns 409
- [x] pending → under_review without analyst_id assigned returns 409 (or 422)

### Analyst Assignment
- [x] Assigning analyst to a pending alert succeeds
- [x] Assigning analyst to an under_review alert succeeds (re-assignment)
- [x] Assigning analyst to a confirmed_fraud alert returns 409
- [x] Assigning analyst to a false_positive alert returns 409
- [x] Assigning analyst to an escalated alert returns 409
- [x] Assignment updates the updated_at timestamp

### Audit Trail
- [x] A newly created alert has exactly one status_history entry (pending)
- [x] After transitioning pending → under_review → confirmed_fraud, status_history has 3 entries
- [x] Status history entries are in chronological order
- [x] Each entry contains the correct changed_by value from the request
- [x] Status history is immutable — previous entries are unchanged after new transitions