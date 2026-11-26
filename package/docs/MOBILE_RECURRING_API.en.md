# Mobile API for server-managed recurring transactions

Version: 1.9.62-dev.1 · 2026-11-26 · development branch only

FieLanzen Android can retain its offline UI while accessing server-only recurring rules. No synchronization with local Android rules, finance backups or database-format changes.

## Authentication and endpoints

Base path: `/api/mobile/v1`; authenticate with `Authorization: Bearer <API-Key>`. Read keys may fetch recurring rules. Mutations require a write key, administrator/editor role, and authoritative `finance_mode=web`. Automatic posting can only be enabled by admins. `GET /capabilities` advertises `features.recurring_rules=true`.

| HTTP | Path | Purpose |
|---|---|---|
| GET | /recurring | List non-archived rules |
| POST | /recurring | Create new paused rule |
| PUT | /recurring/{id} | Edit rule and pause |
| PUT | /recurring/{id}/mode | Explicit paused/manual/auto selection |
| POST | /recurring/{id}/post | Confirm one due manual occurrence |
| DELETE | /recurring/{id} | Soft-delete without modifying posted transactions |

Example GET response:
```json
{"items":[{"id":11,"revision":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","title":"Rent","kind":"expense","account_id":1,"to_account_id":0,"category_id":2,"payee_id":0,"payee_title":"Landlord","amount_minor":95000,"note":"","frequency":"monthly","interval_count":1,"day_of_month":28,"start_on":"2026-11-01","run_at":"09:30","end_on":null,"max_occurrences":12,"completed_count":3,"next_on":"2026-11-28","mode":"manual","needs_review":""}]}
```

POST and full PUT use the read fields except `id`, `revision`, `mode`, `next_on`, `completed_count`, `needs_review`, and `payee_id`. JSON `amount_minor` is always a positive absolute value; `kind` determines the stored sign. Frequencies: daily, weekly, monthly, quarterly, yearly. Interval 1–120, day-of-month 1–31, time HH:MM.

Every mutation requires a UUID `Idempotency-Key`; existing rules also require their latest 32-character `If-Match` revision. Repeated requests with the same key and body return the stored receipt without executing again. A conflicting body or stale revision is rejected. Following a timeout, retry only with the original key; never silently use a new key for a posting. The server additionally blocks multiple manual postings for a rule on the same calendar day.

Bodies:
```json
{"mode":"manual"}
```
```json
{"confirm":"BUCHEN"}
```
```json
{"confirm_title":"Rent"}
```

Revisions are 32-character hex hashes of rule state and the completed-run count. Editing or archiving never changes historical postings, balances or the audit trail. Automatic execution remains exclusive to the existing server worker. Errors: 400 malformed input, 401 authentication, 403 authorization, 404 missing/archived rule, 409 conflict, and 428 missing revision.
