# Feature Spec: PII Masking

## Goal
- Ensure PII-sensitive fields are masked by default in all API responses, reflecting Ally Financial's commitment to responsible data handling. Ally contributed a PII Masking module to LangChain's open-source ecosystem specifically because customer interactions always involve PII — this feature demonstrates awareness of that principle.

## Scope
- In: Masking card_id and account_id in API responses, an authorized access flag to reveal full values, consistent masking across all endpoints that return transaction data
- Out: Encryption at rest, role-based access control, authentication/authorization (this is a demonstration of the concept, not a production auth system)

## Requirements

### Masked Fields
- `card_id` and `account_id` are the PII-sensitive fields
- When masked, only the last 4 characters are visible, prefixed with asterisks: `****1234`
- If the value is 4 characters or fewer, mask the entire value: `****`
- Masking is applied at the API response layer — storage retains the full value

### Default Behavior
- All API responses that include transaction data mask PII fields by default
- This applies to:
  - GET /transactions/{id}
  - POST /transactions (response body)
  - GET /alerts/{id} (embedded transaction data)
  - GET /alerts (embedded transaction data in each alert)

### Authorized Access
- A query parameter `show_pii=true` reveals the unmasked values
- This simulates an authorized analyst session — in production this would be gated by role-based auth
- When `show_pii=true`, card_id and account_id are returned in full
- When `show_pii` is absent or `false`, fields are masked

### contains_pii Flag
- Each alert has a `contains_pii` boolean
- Set to `true` by default since linked transactions always contain card_id and account_id
- This flag is informational — it does not control masking behavior (masking always applies regardless)

## Acceptance Criteria

### Default Masking
- [x] GET /transactions/{id} returns card_id and account_id masked (e.g., "****5678")
- [x] POST /transactions response body returns masked PII fields
- [x] GET /alerts/{id} returns embedded transaction data with masked PII
- [x] GET /alerts list returns all embedded transaction data with masked PII
- [x] Masking shows last 4 characters: "1234567890" → "****7890"
- [x] Values with 4 or fewer characters are fully masked: "1234" → "****"

### Authorized Access
- [x] GET /transactions/{id}?show_pii=true returns full card_id and account_id
- [x] GET /alerts/{id}?show_pii=true returns full PII in embedded transaction
- [x] GET /alerts?show_pii=true returns full PII across all results
- [x] show_pii=false behaves the same as omitting the parameter (masked)

### Consistency
- [x] PII masking is applied consistently across all endpoints — no endpoint leaks unmasked data by default
- [x] Masking does not affect stored data — full values are preserved in the database
- [x] The contains_pii flag on alerts is set to true by default

### Edge Cases
- [x] Empty string card_id or account_id is masked as "****"
- [x] Very long PII values are correctly masked (only last 4 shown)
- [x] show_pii parameter with non-boolean values (e.g., "yes", "1") is handled gracefully (treat as false or return 422)