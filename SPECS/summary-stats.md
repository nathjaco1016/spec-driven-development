# Feature Spec: Summary Statistics

## Goal
- Provide an aggregation endpoint that gives analysts and team leads a dashboard-level view of fraud alert volume, distribution, and resolution performance.

## Scope
- In: GET /alerts/summary endpoint returning counts by status, counts by risk level, and average resolution time
- Out: Historical trend data, per-analyst performance metrics, real-time streaming updates

## Requirements

### Response Structure
- `total_alerts` — total number of alerts in the system
- `by_status` — object with counts for each status: `pending`, `under_review`, `confirmed_fraud`, `false_positive`, `escalated`
- `by_risk_level` — object with counts for each risk level: `low`, `medium`, `high`, `critical`
- `avg_resolution_time_seconds` — average time from alert creation to reaching a terminal state (confirmed_fraud, false_positive, or escalated), in seconds. Null if no alerts have been resolved.
- All counts default to 0 if no alerts match that category

### Resolution Time Calculation
- Resolution time = timestamp of terminal status transition minus `created_at`
- Only alerts in terminal states (confirmed_fraud, false_positive, escalated) are included in the average
- If no alerts are in a terminal state, `avg_resolution_time_seconds` is null (not 0)
- Resolution time is calculated from the `status_history` entries, using the timestamp of the terminal transition

## Acceptance Criteria

### Basic Stats
- [ ] GET /alerts/summary returns 200 with the correct response structure
- [ ] total_alerts matches the actual number of alerts
- [ ] by_status counts are accurate for each status category
- [ ] by_risk_level counts are accurate for each risk level category
- [ ] All status keys are present even when count is 0
- [ ] All risk_level keys are present even when count is 0

### Resolution Time
- [ ] avg_resolution_time_seconds is calculated correctly for resolved alerts
- [ ] avg_resolution_time_seconds is null when no alerts have been resolved
- [ ] Resolution time uses the terminal status_history entry timestamp minus created_at
- [ ] Average is computed across all terminal states (confirmed_fraud, false_positive, escalated)

### Edge Cases
- [ ] Summary with zero alerts returns all counts as 0 and avg_resolution_time as null
- [ ] Summary with one resolved alert returns that alert's resolution time as the average
- [ ] Summary with multiple resolved alerts returns the correct arithmetic mean
- [ ] Alerts in non-terminal states (pending, under_review) do not affect avg_resolution_time
- [ ] by_status and by_risk_level always include all possible keys regardless of data present