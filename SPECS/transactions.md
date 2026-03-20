# Feature Spec: Transactions

## Goal
- Provide CRUD endpoints for transaction records that represent raw financial transaction data flagged upstream by Ally's fraud detection AI.

## Scope
- In: Creating transactions, retrieving transactions by ID, field validation, PII-sensitive field storage
- Out: Updating or deleting transactions (transactions are immutable records of what occurred), bulk import, transaction search/listing (transactions are accessed individually or via their linked alerts)

## Requirements
- Each transaction must have a unique `id` (UUID, server-generated)
- Required fields on creation: `amount`, `merchant_name`, `merchant_category`, `location`, `timestamp`, `card_id`, `account_id`
- `amount` must be a positive number greater than 0
- `merchant_category` must be one of a defined enum: `electronics`, `travel`, `groceries`, `gas_station`, `restaurant`, `entertainment`, `healthcare`, `utilities`, `cash_advance`, `other`
- `location` is a string (e.g., "Charlotte, NC")
- `timestamp` must be a valid ISO 8601 datetime string
- `card_id` and `account_id` are stored in full but treated as PII-sensitive (see pii-masking spec)
- Transactions are immutable after creation, so no update or delete endpoints
- GET response returns the transaction with PII fields masked by default

## Acceptance Criteria
- [ ] POST /transactions creates a transaction and returns it with a generated UUID
- [ ] POST /transactions returns 422 for missing required fields
- [ ] POST /transactions returns 422 for amount <= 0
- [ ] POST /transactions returns 422 for invalid merchant_category
- [ ] POST /transactions returns 422 for invalid timestamp format
- [ ] GET /transactions/{id} returns the transaction with PII fields masked
- [ ] GET /transactions/{id} returns 404 for nonexistent ID
- [ ] POST /transactions accepts and stores all valid merchant_category values
- [ ] Response includes server-generated `id` that was not provided in the request body
- [ ] Extra/unknown fields in the request body are ignored or rejected (pick one, document it)